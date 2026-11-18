"""Conversational intake. The model extracts only what the user actually said;
we merge it into the spec with provenance and ask only for what is missing."""
from __future__ import annotations

from pydantic import BaseModel, Field, create_model

from ..models import missing_fields
from ..types import REGISTRY

SYSTEM = (
    "You extract agreement details from a message by an Indian user ({hint}). The message may be in any of the 22 Scheduled Indian languages, English, or a mix of languages and scripts; "
    "understand it, write names in Roman script as spoken, and fill the fields in English. "
    "Fill a field ONLY if the user stated it or it follows by simple arithmetic from stated values. "
    "Never guess the state, city, governing law or jurisdiction; ask the user if it is not stated. "
    "For example, 'two months deposit' with rent 22000 gives 44000; list such computed fields in "
    "inferred_fields. NEVER invent values, notice periods, fees, penalties or legal terms. Leave everything else null. "
    "Dates as ISO (YYYY-MM-DD); amounts in rupees as integers."
)


def _patch_model(spec_cls):
    # every field optional, default None
    fields = {n: (f.annotation, Field(None)) for n, f in spec_cls.model_fields.items()
              if n not in ("provenance", "contract_type")}
    fields["inferred_fields"] = (list[str], Field(default_factory=list))
    return create_model(f"{spec_cls.__name__}Patch", **fields)


async def extract(llm, message: str, current):
    td = REGISTRY[current.contract_type]
    Patch = _patch_model(td.spec_cls)
    patch = await llm.structured(
        SYSTEM.format(hint=td.intake_hint),
        f"Already known: {current.model_dump_json(exclude={'provenance'}, exclude_none=True)}\n\nMessage:\n{message}",
        Patch,
    )
    merged = current.model_copy(deep=True)
    data = patch.model_dump(exclude={"inferred_fields"})
    for field, value in data.items():
        if value is None:
            continue
        setattr(merged, field, value)
        merged.provenance[field] = "inferred" if field in patch.inferred_fields else "user"
    return type(current).model_validate(merged.model_dump())  # re-validate ranges after merge


def next_questions(spec, limit: int = 3) -> list[dict]:
    td = REGISTRY[spec.contract_type]
    return [{"field": f, "question": td.questions[f]} for f in missing_fields(spec)[:limit]]
