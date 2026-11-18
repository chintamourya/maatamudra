from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app import deps
from app.contracts.compiler import compile_contract
from app.contracts.intake import extract
from app.db import Repo
from app.extras import build_ics, fingerprint
from app.main import app
from app.models import Spec
from app.types import REGISTRY
from app.types import employment as emp
from app.types import freelance as fl
from tests.test_api import StubLLM
from tests.test_verifier import FakeKanoon

A = TypeAdapter(Spec)


def sample(key):
    return A.validate_python(REGISTRY[key].sample)


@pytest.mark.parametrize("key", list(REGISTRY))
def test_every_type_compiles_lints_and_exports(key):
    spec = sample(key)
    c = compile_contract(spec)
    assert len(c.clauses) >= 8 and c.obligations
    assert all(f["severity"] in ("low", "medium", "high") for f in REGISTRY[key].lint(spec))
    assert REGISTRY[key].key_dates(spec)
    assert "BEGIN:VEVENT" in build_ics(c, REGISTRY[key].key_dates(spec))


def test_fingerprint_changes_when_a_term_changes():
    spec = sample("freelance_service")
    a = fingerprint(compile_contract(spec))
    b = fingerprint(compile_contract(spec.model_copy(update={"total_fee": 130000})))
    assert a != b and a == fingerprint(compile_contract(spec))


def test_contract_requires_explicit_state():
    spec = sample("rental_agreement").model_copy(update={"state": None})
    with pytest.raises(ValueError, match="state"):
        compile_contract(spec)


@pytest.mark.asyncio
async def test_intake_does_not_assume_a_default_state():
    class EmptyIntake:
        async def structured(self, system, user, schema):
            return schema()

    spec = sample("rental_agreement").model_copy(update={"state": None})
    result = await extract(EmptyIntake(), "Prepare a rental agreement.", spec)
    assert result.state is None
    assert "state" in REGISTRY["rental_agreement"].missing(result)


@pytest.mark.parametrize("key", ["nda", "sale_purchase", "partnership", "private_loan", "ip_licence", "mou"])
def test_common_agreement_types_require_an_explicit_state(key):
    spec = sample(key).model_copy(update={"state": None})
    with pytest.raises(ValueError, match="state"):
        compile_contract(spec)


def test_private_loan_and_mou_reject_contradictory_dates_or_intent():
    loan = sample("private_loan").model_copy(update={"final_due_date": date(2026, 11, 30)})
    with pytest.raises(ValueError, match="before the loan disbursement"):
        compile_contract(loan)

    mou = sample("mou").model_copy(update={
        "binding_status": "selected_terms_binding",
        "binding_terms": "None",
    })
    with pytest.raises(ValueError, match="needs at least one binding term"):
        compile_contract(mou)


def test_freelance_non_compete_flagged_and_evidence_queries_present():
    c = compile_contract(sample("freelance_service"))
    nc = next(x for x in c.clauses if x.key == "non_compete")
    assert nc.risk == "high" and "contract_act_s27" in nc.legal_basis and nc.evidence_queries
    assert any(f["clause_key"] == "non_compete" for f in REGISTRY["freelance_service"].lint(sample("freelance_service")))


def test_freelance_optional_terms_omitted():
    s = sample("freelance_service").model_copy(update={"non_compete_months": None, "advance_percent": 0, "liability_cap_multiple": None})
    keys = [x.key for x in compile_contract(s).clauses]
    assert "non_compete" not in keys and "advance" not in keys and "liability" not in keys


def test_freelance_late_interest_and_no_mechanism():
    s = sample("freelance_service")
    r = fl.late_payment(s, date(2027, 1, 15), 30)
    assert r["invoice_amount"] == 84000 and r["late_interest"] == round(84000 * 2 / 100)  # 30 days = 1 month
    none = s.model_copy(update={"late_interest_pct_per_month": None})
    assert fl.late_payment(none, date(2027, 1, 15), 30)["late_interest"] is None


def test_freelance_termination_math_and_ip():
    s = sample("freelance_service")
    r = fl.termination(s, "client", date(2027, 1, 10), 40)
    # work 48000, advance 36000, kill fee 20% of remaining 72000 = 14400 -> 12000 + 14400
    assert r["work_fee"] == 48000 and r["advance_paid"] == 36000 and r["kill_fee"] == 14400
    assert r["net_payable_to_freelancer"] == 26400
    assert fl.ip_status(s, False)["owner"] == "freelancer" and fl.ip_status(s, True)["owner"] == "client"
    assert fl.termination(s, "freelancer", date(2027, 1, 10), 40)["kill_fee"] == 0
    with pytest.raises(ValueError):
        fl.termination(s, "client", date(2027, 1, 10), 140)


def test_employment_probation_notice_and_bond():
    s = sample("employment")
    r = emp.resignation(s, date(2027, 2, 1))  # inside 6-month probation from Dec 15
    assert r["notice_days_applied"] == 15
    r2 = emp.resignation(s, date(2027, 8, 1))
    assert r2["notice_days_applied"] == 60 and r2["salary_for_notice_period"] == 170000
    b = emp.bond_exit(s, date(2027, 6, 30))
    assert b["claimable_under_contract"] == 150000 and b["bond_end"] == "2028-06-15"
    assert emp.bond_exit(s, date(2028, 7, 1))["claimable_under_contract"] == 0
    pr = s.model_copy(update={"bond_pro_rata": True})
    assert 0 < emp.bond_exit(pr, date(2027, 6, 30))["claimable_under_contract"] < 150000


def test_employment_flat_bond_and_non_compete_linted():
    msgs = " ".join(f["message"] for f in REGISTRY["employment"].lint(sample("employment")))
    assert "Section 27" in msgs and "Section 74" in msgs


@pytest.fixture
def client():
    deps.services = deps.Services(llm=StubLLM(), repo=Repo(), kanoon=FakeKanoon())
    return TestClient(app)


def test_types_endpoint_and_multi_type_flow(client):
    t = client.get("/api/types").json()
    assert {x["key"] for x in t} == set(REGISTRY)
    for x in t:
        cid = client.post("/api/contracts", json=x["sample"]).json()["id"]
        assert client.get(f"/api/contracts/{cid}/lint").status_code == 200
        ob = client.get(f"/api/contracts/{cid}/obligations").json()
        assert len(ob["fingerprint"]) == 64 and ob["obligations"] and ob["key_dates"]
        assert client.get(f"/api/contracts/{cid}/calendar.ics").text.startswith("BEGIN:VCALENDAR")
        assert client.get(f"/api/contracts/{cid}/docx").content[:2] == b"PK"
        assert client.get(f"/api/contracts/{cid}/execution").json()["supported"]
        for sc in x["scenarios"]:  # every UI scenario must run with its own defaults
            body = {"type": sc["type"], **sc.get("fixed", {}),
                    **{i["name"]: (i["default"] == "yes" if i["name"] == "fully_paid" else i["default"]) for i in sc["inputs"]}}
            assert client.post(f"/api/contracts/{cid}/simulate", json=body).status_code == 200, sc["type"]


def test_review_uses_party_labels(client):
    cid = client.post("/api/contracts", json=REGISTRY["employment"].sample).json()["id"]
    c = client.post(f"/api/contracts/{cid}/review").json()
    assert c["redlines"] and "risk_to_party_a" in c["redlines"][0]
