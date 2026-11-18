"""Freelance / service agreement (India). Clause text is our own drafting; have a lawyer review."""
from __future__ import annotations

from datetime import date, timedelta

from ..contracts.compiler import inr
from ..contracts.library import ClauseDef
from ..models import FreelanceSpec, Obligation
from ..obligations.simulator import NOT_LEGAL
from .base import TypeDef

REQUIRED = ["state", "client_name", "freelancer_name", "services_description", "start_date", "delivery_date",
            "total_fee", "payment_due_days", "ip_ownership", "termination_notice_days"]
QUESTIONS = {
    "state": "Which Indian state or Union Territory is most relevant to where the services will be performed?",
    "client_name": "What is the client's name or company name?",
    "freelancer_name": "What is the freelancer's full name?",
    "services_description": "What work will the freelancer do? Describe the deliverables.",
    "start_date": "When does the work start?",
    "delivery_date": "By when must the work be delivered?",
    "total_fee": "What is the total fee in rupees?",
    "payment_due_days": "Within how many days of an invoice must the client pay?",
    "ip_ownership": "Who owns the finished work: the client once fully paid, or does the freelancer keep ownership and license it?",
    "termination_notice_days": "How many days' written notice to end the agreement early?",
}
LABELS = {
    "state": "State / UT", "city": "City", "client_name": "Client", "freelancer_name": "Freelancer", "services_description": "Services", "start_date": "Start",
    "delivery_date": "Delivery by", "total_fee": "Total fee", "payment_due_days": "Pay within (days)",
    "ip_ownership": "Ownership of work", "termination_notice_days": "Notice days", "advance_percent": "Advance %",
    "late_interest_pct_per_month": "Late interest %/month", "revision_rounds": "Revision rounds",
    "confidentiality_years": "Confidentiality (years)", "non_compete_months": "Non-compete (months)",
    "liability_cap_multiple": "Liability cap (x fee)", "kill_fee_percent": "Kill fee %",
}

FREELANCE: list[ClauseDef] = [
    ClauseDef("parties_services", "Parties and services",
        "This Agreement is made at {place} between {client_name} (the \"Client\") and {freelancer_name} (the "
        "\"Freelancer\"). The Freelancer shall provide the following services (the \"Services\"): {services_description}.",
        ["client_name", "freelancer_name", "services_description"]),
    ClauseDef("term_delivery", "Timeline",
        "The Services begin on {start_date} and the final deliverables are due by {delivery_date}. The Freelancer is an "
        "independent contractor and controls how and when the work is done, within this timeline.",
        ["start_date", "delivery_date"]),
    ClauseDef("fee_payment", "Fee and payment",
        "The total fee is {total_fee}. The Client shall pay each invoice within {payment_due_days} days of receiving it, "
        "by bank transfer or another traceable mode. Fees are exclusive of GST and any tax deducted at source as applicable.",
        ["total_fee", "payment_due_days"]),
    ClauseDef("advance", "Advance",
        "The Client shall pay {advance_percent}% of the total fee as a non-refundable advance before work starts, "
        "adjusted against the final invoice.", ["total_fee", "advance_percent"]),
    ClauseDef("late_payment", "Late payment",
        "If an invoice is not paid by its due date, the Client shall pay interest at {late_interest_pct_per_month}% of the "
        "unpaid amount per month, pro-rated daily, until payment, as reasonable compensation for the delay.",
        ["late_interest_pct_per_month"], "medium", ["contract_act_s74", "msmed_s15_16"],
        ["interest on delayed payment reasonable compensation section 74 contract act"],
        "A stipulated interest or sum on delayed payment is enforceable only as reasonable compensation."),
    ClauseDef("revisions", "Revisions",
        "The fee includes {revision_rounds} round(s) of revisions to the agreed scope. Further revisions or changes "
        "to scope are charged separately by written agreement.", ["revision_rounds"]),
    ClauseDef("ip", "Ownership of work",
        "{ip_text}", ["ip_ownership"], "medium", ["copyright_act_s17_19"],
        ["assignment of copyright in writing terms period territory section 19"],
        "An assignment of copyright must be in writing and state the rights, duration and territory."),
    ClauseDef("confidentiality", "Confidentiality",
        "Each party shall keep the other's non-public information confidential and use it only for this engagement, "
        "during the engagement and for {confidentiality_years} years after it ends.", ["confidentiality_years"]),
    ClauseDef("non_compete", "Restriction on competing work",
        "For {non_compete_months} months after this Agreement ends, the Freelancer shall not provide similar services "
        "to any competitor of the Client.", ["non_compete_months"], "high", ["contract_act_s27"],
        ["restraint of trade section 27 contract act post termination non compete"],
        "A post-termination restraint on practising a profession or business is void to that extent under Section 27."),
    ClauseDef("liability", "Limit of liability",
        "The Freelancer's total liability under this Agreement shall not exceed {liability_cap_amount}, being "
        "{liability_cap_multiple} times the total fee.", ["total_fee", "liability_cap_multiple"], "medium",
        ["contract_act_s73"], ["limitation of liability clause enforceability breach compensation"],
        "A limitation of liability clause is generally enforceable if freely agreed, subject to the law on compensation."),
    ClauseDef("termination", "Termination",
        "Either party may end this Agreement by {termination_notice_days} days' written notice. The Client shall pay "
        "for work completed up to the end of the notice period.{kill_fee_text}", ["termination_notice_days"], "medium",
        ["contract_act_s73"], ["termination of contract compensation for work done quantum meruit"],
        "On termination, a party is generally entitled to payment for work already performed."),
    ClauseDef("disputes", "Disputes",
        "The parties shall first try to settle any dispute by discussion. Failing that, the courts at {place} shall have "
        "jurisdiction."),
    ClauseDef("execution", "Execution",
        "This Agreement shall be executed on stamp paper or by e-stamping as required by the law applicable in {state}. "
        "Each party shall keep one signed copy."),
]


def context(spec: FreelanceSpec) -> dict:
    ctx = {k: v for k, v in spec.model_dump().items() if v is not None}
    ctx["total_fee"] = inr(spec.total_fee)
    ctx["start_date"] = spec.start_date.strftime("%d %B %Y")
    ctx["delivery_date"] = spec.delivery_date.strftime("%d %B %Y")
    ctx["place"] = spec.city or spec.state or "the place of execution"
    ctx["state"] = spec.state or "the relevant state"
    if spec.liability_cap_multiple:
        ctx["liability_cap_amount"] = inr(spec.total_fee * spec.liability_cap_multiple)
    if spec.ip_ownership == "client_on_full_payment":
        ctx["ip_text"] = ("Ownership of the final deliverables, including copyright in them, passes to the Client throughout "
                          "the world and for the full term of copyright only on receipt of the full fee. Until then the Client "
                          "may use them for review only. The Freelancer keeps ownership of pre-existing tools and materials.")
    else:
        ctx["ip_text"] = ("The Freelancer retains ownership of the deliverables. The Client receives a non-exclusive, perpetual "
                          "licence to use them for its business. The Freelancer keeps ownership of pre-existing tools and materials.")
    ctx["kill_fee_text"] = ""
    if spec.kill_fee_percent:
        ctx["kill_fee_text"] = (f" If the Client ends the Agreement for convenience, it shall also pay {spec.kill_fee_percent}% of "
                                "the fee for work not yet performed.")
    return ctx


def obligations(spec: FreelanceSpec) -> list[Obligation]:
    ob = [
        Obligation(id="deliver", kind="deliver_work", party="freelancer", clause_key="term_delivery",
                   description="Deliver the final deliverables", rule={"due": spec.delivery_date.isoformat()}),
        Obligation(id="pay_invoice", kind="pay_invoice", party="client", clause_key="fee_payment",
                   description="Pay each invoice within the payment window",
                   rule={"within_days": spec.payment_due_days, "total_fee": spec.total_fee}),
        Obligation(id="termination_notice", kind="termination_notice", party="both", clause_key="termination",
                   description="Give written notice to end early", rule={"notice_days": spec.termination_notice_days}),
    ]
    if spec.advance_percent:
        ob.append(Obligation(id="advance", kind="pay_advance", party="client", clause_key="advance",
                             description="Pay the advance before work starts", rule={"percent": spec.advance_percent}))
    if spec.late_interest_pct_per_month is not None:
        ob.append(Obligation(id="late_interest", kind="late_interest", party="client", clause_key="late_payment",
                             description="Pay interest on overdue invoices", rule={"pct_per_month": spec.late_interest_pct_per_month}))
    if spec.confidentiality_years:
        ob.append(Obligation(id="confidentiality", kind="confidentiality", party="both", clause_key="confidentiality",
                             description="Keep information confidential", rule={"years": spec.confidentiality_years}))
    return ob


def _advance_amount(spec: FreelanceSpec) -> int:
    return round(spec.total_fee * (spec.advance_percent or 0) / 100)


def late_payment(spec: FreelanceSpec, invoice_date: date, days_late: int, amount: int | None = None) -> dict:
    if days_late < 0:
        raise ValueError("days_late must be >= 0")
    amount = amount if amount is not None else spec.total_fee - _advance_amount(spec)
    due = invoice_date + timedelta(days=spec.payment_due_days)
    notes = []
    interest = None
    if spec.late_interest_pct_per_month is None:
        notes.append("This contract defines no interest on late payment, so no contractual interest applies.")
    else:
        interest = round(amount * spec.late_interest_pct_per_month / 100 * days_late / 30)
    notes.append("If the Freelancer is a registered micro or small enterprise, a statutory payment-delay regime may apply "
                 "separately. Check whether it does.")
    events = [{"date": invoice_date.isoformat(), "kind": "invoice", "label": f"Invoice of {inr(amount)} sent", "clause": "fee_payment"},
              {"date": due.isoformat(), "kind": "due", "label": f"Payment due ({spec.payment_due_days} days)", "clause": "fee_payment"}]
    if days_late:
        events.append({"date": (due + timedelta(days=days_late)).isoformat(), "kind": "paid",
                       "label": f"Paid {days_late} days late; interest {inr(interest or 0)}", "clause": "late_payment"})
    return {"scenario": "late_payment", "invoice_amount": amount, "due_date": due.isoformat(), "days_late": days_late,
            "late_interest": interest, "events": events, "notes": notes, "disclaimer": NOT_LEGAL}


def termination(spec: FreelanceSpec, party: str, notice_date: date, work_done_pct: int) -> dict:
    if party not in ("client", "freelancer"):
        raise ValueError("party must be client or freelancer")
    if not 0 <= work_done_pct <= 100:
        raise ValueError("work_done_pct must be 0-100")
    effective = notice_date + timedelta(days=spec.termination_notice_days)
    work_fee = round(spec.total_fee * work_done_pct / 100)
    advance = _advance_amount(spec)
    balance = work_fee - advance
    kill_fee = 0
    notes = []
    if party == "client" and spec.kill_fee_percent:
        kill_fee = round((spec.total_fee - work_fee) * spec.kill_fee_percent / 100)
        notes.append(f"The client ends the agreement, so the contract's kill fee applies: {inr(kill_fee)}.")
    elif party == "client":
        notes.append("This contract defines no kill fee.")
    total = balance + kill_fee
    if total >= 0:
        notes.append(f"Under the contract the client owes the freelancer {inr(total)} (work done {inr(work_fee)} less advance {inr(advance)}{' plus kill fee' if kill_fee else ''}).")
    else:
        notes.append(f"The advance exceeds the work done. The contract describes the advance as non-refundable, so check how the shortfall of {inr(-total)} is treated.")
    if spec.ip_ownership == "client_on_full_payment":
        notes.append("Ownership of the deliverables passes to the client only on full payment of the fee, so the client would not own the unfinished work.")
    events = [{"date": notice_date.isoformat(), "kind": "notice", "label": f"{party.title()} gives written notice", "clause": "termination"},
              {"date": effective.isoformat(), "kind": "effective", "label": f"Agreement ends ({spec.termination_notice_days}-day notice)", "clause": "termination"}]
    return {"scenario": "termination", "party": party, "effective_date": effective.isoformat(), "work_done_pct": work_done_pct,
            "work_fee": work_fee, "advance_paid": advance, "kill_fee": kill_fee, "net_payable_to_freelancer": total,
            "events": events, "notes": notes, "disclaimer": NOT_LEGAL}


def ip_status(spec: FreelanceSpec, fully_paid: bool) -> dict:
    if spec.ip_ownership == "freelancer_retains":
        note = "The freelancer retains ownership; the client holds a perpetual, non-exclusive licence."
        owner = "freelancer"
    elif fully_paid:
        note = "The fee has been paid in full, so ownership of the final deliverables has passed to the client."
        owner = "client"
    else:
        note = "The fee is not fully paid, so under the contract ownership has not passed to the client."
        owner = "freelancer"
    return {"scenario": "ip_status", "owner": owner, "events": [], "notes": [note], "disclaimer": NOT_LEGAL}


def simulate(spec: FreelanceSpec, s: dict) -> dict:
    t = s.get("type")
    if t == "late_payment":
        return late_payment(spec, date.fromisoformat(s["invoice_date"]), int(s["days_late"]))
    if t == "termination":
        return termination(spec, s["party"], date.fromisoformat(s["notice_date"]), int(s["work_done_pct"]))
    if t == "ip_status":
        return ip_status(spec, bool(s.get("fully_paid")))
    raise ValueError(f"Unknown scenario type {t!r}")


def key_dates(spec: FreelanceSpec) -> list[dict]:
    return [{"date": spec.start_date, "title": "Work starts"}, {"date": spec.delivery_date, "title": "Final deliverables due"}]


def lint(spec: FreelanceSpec) -> list[dict]:
    f = []
    if spec.non_compete_months:
        f.append({"clause_key": "non_compete", "severity": "high", "message": f"A {spec.non_compete_months}-month post-termination restriction on a freelancer is commonly challenged under Section 27 of the Contract Act. See the case-law check."})
    if spec.liability_cap_multiple is None:
        f.append({"clause_key": "liability", "severity": "medium", "message": "No liability cap: the freelancer's exposure is open-ended."})
    if spec.revision_rounds is None:
        f.append({"clause_key": "revisions", "severity": "medium", "message": "No revision limit: scope can grow without extra pay."})
    if spec.late_interest_pct_per_month is None:
        f.append({"clause_key": "fee_payment", "severity": "medium", "message": "No consequence for late payment."})
    if not spec.advance_percent:
        f.append({"clause_key": "fee_payment", "severity": "low", "message": "No advance: the freelancer carries all the payment risk."})
    if spec.confidentiality_years is None:
        f.append({"clause_key": "parties_services", "severity": "low", "message": "No confidentiality clause."})
    return f


SCENARIOS = [
    {"type": "late_payment", "label": "Client pays late", "inputs": [
        {"name": "invoice_date", "label": "Invoice date", "kind": "date", "default": "2027-01-15"},
        {"name": "days_late", "label": "Days late", "kind": "range", "min": 0, "max": 90, "default": 30}]},
    {"type": "termination", "label": "Someone ends the agreement", "inputs": [
        {"name": "party", "label": "Who gives notice", "kind": "select", "options": ["client", "freelancer"], "default": "client"},
        {"name": "notice_date", "label": "Notice date", "kind": "date", "default": "2027-01-10"},
        {"name": "work_done_pct", "label": "Work done (%)", "kind": "range", "min": 0, "max": 100, "default": 40}]},
    {"type": "ip_status", "label": "Who owns the work?", "inputs": [
        {"name": "fully_paid", "label": "Fee paid in full", "kind": "select", "options": ["no", "yes"], "default": "no"}]},
]

SAMPLE = {
    "contract_type": "freelance_service", "state": "Telangana", "city": "Hyderabad", "client_name": "BrightLeaf Foods Pvt Ltd",
    "freelancer_name": "Meena Iyer", "services_description": "design and development of a 5-page marketing website",
    "start_date": "2026-12-05", "delivery_date": "2027-01-20", "total_fee": 120000, "payment_due_days": 15,
    "ip_ownership": "client_on_full_payment", "termination_notice_days": 14, "advance_percent": 30,
    "late_interest_pct_per_month": 2, "revision_rounds": 2, "confidentiality_years": 2, "non_compete_months": 24,
    "liability_cap_multiple": 1, "kill_fee_percent": 20, "provenance": {},
}

FREELANCE_TYPE = TypeDef(
    key="freelance_service", title="Freelancer / service agreement", doc_title="SERVICE AGREEMENT",
    spec_cls=FreelanceSpec, required=REQUIRED, questions=QUESTIONS, labels=LABELS, party_a="client", party_b="freelancer",
    party_a_field="client_name", party_b_field="freelancer_name", clauses=FREELANCE, money_fields=("total_fee",),
    context=context, obligations=obligations, simulate=simulate, scenarios=SCENARIOS, key_dates=key_dates, lint=lint,
    sample=SAMPLE, intake_hint="Freelance or service agreement in India between a client and an independent freelancer.",
)
