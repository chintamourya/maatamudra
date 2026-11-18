"""Static analysis of a contract's terms ("type-checking" for agreements). Deterministic, no LLM.
`error` findings block drafting (the terms contradict each other); `warning` findings are shown to the user."""
from __future__ import annotations

PAIRS = {  # optional mechanisms that only work together: (a, b)
    "rental_agreement": [("grace_days", "late_fee_per_day"), ("default_threshold_days", "cure_days")],
    "freelance_service": [],
    "employment": [("training_bond_amount", "training_bond_months"), ("probation_months", "probation_notice_days")],
}


def _f(clause_key, severity, message):
    return {"clause_key": clause_key, "severity": severity, "message": message, "kind": "consistency"}


def check(spec) -> list[dict]:
    out: list[dict] = []
    for a, b in PAIRS.get(spec.contract_type, []):
        va, vb = getattr(spec, a), getattr(spec, b)
        if (va is None) != (vb is None):
            given, missing = (a, b) if va is not None else (b, a)
            out.append(_f(given, "warning", f"'{given}' was given without '{missing}', so that clause is left out until both are set."))
    t = spec.contract_type
    if t == "rental_agreement":
        if spec.lock_in_months and spec.lock_in_months > spec.term_months:
            out.append(_f("lock_in", "error", f"The lock-in ({spec.lock_in_months} months) is longer than the whole term ({spec.term_months} months)."))
        if spec.default_threshold_days is not None and spec.grace_days is not None and spec.default_threshold_days <= spec.grace_days:
            out.append(_f("default_cure", "warning", "The default threshold is not later than the grace period, so a default can arise before any late fee does."))
        if spec.cure_days == 0 and spec.default_threshold_days is not None:
            out.append(_f("default_cure", "warning", "A cure period of 0 days gives the tenant no real chance to cure."))
        if spec.notice_days > spec.term_months * 30:
            out.append(_f("termination_notice", "warning", "The notice period is longer than the whole term."))
        if spec.annual_escalation_pct is not None and spec.term_months <= 12:
            out.append(_f("escalation", "warning", "Escalation applies only on renewal, which is outside this term."))
    elif t == "freelance_service":
        if spec.delivery_date < spec.start_date:
            out.append(_f("term_delivery", "error", "The delivery date is before the start date."))
        else:
            span = (spec.delivery_date - spec.start_date).days
            if spec.termination_notice_days > span:
                out.append(_f("termination", "warning", f"The notice period ({spec.termination_notice_days} days) is longer than the whole project ({span} days)."))
        if spec.advance_percent == 100:
            out.append(_f("advance", "warning", "A 100% advance leaves the client no payment leverage and the freelancer no reason to keep working."))
    elif t == "employment":
        if spec.probation_notice_days is not None and spec.probation_notice_days > spec.notice_period_days:
            out.append(_f("probation", "warning", "The probation notice is longer than the regular notice, which is unusual."))
        if spec.training_bond_months and spec.non_compete_months and spec.training_bond_months < 1:
            out.append(_f("training_bond", "warning", "The bond period is under one month."))
    elif t == "private_loan":
        if spec.final_due_date < spec.disbursement_date:
            out.append(_f("repayment", "error", "The final repayment date is before the loan disbursement date."))
    elif t == "mou":
        binding_terms = spec.binding_terms.strip().lower()
        none_terms = {"none", "none.", "no", "no binding terms", "n/a"}
        if spec.binding_status == "selected_terms_binding" and binding_terms in none_terms:
            out.append(_f("binding_status", "error", "Selected-terms-binding status needs at least one binding term, or a different status."))
        if spec.binding_status == "non_binding" and binding_terms not in none_terms:
            out.append(_f("binding_status", "error", "Non-binding status conflicts with the binding terms listed. Choose selected-terms-binding or clarify the terms."))
    return out


def errors(spec) -> list[dict]:
    return [f for f in check(spec) if f["severity"] == "error"]
