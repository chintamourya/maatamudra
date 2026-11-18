"""Contract Time Machine: a deterministic engine that evaluates what the CONTRACT's
own terms say for a scenario. No LLM, no invented thresholds. If the contract defines
no mechanism for something, the result says so. This is not a legal determination
of anyone's rights; it shows contractual consequences."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from ..models import RentalSpec

NOT_LEGAL = ("Shows what the contract's own terms provide. It is not a determination of legal "
             "rights; enforceability depends on law and facts.")


def _clamp_day(y: int, m: int, d: int) -> date:
    return date(y, m, min(d, monthrange(y, m)[1]))


def rent_schedule(spec: RentalSpec) -> list[date]:
    out = []
    for i in range(spec.term_months):
        m = spec.start_date + relativedelta(months=i)
        due = _clamp_day(m.year, m.month, spec.due_day)
        out.append(max(due, spec.start_date) if i == 0 else due)
    return out


def lease_end(spec: RentalSpec) -> date:
    return spec.start_date + relativedelta(months=spec.term_months) - timedelta(days=1)


def late_payment(spec: RentalSpec, month_index: int, days_late: int) -> dict:
    sched = rent_schedule(spec)
    if not 0 <= month_index < len(sched):
        raise ValueError("month_index outside the lease term")
    if days_late < 0:
        raise ValueError("days_late must be >= 0")
    due = sched[month_index]
    events = [{"date": due.isoformat(), "kind": "due", "label": f"Rent of {spec.monthly_rent} due", "clause": "rent"}]
    notes: list[str] = []
    late_fee = None
    if spec.grace_days is None or spec.late_fee_per_day is None:
        notes.append("This contract defines no late-fee mechanism, so no contractual late fee applies.")
    else:
        events.append({"date": (due + timedelta(days=spec.grace_days)).isoformat(), "kind": "grace_end",
                       "label": f"Grace period of {spec.grace_days} days ends", "clause": "late_payment"})
        chargeable = max(0, days_late - spec.grace_days)
        late_fee = chargeable * spec.late_fee_per_day
        if days_late > 0:
            events.append({"date": (due + timedelta(days=days_late)).isoformat(), "kind": "paid",
                           "label": f"Rent paid {days_late} days after due date; late fee {late_fee}", "clause": "late_payment"})
    default_eligible = None
    cure_deadline = None
    if spec.default_threshold_days is None or spec.cure_days is None:
        notes.append("This contract defines no default-and-cure mechanism.")
    else:
        threshold_date = due + timedelta(days=spec.default_threshold_days)
        default_eligible = days_late >= spec.default_threshold_days
        events.append({"date": threshold_date.isoformat(), "kind": "default_threshold",
                       "label": f"Landlord may serve a default notice from this date if rent is still unpaid",
                       "clause": "default_cure"})
        if default_eligible:
            cure_deadline = (threshold_date + timedelta(days=spec.cure_days)).isoformat()
            notes.append(f"If a default notice were served on the threshold date, the cure period would end on {cure_deadline}.")
        else:
            notes.append(f"Paying within {spec.default_threshold_days - 1} days of the due date stays below the contract's default threshold.")
    events.sort(key=lambda e: e["date"])
    return {
        "scenario": "late_payment", "due_date": due.isoformat(), "days_late": days_late,
        "late_fee": late_fee, "default_notice_possible_under_contract": default_eligible,
        "cure_deadline_if_notice_served_on_threshold": cure_deadline,
        "events": events, "notes": notes, "disclaimer": NOT_LEGAL,
    }


def early_termination(spec: RentalSpec, party: str, notice_date: date) -> dict:
    if party not in ("tenant", "landlord"):
        raise ValueError("party must be tenant or landlord")
    end = lease_end(spec)
    notice_effective = notice_date + timedelta(days=spec.notice_days)
    events = [{"date": notice_date.isoformat(), "kind": "notice", "label": f"{party.title()} gives written notice", "clause": "termination_notice"},
              {"date": notice_effective.isoformat(), "kind": "notice_expiry",
               "label": f"{spec.notice_days}-day notice expires", "clause": "termination_notice"}]
    notes: list[str] = []
    lock_end = None
    exit_date = notice_effective
    if spec.lock_in_months:
        lock_end = spec.start_date + relativedelta(months=spec.lock_in_months) - timedelta(days=1)
        events.append({"date": lock_end.isoformat(), "kind": "lock_in_end", "label": "Lock-in period ends", "clause": "lock_in"})
    liable_months = 0
    liability = 0
    if lock_end and notice_effective <= lock_end:
        if party == "landlord":
            notes.append("The lock-in binds both parties, so a landlord notice expiring inside it is not permitted by the contract's own terms.")
        else:
            later = [d for d in rent_schedule(spec) if notice_effective < d <= lock_end]
            liable_months = len(later)
            liability = liable_months * spec.monthly_rent
            notes.append(f"Notice expires inside the lock-in. The contract makes the tenant liable for rent for the unexpired lock-in: {liable_months} rent due date(s), {liability} in total.")
    if notice_effective > end:
        notes.append("The lease term ends before the notice would expire, so the term end applies first.")
        exit_date = end
    dues_until_exit = len([d for d in rent_schedule(spec) if d <= exit_date])
    events.append({"date": exit_date.isoformat(), "kind": "handover", "label": "Vacant possession due", "clause": "termination_notice"})
    events.sort(key=lambda e: e["date"])
    return {
        "scenario": "early_termination", "party": party, "notice_date": notice_date.isoformat(),
        "notice_effective": notice_effective.isoformat(), "handover_due": exit_date.isoformat(),
        "lock_in_end": lock_end.isoformat() if lock_end else None,
        "rent_dues_through_handover": dues_until_exit,
        "lock_in_rent_liability": liability, "events": events, "notes": notes, "disclaimer": NOT_LEGAL,
    }


def deposit_return(spec: RentalSpec, handover_date: date, deductions: list[dict], actual_refund_date: date | None = None) -> dict:
    total = sum(int(d.get("amount", 0)) for d in deductions)
    notes: list[str] = []
    if total > spec.security_deposit:
        notes.append(f"Deductions ({total}) exceed the deposit ({spec.security_deposit}); the excess would be a separate claim.")
    refund = max(0, spec.security_deposit - total)
    due = None
    overdue = None
    events = [{"date": handover_date.isoformat(), "kind": "handover", "label": "Vacant possession handed over", "clause": "deposit_refund"}]
    if spec.deposit_refund_days is None:
        notes.append("This contract sets no deadline for returning the deposit.")
    else:
        due = handover_date + timedelta(days=spec.deposit_refund_days)
        events.append({"date": due.isoformat(), "kind": "refund_due", "label": f"Refund of {refund} due", "clause": "deposit_refund"})
        if actual_refund_date:
            overdue = max(0, (actual_refund_date - due).days)
            notes.append(f"Refund made {overdue} day(s) after the contractual deadline." if overdue else "Refund made within the contractual deadline.")
    notes.append("The contract provides no interest on a delayed refund." )
    events.sort(key=lambda e: e["date"])
    return {
        "scenario": "deposit_return", "deposit": spec.security_deposit, "deductions_total": total,
        "refund_amount": refund, "refund_due_date": due.isoformat() if due else None,
        "days_overdue": overdue, "events": events, "notes": notes, "disclaimer": NOT_LEGAL,
    }


def renewal(spec: RentalSpec) -> dict:
    notes = []
    new_rent = spec.monthly_rent
    if spec.annual_escalation_pct is None:
        notes.append("This contract defines no escalation, so any renewal rent must be agreed fresh.")
    else:
        new_rent = round(spec.monthly_rent * (1 + spec.annual_escalation_pct / 100))
        notes.append(f"Per the escalation clause, rent on a written renewal becomes {new_rent}.")
    notes.append("The contract requires any renewal to be agreed in writing.")
    return {"scenario": "renewal", "current_rent": spec.monthly_rent, "renewal_rent": new_rent,
            "new_term_starts": (lease_end(spec) + timedelta(days=1)).isoformat(), "events": [], "notes": notes,
            "disclaimer": NOT_LEGAL}


def simulate(spec: RentalSpec, scenario: dict) -> dict:
    t = scenario.get("type")
    if t == "late_payment":
        return late_payment(spec, int(scenario.get("month_index", 0)), int(scenario["days_late"]))
    if t == "early_termination":
        return early_termination(spec, scenario["party"], date.fromisoformat(scenario["notice_date"]))
    if t == "deposit_return":
        ar = scenario.get("actual_refund_date")
        ded = scenario.get("deductions") or ([{"label": "Deductions", "amount": scenario["deduction_amount"]}] if scenario.get("deduction_amount") else [])
        return deposit_return(spec, date.fromisoformat(scenario["handover_date"]), ded,
                              date.fromisoformat(ar) if ar else None)
    if t == "renewal":
        return renewal(spec)
    raise ValueError(f"Unknown scenario type {t!r}")
