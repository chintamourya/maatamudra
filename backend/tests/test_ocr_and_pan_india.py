import io
from PIL import Image, ImageDraw, ImageFont
import fitz
from app.upload_review import extract_text, extract_text_with_method
from app.execution.checklist import checklist
from app.legal.jurisdictions import list_jurisdictions
from app.types import REGISTRY
from app.models import ExecutionStatus, RentalSpec
from datetime import date

def scanned_pdf(text="SERVICE AGREEMENT BETWEEN THE PARTIES WITH PAYMENT TERMS AND TERMINATION CONDITIONS FOR THE PROVIDED PROFESSIONAL SERVICES."):
    im=Image.new("RGB",(1200,500),"white")
    d=ImageDraw.Draw(im); d.multiline_text((40,80),"SERVICE AGREEMENT BETWEEN THE PARTIES\nWITH PAYMENT TERMS AND TERMINATION\nCONDITIONS FOR PROFESSIONAL SERVICES.",fill="black",font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",30))
    b=io.BytesIO(); im.save(b,format="PNG")
    doc=fitz.open(); page=doc.new_page(width=600,height=250); page.insert_image(page.rect,stream=b.getvalue())
    out=doc.tobytes(); doc.close(); return out

def test_scanned_pdf_ocr_extracts_text():
    result, method=extract_text_with_method("scan.pdf",scanned_pdf())
    assert "SERVICE" in result.upper()
    assert method.startswith("tesseract_ocr:")

def test_execution_checklist_supports_all_36_jurisdictions():
    for j in list_jurisdictions():
        spec=RentalSpec(state=j["name"],city="Test City",landlord_name="A",tenant_name="B",property_address="Test",start_date=date(2026,12,1),term_months=11,monthly_rent=10000,security_deposit=20000,due_day=5,notice_days=30,grace_days=5,late_fee_per_day=0,default_threshold_days=30,cure_days=15,deposit_refund_days=30,lock_in_months=0)
        out=checklist(spec,ExecutionStatus())
        assert out["supported"] is True, j["name"]
        assert len(out["items"]) >= 4

def test_supported_templates_have_nonempty_clause_sets():
    assert len(REGISTRY) >= 9
    for key, td in REGISTRY.items():
        assert td.title
        assert td.clauses, key

def test_jurisdiction_registry_marks_portal_and_rule_limits():
    rows=list_jurisdictions()
    assert sum(x["digital_e_stamp_status"] == "listed_on_NeSL_DDE_directory" for x in rows) == 30
    assert all("stamp_duty_amounts" in x["not_verified"] for x in rows)

def test_evaluation_benchmark_has_all_supported_template_types():
    import json
    from pathlib import Path
    path=Path(__file__).resolve().parents[2] / "evaluation" / "benchmark_cases.json"
    data=json.loads(path.read_text())
    types={x["contract_type"] for x in data["cases"]}
    assert set(REGISTRY).issubset(types)
