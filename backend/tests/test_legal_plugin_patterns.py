from app.review.playbook import get_playbook, NdaTriage, TriageFinding, triage_nda


def test_playbook_has_risk_rubric_and_indian_contract_topics():
    pb = get_playbook()
    assert {"GREEN", "YELLOW", "RED"}.issubset(pb["risk_levels"])
    topics = {p["topic"] for p in pb["positions"]}
    assert {"Limitation of liability", "Indemnification", "Confidentiality", "Personal data and security", "Intellectual property"}.issubset(topics)
    assert len(pb["nda_checklist"]) >= 8
    assert "not legal standards" in pb["notice"]


class FakeLLM:
    async def structured(self, system, prompt, model):
        return model(
            classification="GREEN",
            summary="Most checklist items appear present, but counsel should confirm scope.",
            findings=[TriageFinding(id="purpose", status="GREEN", evidence="Purpose means evaluation of the proposed services.")],
            missing_information=[],
            escalation_reasons=[],
        )


def test_nda_triage_uses_only_known_checklist_ids_and_safe_classification():
    import asyncio
    result = asyncio.run(triage_nda(FakeLLM(), "A sufficiently long NDA text for the test harness."))
    assert isinstance(result, NdaTriage)
    assert result.classification == "GREEN"
    assert result.findings[0].id == "purpose"
