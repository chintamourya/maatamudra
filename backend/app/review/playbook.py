"""Playbook-based contract review and NDA triage.

Adapted conceptually from Anthropic's open-source legal plugin workflow patterns:
context gathering, playbook deviations, GREEN/YELLOW/RED triage, redlines,
business impact and escalation. India-specific rules are not asserted by defaults.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from pydantic import BaseModel, Field

DATA = Path(__file__).resolve().parents[2] / "data" / "legal_playbook.json"

def get_playbook():
    return json.loads(DATA.read_text(encoding="utf-8"))

class TriageFinding(BaseModel):
    id: str
    status: str
    evidence: str = ""
    concern: str = ""
    recommended_action: str = ""

class NdaTriage(BaseModel):
    classification: str
    summary: str
    findings: list[TriageFinding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    escalation_reasons: list[str] = Field(default_factory=list)
    disclaimer: str = "AI pre-screen only; qualified legal review is required before relying on or signing."

TRIAGE_SYSTEM = """You are an Indian commercial contract pre-screening assistant. Triage this NDA against the supplied checklist. Use only the provided text; do not assume missing clauses exist. GREEN means no material issue detected against this limited checklist, YELLOW means counsel/business review is needed, RED means a material omission or exposure needs escalation. Be conservative. Return short evidence quotations copied from the input; if no quotation exists, say absent. Do not state that the NDA is enforceable or legally valid. Distinguish missing text from legal invalidity."""

async def triage_nda(llm, text: str) -> NdaTriage:
    playbook = get_playbook()
    class _Out(BaseModel):
        classification: str
        summary: str
        findings: list[TriageFinding] = Field(default_factory=list)
        missing_information: list[str] = Field(default_factory=list)
        escalation_reasons: list[str] = Field(default_factory=list)
    checklist = playbook["nda_checklist"]
    out = await llm.structured(TRIAGE_SYSTEM, "CHECKLIST:\n" + json.dumps(checklist) + "\n\nNDA TEXT:\n" + text[:50000], _Out)
    valid = {x["id"] for x in checklist}
    findings = [f for f in out.findings if f.id in valid and f.status in {"GREEN", "YELLOW", "RED", "NOT_FOUND"}]
    rank = {"GREEN":0,"YELLOW":1,"RED":2,"NOT_FOUND":1}
    classification = max([out.classification.upper() if out.classification.upper() in {"GREEN","YELLOW","RED"} else "YELLOW"] + ["RED" if f.status == "RED" else "YELLOW" if f.status in {"YELLOW","NOT_FOUND"} else "GREEN" for f in findings], key=lambda x: rank[x])
    return NdaTriage(classification=classification, summary=out.summary, findings=findings,
                     missing_information=out.missing_information, escalation_reasons=out.escalation_reasons)

class PlaybookReviewResult(BaseModel):
    overall_risk: str
    executive_summary: str
    clause_findings: list[dict] = Field(default_factory=list)
    negotiation_priorities: list[str] = Field(default_factory=list)
    redline_suggestions: list[dict] = Field(default_factory=list)
    business_impact: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    disclaimer: str = "Draft for review by qualified counsel; not legal advice or a legal-validity determination."

REVIEW_SYSTEM = """You are an Indian commercial contract review assistant. Review the supplied agreement against the supplied negotiation playbook and deal context. Produce clause-by-clause findings, classify each GREEN/YELLOW/RED, explain business impact, prioritize negotiation points and offer narrowly tailored fallback redline language for YELLOW/RED items. Do not invent facts, legal authorities, statutory requirements, prices, dates or agreed positions. Treat the playbook as the client's preference, not law. Identify ambiguity and missing information. Do not claim legal validity or enforceability. If jurisdiction-specific law is not supplied, state that it requires verification. Preserve all commercial numbers unless the user explicitly asks to negotiate them. Cite only source/evidence IDs included in the input; otherwise leave citations empty."""

async def playbook_review(llm, contract_text: str, context: dict, playbook: dict | None = None) -> PlaybookReviewResult:
    pb = playbook or get_playbook()
    class _Out(PlaybookReviewResult):
        pass
    prompt = "PLAYBOOK (client positions, not law):\n" + json.dumps(pb.get("positions", []))
    prompt += "\n\nDEAL CONTEXT:\n" + json.dumps(context or {})
    prompt += "\n\nAGREEMENT TEXT:\n" + contract_text[:65000]
    out = await llm.structured(REVIEW_SYSTEM, prompt, _Out)
    # Conservative classification and output bounds.
    if out.overall_risk not in {"GREEN","YELLOW","RED"}: out.overall_risk = "YELLOW"
    for f in out.clause_findings:
        if f.get("risk") not in {"GREEN","YELLOW","RED"}: f["risk"] = "YELLOW"
    return out
