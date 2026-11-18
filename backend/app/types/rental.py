from __future__ import annotations

from datetime import timedelta

from ..contracts.compiler import end_date, inr, ordinal
from ..contracts.library import RENTAL
from ..models import RentalSpec
from ..obligations.compiler import compile_obligations
from ..obligations.simulator import lease_end, rent_schedule, simulate
from .base import TypeDef

REQUIRED = ["state", "landlord_name", "tenant_name", "property_address", "start_date", "term_months",
            "monthly_rent", "security_deposit", "due_day", "notice_days"]
QUESTIONS = {
    "state": "Which Indian state or Union Territory is the property in?",
    "landlord_name": "What is the landlord's full name?",
    "tenant_name": "What is the tenant's full name?",
    "property_address": "What is the full address of the property being rented?",
    "start_date": "When should the tenancy start?",
    "term_months": "For how many months is the agreement (for example 11)?",
    "monthly_rent": "What is the monthly rent in rupees?",
    "security_deposit": "How much is the security deposit in rupees?",
    "due_day": "On which day of each month is rent due?",
    "notice_days": "How many days' written notice must either side give to end the tenancy?",
}
LABELS = {
    "state": "State / UT", "city": "City", "landlord_name": "Landlord", "tenant_name": "Tenant", "property_address": "Property", "start_date": "Start",
    "term_months": "Months", "monthly_rent": "Rent", "security_deposit": "Deposit", "due_day": "Rent due day",
    "notice_days": "Notice days", "grace_days": "Grace days", "late_fee_per_day": "Late fee/day",
    "default_threshold_days": "Default after (days)", "cure_days": "Cure days",
    "deposit_refund_days": "Refund within (days)", "lock_in_months": "Lock-in months",
    "maintenance_monthly": "Maintenance/month", "annual_escalation_pct": "Escalation %",
}


def context(spec: RentalSpec) -> dict:
    ctx = {k: v for k, v in spec.model_dump().items() if v is not None}
    for f in ("monthly_rent", "security_deposit", "maintenance_monthly", "late_fee_per_day"):
        if ctx.get(f) is not None:
            ctx[f] = inr(ctx[f])
    ctx["start_date"] = spec.start_date.strftime("%d %B %Y")
    ctx["end_date"] = end_date(spec).strftime("%d %B %Y")
    ctx["due_day_ord"] = ordinal(spec.due_day)
    ctx["place"] = spec.city or spec.state or "the place of execution"
    ctx["state"] = spec.state or "the relevant state"
    return ctx


def key_dates(spec: RentalSpec) -> list[dict]:
    out = [{"date": d, "title": f"Rent due: {inr(spec.monthly_rent)}"} for d in rent_schedule(spec)]
    end = lease_end(spec)
    out.append({"date": end, "title": "Lease term ends"})
    out.append({"date": end - timedelta(days=spec.notice_days), "title": "Last day to give notice before the term ends"})
    return out


def lint(spec: RentalSpec) -> list[dict]:
    f = []
    if spec.notice_days == 0:
        f.append({"clause_key": "termination_notice", "severity": "high", "message": "No notice period: either side can end the tenancy immediately. Courts and tenancy law usually expect a defined notice."})
    if spec.default_threshold_days is None:
        f.append({"clause_key": "termination_notice", "severity": "medium", "message": "No default-and-cure clause: what happens on non-payment of rent is left to the notice clause and general law."})
    if spec.deposit_refund_days is None:
        f.append({"clause_key": "security_deposit", "severity": "medium", "message": "No deadline for returning the deposit."})
    if spec.grace_days is None or spec.late_fee_per_day is None:
        f.append({"clause_key": "rent", "severity": "low", "message": "No late-payment mechanism. Late rent has no contractual consequence."})
    if spec.term_months > 11:
        f.append({"clause_key": "term", "severity": "medium", "message": "Term is longer than 11 months: check whether registration is required."})
    return f


SCENARIOS = [
    {"type": "late_payment", "label": "Rent paid late", "inputs": [
        {"name": "days_late", "label": "Days late", "kind": "range", "min": 0, "max": 90, "default": 20}],
     "fixed": {"month_index": 0}},
    {"type": "early_termination", "label": "Someone ends the tenancy early", "inputs": [
        {"name": "party", "label": "Who gives notice", "kind": "select", "options": ["tenant", "landlord"], "default": "tenant"},
        {"name": "notice_date", "label": "Notice date", "kind": "date", "default": "2026-12-20"}]},
    {"type": "deposit_return", "label": "Deposit is returned", "inputs": [
        {"name": "handover_date", "label": "Handover date", "kind": "date", "default": "2027-10-31"},
        {"name": "deduction_amount", "label": "Deductions (₹)", "kind": "number", "default": 0}]},
    {"type": "renewal", "label": "Agreement is renewed", "inputs": []},
]

SAMPLE = {
    "contract_type": "rental_agreement", "state": "Telangana", "city": "Hyderabad", "landlord_name": "Ravi Kumar",
    "tenant_name": "Anita Rao", "property_address": "Flat 302, Green Heights, Madhapur, Hyderabad",
    "start_date": "2026-12-01", "term_months": 11, "monthly_rent": 22000, "security_deposit": 44000, "due_day": 5,
    "notice_days": 30, "grace_days": 5, "late_fee_per_day": 50, "default_threshold_days": 30, "cure_days": 15,
    "deposit_refund_days": 30, "lock_in_months": 6, "provenance": {},
}

RENTAL_TYPE = TypeDef(
    key="rental_agreement", title="Rental agreement", doc_title="RENTAL AGREEMENT", spec_cls=RentalSpec,
    required=REQUIRED, questions=QUESTIONS, labels=LABELS, party_a="landlord", party_b="tenant",
    party_a_field="landlord_name", party_b_field="tenant_name", clauses=RENTAL,
    money_fields=("monthly_rent", "security_deposit"), context=context, obligations=compile_obligations,
    simulate=simulate, scenarios=SCENARIOS, key_dates=key_dates, lint=lint, sample=SAMPLE,
    intake_hint="Residential rental agreement in India. Deposit like 'two months' means 2 x monthly rent.",
)
