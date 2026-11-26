"""Small transparent benchmark for deterministic MAATAMUDRA legal issue spotting."""
from types import SimpleNamespace
from app.legal.jurisdictions import list_jurisdictions
from app.legal.intelligence import analyze_contract

def spec(kind="rental_agreement", state="Telangana", term=18, non_compete=None):
    return SimpleNamespace(contract_type=kind, state=state, term_months=term, non_compete_months=non_compete)

def test_all_36_jurisdictions_have_official_directory_record():
    rows=list_jurisdictions()
    assert len(rows)==36
    assert len({r["name"] for r in rows})==36
    assert all(r["registration_source"].startswith("https://ngdrs.gov.in/") for r in rows)

def test_unknown_stamp_amount_is_not_invented_and_portal_is_exposed():
    report=analyze_contract(spec(), [], list_jurisdictions())
    assert report["jurisdiction"]["registration_portal"] == "https://registration.telangana.gov.in/"
    assert any(f["id"]=="rental_stamp_duty" for f in report["findings"])
    assert any(f["category"]=="coverage_gap" for f in report["findings"])

def test_rental_over_one_year_flags_registration_review():
    report=analyze_contract(spec(term=18), [], list_jurisdictions())
    assert any(f["id"]=="lease_registration" for f in report["findings"])

def test_post_term_non_compete_flags_section_27_review():
    report=analyze_contract(spec(kind="employment", term=None, non_compete=6), [], list_jurisdictions())
    finding=next(f for f in report["findings"] if f["id"]=="restraint_of_trade")
    assert "section 27" in finding["message"].lower()

def test_no_state_selected_is_explicit():
    report=analyze_contract(spec(state=None), [], list_jurisdictions())
    assert any(f["id"]=="jurisdiction_missing" for f in report["findings"])
