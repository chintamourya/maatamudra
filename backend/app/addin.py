"""Microsoft Word task-pane add-in support.

The add-in is a thin client: it reads the open document in Word, sends the text to the existing
`POST /api/upload/analyze`, and uses `POST /api/addin/rewrite` (below) to propose a clause rewrite that the user
can accept as a Word tracked change. The add-in's static files are served by this same app under `/addin`, so one
HTTPS origin hosts both the UI and the API and no CORS configuration is needed.

`GET /addin/manifest.xml` returns the Office manifest with this server's own URL filled in, ready to sideload.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .deps import Services, get_services
from .textutil import numbers

ADDIN_DIR = Path(__file__).resolve().parents[1] / "addin"
_HOST_OK = re.compile(r"^[A-Za-z0-9.\-]+(:\d{1,5})?$")

router = APIRouter()


# ---- manifest -----------------------------------------------------------
def _base_url(request: Request) -> str:
    """Public origin of this server, honouring reverse-proxy headers (Azure Container Apps, ngrok, ...)."""
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
    if proto not in ("http", "https") or not _HOST_OK.match(host):
        proto, host = request.url.scheme, request.url.netloc
    return f"{proto}://{host}"


@router.get("/addin/manifest.xml")
async def manifest(request: Request):
    template = (ADDIN_DIR / "manifest.template.xml").read_text(encoding="utf-8")
    xml = template.replace("{{BASE}}", _base_url(request))
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "no-cache"})


# ---- stateless clause rewrite ------------------------------------------
class AddinRewriteLLM(BaseModel):
    proposed_text: str = Field(min_length=1, max_length=12000)
    rationale: str = Field(max_length=800)
    tradeoffs: list[str] = Field(default_factory=list, max_length=5)


class AddinRewriteIn(BaseModel):
    clause_text: str = Field(min_length=20, max_length=6000)
    contract_type: str | None = Field(default=None, max_length=60)
    concern: str | None = Field(default=None, max_length=500)
    instruction: str | None = Field(default=None, max_length=500)
    stance: Literal["balanced", "protect_weaker_party"] = "balanced"


REWRITE_SYSTEM = (
    "You are a drafting aid for one clause of an Indian agreement that a person has open in Word. This is not legal "
    "advice. Rewrite the clause so the flagged concern is addressed while staying fair to both parties "
    "(stance=balanced) or, if stance=protect_weaker_party, so the less-protected party is not left exposed. "
    "Hard rules: keep every party name, defined term, number, amount, date and duration from the original exactly as "
    "written; do NOT introduce any new number, date, amount, percentage, statute, section or case citation; if fixing "
    "the concern would need a figure the original does not contain, leave a visible placeholder such as [number of "
    "days] instead of inventing one. Keep the original language and register. Do not add clause numbers or headings "
    "unless the original has them. Output only the replacement clause text in proposed_text. In rationale, say in "
    "plain words what changed and why. In tradeoffs, list material trade-offs the parties should discuss."
)


@router.post("/api/addin/rewrite")
async def addin_rewrite(body: AddinRewriteIn, svc: Services = Depends(get_services)):
    payload = (
        f"contract_type: {body.contract_type or 'unknown'}\n"
        f"stance: {body.stance}\n"
        f"flagged_concern: {body.concern or 'none given'}\n"
        f"user_instruction: {body.instruction or 'none given'}\n"
        f"--- clause_text ---\n{body.clause_text}"
    )
    result = await svc.llm.structured(REWRITE_SYSTEM, payload, AddinRewriteLLM)

    allowed = numbers(" ".join([body.clause_text, body.concern or "", body.instruction or ""]))
    unmatched = sorted(numbers(result.proposed_text) - allowed)
    warnings: list[str] = []
    if unmatched:
        warnings.append("The rewrite contains figures that are not in your clause or instruction: "
                        + ", ".join(unmatched) + ". It cannot be applied until they are removed.")
    if result.proposed_text.strip() == body.clause_text.strip():
        warnings.append("The model returned the clause unchanged.")
    return {
        "proposed_text": result.proposed_text,
        "rationale": result.rationale,
        "tradeoffs": result.tradeoffs,
        "number_integrity": not unmatched,
        "unmatched_numbers": unmatched,
        "apply_allowed": not unmatched,
        "warnings": warnings,
        "disclaimer": "Drafting aid, not legal advice. Have an advocate verify before signing.",
    }


def mount_addin(app) -> None:
    """Serve the task-pane files. Call BEFORE the catch-all '/' static mount."""
    if ADDIN_DIR.is_dir():
        app.mount("/addin", StaticFiles(directory=ADDIN_DIR), name="addin")
