"""Structured, contract-grounded AI review and clause rewrite proposals."""
from __future__ import annotations

import json
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from ..models import Contract, now
from ..textutil import numbers


class ReviewFinding(BaseModel):
    priority: Literal["high", "medium", "low"]
    category: Literal["ambiguity", "conflict", "missing_detail", "one_sidedness", "operational_gap", "other"]
    title: str = Field(max_length=180)
    observation: str = Field(max_length=700)
    impact: str = Field(max_length=500)
    next_step: str = Field(max_length=500)
    clause_keys: list[str] = Field(default_factory=list, max_length=6)


class ContractReview(BaseModel):
    summary: str = Field(max_length=1200)
    overall_attention: Literal["low", "medium", "high"]
    findings: list[ReviewFinding] = Field(default_factory=list, max_length=12)
    open_questions: list[str] = Field(default_factory=list, max_length=12)


class ClauseRewrite(BaseModel):
    proposed_text: str = Field(min_length=1, max_length=12000)
    rationale: str = Field(max_length=800)
    tradeoffs: list[str] = Field(default_factory=list, max_length=6)


REVIEW_SYSTEM = (
    "Review one Indian agreement as a careful contract analyst. Return review prompts, not legal advice or legal "
    "conclusions. Use only the supplied terms, clauses, and deterministic checks; do not invent facts, values, "
    "dates, legal citations, statutes, or state-law rules. Identify contradictions between clauses, ambiguous wording, "
    "important unspecified details, one-sided terms, and practical follow-through gaps. Every finding must cite one "
    "or more exact supplied clause keys when a clause is relevant; an absent detail may cite the nearest related clause. "
    "Explain the text-based observation, practical impact, and a concrete next step. Do not calculate consequences. "
    "Rank attention by practical importance, not legal validity. Provide no more than 12 findings and 12 questions. "
    "Keep the review concise and understandable to a non-lawyer."
)

REWRITE_SYSTEM = (
    "Propose a clearer replacement for one clause in an Indian agreement. This is a draft suggestion, not legal advice. "
    "Follow the user's instruction only to the extent it is consistent with the supplied agreement facts. Preserve every "
    "number, amount, date, party name, defined term, and obligation from the original clause; do not add new facts, "
    "deadlines, amounts, legal citations, or legal conclusions. Keep the scope of the clause unchanged unless the "
    "instruction explicitly asks otherwise. If the requested change requires changing a number or a fact, keep the "
    "original term and explain that the agreement facts should be updated first. Return the replacement text, a short "
    "rationale, and any material tradeoffs."
)


def _review_text(contract: Contract) -> str:
    return json.dumps({
        "contract_type": contract.spec.contract_type,
        "state_or_union_territory": contract.spec.state,
        "terms": contract.spec.model_dump(mode="json", exclude={"provenance"}, exclude_none=True),
        "clauses": [{"key": c.key, "title": c.title, "risk_marker": c.risk, "text": c.text} for c in contract.clauses],
    }, ensure_ascii=False, default=str)


async def review_contract(llm, contract: Contract, checks: list[dict]) -> dict:
    clause_keys = {c.key for c in contract.clauses}
    context = {
        "agreement": json.loads(_review_text(contract)),
        "deterministic_checks": checks,
    }
    result = await llm.structured(REVIEW_SYSTEM, json.dumps(context, ensure_ascii=False, default=str), ContractReview)
    corpus = json.dumps(context, ensure_ascii=False, default=str)
    warnings = []
    findings = []
    for finding in result.findings:
        supplied_keys = [key for key in finding.clause_keys if key in clause_keys]
        if len(supplied_keys) != len(finding.clause_keys):
            warnings.append("One or more AI clause references did not match this agreement and were removed.")
        values = finding.model_dump()
        values["clause_keys"] = supplied_keys
        finding_text = " ".join((finding.title, finding.observation, finding.impact, finding.next_step))
        finding_numbers = sorted(numbers(finding_text) - numbers(corpus))
        values["numbers_match_source"] = not finding_numbers
        values["unmatched_numbers"] = finding_numbers
        findings.append(values)

    all_text = " ".join(
        [result.summary, *result.open_questions]
        + [f"{f['title']} {f['observation']} {f['impact']} {f['next_step']}" for f in findings]
    )
    unmatched = sorted(numbers(all_text) - numbers(corpus))
    if unmatched:
        warnings.append("Some figures in the AI review were not found in the supplied agreement or checks. Verify them before relying on the review.")

    return {
        "summary": result.summary,
        "overall_attention": result.overall_attention,
        "findings": findings,
        "open_questions": result.open_questions,
        "basis": {
            "clauses_reviewed": [c.key for c in contract.clauses],
            "deterministic_checks_included": len(checks),
            "external_legal_sources_used": False,
        },
        "number_integrity": not unmatched,
        "unmatched_numbers": unmatched,
        "warnings": list(dict.fromkeys(warnings)),
    }


async def rewrite_clause(llm, contract: Contract, clause_key: str, instruction: str) -> dict:
    clause = next((item for item in contract.clauses if item.key == clause_key), None)
    if clause is None:
        raise ValueError("Clause not found")
    other_clauses = [
        {"key": item.key, "title": item.title, "text": item.text}
        for item in contract.clauses if item.key != clause_key
    ]
    context = {
        "contract_type": contract.spec.contract_type,
        "state_or_union_territory": contract.spec.state,
        "agreed_terms": contract.spec.model_dump(mode="json", exclude={"provenance"}, exclude_none=True),
        "target_clause": {"key": clause.key, "title": clause.title, "text": clause.text},
        "other_clauses_for_consistency": other_clauses,
        "user_instruction": instruction.strip(),
    }
    result = await llm.structured(REWRITE_SYSTEM, json.dumps(context, ensure_ascii=False, default=str), ClauseRewrite)
    same_numbers = numbers(result.proposed_text) == numbers(clause.text)
    return {
        "suggestion_id": str(uuid.uuid4()),
        "clause_key": clause.key,
        "clause_title": clause.title,
        "expected_version": clause.version,
        "original_text": clause.text,
        "proposed_text": result.proposed_text,
        "rationale": result.rationale,
        "tradeoffs": result.tradeoffs,
        "number_integrity": same_numbers,
        "apply_allowed": same_numbers and result.proposed_text.strip() != clause.text.strip(),
        "created_at": now(),
    }
