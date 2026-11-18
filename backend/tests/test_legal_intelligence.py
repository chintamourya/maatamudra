from types import SimpleNamespace
from app.legal.jurisdictions import STATES_AND_UTS, list_jurisdictions
from app.legal.intelligence import analyze_contract


def test_pan_india_catalogue_has_all_36_states_and_uts():
    assert len(STATES_AND_UTS) == 36
    assert len(list_jurisdictions()) == 36
    assert "Telangana" in STATES_AND_UTS
    assert "Ladakh" in STATES_AND_UTS


def test_unknown_state_is_not_silently_treated_as_verified():
    spec = SimpleNamespace(contract_type="rental_agreement", state="Atlantis", term_months=11,
                           non_compete_months=None)
    report = analyze_contract(spec, [], list_jurisdictions())
    assert report["jurisdiction"]["catalogue_match"] is False
    assert any(f["id"] == "jurisdiction_unrecognised" for f in report["findings"])


def test_rental_longer_than_one_year_flags_registration_review():
    spec = SimpleNamespace(contract_type="rental_agreement", state="Assam", term_months=18,
                           non_compete_months=None)
    report = analyze_contract(spec, [], list_jurisdictions())
    assert any(f["id"] == "lease_registration" for f in report["findings"])
    assert report["jurisdiction"]["state_rules_verified"] is False


def test_non_compete_is_flagged_without_claiming_invalidity():
    spec = SimpleNamespace(contract_type="employment", state="Delhi", term_months=None,
                           non_compete_months=12)
    report = analyze_contract(spec, [], list_jurisdictions())
    finding = next(f for f in report["findings"] if f["id"] == "restraint_of_trade")
    assert finding["severity"] == "high"
    assert "may raise" in finding["message"]
    assert "void" not in finding["message"].lower()


def test_freelance_always_prompts_msme_status():
    spec = SimpleNamespace(contract_type="freelance_service", state="Kerala", term_months=None, non_compete_months=None)
    report = analyze_contract(spec, [], list_jurisdictions())
    assert any(f["id"] == "msme_status_check" for f in report["findings"])
