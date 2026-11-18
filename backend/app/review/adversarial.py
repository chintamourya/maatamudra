"""Three-role adversarial review: landlord advocate, tenant advocate, neutral reviewer.
Guardrails (code, not prompts): the neutral reviewer may cite only evidence ids we supply and
only `verified` evidence is supplied; any proposal that introduces new numbers is flagged and
cannot be auto-accepted."""
from __future__ import annotations

import asyncio
import re

from pydantic import BaseModel, Field

from ..legal.statutes import get_many
from ..models import Clause, Evidence, Redline

MAX_CLAUSES = 6


class Argument(BaseModel):
    risks: str
    suggested_change: str


class Neutral(BaseModel):
    risk_to_party_a: str
    risk_to_party_b: str
    legal_question: str
    proposed_text: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


ADVOCATE = (
    "You are the advocate for the {side} in an Indian {kind}. Read the clause and say, "
    "briefly and concretely, what could go wrong for your client and what change would protect them. "
    "Do not cite case law or statutes you were not given. Do not invent facts."
)
NEUTRAL = (
    "You are a neutral reviewer of a clause in an Indian {kind}. You get the clause, both "
    "advocates' arguments, statute summaries (unverified unless marked) and verified judgment passages with ids. "
    "Propose ONE balanced replacement for the clause. Keep every number (amounts, days, months, percentages) from "
    "the original unchanged unless there is no alternative; never add new numbers. Cite evidence only by the ids "
    "provided. If no evidence is provided, say so in the rationale and set evidence_ids to []. "
    "State a legal question for a lawyer to confirm instead of asserting a legal conclusion."
)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d[\d,\.]*", text))


async def review_clause(llm, clause: Clause, evidence: list[Evidence], td) -> Redline:
    ctx = f"Clause '{clause.title}':\n{clause.text}"
    a, b = await asyncio.gather(
        llm.structured(ADVOCATE.format(side=td.party_a, kind=td.title.lower()), ctx, Argument),
        llm.structured(ADVOCATE.format(side=td.party_b, kind=td.title.lower()), ctx, Argument),
    )
    verified = [e for e in evidence if e.clause_key == clause.key and e.status == "verified"]
    statutes = get_many(clause.legal_basis)
    ev_block = "\n".join(f"[{e.id}] {e.title} ({e.court}, {e.date}): {e.passage[:600]}" for e in verified) or "(none)"
    st_block = "\n".join(
        f"- {s['act']} s.{s['section']}: {s['summary']} ({'verified' if s['verified'] else 'UNVERIFIED'})" for s in statutes
    ) or "(none)"
    user = (f"{ctx}\n\n{td.party_a.upper()} ADVOCATE: {a.risks}\nSuggested: {a.suggested_change}\n\n"
            f"{td.party_b.upper()} ADVOCATE: {b.risks}\nSuggested: {b.suggested_change}\n\n"
            f"STATUTES:\n{st_block}\n\nVERIFIED JUDGMENT PASSAGES:\n{ev_block}")
    n = await llm.structured(NEUTRAL.format(kind=td.title.lower()), user, Neutral)
    allowed = {e.id for e in verified}
    ids = [i for i in n.evidence_ids if i in allowed]  # drop anything the model invented
    warning = None
    if _numbers(n.proposed_text) - _numbers(clause.original_text):
        warning = ("The proposal introduces numbers not in the original clause. Change the contract details "
                   "instead of accepting this text, so the obligations stay consistent.")
    return Redline(
        clause_key=clause.key, original=clause.text, proposed=n.proposed_text,
        risk_to_party_a=n.risk_to_party_a, risk_to_party_b=n.risk_to_party_b,
        legal_question=n.legal_question, rationale=n.rationale, evidence_ids=ids, warning=warning,
    )


async def review_contract(llm, clauses: list[Clause], evidence: list[Evidence], td) -> list[Redline]:
    targets = [c for c in clauses if c.risk in ("medium", "high")]
    targets.sort(key=lambda c: 0 if c.risk == "high" else 1)
    return list(await asyncio.gather(*(review_clause(llm, c, evidence, td) for c in targets[:MAX_CLAUSES])))
