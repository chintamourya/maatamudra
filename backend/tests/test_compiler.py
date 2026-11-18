import pytest

from app.contracts.compiler import compile_contract, inr
from app.models import RentalSpec, missing_fields


def test_inr_grouping():
    assert inr(22000) == "₹22,000" and inr(1234567) == "₹12,34,567" and inr(500) == "₹500"


def test_missing_required_blocks_compile():
    with pytest.raises(ValueError):
        compile_contract(RentalSpec(landlord_name="A"))


def test_full_spec_compiles_all_clauses(spec):
    c = compile_contract(spec)
    keys = [x.key for x in c.clauses]
    assert {"late_payment", "default_cure", "lock_in", "termination_notice", "deposit_refund"} <= set(keys)
    rent = next(x for x in c.clauses if x.key == "rent")
    assert "₹22,000" in rent.text and "5th" in rent.text
    assert {o.kind for o in c.obligations} >= {"pay_rent", "late_fee", "termination_notice", "lock_in"}


def test_optional_mechanisms_are_omitted_not_invented(spec):
    s = spec.model_copy(update={"grace_days": None, "lock_in_months": None, "default_threshold_days": None})
    keys = [x.key for x in compile_contract(s).clauses]
    assert "late_payment" not in keys and "lock_in" not in keys and "default_cure" not in keys
    assert "rent" in keys and "termination_notice" in keys


def test_missing_fields_listing():
    assert "monthly_rent" in missing_fields(RentalSpec())
