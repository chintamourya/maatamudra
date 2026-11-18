"""Citation verification pipeline.

A citation is shown as `verified` only when ALL of these hold:
  1. the document resolves through Indian Kanoon docmeta (title present)
  2. a passage was retrieved through docfragment (we store the retrieved text,
     never text written by the model)
  3. the model judge says the passage supports the proposition
  4. the judge's supporting quote is found inside the retrieved passage
Anything else is stored with a non-verified status and is never presented as proof."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

from ..models import Evidence, now
from .kanoon import KanoonClient, KanoonError, strip_html

MAX_CANDIDATES = 4
MIN_PASSAGE_CHARS = 60


class Judgement(BaseModel):
    relation: Literal["supports", "contradicts", "unrelated"]
    supporting_quote: str  # must be copied verbatim from the passage
    reason: str


class Queries(BaseModel):
    queries: list[str]


REFORMULATE_SYSTEM = (
    "You help search Indian court judgments. Given a legal proposition and search queries that did not yield a "
    "supporting passage, write up to 2 NEW short search queries (3 to 8 words each) using different legal terms "
    "or synonyms that a judgment would actually use. Do not repeat earlier queries. Never invent case names."
)

JUDGE_SYSTEM = (
    "You check whether a passage from an Indian court judgment supports a legal proposition. "
    "Use ONLY the passage. If it does not clearly speak to the proposition, answer 'unrelated'. "
    "If it points the other way, answer 'contradicts'. For 'supports', copy ONE short quote "
    "verbatim from the passage that supports it. Never paraphrase the quote. Be conservative."
)


def _normalise_quote(value: str) -> str:
    """Normalize whitespace and case only; never accept approximate/fuzzy quotations."""
    return " ".join((value or "").casefold().split())


def quote_in_passage(quote: str, passage: str) -> bool:
    if not quote or not passage:
        return False
    q, p = _normalise_quote(quote), _normalise_quote(passage)
    return len(q) >= 30 and q in p


async def verify_proposition(
    clause_key: str,
    proposition: str,
    queries: list[str],
    kanoon: KanoonClient,
    llm,
    doctypes: str | None = "judgments",
    reformulate: int = 1,
) -> list[Evidence]:
    out: list[Evidence] = []
    seen: set[str] = set()
    tried: list[str] = []
    await _run_queries(clause_key, proposition, queries, kanoon, llm, doctypes, out, seen, tried)
    # Self-correcting retrieval: if nothing verified, ask the model for different search terms (bounded).
    for _ in range(reformulate):
        if any(e.status == "verified" for e in out):
            break
        alt = await llm.structured(
            REFORMULATE_SYSTEM, f"PROPOSITION:\n{proposition}\n\nQUERIES ALREADY TRIED:\n" + "\n".join(tried), Queries)
        fresh = [q for q in alt.queries[:2] if q and q not in tried]
        if not fresh:
            break
        await _run_queries(clause_key, proposition, fresh, kanoon, llm, doctypes, out, seen, tried)
    order = {"verified": 0, "contradicts": 1, "unsupported": 2, "unresolved": 3}
    out.sort(key=lambda e: order[e.status])
    return out


async def _run_queries(clause_key, proposition, queries, kanoon, llm, doctypes, out, seen, tried):
    for q in queries:
        tried.append(q)
        try:
            result = await kanoon.search(q, doctypes=doctypes)
        except KanoonError:
            continue
        for doc in (result.get("docs") or [])[:MAX_CANDIDATES]:
            tid = str(doc.get("tid", ""))
            if not tid or tid in seen:
                continue
            seen.add(tid)
            out.append(await _verify_one(clause_key, proposition, q, tid, doc, kanoon, llm))


async def _verify_one(clause_key, proposition, query, tid, doc, kanoon, llm) -> Evidence:
    url = f"https://indiankanoon.org/doc/{tid}/"
    base = dict(
        id=str(uuid.uuid4()), clause_key=clause_key, proposition=proposition,
        source_id=tid, url=url, retrieved_at=now(), query=query, source=getattr(kanoon, "mode", "indiankanoon"),
    )
    # 1. metadata must resolve
    try:
        meta = await kanoon.docmeta(tid)
    except KanoonError:
        return Evidence(**base, status="unresolved", judge_reason="Document metadata could not be retrieved.")
    title = meta.get("title") or doc.get("title")
    if not title:
        return Evidence(**base, status="unresolved", judge_reason="Document has no resolvable title.")
    court = meta.get("docsource") or meta.get("court") or doc.get("docsource")
    date = meta.get("publishdate") or meta.get("date")
    base.update(title=strip_html(title), court=court, date=date)

    # 2. passage must come from the API, not the model
    try:
        frag = await kanoon.docfragment(tid, query)
    except KanoonError:
        return Evidence(**base, status="unresolved", judge_reason="Passage could not be retrieved.")
    passage = strip_html(frag.get("headline", ""))
    if len(passage) < MIN_PASSAGE_CHARS:
        return Evidence(**base, passage=passage, status="unsupported", judge_reason="Retrieved passage too short to assess.")

    # 3 and 4. judge, then confirm the quote really is in the retrieved passage
    verdict = await llm.structured(
        JUDGE_SYSTEM, f"PROPOSITION:\n{proposition}\n\nPASSAGE:\n{passage}", Judgement
    )
    if verdict.relation == "contradicts":
        return Evidence(**base, passage=passage, status="contradicts", judge_reason=verdict.reason)
    if verdict.relation == "supports" and quote_in_passage(verdict.supporting_quote, passage):
        return Evidence(**base, passage=passage, status="verified", judge_reason=verdict.reason)
    reason = verdict.reason if verdict.relation != "supports" else "Supporting quote not found in the retrieved passage."
    return Evidence(**base, passage=passage, status="unsupported", judge_reason=reason)
