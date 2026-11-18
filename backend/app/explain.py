"""Plain-language explanation in English, Telugu or Hindi. The English clause stays authoritative.
Guard in code: every number in an explanation must also be in its clause; items that fail are flagged."""
from __future__ import annotations

from pydantic import BaseModel

from .textutil import numbers

LANGUAGES = {
    "Assamese": "as-IN", "Bengali": "bn-IN", "Bodo": "brx-IN", "Dogri": "doi-IN",
    "Gujarati": "gu-IN", "Hindi": "hi-IN", "Kannada": "kn-IN", "Kashmiri": "ks-IN",
    "Konkani": "kok-IN", "Maithili": "mai-IN", "Malayalam": "ml-IN", "Manipuri": "mni-IN",
    "Marathi": "mr-IN", "Nepali": "ne-IN", "Odia": "or-IN", "Punjabi": "pa-IN",
    "Sanskrit": "sa-IN", "Santali": "sat-IN", "Sindhi": "sd-IN", "Tamil": "ta-IN",
    "Telugu": "te-IN", "Urdu": "ur-IN", "English": "en-IN",
}


class Item(BaseModel):
    clause_key: str
    plain: str       # what this clause means
    you_must: str    # what each side has to do (empty if nothing)
    watch_out: str   # what to be careful about (empty if nothing)


class Explanation(BaseModel):
    summary: str
    items: list[Item]


SYSTEM = (
    "You explain clauses of an Indian agreement to an ordinary person with no legal training, in {language}. "
    "Use short, simple sentences and everyday words. Rules: keep EVERY number, amount and date exactly as in the clause, "
    "written with ASCII digits (0-9); add no terms, promises or legal conclusions that the clause does not contain; "
    "write party names as in the clause; if something is unclear in the clause, say it is unclear. "
    "Return one item per clause given, using the same clause_key."
)


async def explain(llm, contract, language: str) -> dict:
    if language not in LANGUAGES:
        raise ValueError(f"language must be one of {list(LANGUAGES)}")
    body = "\n\n".join(f"[{c.key}] {c.title}: {c.text}" for c in contract.clauses)
    out = await llm.structured(SYSTEM.format(language=language), body, Explanation)
    by_key = {c.key: c for c in contract.clauses}
    items = []
    for it in out.items:
        c = by_key.get(it.clause_key)
        if not c:
            continue  # drop items for clauses that do not exist
        extra = sorted(numbers(it.plain + " " + it.you_must + " " + it.watch_out) - numbers(c.text), key=float)
        items.append({**it.model_dump(), "title": c.title, "numbers_ok": not extra, "extra_numbers": extra})
    return {"language": language, "speech_lang": LANGUAGES[language], "summary": out.summary, "items": items,
            "note": "This is an explanation to help you understand. The English clause is the agreement."}
