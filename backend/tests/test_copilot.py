import json

from fastapi.testclient import TestClient

from app import deps
from app.analysis.copilot import ClauseRewrite, ContractReview, RequestedTermChange, ReviewFinding
from app.db import Repo
from app.main import app
from tests.test_api import StubLLM
from tests.test_verifier import FakeKanoon


class CopilotStubLLM(StubLLM):
    def __init__(self):
        self.change_numbers = False
        self.change_term = False
        self.term_value = "75"

    async def structured(self, system, user, schema):
        if schema is ContractReview:
            return ContractReview(
                summary="Review the rent and payment terms.",
                overall_attention="medium",
                findings=[ReviewFinding(
                    priority="medium",
                    category="ambiguity",
                    title="Clarify payment timing",
                    observation="The payment timing should be easier to follow.",
                    impact="The parties may disagree about when payment is due.",
                    next_step="Confirm the agreed due date.",
                    clause_keys=["rent", "invented_clause"],
                )],
                open_questions=["Is the payment date agreed?"],
            )
        if schema is ClauseRewrite:
            context = json.loads(user)
            original = context["target_clause"]["text"]
            if self.change_term:
                return ClauseRewrite(
                    intent="term_change",
                    proposed_text=original,
                    rationale="The requested notice period differs from the current agreement term.",
                    requested_term_change=RequestedTermChange(
                        field="notice_days",
                        requested_value=self.term_value,
                        rationale="Update the structured notice-days term.",
                    ),
                )
            proposed = original + " The parties will confirm payment details in writing."
            if self.change_numbers:
                proposed += " The revised amount is 999999."
            return ClauseRewrite(
                intent="wording",
                proposed_text=proposed,
                rationale="Makes the payment wording clearer.",
                tradeoffs=["The parties should confirm the exact timing."],
            )
        return await super().structured(system, user, schema)


def test_ai_studio_review_and_approved_clause_rewrite(spec):
    llm = CopilotStubLLM()
    deps.services = deps.Services(llm=llm, repo=Repo(), kanoon=FakeKanoon())
    with TestClient(app) as client:
        created = client.post("/api/contracts", json=spec.model_dump(mode="json")).json()
        cid = created["id"]

        review = client.post(f"/api/contracts/{cid}/copilot/review")
        assert review.status_code == 200
        review_body = review.json()
        assert review_body["basis"]["external_legal_sources_used"] is False
        assert review_body["findings"][0]["clause_keys"] == ["rent"]
        assert any("references did not match" in warning for warning in review_body["warnings"])

        proposal = client.post(f"/api/contracts/{cid}/copilot/rewrite", json={
            "clause_key": "rent",
            "instruction": "Make the payment wording clearer.",
        })
        assert proposal.status_code == 200
        proposal_body = proposal.json()
        assert proposal_body["apply_allowed"] is True
        applied = client.post(f"/api/contracts/{cid}/copilot/apply", json={
            "suggestion_id": proposal_body["suggestion_id"],
        })
        assert applied.status_code == 200
        rent = next(clause for clause in applied.json()["clauses"] if clause["key"] == "rent")
        assert rent["status"] == "revised"
        assert "confirm payment details" in rent["text"]

        llm.change_numbers = True
        unsafe = client.post(f"/api/contracts/{cid}/copilot/rewrite", json={
            "clause_key": "rent",
            "instruction": "Make the payment wording clearer.",
        })
        assert unsafe.status_code == 200
        unsafe_body = unsafe.json()
        assert unsafe_body["number_integrity"] is False
        assert unsafe_body["apply_allowed"] is False
        rejected = client.post(f"/api/contracts/{cid}/copilot/apply", json={
            "suggestion_id": unsafe_body["suggestion_id"],
        })
        assert rejected.status_code == 409


def test_ai_term_change_updates_spec_clauses_and_compiled_contract(spec):
    spec = spec.model_copy(update={"notice_days": 60})
    llm = CopilotStubLLM()
    deps.services = deps.Services(llm=llm, repo=Repo(), kanoon=FakeKanoon())
    with TestClient(app) as client:
        created = client.post("/api/contracts", json=spec.model_dump(mode="json")).json()
        cid = created["id"]
        llm.change_term = True

        proposal = client.post(f"/api/contracts/{cid}/copilot/rewrite", json={
            "clause_key": "termination_notice",
            "instruction": "75 days notice",
        })
        assert proposal.status_code == 200
        change = proposal.json()["term_change"]
        assert change["field"] == "notice_days"
        assert change["current_value"] == 60
        assert change["requested_value"] == 75
        assert change["can_apply"] is True

        applied = client.post(f"/api/contracts/{cid}/copilot/terms/apply", json={
            "suggestion_id": change["suggestion_id"],
        })
        assert applied.status_code == 200
        updated = applied.json()
        assert updated["spec"]["notice_days"] == 75
        assert updated["spec"]["provenance"]["notice_days"] == "user"
        notice_clause = next(item for item in updated["clauses"] if item["key"] == "termination_notice")
        assert "75 days" in notice_clause["text"]
        assert not updated["copilot_term_suggestions"]
        simulation = client.post(f"/api/contracts/{cid}/simulate", json={
            "type": "early_termination",
            "party": "tenant",
            "notice_date": "2027-01-01",
        })
        assert simulation.status_code == 200
        assert any("75-day notice expires" == event["label"] for event in simulation.json()["events"])

        llm.term_value = "366"
        invalid = client.post(f"/api/contracts/{cid}/copilot/rewrite", json={
            "clause_key": "termination_notice",
            "instruction": "Change notice period to 366 days",
        })
        assert invalid.status_code == 200
        invalid_change = invalid.json()["term_change"]
        assert invalid_change["can_apply"] is False
        assert invalid_change["validation_error"]
