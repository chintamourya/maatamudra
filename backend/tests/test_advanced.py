import base64
import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app import deps
from app.agent import ask, verify_answer
from app.analysis.consistency import check, errors
from app.contracts.compiler import compile_contract
from app.db import Repo
from app.explain import Explanation, Item, explain
from app.legal import verifier as v
from app.main import app
from app.models import Spec
from app.obligations.sweep import consequence_map
from app.textutil import norm_digits, numbers
from app.types import REGISTRY
from app.upload_review import (Label, Labels, TypeGuess, build_contract, extract_text, gap_analysis, segment)
from tests.test_api import StubLLM
from tests.test_verifier import FakeKanoon, FakeLLM, PASSAGE

A = TypeAdapter(Spec)


def sample(k):
    return A.validate_python(REGISTRY[k].sample)


# ---- consistency --------------------------------------------------------
def test_lock_in_longer_than_term_blocks_drafting(spec):
    bad = spec.model_copy(update={"lock_in_months": 12})
    assert errors(bad)
    with pytest.raises(ValueError, match="contradict"):
        compile_contract(bad)


def test_freelance_delivery_before_start_is_error():
    s = sample("freelance_service")
    assert errors(s.model_copy(update={"delivery_date": s.start_date.replace(year=s.start_date.year - 1)}))


def test_partial_optional_pairs_warn_not_block(spec):
    s = spec.model_copy(update={"late_fee_per_day": None})
    f = check(s)
    assert any("left out" in x["message"] for x in f) and not errors(s)
    compile_contract(s)


def test_samples_have_no_blocking_errors():
    for k in REGISTRY:
        assert not errors(sample(k)), k


# ---- consequence map ----------------------------------------------------
def test_rental_map_finds_dead_zone_and_cliff(spec):
    m = consequence_map(spec)
    labels = [z["label"] for z in m["zones"]]
    assert labels == ["No consequence yet", "Late fee accrues, no default route yet", "Default notice possible"]
    assert m["zones"][1] == {"from": 6, "to": 29, "label": labels[1]}
    assert any("Cliff at day 30" in f for f in m["findings"])
    assert any("At 30 days late the fee totals ₹1,250" in f for f in m["findings"])  # (30-5) x 50


def test_rental_map_without_mechanisms(spec):
    s = spec.model_copy(update={"grace_days": None, "late_fee_per_day": None, "default_threshold_days": None, "cure_days": None})
    assert consequence_map(s)["zones"][0]["label"] == "No consequence defined"


def test_employment_flat_bond_has_cliff_and_prorata_does_not_claim_cliff():
    s = sample("employment")
    m = consequence_map(s)
    assert any("Cliff" in f for f in m["findings"]) and m["zones"][-1]["label"] == "Bond has ended"
    pr = consequence_map(s.model_copy(update={"bond_pro_rata": True}))
    assert not any("Cliff" in f for f in pr["findings"])
    assert consequence_map(s.model_copy(update={"training_bond_amount": None}))["available"] is False


def test_freelance_map_has_interest_series():
    m = consequence_map(sample("freelance_service"))
    assert m["series"][30]["y"] == round(84000 * 2 / 100) and m["series"][0]["y"] == 0


# ---- self-correcting retrieval -----------------------------------------
async def test_reformulation_recovers_a_miss():
    class Kan(FakeKanoon):
        async def search(self, q, doctypes=None, page=0):
            return {"docs": [{"tid": 111, "title": "X v Y"}]} if "compensation" in q else {"docs": []}

    ev = await v.verify_proposition("late_payment", "prop", ["fee clause"], Kan(), FakeLLM(alt_queries=["reasonable compensation breach"]))
    assert ev and ev[0].status == "verified" and ev[0].query == "reasonable compensation breach"


async def test_reformulation_is_bounded_and_skips_when_verified():
    calls = []

    class Counting(FakeLLM):
        async def structured(self, system, user, schema):
            if schema is v.Queries:
                calls.append(1)
            return await super().structured(system, user, schema)

    await v.verify_proposition("c", "p", ["q"], FakeKanoon(), Counting())  # verifies first time
    assert calls == []
    await v.verify_proposition("c", "p", ["q"], FakeKanoon(passage="short"), Counting(alt_queries=["other"]))
    assert len(calls) == 1


# ---- text utilities -----------------------------------------------------
def test_numbers_handles_commas_and_telugu_digits():
    assert numbers("₹22,000 and ౩౦ days") == {"22000", "30"}
    assert norm_digits("१५") == "15"


# ---- agent --------------------------------------------------------------
def call(name, args, i="1"):
    return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(id=i, function=SimpleNamespace(name=name, arguments=json.dumps(args)))])


def final(text):
    return SimpleNamespace(content=text, tool_calls=None)


class Script:
    def __init__(self, *msgs):
        self.msgs = list(msgs)

    async def chat(self, messages, tools):
        return self.msgs.pop(0)


async def test_agent_runs_simulator_and_answer_checks_out(spec):
    c = compile_contract(spec)
    llm = Script(call("simulate", {"scenario": {"type": "late_payment", "month_index": 0, "days_late": 20}}),
                 final("The late fee would be ₹750 [clause:late_payment]."))
    r = await ask(llm, c, REGISTRY["rental_agreement"], "What if I pay 20 days late?")
    assert r["warnings"] == [] and r["citations"] == ["late_payment"] and r["trace"][0]["tool"] == "simulate"


async def test_agent_flags_invented_figure_and_citation(spec):
    c = compile_contract(spec)
    llm = Script(call("get_terms", {}), final("The fee is ₹99,999 [clause:made_up]."))
    r = await ask(llm, c, REGISTRY["rental_agreement"], "fee?")
    assert any("99999" in w for w in r["warnings"]) and any("made_up" in w for w in r["warnings"]) and r["citations"] == []


async def test_agent_without_tools_is_warned(spec):
    r = await ask(Script(final("It is fine.")), compile_contract(spec), REGISTRY["rental_agreement"], "ok?")
    assert any("without reading" in w for w in r["warnings"])


async def test_agent_bad_scenario_returns_error_to_model_not_crash(spec):
    c = compile_contract(spec)
    llm = Script(call("simulate", {"scenario": {"type": "nonsense"}}), final("I could not run that [clause:rent]."))
    r = await ask(llm, c, REGISTRY["rental_agreement"], "x")
    assert "error" in r["trace"][0]["result"]


def test_verify_answer_ignores_single_digits():
    assert verify_answer("on the 5th [clause:rent]", {"rent"}, "")[1] == []


# ---- explain ------------------------------------------------------------
async def test_explain_flags_changed_numbers_and_drops_unknown_keys(spec):
    c = compile_contract(spec)
    rent = next(x for x in c.clauses if x.key == "rent")

    class L:
        async def structured(self, system, user, schema):
            return Explanation(summary="s", items=[
                Item(clause_key="rent", plain="You pay ₹22,000 each month.", you_must="Pay by the 5th.", watch_out=""),
                Item(clause_key="term", plain="It lasts 12 months.", you_must="", watch_out=""),
                Item(clause_key="ghost", plain="x", you_must="", watch_out="")])
    r = await explain(L(), c, "Telugu")
    by = {i["clause_key"]: i for i in r["items"]}
    assert by["rent"]["numbers_ok"] is True and by["term"]["numbers_ok"] is False and "12" in by["term"]["extra_numbers"]
    assert "ghost" not in by and r["speech_lang"] == "te-IN"
    with pytest.raises(ValueError):
        await explain(L(), c, "French")


# ---- upload review ------------------------------------------------------
DOC = """RENTAL AGREEMENT
This agreement is made between Ravi Kumar (Landlord) and Anita Rao (Tenant) for Flat 302, Madhapur, Hyderabad.
1. Term. The tenancy starts on 1 December 2026 for 11 months.
2. Rent. The Tenant shall pay Rs 22,000 on or before the 5th of every month.
3. Deposit. The Tenant pays a deposit of Rs 44,000.
4. Termination. The Landlord may terminate the tenancy at any time without notice.
5. Disputes. Courts at Hyderabad have jurisdiction.
"""


def test_segmentation_splits_numbered_clauses():
    segs = segment(DOC)
    assert len(segs) >= 5 and any(s["text"].startswith("4. Termination") for s in segs)


def test_extract_text_docx_roundtrip_and_short_file_rejected():
    from docx import Document
    d = Document()
    for line in DOC.splitlines():
        d.add_paragraph(line)
    b = io.BytesIO()
    d.save(b)
    assert "Termination" in extract_text("x.docx", b.getvalue())
    with pytest.raises(ValueError):
        extract_text("x.txt", b"too short")


def test_gap_analysis_separates_basics_from_optional():
    td = REGISTRY["rental_agreement"]
    g = gap_analysis(td, {"parties_premises", "term", "rent"})
    basics = {x["clause_key"] for x in g["missing_basics"]}
    optional = {x["clause_key"] for x in g["worth_considering"]}
    assert {"security_deposit", "termination_notice"} <= basics and {"late_payment", "deposit_refund"} <= optional


def test_build_contract_keeps_user_text_and_blocks_incomplete(spec):
    segs = [{"text": "2. Rent. The Tenant shall pay Rs 22,000.", "clause_key": "rent", "heading": "2. Rent"},
            {"text": "4. Termination. Landlord may terminate at any time.", "clause_key": "termination_notice", "heading": "4"},
            {"text": "Misc text", "clause_key": None, "heading": "Misc"}, {"text": "Rent again", "clause_key": "rent", "heading": "r2"}]
    c = build_contract(spec, segs, "x.docx")
    assert c.clauses[0].text.startswith("2. Rent") and c.clauses[1].risk == "high" and c.clauses[1].evidence_queries
    assert [x.key for x in c.clauses][2:] == ["other_1", "other_2"] and c.source["uploaded"]
    with pytest.raises(ValueError):
        build_contract(type(spec)(landlord_name="A"), segs)


class UploadLLM(StubLLM):
    async def structured(self, system, user, schema):
        if schema is TypeGuess:
            return TypeGuess(contract_type="rental_agreement", reason="rent")
        if schema is Labels:
            keys = {"1": "term", "2": "rent", "3": "security_deposit", "4": "termination_notice"}
            return Labels(labels=[Label(idx=i, clause_key=keys.get(str(i), "not_a_key" if i == 0 else None),
                                        concern="No notice period" if i == 4 else None) for i in range(8)])
        if schema.__name__.endswith("Patch"):
            from datetime import date
            return schema(landlord_name="Ravi Kumar", tenant_name="Anita Rao", property_address="Flat 302, Madhapur, Hyderabad",
                          start_date=date(2026, 12, 1), term_months=11, monthly_rent=22000, security_deposit=44000,
                          due_day=5, notice_days=0, inferred_fields=[])
        return await super().structured(system, user, schema)


@pytest.fixture
def client():
    deps.services = deps.Services(llm=UploadLLM(), repo=Repo(), kanoon=FakeKanoon())
    return TestClient(app)


def test_upload_flow_end_to_end(client):
    r = client.post("/api/upload/analyze", json={"filename": "r.txt", "content_b64": base64.b64encode(DOC.encode()).decode()})
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["contract_type"] == "rental_agreement" and a["missing"] == ["state"]
    assert a["spec"]["state"] is None and a["questions"][0]["field"] == "state"
    assert all(s["clause_key"] in (None, "term", "rent", "security_deposit", "termination_notice") for s in a["segments"])  # invented key dropped
    assert {"security_deposit"} .isdisjoint({g["clause_key"] for g in a["gaps"]["missing_basics"]})
    assert a["spec"]["provenance"]["landlord_name"] == "document"
    a["spec"]["state"] = "Telangana"  # supplied explicitly, not inferred from Hyderabad
    a["spec"]["provenance"]["state"] = "user"
    o = client.post("/api/upload/contract", json={"spec": a["spec"], "segments": a["segments"], "filename": "r.txt"})
    assert o.status_code == 200
    cid = o.json()["id"]
    assert any(c["clause_key"] == "termination_notice" and c["severity"] == "high" for c in client.get(f"/api/contracts/{cid}/lint").json())  # notice = 0
    ev = client.post(f"/api/contracts/{cid}/evidence/termination_notice").json()["evidence"]
    assert ev and ev[0]["status"] == "verified"
    assert client.post(f"/api/contracts/{cid}/simulate", json={"type": "late_payment", "month_index": 0, "days_late": 3}).status_code == 200
    assert client.get(f"/api/contracts/{cid}/consequence-map").json()["available"]
    assert client.post("/api/upload/analyze", json={"text": "short"}).status_code == 422
    assert client.post("/api/contracts/%s/explain" % cid, json={"language": "French"}).status_code == 422
