"""Compiles a spec into machine-readable obligations. Deterministic, no LLM."""
from __future__ import annotations

from ..models import Obligation, RentalSpec


def compile_obligations(spec: RentalSpec) -> list[Obligation]:
    ob: list[Obligation] = []

    def add(kind, party, clause, desc, **rule):
        ob.append(Obligation(id=f"{kind}", kind=kind, party=party, clause_key=clause, description=desc, rule=rule))

    add("pay_rent", "tenant", "rent", f"Pay rent on or before day {spec.due_day} of each month",
        amount=spec.monthly_rent, due_day=spec.due_day)
    if spec.grace_days is not None and spec.late_fee_per_day is not None:
        add("late_fee", "tenant", "late_payment", "Pay a late fee per day after the grace period",
            grace_days=spec.grace_days, per_day=spec.late_fee_per_day)
    if spec.default_threshold_days is not None and spec.cure_days is not None:
        add("default_notice", "landlord", "default_cure",
            "Landlord may serve a default notice once rent is overdue for the threshold; tenant may cure within the cure period",
            threshold_days=spec.default_threshold_days, cure_days=spec.cure_days)
    add("termination_notice", "both", "termination_notice", "Give written notice to end the tenancy",
        notice_days=spec.notice_days)
    if spec.lock_in_months:
        add("lock_in", "both", "lock_in", "No termination during the lock-in period", months=spec.lock_in_months)
    if spec.deposit_refund_days is not None:
        add("refund_deposit", "landlord", "deposit_refund", "Return deposit less itemised lawful deductions",
            amount=spec.security_deposit, within_days=spec.deposit_refund_days)
    if spec.annual_escalation_pct is not None:
        add("escalation", "both", "escalation", "Rent escalation applies on written renewal",
            pct=spec.annual_escalation_pct)
    return ob
