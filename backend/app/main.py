from __future__ import annotations

import uuid
from datetime import date as _date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field

from .config import settings
from .contracts.compiler import compile_contract
from .contracts.intake import extract, next_questions
from .deps import Services, get_services
from .execution.checklist import checklist
from .analysis.copilot import review_contract as ai_contract_review, rewrite_clause as ai_rewrite_clause
from .documents.docx_builder import build_docx
from .legal.kanoon import KanoonError
from .legal.statutes import get_many
from .legal.jurisdictions import list_jurisdictions, CENTRAL_LAWS
from .legal.intelligence import analyze_contract
from .legal.verifier import verify_proposition
from .llm import LLMNotConfigured
from .extras import build_ics, fingerprint
from .models import Contract, CopilotSuggestion, CopilotTermSuggestion, Spec, missing_fields, now
from .review.adversarial import review_contract
from .review.playbook import get_playbook, playbook_review, triage_nda
from .types import REGISTRY
import base64
from .agent import ask as ask_agent
from .analysis.consistency import check as consistency_check
from .explain import explain as explain_contract
from .obligations.sweep import consequence_map
from .upload_review import analyze as analyze_upload, build_contract, extract_text, extract_text_with_method
from pydantic import TypeAdapter

import logging
from contextlib import asynccontextmanager

from .db import Repo
from .addin import router as addin_router, mount_addin

log = logging.getLogger("maatamudra")


@asynccontextmanager
async def lifespan(_app):
    svc = get_services()
    try:
        await svc.repo.init()
    except Exception as e:  # keep the demo alive, but say so in /api/health
        log.warning("Database unavailable (%s); using in-memory storage", type(e).__name__)
        svc.repo = svc.kanoon.repo = Repo()
        svc.repo.fallback_reason = f"database unavailable ({type(e).__name__}); data is NOT being saved"
    yield
    await svc.repo.close()


app = FastAPI(title="Maatamudra API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(LLMNotConfigured)
async def _llm_cfg(_, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(KanoonError)
async def _kanoon(_, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=502, content={"detail": str(exc)})


async def _load(svc: Services, cid: str) -> Contract:
    raw = await svc.repo.get_contract(cid)
    if not raw:
        raise HTTPException(404, "Contract not found")
    return Contract.model_validate(raw)


async def _save(svc: Services, c: Contract, action: str, payload: dict | None = None) -> Contract:
    c.updated_at = now()
    await svc.repo.save_contract(c.id, c.model_dump(mode="json"))
    await svc.repo.audit(c.id, action, payload)
    return c


@app.get("/api/health")
async def health(svc: Services = Depends(get_services)):
    from .config import settings as cfg

    return {"ok": True, "db": svc.repo.backend, "db_note": svc.repo.fallback_reason,
            "llm_configured": bool(cfg.azure_endpoint and cfg.azure_key and cfg.chat_deployment),
            "case_law_source": svc.kanoon.mode}


# ---- intake -------------------------------------------------------------
SPEC = TypeAdapter(Spec)


@app.get("/api/jurisdictions")
async def jurisdictions():
    """All Indian States and UTs; catalogue membership does not imply verified state-law coverage."""
    return list_jurisdictions()


@app.get("/api/legal/coverage")
async def legal_coverage():
    return {"country": "India", "central_laws": CENTRAL_LAWS, "jurisdictions": list_jurisdictions(),
            "notice": "State/UT-specific rules are not represented as verified unless explicitly marked."}


@app.get("/api/market-research")
async def market_research():
    """Curated, dated India contract-tech market snapshot and editable planning assumptions."""
    import json
    path = Path(__file__).resolve().parent.parent / "data" / "market_research.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/types")
async def types():
    return [t.meta() for t in REGISTRY.values()]


class IntakeIn(BaseModel):
    message: str
    spec: dict
    previous_questions: list[dict] = Field(default_factory=list, max_length=12)


@app.post("/api/intake")
async def intake(body: IntakeIn, svc: Services = Depends(get_services)):
    current = SPEC.validate_python(body.spec)
    spec = await extract(svc.llm, body.message, current, body.previous_questions)
    questions = next_questions(spec, message=body.message, previous_questions=body.previous_questions)
    return {"spec": spec, "missing": missing_fields(spec), "questions": questions}


@app.post("/api/contracts")
async def create_contract(body: dict, svc: Services = Depends(get_services)):
    try:
        spec = SPEC.validate_python(body)
        c = compile_contract(spec)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return await _save(svc, c, "contract_created", {"type": spec.contract_type})


@app.get("/api/contracts")
async def list_contracts(svc: Services = Depends(get_services)):
    out = []
    for c in await svc.repo.list_contracts():
        td = REGISTRY[c["spec"]["contract_type"]]
        out.append({"id": c["id"], "type": td.title, "updated_at": c["updated_at"],
                    "title": f"{c['spec'].get(td.party_a_field)} / {c['spec'].get(td.party_b_field)}"})
    return out


@app.get("/api/contracts/{cid}")
async def get_contract(cid: str, svc: Services = Depends(get_services)):
    return await _load(svc, cid)


@app.get("/api/contracts/{cid}/legal-intelligence")
async def legal_intelligence(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    return analyze_contract(c.spec, c.clauses, list_jurisdictions())


@app.get("/api/contracts/{cid}/statutes")
async def statutes(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    return {cl.key: get_many(cl.legal_basis) for cl in c.clauses if cl.legal_basis}


# ---- legal evidence -----------------------------------------------------
@app.post("/api/contracts/{cid}/evidence/{clause_key}")
async def gather_evidence(cid: str, clause_key: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    cl = next((x for x in c.clauses if x.key == clause_key), None)
    if not cl:
        raise HTTPException(404, "Clause not found")
    d = next((d for d in REGISTRY[c.spec.contract_type].clauses if d.key == clause_key), None)
    if not cl.evidence_queries or not d:
        return {"evidence": [], "note": "No case-law queries are defined for this clause."}
    found = await verify_proposition(clause_key, d.proposition, cl.evidence_queries, svc.kanoon, svc.llm)
    c.evidence = [e for e in c.evidence if e.clause_key != clause_key] + found
    await _save(svc, c, "evidence_gathered", {"clause": clause_key, "verified": sum(e.status == "verified" for e in found)})
    return {"evidence": found}


# ---- adversarial review -------------------------------------------------
@app.get("/api/legal/playbook")
async def legal_playbook():
    """Return the editable illustrative negotiation playbook and risk rubric."""
    return get_playbook()


class PlaybookReviewIn(BaseModel):
    side: str = "not specified"
    deadline: str = "not specified"
    focus_areas: list[str] = []
    deal_context: str = ""


class CopilotRewriteIn(BaseModel):
    clause_key: str = Field(min_length=1, max_length=100)
    instruction: str = Field(min_length=8, max_length=1200)


class CopilotApplyIn(BaseModel):
    suggestion_id: str = Field(min_length=1, max_length=100)


class CopilotTermApplyIn(BaseModel):
    suggestion_id: str = Field(min_length=1, max_length=100)


@app.post("/api/contracts/{cid}/copilot/review")
async def copilot_review(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    checks = REGISTRY[c.spec.contract_type].lint(c.spec) + consistency_check(c.spec)
    result = await ai_contract_review(svc.llm, c, checks)
    await svc.repo.audit(cid, "copilot_review_run", {
        "findings": len(result["findings"]),
        "number_integrity": result["number_integrity"],
    })
    return result


@app.post("/api/contracts/{cid}/copilot/rewrite")
async def copilot_rewrite(cid: str, body: CopilotRewriteIn, svc: Services = Depends(get_services)):
    if len(body.instruction.strip()) < 8:
        raise HTTPException(422, "Describe the clause change in at least 8 characters.")
    c = await _load(svc, cid)
    if any(redline.clause_key == body.clause_key and redline.status == "pending" for redline in c.redlines):
        raise HTTPException(409, "Resolve the pending review redline for this clause before drafting an AI rewrite.")
    try:
        proposal = await ai_rewrite_clause(
            svc.llm, c, body.clause_key, body.instruction, REGISTRY[c.spec.contract_type].labels)
    except ValueError as e:
        raise HTTPException(404, str(e))
    if proposal["intent"] == "term_change":
        change = proposal["term_change"]
        if change["can_apply"] and c.source and c.source.get("uploaded"):
            change["can_apply"] = False
            change["validation_error"] = "This is an uploaded document. Create a draft from the updated agreed terms instead of regenerating its clauses."
        elif change["can_apply"] and (
            c.execution.signed_by_parties or c.execution.stamp_duty_paid or c.execution.registration_completed
        ):
            change["can_apply"] = False
            change["validation_error"] = "This agreement has an execution step recorded. Do not rewrite it; prepare an amendment for review."
        elif change["can_apply"] and any(redline.status == "pending" for redline in c.redlines):
            change["can_apply"] = False
            change["validation_error"] = "Resolve pending review redlines before changing an agreed term."
        if not change["can_apply"]:
            change.pop("suggestion_id", None)
            change.pop("expected_terms", None)
            change.pop("expected_clause_versions", None)
            return proposal
        for existing in c.copilot_term_suggestions:
            if existing.field == change["field"] and existing.status == "pending":
                existing.status = "dismissed"
        c.copilot_term_suggestions.append(CopilotTermSuggestion(
            id=change["suggestion_id"],
            field=change["field"],
            expected_value=change["current_value"],
            proposed_value=change["requested_value"],
            expected_terms=change["expected_terms"],
            expected_clause_versions=change["expected_clause_versions"],
            rationale=change["rationale"],
        ))
        await _save(svc, c, "copilot_term_change_created", {"field": change["field"]})
        return proposal
    for existing in c.copilot_suggestions:
        if existing.clause_key == body.clause_key and existing.status == "pending":
            existing.status = "dismissed"
    c.copilot_suggestions.append(CopilotSuggestion(
        id=proposal["suggestion_id"],
        clause_key=proposal["clause_key"],
        expected_version=proposal["expected_version"],
        original_text=proposal["original_text"],
        proposed_text=proposal["proposed_text"],
        rationale=proposal["rationale"],
        number_integrity=proposal["number_integrity"],
        created_at=proposal["created_at"],
    ))
    await _save(svc, c, "copilot_rewrite_created", {
        "clause": body.clause_key,
        "number_integrity": proposal["number_integrity"],
        "apply_allowed": proposal["apply_allowed"],
    })
    return proposal


@app.post("/api/contracts/{cid}/copilot/terms/apply")
async def copilot_apply_term_change(cid: str, body: CopilotTermApplyIn, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    suggestion = next((item for item in c.copilot_term_suggestions
                       if item.id == body.suggestion_id and item.status == "pending"), None)
    if suggestion is None:
        raise HTTPException(404, "Pending agreement-term proposal not found")
    if c.source and c.source.get("uploaded"):
        raise HTTPException(409, "Uploaded agreements cannot be regenerated from structured terms.")
    if c.execution.signed_by_parties or c.execution.stamp_duty_paid or c.execution.registration_completed:
        raise HTTPException(409, "This agreement has an execution step recorded. Prepare an amendment instead.")
    if any(redline.status == "pending" for redline in c.redlines):
        raise HTTPException(409, "Resolve pending review redlines before changing an agreed term.")

    current_terms = c.spec.model_dump(mode="json", exclude={"provenance"})
    clause_versions = {clause.key: clause.version for clause in c.clauses}
    if current_terms != suggestion.expected_terms or clause_versions != suggestion.expected_clause_versions:
        suggestion.status = "stale"
        await _save(svc, c, "copilot_term_change_stale", {"field": suggestion.field})
        raise HTTPException(409, "The agreement changed after this proposal. Generate a fresh term-change proposal.")
    try:
        updated_data = c.spec.model_dump(mode="python")
        updated_data[suggestion.field] = suggestion.proposed_value
        updated_data.setdefault("provenance", {})[suggestion.field] = "user"
        updated_spec = TypeAdapter(type(c.spec)).validate_python(updated_data)
        updated_contract = compile_contract(updated_spec, contract_id=c.id)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, f"Could not regenerate the agreement: {e}")

    updated_contract.created_at = c.created_at
    return await _save(svc, updated_contract, "copilot_term_change_applied", {
        "field": suggestion.field,
        "old_value": suggestion.expected_value,
        "new_value": suggestion.proposed_value,
    })


@app.post("/api/contracts/{cid}/copilot/terms/{suggestion_id}/dismiss")
async def copilot_dismiss_term_change(cid: str, suggestion_id: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    suggestion = next((item for item in c.copilot_term_suggestions
                       if item.id == suggestion_id and item.status == "pending"), None)
    if suggestion is None:
        raise HTTPException(404, "Pending agreement-term proposal not found")
    suggestion.status = "dismissed"
    return await _save(svc, c, "copilot_term_change_dismissed", {"field": suggestion.field})


@app.post("/api/contracts/{cid}/copilot/apply")
async def copilot_apply(cid: str, body: CopilotApplyIn, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    suggestion = next((item for item in c.copilot_suggestions
                       if item.id == body.suggestion_id and item.status == "pending"), None)
    if suggestion is None:
        raise HTTPException(404, "Pending AI suggestion not found")
    clause = next((item for item in c.clauses if item.key == suggestion.clause_key), None)
    if clause is None:
        raise HTTPException(404, "Clause not found")
    if clause.version != suggestion.expected_version or clause.text != suggestion.original_text:
        suggestion.status = "stale"
        await _save(svc, c, "copilot_suggestion_stale", {"clause": clause.key})
        raise HTTPException(409, "This suggestion is out of date. Generate a fresh proposal for the current clause.")
    if not suggestion.number_integrity:
        raise HTTPException(409, "This proposal changes numeric terms. Update the agreed facts first; this suggestion cannot be applied.")
    if suggestion.proposed_text.strip() == clause.text.strip():
        raise HTTPException(409, "This proposal does not change the clause.")
    if any(redline.clause_key == clause.key and redline.status == "pending" for redline in c.redlines):
        raise HTTPException(409, "Resolve the pending review redline for this clause before applying an AI suggestion.")

    clause.text = suggestion.proposed_text
    clause.version += 1
    clause.status = "revised"
    suggestion.status = "applied"
    for other in c.copilot_suggestions:
        if other.clause_key == clause.key and other.status == "pending":
            other.status = "stale"
    return await _save(svc, c, "copilot_suggestion_applied", {
        "clause": clause.key,
        "version": clause.version,
    })


@app.post("/api/contracts/{cid}/copilot/suggestions/{suggestion_id}/dismiss")
async def copilot_dismiss(cid: str, suggestion_id: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    suggestion = next((item for item in c.copilot_suggestions
                       if item.id == suggestion_id and item.status == "pending"), None)
    if suggestion is None:
        raise HTTPException(404, "Pending AI suggestion not found")
    suggestion.status = "dismissed"
    return await _save(svc, c, "copilot_suggestion_dismissed", {"clause": suggestion.clause_key})


@app.post("/api/contracts/{cid}/playbook-review")
async def run_playbook_review(cid: str, body: PlaybookReviewIn, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    contract_text = "\n\n".join(f"{cl.title}\n{cl.text}" for cl in c.clauses)
    context = body.model_dump()
    result = await playbook_review(svc.llm, contract_text, context)
    await svc.repo.audit(c.id, "playbook_review_run", {"overall_risk": result.overall_risk, "side": body.side})
    return result


class NdaTriageIn(BaseModel):
    text: str = Field(min_length=50, max_length=50000)


@app.post("/api/legal/nda-triage")
async def nda_triage_endpoint(body: NdaTriageIn, svc: Services = Depends(get_services)):
    return await triage_nda(svc.llm, body.text)


@app.post("/api/contracts/{cid}/review")
async def review(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    c.redlines = await review_contract(svc.llm, c.clauses, c.evidence, REGISTRY[c.spec.contract_type])
    return await _save(svc, c, "review_run", {"redlines": len(c.redlines)})


@app.post("/api/contracts/{cid}/redlines/{clause_key}/{decision}")
async def decide(cid: str, clause_key: str, decision: str, svc: Services = Depends(get_services)):
    if decision not in ("accept", "reject"):
        raise HTTPException(400, "decision must be accept or reject")
    c = await _load(svc, cid)
    r = next((r for r in c.redlines if r.clause_key == clause_key and r.status == "pending"), None)
    if not r:
        raise HTTPException(404, "No pending redline for that clause")
    if decision == "accept":
        if r.warning:
            raise HTTPException(409, r.warning)
        cl = next(x for x in c.clauses if x.key == clause_key)
        cl.text, cl.version, cl.status = r.proposed, cl.version + 1, "revised"
        r.status = "accepted"
    else:
        r.status = "rejected"
    return await _save(svc, c, f"redline_{decision}ed", {"clause": clause_key})


# ---- obligations, simulator, execution, export --------------------------
@app.post("/api/contracts/{cid}/simulate")
async def run_simulation(cid: str, scenario: dict, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    try:
        return REGISTRY[c.spec.contract_type].simulate(c.spec, scenario)
    except (ValueError, KeyError) as e:
        raise HTTPException(422, f"Invalid scenario: {e}")


@app.get("/api/contracts/{cid}/execution")
async def execution(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    return checklist(c.spec, c.execution)


class Confirm(BaseModel):
    step: str
    done: bool = True
    note: str


STEPS = {"legal_review_completed", "stamp_duty_verified", "stamp_duty_paid", "registration_completed", "signed_by_parties"}


@app.post("/api/contracts/{cid}/execution/confirm")
async def confirm(cid: str, body: Confirm, svc: Services = Depends(get_services)):
    if body.step not in STEPS:
        raise HTTPException(400, f"step must be one of {sorted(STEPS)}")
    if body.done and len(body.note.strip()) < 5:
        raise HTTPException(422, "Record the evidence (receipt number, date, who confirmed) in the note.")
    c = await _load(svc, cid)
    setattr(c.execution, body.step, body.done)
    c.execution.notes[body.step] = body.note
    return await _save(svc, c, "execution_confirmed", body.model_dump())


@app.get("/api/contracts/{cid}/lint")
async def lint(cid: str, svc: Services = Depends(get_services)):
    """Deterministic structural checks (no LLM). These are prompts for a lawyer, not legal conclusions."""
    c = await _load(svc, cid)
    return REGISTRY[c.spec.contract_type].lint(c.spec) + consistency_check(c.spec)


@app.get("/api/contracts/{cid}/obligations")
async def obligations(cid: str, svc: Services = Depends(get_services)):
    """Machine-readable terms: obligations, key dates and the document fingerprint."""
    c = await _load(svc, cid)
    td = REGISTRY[c.spec.contract_type]
    return {"contract_type": c.spec.contract_type, "fingerprint": fingerprint(c),
            "terms": c.spec.model_dump(mode="json", exclude={"provenance"}),
            "obligations": [o.model_dump() for o in c.obligations],
            "key_dates": [{"date": e["date"].isoformat(), "title": e["title"]} for e in td.key_dates(c.spec)]}


@app.get("/api/contracts/{cid}/calendar.ics")
async def calendar(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    events = sorted(REGISTRY[c.spec.contract_type].key_dates(c.spec), key=lambda e: e["date"])
    return Response(build_ics(c, events), media_type="text/calendar",
                    headers={"Content-Disposition": f'attachment; filename="contract-dates-{cid[:8]}.ics"'})


@app.get("/api/contracts/{cid}/fingerprint")
async def get_fingerprint(cid: str, svc: Services = Depends(get_services)):
    return {"sha256": fingerprint(await _load(svc, cid))}


class AskIn(BaseModel):
    question: str


@app.post("/api/contracts/{cid}/ask")
async def ask_contract(cid: str, body: AskIn, svc: Services = Depends(get_services)):
    """Tool-using agent over this agreement; the answer is verified in code (clause citations, figures)."""
    if not body.question.strip():
        raise HTTPException(422, "Ask a question.")
    c = await _load(svc, cid)
    res = await ask_agent(svc.llm, c, REGISTRY[c.spec.contract_type], body.question.strip()[:1000])
    await svc.repo.audit(cid, "question_asked", {"q": body.question[:200], "warnings": len(res["warnings"])})
    return res


class ExplainIn(BaseModel):
    language: str = "English"


@app.post("/api/contracts/{cid}/explain")
async def explain(cid: str, body: ExplainIn, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    try:
        return await explain_contract(svc.llm, c, body.language)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/contracts/{cid}/consequence-map")
async def get_consequence_map(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    return consequence_map(c.spec)


class UploadIn(BaseModel):
    filename: str | None = None
    content_b64: str | None = None
    text: str | None = None
    contract_type: str | None = None




class TranslateIn(BaseModel):
    text: str
    target_language: str
    source_language: str = "auto"

@app.post("/api/translate")
async def translate_text(body: TranslateIn, svc: Services = Depends(get_services)):
    if not body.text.strip() or len(body.text) > 12000:
        raise HTTPException(422, "Provide text up to 12,000 characters.")
    if body.target_language.casefold() in {"english", "en", "en-in"} and body.source_language.casefold() in {"english", "en", "en-in"}:
        return {"translated_text": body.text, "source_language": body.source_language, "target_language": body.target_language, "mode": "no_translation_needed", "legal_status": "translation_is_not_a_legal_opinion"}
    system = ("You are a careful multilingual translator for Indian legal and commercial documents. Translate faithfully into the requested language. Preserve names, dates, amounts, section numbers, defined terms, clause numbering, citations and formatting. Do not summarize, add legal advice, change obligations, or resolve ambiguity. If a phrase has no reliable equivalent, retain the original legal term in parentheses. Output only the translation. State that translation is informational and the source-language signed text controls unless the parties expressly agree otherwise.")
    prompt = f"Source language: {body.source_language}. Target language: {body.target_language}.\n\nTranslate the following text faithfully:\n{body.text}"
    translated = await svc.llm.complete_text(system, prompt)
    from .textutil import numbers
    source_numbers, translated_numbers = numbers(body.text), numbers(translated)
    return {"translated_text": translated, "source_language": body.source_language, "target_language": body.target_language, "mode": "llm_translation",
            "number_integrity": source_numbers == translated_numbers,
            "missing_numbers": sorted(source_numbers - translated_numbers),
            "extra_numbers": sorted(translated_numbers - source_numbers),
            "legal_status": "informational_translation_not_certified_or_authoritative"}

class DemoAuthIn(BaseModel):
    user_label: str = "Demo participant"
    role: str = "citizen"

@app.post("/api/demo/auth/session")
async def demo_auth_session(body: DemoAuthIn):
    if body.role not in {"citizen", "advocate", "business"}:
        raise HTTPException(422, "Choose citizen, advocate or business.")
    return {"status":"SIMULATED_ONLY", "provider":"MAATAMUDRA demo identity flow", "user_label":body.user_label[:80], "role":body.role, "steps":["User selects a role", "Demo consent screen shown", "Demo session identifier generated (not an authenticated account)"], "real_authentication":False, "notice":"No identity verification, account authentication or access-control protection has occurred. Do not upload confidential documents to a public demo."}

@app.post("/api/demo/signing/session")
async def demo_signing_session(body: dict):
    cid = str(body.get("contract_id") or "")
    if not cid:
        raise HTTPException(422, "contract_id is required")
    return {"status":"SIMULATED_ONLY", "provider":"Illustrative CCA-compliant eSign provider adapter", "contract_id":cid, "steps":["Document hash generated", "Signer identity/KYC hand-off would occur at the selected authorized provider", "Signer consent would be captured", "Provider would apply its legally recognized signing process", "Provider callback and certificate evidence would be verified", "Final signed document and audit evidence would be returned"], "document_hash":None, "signature_applied":False, "identity_verified":False, "provider_connected":False, "notice":"This is a workflow simulation only. No Aadhaar/eKYC, CCA service, digital signature, stamp duty payment or legal execution has occurred."}

@app.post("/api/upload/analyze")
async def upload_analyze(body: UploadIn, svc: Services = Depends(get_services)):
    try:
        if body.content_b64:
            if len(body.content_b64) > 14_000_000:
                raise ValueError("File is too large. The hackathon demo limit is 10 MB.")
            try:
                raw_file = base64.b64decode(body.content_b64, validate=True)
            except (ValueError, base64.binascii.Error):
                raise ValueError("The uploaded file encoding is invalid.")
            if len(raw_file) > 10 * 1024 * 1024:
                raise ValueError("File is too large. The hackathon demo limit is 10 MB.")
            text, extraction_method = extract_text_with_method(body.filename or "", raw_file)
        elif body.text and len(body.text.strip()) >= 80:
            text = body.text.strip()[:60000]
            extraction_method = "pasted_text"
        else:
            raise ValueError("Upload a .docx, .pdf or .txt file, or paste at least a few sentences of the agreement.")
        result = await analyze_upload(svc.llm, text, body.contract_type)
        result["extraction_method"] = extraction_method
        return result
    except ValueError as e:
        raise HTTPException(422, str(e))


class OpenUploadIn(BaseModel):
    spec: dict
    segments: list[dict]
    filename: str | None = None


@app.post("/api/upload/contract")
async def upload_open(body: OpenUploadIn, svc: Services = Depends(get_services)):
    try:
        c = build_contract(SPEC.validate_python(body.spec), body.segments, body.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return await _save(svc, c, "contract_opened_from_upload", {"file": body.filename})


@app.get("/api/contracts/{cid}/docx")
async def export_docx(cid: str, svc: Services = Depends(get_services)):
    c = await _load(svc, cid)
    return Response(build_docx(c), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="agreement-{cid[:8]}.docx"'})


@app.get("/api/contracts/{cid}/audit")
async def audit(cid: str, svc: Services = Depends(get_services)):
    return await svc.repo.audit_for(cid)


# Word add-in: manifest + API router, then its static task-pane files (must come before the catch-all "/" mount).
app.include_router(addin_router)
mount_addin(app)

# Serve the built frontend when present (single-container deployment).
_static = Path(__file__).resolve().parents[1] / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
