"""Conversational intake. The model extracts only what the user actually said;
we merge it into the spec with provenance and ask only for what is missing."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field, create_model

from ..models import missing_fields
from ..types import REGISTRY

SYSTEM = (
    "You extract agreement details from a message by an Indian user ({hint}). The message may be in any of the 22 Scheduled Indian languages, English, or a mix of languages and scripts; "
    "understand it, write names in Roman script as spoken, and fill the fields in English. "
    "Extract every distinct fact stated in the current message; one message may answer several questions. "
    "Do not stop after extracting the first matching field, and do not replace a fact already stated in the same message. "
    "Use the previous follow-up questions as context when the reply is brief. "
    "Fill a field ONLY if the user stated it or it follows by simple arithmetic from stated values. "
    "Never guess the state, city, governing law or jurisdiction; ask the user if it is not stated. "
    "For example, 'two months deposit' with rent 22000 gives 44000; list such computed fields in "
    "inferred_fields. NEVER invent values, notice periods, fees, penalties or legal terms. Leave everything else null. "
    "A month and year without a day is not an exact date: leave the date null and ask which day, rather than assuming "
    "the first of the month. Dates as ISO (YYYY-MM-DD); amounts in rupees as integers."
)

_MONTHS = {
    "jan": "January", "january": "January",
    "feb": "February", "february": "February",
    "mar": "March", "march": "March",
    "apr": "April", "april": "April",
    "may": "May",
    "jun": "June", "june": "June",
    "jul": "July", "july": "July",
    "aug": "August", "august": "August",
    "sep": "September", "sept": "September", "september": "September",
    "oct": "October", "october": "October",
    "nov": "November", "november": "November",
    "dec": "December", "december": "December",
}
_MONTH_YEAR = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(?P<year>20\d{2})\b"
    r"|\b(?P<year_first>20\d{2})\s+(?P<month_first>January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\b",
    re.IGNORECASE,
)
_MONTH_NUMBERS = {
    name: index for index, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"),
        start=1,
    )
}


def _partial_start_month_year(
    message: str, previous_questions: list[dict] | None = None,
) -> tuple[int, int, str] | None:
    match = _MONTH_YEAR.search(message)
    if not match:
        return None
    month_start = match.start("month") if match.group("month") else match.start("month_first")
    if re.search(r"\b\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+$", message[:month_start], re.I):
        return None
    has_start_context = any(q.get("field") == "start_date" for q in (previous_questions or []))
    has_start_context = has_start_context or bool(
        re.search(r"\b(tenancy|lease|rental|start(?:s|ed|ing)?|begin(?:s|ning)?|commenc(?:e|es|ed|ing))\b", message, re.I)
    )
    if not has_start_context:
        return None
    month = match.group("month") or match.group("month_first")
    year = match.group("year") or match.group("year_first")
    display_month = _MONTHS[month.lower()]
    return _MONTH_NUMBERS[display_month], int(year), f"{display_month} {year}"


def _patch_model(spec_cls):
    # every field optional, default None
    fields = {n: (f.annotation, Field(None)) for n, f in spec_cls.model_fields.items()
              if n not in ("provenance", "contract_type")}
    fields["inferred_fields"] = (list[str], Field(default_factory=list))
    return create_model(f"{spec_cls.__name__}Patch", **fields)


async def extract(llm, message: str, current, previous_questions: list[dict] | None = None):
    td = REGISTRY[current.contract_type]
    Patch = _patch_model(td.spec_cls)
    relevant_questions = [
        question for question in (previous_questions or [])
        if question.get("field") in td.questions and question.get("question")
    ]
    patch = await llm.structured(
        SYSTEM.format(hint=td.intake_hint),
        f"Already known: {current.model_dump_json(exclude={'provenance'}, exclude_none=True)}\n"
        f"Previous follow-up questions: {relevant_questions}\n\nMessage:\n{message}",
        Patch,
    )
    merged = current.model_copy(deep=True)
    data = patch.model_dump(exclude={"inferred_fields"})
    partial_start = _partial_start_month_year(message, relevant_questions)
    proposed_start = data.get("start_date")
    if partial_start and proposed_start is not None:
        month_number, year, _ = partial_start
        if proposed_start.year == year and proposed_start.month == month_number and proposed_start.day == 1:
            data["start_date"] = None
    for field, value in data.items():
        if value is None:
            continue
        setattr(merged, field, value)
        merged.provenance[field] = "inferred" if field in patch.inferred_fields else "user"
    return type(current).model_validate(merged.model_dump())  # re-validate ranges after merge


def next_questions(
    spec, limit: int = 3, message: str | None = None, previous_questions: list[dict] | None = None,
) -> list[dict]:
    td = REGISTRY[spec.contract_type]
    missing = missing_fields(spec)
    partial = _partial_start_month_year(message, previous_questions) if message else None
    partial_start = partial[2] if partial else None

    questions = []
    for field in missing[:limit]:
        question = td.questions[field]
        if field == "start_date" and partial_start and question.lower().startswith("when"):
            question = f"You mentioned {partial_start}. What exact day{question[4:]}"
        questions.append({"field": field, "question": question})
    return questions
