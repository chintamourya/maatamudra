"""End-to-end API flow with stubbed LLM and Indian Kanoon (no network)."""
import pytest
from fastapi.testclient import TestClient

from app import deps
from app.db import Repo
from app.legal import verifier as v
from app.main import app
from app.review.adversarial import Neutral
from tests.test_verifier import FakeKanoon, FakeLLM as JudgeLLM


class StubLLM(JudgeLLM):
    async def structured(self, system, user, schema):
        if schema is v.Judgement:
            return self.out
        if schema is v.Queries:
            return v.Queries(queries=[])
        if schema.__name__ == "Argument":
            return schema(risks="risk", suggested_change="change")
        if schema is Neutral:
            ids = [w.strip("[]") for w in user.split() if w.startswith("[") and "-" in w and w.endswith("]")]
            return Neutral(risk_to_party_a="a", risk_to_party_b="b", legal_question="q",
                           proposed_text="Rent is payable monthly.", rationale="r",
                           evidence_ids=ids + ["invented-id"])
        raise AssertionError(schema)


@pytest.fixture
def client():
    repo = Repo()
    deps.services = deps.Services(llm=StubLLM(), repo=repo, kanoon=FakeKanoon())
    return TestClient(app)


def test_full_flow(client, spec):
    r = client.post("/api/contracts", json=spec.model_dump(mode="json"))
    assert r.status_code == 200
    cid = r.json()["id"]

    assert client.post("/api/contracts", json={"landlord_name": "A"}).status_code == 422

    ev = client.post(f"/api/contracts/{cid}/evidence/late_payment").json()["evidence"]
    assert ev and ev[0]["status"] == "verified"

    c = client.post(f"/api/contracts/{cid}/review").json()
    assert c["redlines"]
    for red in c["redlines"]:  # invented ids must be dropped
        assert "invented-id" not in red["evidence_ids"]
    lp = next(x for x in c["redlines"] if x["clause_key"] == "late_payment")
    assert lp["evidence_ids"] == [ev[0]["id"]]
    assert lp["warning"] is None
    assert client.post(f"/api/contracts/{cid}/redlines/late_payment/accept").status_code == 200
    got = client.get(f"/api/contracts/{cid}").json()
    assert next(x for x in got["clauses"] if x["key"] == "late_payment")["status"] == "revised"

    sim = client.post(f"/api/contracts/{cid}/simulate", json={"type": "late_payment", "month_index": 0, "days_late": 20}).json()
    assert sim["late_fee"] == 750
    assert client.post(f"/api/contracts/{cid}/simulate", json={"type": "bogus"}).status_code == 422

    ex = client.get(f"/api/contracts/{cid}/execution").json()
    assert ex["supported"] and all(i["done"] is False for i in ex["items"])
    assert client.post(f"/api/contracts/{cid}/execution/confirm", json={"step": "stamp_duty_paid", "note": "x"}).status_code == 422
    ok = client.post(f"/api/contracts/{cid}/execution/confirm", json={"step": "stamp_duty_paid", "note": "e-stamp receipt 123, 2 Dec"})
    assert ok.json()["execution"]["stamp_duty_paid"] is True

    d = client.get(f"/api/contracts/{cid}/docx")
    assert d.status_code == 200 and d.content[:2] == b"PK"
    assert len(client.get(f"/api/contracts/{cid}/audit").json()) >= 5


def test_number_changing_redline_cannot_be_auto_accepted(client, spec):
    class Greedy(StubLLM):
        async def structured(self, system, user, schema):
            if schema is Neutral:
                return Neutral(risk_to_party_a="a", risk_to_party_b="b", legal_question="q",
                               proposed_text="Late fee is 900 per day.", rationale="r")
            return await super().structured(system, user, schema)
    deps.services.llm = Greedy()
    cid = client.post("/api/contracts", json=spec.model_dump(mode="json")).json()["id"]
    c = client.post(f"/api/contracts/{cid}/review").json()
    assert any(r["warning"] for r in c["redlines"])
    key = next(r["clause_key"] for r in c["redlines"] if r["warning"])
    assert client.post(f"/api/contracts/{cid}/redlines/{key}/accept").status_code == 409


def test_pan_india_legal_endpoints(client, spec):
    jurisdictions = client.get("/api/jurisdictions")
    assert jurisdictions.status_code == 200
    assert len(jurisdictions.json()) == 36
    assert any(x["name"] == "Assam" for x in jurisdictions.json())

    cid = client.post("/api/contracts", json=spec.model_dump(mode="json")).json()["id"]
    report = client.get(f"/api/contracts/{cid}/legal-intelligence")
    assert report.status_code == 200
    body = report.json()
    assert body["jurisdiction"]["state_ut"] == "Telangana"
    assert body["jurisdiction"]["state_rules_verified"] is False
    assert any(x["id"] == "rental_stamp_duty" for x in body["findings"])
    assert "not legal advice" in body["notice"].lower()


def test_demo_identity_and_signing_are_explicitly_simulated(client, spec):
    identity = client.post("/api/demo/auth/session", json={"user_label": "Judge", "role": "advocate"})
    assert identity.status_code == 200
    assert identity.json()["status"] == "SIMULATED_ONLY"
    assert identity.json()["real_authentication"] is False
    cid = client.post("/api/contracts", json=spec.model_dump(mode="json")).json()["id"]
    signing = client.post("/api/demo/signing/session", json={"contract_id": cid})
    assert signing.status_code == 200
    assert signing.json()["signature_applied"] is False
    assert signing.json()["identity_verified"] is False


def test_translation_endpoint_preserves_explicit_demo_label(client):
    class Translator(StubLLM):
        async def complete_text(self, system, user):
            assert "Preserve names, dates, amounts" in system
            return "अनुवादित कानूनी जानकारी"
    deps.services.llm = Translator()
    response = client.post("/api/translate", json={"text": "Payment is due in 30 days.", "target_language": "Hindi", "source_language": "English"})
    assert response.status_code == 200
    assert response.json()["translated_text"] == "अनुवादित कानूनी जानकारी"
    assert response.json()["legal_status"] == "informational_translation_not_certified_or_authoritative"
    assert response.json()["number_integrity"] is False
    assert response.json()["missing_numbers"] == ["30"]


def test_market_research_snapshot_is_dated_and_transparent(client):
    response = client.get("/api/market-research")
    assert response.status_code == 200
    data = response.json()
    assert data["research_as_of"] == "2026-11-18"
    assert len(data["gaps"]) >= 4
    assert set(data["model"]["scenarios"]) == {"conservative", "base", "aggressive"}
    assert "not an audited market report" in data["disclaimer"]
    assert len(data["research_iterations"]) >= 3
