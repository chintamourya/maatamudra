import json

from fastapi.testclient import TestClient

from app import deps
from app.analysis.copilot import ClauseRewrite, ContractReview, ReviewFinding
from app.db import Repo
from app.main import app
from tests.test_api import StubLLM
from tests.test_verifier import FakeKanoon


class CopilotStubLLM(StubLLM):
    def __init__(self):
        self.change_numbers = False

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
            proposed = original + " The parties will confirm payment details in writing."
            if self.change_numbers:
                proposed += " The revised amount is 999999."
            return ClauseRewrite(
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
