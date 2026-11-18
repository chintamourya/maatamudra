"""Consequence map: sweep a scenario over time and find the regions where the contract's behaviour changes.
It reports dead zones (no consequence), cliffs (a sudden jump) and how big a consequence is relative to the money at stake.
All values come from the deterministic simulator; the wording states facts, not legal conclusions."""
from __future__ import annotations

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from ..contracts.compiler import inr


def _zones(points, key, labels):
    zones, start = [], 0
    for i in range(1, len(points) + 1):
        if i == len(points) or key(points[i]) != key(points[start]):
            zones.append({"from": points[start]["x"], "to": points[i - 1]["x"], "label": labels(points[start])})
            start = i
    return zones


def rental(spec) -> dict:
    from .simulator import late_payment

    pts = []
    for d in range(0, 91):
        r = late_payment(spec, 0, d)
        pts.append({"x": d, "y": r["late_fee"] or 0, "fee": r["late_fee"], "default": r["default_notice_possible_under_contract"]})
    if spec.grace_days is None and spec.default_threshold_days is None:
        return {"available": True, "title": "Late rent", "x_label": "Days late", "y_label": "Late fee (₹)", "series": pts,
                "zones": [{"from": 0, "to": 90, "label": "No consequence defined"}],
                "findings": ["This agreement defines no consequence for late rent at any point in 90 days."]}

    def state(p):
        return (bool(p["fee"]), bool(p["default"]))

    def label(p):
        if p["default"]:
            return "Default notice possible"
        return "Late fee accrues, no default route yet" if p["fee"] else "No consequence yet"

    zones = _zones(pts, state, label)
    f = []
    dead = [z for z in zones if z["label"] == "Late fee accrues, no default route yet"]
    for z in dead:
        f.append(f"Days {z['from']} to {z['to']}: only a late fee applies; the landlord has no default route under the agreement until day {z['to'] + 1}.")
    no_cons = [z for z in zones if z["label"] == "No consequence yet"]
    for z in no_cons:
        f.append(f"Days {z['from']} to {z['to']}: nothing happens under the agreement (grace period).")
    if spec.default_threshold_days is not None:
        f.append(f"Cliff at day {spec.default_threshold_days}: a default notice becomes possible.")
    for d in (30, 60, 90):
        fee = pts[d]["fee"]
        if fee is not None:
            f.append(f"At {d} days late the fee totals {inr(fee)}, which is {fee / spec.monthly_rent * 100:.0f}% of one month's rent.")
    return {"available": True, "title": "Late rent", "x_label": "Days late", "y_label": "Late fee (₹)", "series": pts, "zones": zones, "findings": f}


def freelance(spec) -> dict:
    from ..types.freelance import late_payment
    from datetime import date

    inv = date(2027, 1, 15)
    pts = []
    for d in range(0, 91):
        r = late_payment(spec, inv, d)
        pts.append({"x": d, "y": r["late_interest"] or 0, "fee": r["late_interest"]})
    if spec.late_interest_pct_per_month is None:
        return {"available": True, "title": "Late client payment", "x_label": "Days late", "y_label": "Interest (₹)", "series": pts,
                "zones": [{"from": 0, "to": 90, "label": "No consequence defined"}],
                "findings": ["This agreement defines no consequence for late payment at any point in 90 days."]}
    base = pts and late_payment(spec, inv, 0)["invoice_amount"]
    f = [f"Interest accrues from day 1 at {spec.late_interest_pct_per_month:g}% a month on the unpaid amount."]
    for d in (30, 60, 90):
        f.append(f"At {d} days late the interest totals {inr(pts[d]['fee'])}, which is {pts[d]['fee'] / base * 100:.1f}% of the {inr(base)} outstanding.")
    f.append("The agreement gives the freelancer no stated right to pause or stop work while an invoice is unpaid.")
    return {"available": True, "title": "Late client payment", "x_label": "Days late", "y_label": "Interest (₹)", "series": pts,
            "zones": [{"from": 0, "to": 90, "label": "Interest accrues"}], "findings": f}


def employment(spec) -> dict:
    from ..types.employment import bond_exit

    if not (spec.training_bond_amount and spec.training_bond_months):
        return {"available": False, "reason": "This agreement has no training bond to map."}
    pts = []
    for m in range(0, spec.training_bond_months + 4):
        leave = spec.start_date + relativedelta(months=m) - timedelta(days=1)
        r = bond_exit(spec, leave)
        pts.append({"x": m, "y": r["claimable_under_contract"], "fee": r["claimable_under_contract"], "date": leave.isoformat()})
    zones = _zones(pts, lambda p: p["y"] > 0, lambda p: "Bond named in the contract applies" if p["y"] > 0 else "Bond has ended")
    f = []
    first, last_pos = pts[0]["y"], [p for p in pts if p["y"] > 0][-1]
    if not spec.bond_pro_rata:
        f.append(f"Flat bond: leaving in month 1 or in month {last_pos['x']} costs the same {inr(first)}.")
        f.append(f"Cliff: the amount falls from {inr(last_pos['y'])} to {inr(0)} in one step when the bond period ends.")
    else:
        f.append(f"Pro-rata bond: the amount falls from {inr(first)} at joining to {inr(last_pos['y'])} in month {last_pos['x']}.")
    f.append("Whether the full named amount can be recovered is a legal question; see the case-law check for the bond clause.")
    return {"available": True, "title": "Leaving during the bond", "x_label": "Months served", "y_label": "Bond named (₹)", "series": pts, "zones": zones, "findings": f}


def consequence_map(spec) -> dict:
    fn = {"rental_agreement": rental, "freelance_service": freelance, "employment": employment}.get(spec.contract_type)
    if fn is None:
        return {"available": False, "reason": "A deterministic consequence map is not yet available for this agreement type."}
    return fn(spec)
