from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date

from dateutil.relativedelta import relativedelta

from ..models import Clause, Contract, RentalSpec


def inr(n: int | float) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567"""
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def end_date(spec: RentalSpec) -> date:
    return spec.start_date + relativedelta(months=spec.term_months) - relativedelta(days=1)


# Optional mechanisms where 0 means "not chosen": the clause is omitted rather than rendered as 0.
ZERO_MEANS_OFF = {"advance_percent", "lock_in_months", "confidentiality_years", "non_compete_months",
                  "non_solicit_months", "training_bond_amount", "training_bond_months", "probation_months"}


def _absent(spec, field: str) -> bool:
    v = getattr(spec, field)
    return v is None or (field in ZERO_MEANS_OFF and v == 0)


def compile_contract(spec, contract_id: str | None = None) -> Contract:
    from ..models import missing_fields
    from ..types import REGISTRY

    td = REGISTRY[spec.contract_type]
    miss = missing_fields(spec)
    if miss:
        raise ValueError(f"Cannot compile: missing required fields {miss}")
    from ..analysis.consistency import errors

    errs = errors(spec)
    if errs:
        raise ValueError("The terms contradict each other: " + "; ".join(e["message"] for e in errs))
    ctx = {k: (f"{v:g}" if isinstance(v, float) else v) for k, v in td.context(spec).items()}
    clauses: list[Clause] = []
    for d in td.clauses:
        if any(_absent(spec, f) for f in d.requires):
            continue  # optional mechanism not chosen: omit, never invent
        text = d.template.format(**ctx)
        clauses.append(Clause(
            key=d.key, title=d.title, text=text, original_text=text, risk=d.risk,
            legal_basis=d.legal_basis, evidence_queries=d.evidence_queries,
        ))
    c = Contract(id=contract_id or str(uuid.uuid4()), spec=spec, clauses=clauses)
    c.obligations = td.obligations(spec)
    return c
