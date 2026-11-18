"""Check a contract you RECEIVED: extract text, find the type, segment it into clauses, label each against our
clause library, extract its terms, and run gap analysis and checks. The result can be opened as a normal workspace
(case-law checks, two-sided review and the time machine then run on the user's own text and terms)."""
from __future__ import annotations

import io
import re
import uuid
from typing import Optional

from pydantic import BaseModel

from .analysis.consistency import check
from .contracts.intake import extract
from .models import Clause, Contract
from .types import REGISTRY

MAX_CHARS = 60000
MAX_SEGMENTS = 60


def extract_text_with_method(filename: str, data: bytes) -> tuple[str, str]:
    """Extract DOCX/PDF/TXT. For image-only PDFs, render bounded pages with PyMuPDF and OCR via Tesseract."""
    name = (filename or "").lower()
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("File is too large. The hackathon demo limit is 10 MB.")
    method = "plain_text"
    if name.endswith(".docx"):
        method = "docx_text"
        from docx import Document
        d = Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text.strip() for c in row.cells))
        text = "\n".join(parts)
    elif name.endswith(".pdf"):
        method = "pymupdf_text"
        text = ""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=data, filetype="pdf")
            if doc.page_count > 30:
                raise ValueError("PDF exceeds the 30-page hackathon review limit.")
            extracted = [page.get_text("text") or "" for page in doc]
            text = "\n".join(extracted).strip()
            if len(text) < 80:
                try:
                    import pytesseract
                    from PIL import Image
                    ocr_parts = []
                    langs = "eng"
                    try:
                        available = set(pytesseract.get_languages(config=""))
                        wanted = [x for x in ("eng", "hin", "tel") if x in available]
                        langs = "+".join(wanted) if wanted else "eng"
                    except Exception:
                        pass
                    for page in doc:
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        image = Image.open(io.BytesIO(pix.tobytes("png")))
                        ocr_parts.append(pytesseract.image_to_string(image, lang=langs))
                    ocr_text = "\n".join(ocr_parts).strip()
                    if len(ocr_text) > len(text):
                        text = ocr_text
                        method = f"tesseract_ocr:{langs}"
                except Exception as exc:
                    raise ValueError("This PDF appears scanned. Install Tesseract OCR (eng; optional hin/tel language packs) to read it. OCR detail: " + str(exc)[:180])
            doc.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("Could not read this PDF: " + str(exc)[:180])
    else:
        text = data.decode("utf-8", errors="replace")
    text = text.strip()
    if len(text) < 80:
        raise ValueError("Could not read enough text from the file. Check the scan quality or paste the text instead.")
    return text[:MAX_CHARS], method


def extract_text(filename: str, data: bytes) -> str:
    """Backward-compatible text-only helper used by tests and internal callers."""
    return extract_text_with_method(filename, data)[0]


_HEAD = re.compile(r"^\s*(?:clause\s+\d+|\d{1,2}(?:\.\d{1,2})*[\.\):]|\d{1,2}\s+[A-Z][A-Za-z])", re.I)


def segment(text: str) -> list[dict]:
    segs: list[list[str]] = [[]]
    for line in text.splitlines():
        if not line.strip():
            continue
        if _HEAD.match(line) and segs[-1]:
            segs.append([])
        segs[-1].append(line.strip())
    if len(segs) < 3:  # no numbering: fall back to paragraphs
        segs = [[p.strip()] for p in re.split(r"\n\s*\n", text) if p.strip()]
    merged: list[list[str]] = []
    for s in segs:
        if merged and len(" ".join(s)) < 40:
            merged[-1].extend(s)
        else:
            merged.append(list(s))
    out = []
    for i, s in enumerate(merged[:MAX_SEGMENTS]):
        body = " ".join(s)[:1500]
        out.append({"idx": i, "heading": s[0][:70], "text": body})
    return out


class TypeGuess(BaseModel):
    contract_type: str   # one of the supported keys, or "other"
    reason: str


class Label(BaseModel):
    idx: int
    clause_key: Optional[str] = None
    concern: Optional[str] = None


class Labels(BaseModel):
    labels: list[Label]


TYPE_SYSTEM = ("Decide which kind of agreement this is. Answer with exactly one of: {keys}, or 'other' if none fits. "
               "rental_agreement = residential lease/rent; freelance_service = independent contractor/service; "
               "employment = employer-employee; nda = non-disclosure/confidentiality; "
               "sale_purchase = sale of physical goods; partnership = partners operating a business; "
               "private_loan = simple loan between private parties; ip_licence = permission to use intellectual property; "
               "mou = memorandum of understanding for a collaboration.")
LABEL_SYSTEM = ("You label numbered segments of an Indian {kind} against a fixed clause list. For each segment give "
                "clause_key = the single best-matching key from this list, or null if none fits: {keys}. "
                "concern = one short sentence naming a risk or unusual feature a careful reader should notice, or null. "
                "Never invent keys. Do not give legal conclusions.")


async def classify_type(llm, text: str) -> str:
    g = await llm.structured(TYPE_SYSTEM.format(keys=", ".join(REGISTRY)), text[:6000], TypeGuess)
    if g.contract_type not in REGISTRY:
        raise ValueError("This looks like an agreement type Vachan does not support yet (rental, freelancer/service, employment).")
    return g.contract_type


def gap_analysis(td, matched: set[str]) -> dict:
    core, optional = [], []
    for d in td.clauses:
        if d.key in matched:
            continue
        item = {"clause_key": d.key, "title": d.title, "risk": d.risk,
                "why": d.proposition or "A usual part of this kind of agreement."}
        (core if all(r in td.required for r in d.requires) else optional).append(item)
    return {"missing_basics": core, "worth_considering": optional}


async def analyze(llm, text: str, contract_type: str | None = None) -> dict:
    ct = contract_type if contract_type in REGISTRY else await classify_type(llm, text)
    td = REGISTRY[ct]
    segs = segment(text)
    allowed = [d.key for d in td.clauses]
    listing = "\n".join(f"{s['idx']}: {s['text'][:500]}" for s in segs)
    labels = await llm.structured(LABEL_SYSTEM.format(kind=td.title.lower(), keys=", ".join(allowed)), listing, Labels)
    by_idx = {l.idx: l for l in labels.labels}
    for s in segs:
        l = by_idx.get(s["idx"])
        key = l.clause_key if l and l.clause_key in allowed else None  # model cannot introduce keys
        s["clause_key"], s["concern"] = key, (l.concern if l else None)
    spec = await extract(llm, text[:15000], td.spec_cls())
    spec.provenance = {k: ("document" if v == "user" else v) for k, v in spec.provenance.items()}
    matched = {s["clause_key"] for s in segs if s["clause_key"]}
    missing = td.missing(spec)
    checks = []
    if not missing:
        checks = td.lint(spec) + check(spec)
    return {"contract_type": ct, "type_title": td.title, "segments": segs, "spec": spec, "missing": missing,
            "questions": [{"field": f, "question": td.questions[f]} for f in missing[:4]],
            "gaps": gap_analysis(td, matched), "checks": checks}


def build_contract(spec, segments: list[dict], filename: str | None = None) -> Contract:
    from .analysis.consistency import errors

    td = REGISTRY[spec.contract_type]
    missing = td.missing(spec)
    if missing:
        raise ValueError(f"Cannot open: missing required terms {missing}")
    errs = errors(spec)
    if errs:
        raise ValueError("The terms contradict each other: " + "; ".join(e["message"] for e in errs))
    lib = {d.key: d for d in td.clauses}
    clauses: list[Clause] = []
    seen: set[str] = set()
    for s in segments:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        key = s.get("clause_key")
        d = lib.get(key) if key else None
        if d and key not in seen:
            seen.add(key)
            clauses.append(Clause(key=key, title=d.title, text=text, original_text=text, risk=d.risk,
                                  legal_basis=d.legal_basis, evidence_queries=d.evidence_queries))
        else:
            n = sum(1 for c in clauses if c.key.startswith("other_")) + 1
            clauses.append(Clause(key=f"other_{n}", title=(s.get("heading") or f"Clause {n}")[:60], text=text, original_text=text))
    if not clauses:
        raise ValueError("No clauses to open.")
    c = Contract(id=str(uuid.uuid4()), spec=spec, clauses=clauses, source={"filename": filename, "uploaded": True})
    c.obligations = td.obligations(spec)
    return c
