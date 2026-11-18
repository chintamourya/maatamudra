from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from ..extras import fingerprint
from ..models import Contract
from ..types import REGISTRY


def build_docx(c: Contract) -> bytes:
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(11.5)

    td = REGISTRY[c.spec.contract_type]
    h = doc.add_heading(td.doc_title, level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph("DRAFT. Not legally validated, stamped, registered or signed.")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].italic = True

    for i, cl in enumerate(c.clauses, 1):
        para = doc.add_paragraph()
        r = para.add_run(f"{i}. {cl.title}. ")
        r.bold = True
        para.add_run(cl.text)

    doc.add_paragraph()
    t = doc.add_table(rows=3, cols=2)
    t.cell(0, 0).text = td.party_a.upper()
    t.cell(0, 1).text = td.party_b.upper()
    t.cell(1, 0).text = f"\n\n______________________\n{getattr(c.spec, td.party_a_field)}"
    t.cell(1, 1).text = f"\n\n______________________\n{getattr(c.spec, td.party_b_field)}"
    t.cell(2, 0).text = "Witness 1: ______________"
    t.cell(2, 1).text = "Witness 2: ______________"

    doc.add_page_break()
    doc.add_heading("Annexure A: Legal evidence", level=2)
    verified = [e for e in c.evidence if e.status == "verified"]
    if not verified:
        doc.add_paragraph("No verified judgments are attached to this draft.")
    titles = {cl.key: cl.title for cl in c.clauses}
    for e in verified:
        doc.add_paragraph().add_run(f"Clause: {titles.get(e.clause_key, e.clause_key)}").bold = True
        doc.add_paragraph(f"{e.title} ({e.court or 'court n/a'}, {e.date or 'date n/a'})")
        doc.add_paragraph(f"Source: {e.url}   Retrieved: {e.retrieved_at[:10]}")
        doc.add_paragraph(f"Retrieved passage: {e.passage}")
    doc.add_heading("Annexure B: Execution status", level=2)
    s = c.execution
    for label, val in [
        ("Draft prepared", s.draft_prepared), ("Legal review completed", s.legal_review_completed),
        ("Stamp duty verified", s.stamp_duty_verified), ("Stamp duty paid", s.stamp_duty_paid),
        ("Registration completed", s.registration_completed), ("Signed by parties", s.signed_by_parties),
    ]:
        doc.add_paragraph(f"{label}: {'Yes' if val else 'No / not confirmed'}", style="List Bullet")
    doc.add_paragraph(f"Document fingerprint (SHA-256 of the agreed terms and clause text): {fingerprint(c)}")
    doc.add_paragraph("This is an assistive draft and not legal advice. Have a lawyer review it before use.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
