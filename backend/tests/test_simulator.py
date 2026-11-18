from datetime import date

import pytest

from app.obligations import simulator as sim


def test_schedule_length_and_days(spec):
    s = sim.rent_schedule(spec)
    assert len(s) == 11
    assert s[0] == date(2026, 12, 5) and s[1] == date(2027, 1, 5)


def test_lease_end(spec):
    assert sim.lease_end(spec) == date(2027, 10, 31)


def test_on_time_has_no_fee(spec):
    r = sim.late_payment(spec, 0, 0)
    assert r["late_fee"] == 0 and r["default_notice_possible_under_contract"] is False


def test_20_days_late_fee_after_grace(spec):
    r = sim.late_payment(spec, 0, 20)
    assert r["late_fee"] == (20 - 5) * 50
    assert r["default_notice_possible_under_contract"] is False  # threshold is 30


def test_30_days_late_crosses_default_threshold(spec):
    r = sim.late_payment(spec, 0, 30)
    assert r["default_notice_possible_under_contract"] is True
    assert r["cure_deadline_if_notice_served_on_threshold"] == "2027-01-19"  # Dec 5 + 30 + 15


def test_no_mechanism_means_no_invented_fee(spec):
    s = spec.model_copy(update={"grace_days": None, "late_fee_per_day": None,
                                "default_threshold_days": None, "cure_days": None})
    r = sim.late_payment(s, 0, 45)
    assert r["late_fee"] is None and r["default_notice_possible_under_contract"] is None
    assert any("no late-fee mechanism" in n for n in r["notes"])


def test_tenant_exit_inside_lock_in_is_liable(spec):
    r = sim.early_termination(spec, "tenant", date(2026, 12, 20))
    assert r["notice_effective"] == "2027-01-19"
    assert r["lock_in_end"] == "2027-05-31"
    # dues after Jan 19 up to May 31: Feb, Mar, Apr, May 5th
    assert r["lock_in_rent_liability"] == 4 * 22000


def test_exit_after_lock_in_has_no_liability(spec):
    r = sim.early_termination(spec, "tenant", date(2027, 6, 1))
    assert r["lock_in_rent_liability"] == 0


def test_landlord_cannot_exit_in_lock_in(spec):
    r = sim.early_termination(spec, "landlord", date(2026, 12, 20))
    assert any("not permitted" in n for n in r["notes"])


def test_deposit_return_deadline_and_overdue(spec):
    r = sim.deposit_return(spec, date(2027, 10, 31), [{"label": "paint", "amount": 4000}], date(2027, 12, 15))
    assert r["refund_amount"] == 40000 and r["refund_due_date"] == "2027-11-30" and r["days_overdue"] == 15


def test_deductions_exceeding_deposit(spec):
    r = sim.deposit_return(spec, date(2027, 10, 31), [{"label": "x", "amount": 50000}])
    assert r["refund_amount"] == 0 and any("exceed" in n for n in r["notes"])


def test_bad_inputs_rejected(spec):
    with pytest.raises(ValueError):
        sim.late_payment(spec, 99, 3)
    with pytest.raises(ValueError):
        sim.simulate(spec, {"type": "nope"})
