"""Employment agreement with confidentiality (India). Clause text is our own drafting; have a lawyer review.
Labour-code applicability is flagged in the checklist, not assumed."""
from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from ..contracts.compiler import inr
from ..contracts.library import ClauseDef
from ..models import EmploymentSpec, Obligation
from ..obligations.simulator import NOT_LEGAL
from .base import TypeDef

REQUIRED = ["state", "employer_name", "employee_name", "designation", "start_date", "monthly_salary", "notice_period_days",
            "ip_to_employer"]
QUESTIONS = {
    "state": "Which Indian state or Union Territory is the workplace in?",
    "employer_name": "What is the employer's (company's) name?",
    "employee_name": "What is the employee's full name?",
    "designation": "What is the employee's job title?",
    "start_date": "What is the joining date?",
    "monthly_salary": "What is the gross monthly salary in rupees?",
    "notice_period_days": "How many days' notice must either side give to end the employment?",
    "ip_to_employer": "Should work the employee creates in the job belong to the employer? (yes or no)",
}
LABELS = {
    "state": "State / UT", "city": "City", "employer_name": "Employer", "employee_name": "Employee", "designation": "Role", "start_date": "Joining date",
    "monthly_salary": "Monthly salary", "notice_period_days": "Notice days", "ip_to_employer": "Work belongs to employer",
    "probation_months": "Probation (months)", "probation_notice_days": "Probation notice (days)",
    "confidentiality_years": "Confidentiality (years)", "non_solicit_months": "Non-solicit (months)",
    "non_compete_months": "Non-compete (months)", "training_bond_amount": "Training bond (₹)",
    "training_bond_months": "Bond period (months)", "bond_pro_rata": "Bond pro-rata",
}

EMPLOYMENT: list[ClauseDef] = [
    ClauseDef("parties_role", "Parties and role",
        "This Agreement is made at {place} between {employer_name} (the \"Employer\") and {employee_name} (the "
        "\"Employee\"). The Employer employs the Employee as {designation} from {start_date}.",
        ["employer_name", "employee_name", "designation", "start_date"]),
    ClauseDef("remuneration", "Salary",
        "The Employee shall be paid a gross monthly salary of {monthly_salary}, subject to deductions required by law, "
        "payable by the last working day of each month.", ["monthly_salary"]),
    ClauseDef("probation", "Probation",
        "The first {probation_months} months are a probation period. During probation either party may end the "
        "employment by {probation_notice_days} days' written notice.", ["probation_months", "probation_notice_days"]),
    ClauseDef("notice", "Notice of termination",
        "After probation, either party may end the employment by {notice_period_days} days' written notice. The Employer "
        "may pay salary for the notice period in place of requiring the Employee to work it.", ["notice_period_days"],
        "medium", ["contract_act_s74"], ["notice period employment resignation termination compensation in lieu of notice"],
        "A notice period and pay in lieu of notice are enforceable as agreed, subject to reasonableness."),
    ClauseDef("confidentiality", "Confidentiality",
        "The Employee shall keep the Employer's confidential business information secret during the employment and for "
        "{confidentiality_years} years after it ends, and use it only for the Employer's work.", ["confidentiality_years"],
        "low", [], ["confidentiality clause employee post termination trade secrets injunction"],
        "A reasonable confidentiality obligation continuing after employment is enforceable."),
    ClauseDef("ip", "Work created in the job",
        "{ip_text}", ["ip_to_employer"], "medium", ["copyright_act_s17_19"],
        ["employer first owner copyright work made in course of employment section 17"],
        "Work made by an employee in the course of employment generally belongs to the employer unless agreed otherwise."),
    ClauseDef("non_solicit", "Non-solicitation",
        "For {non_solicit_months} months after the employment ends, the Employee shall not solicit the Employer's "
        "employees to leave their jobs.", ["non_solicit_months"], "medium", ["contract_act_s27"],
        ["non solicitation employees clause restraint of trade section 27"],
        "A restriction on soliciting employees after employment is tested against Section 27."),
    ClauseDef("non_compete", "Restriction on competing work",
        "For {non_compete_months} months after the employment ends, the Employee shall not work for a competitor of the "
        "Employer.", ["non_compete_months"], "high", ["contract_act_s27"],
        ["post employment non compete restraint of trade section 27 contract act employee"],
        "A restraint on an employee working for a competitor after employment ends is void to that extent under Section 27."),
    ClauseDef("training_bond", "Training bond",
        "If the Employee leaves within {training_bond_months} months of joining, the Employee shall pay the Employer "
        "{training_bond_amount}{bond_text} as a genuine pre-estimate of the Employer's training cost and not as a penalty.",
        ["training_bond_amount", "training_bond_months"], "high", ["contract_act_s74"],
        ["employment bond liquidated damages leaving before period reasonable compensation section 74"],
        "A training or service bond is enforceable only to the extent of reasonable compensation for the loss."),
    ClauseDef("conduct", "Conduct and duties",
        "The Employee shall perform the duties of the role diligently, follow the Employer's lawful policies and "
        "devote working time to the Employer's business."),
    ClauseDef("disputes", "Disputes",
        "The parties shall first try to settle any dispute by discussion. Failing that, the courts at {place} shall have "
        "jurisdiction."),
    ClauseDef("execution", "Execution",
        "This Agreement shall be executed on stamp paper or by e-stamping as required by the law applicable in {state}. "
        "Each party shall keep one signed copy."),
]


def context(spec: EmploymentSpec) -> dict:
    ctx = {k: v for k, v in spec.model_dump().items() if v is not None}
    ctx["monthly_salary"] = inr(spec.monthly_salary)
    if spec.training_bond_amount is not None:
        ctx["training_bond_amount"] = inr(spec.training_bond_amount)
    ctx["start_date"] = spec.start_date.strftime("%d %B %Y")
    ctx["place"] = spec.city or spec.state or "the place of execution"
    ctx["state"] = spec.state or "the relevant state"
    ctx["bond_text"] = " (reduced in proportion to the months served)" if spec.bond_pro_rata else ""
    ctx["ip_text"] = (
        "All work, inventions and materials the Employee creates in the course of the employment belong to the Employer, "
        "and the Employee assigns all rights in them to the Employer throughout the world for the full term of the rights."
        if spec.ip_to_employer else
        "The Employee keeps ownership of work created in the employment, and gives the Employer a perpetual licence to use it "
        "for its business.")
    return ctx


def obligations(spec: EmploymentSpec) -> list[Obligation]:
    ob = [
        Obligation(id="pay_salary", kind="pay_salary", party="employer", clause_key="remuneration",
                   description="Pay monthly salary", rule={"amount": spec.monthly_salary}),
        Obligation(id="notice", kind="termination_notice", party="both", clause_key="notice",
                   description="Give notice to end the employment", rule={"notice_days": spec.notice_period_days}),
    ]
    if spec.probation_months and spec.probation_notice_days is not None:
        ob.append(Obligation(id="probation", kind="probation", party="both", clause_key="probation",
                             description="Shorter notice during probation",
                             rule={"months": spec.probation_months, "notice_days": spec.probation_notice_days}))
    if spec.confidentiality_years:
        ob.append(Obligation(id="confidentiality", kind="confidentiality", party="employee", clause_key="confidentiality",
                             description="Keep information confidential", rule={"years": spec.confidentiality_years}))
    if spec.training_bond_amount and spec.training_bond_months:
        ob.append(Obligation(id="bond", kind="training_bond", party="employee", clause_key="training_bond",
                             description="Repay the bond if leaving early",
                             rule={"amount": spec.training_bond_amount, "months": spec.training_bond_months, "pro_rata": bool(spec.bond_pro_rata)}))
    return ob


def resignation(spec: EmploymentSpec, notice_date: date) -> dict:
    notes = []
    days = spec.notice_period_days
    probation_end = None
    if spec.probation_months:
        probation_end = spec.start_date + relativedelta(months=spec.probation_months)
        if notice_date < probation_end and spec.probation_notice_days is not None:
            days = spec.probation_notice_days
            notes.append(f"Notice is given during probation (ends {probation_end.isoformat()}), so the shorter probation notice of {days} days applies.")
    last_day = notice_date + timedelta(days=days)
    pay = round(spec.monthly_salary * days / 30)
    notes.append(f"Notice of {days} days ends on {last_day.isoformat()}. Salary for the notice period is about {inr(pay)} (monthly salary pro-rated at 30 days).")
    notes.append("The Employer may pay in lieu of notice under the contract.")
    if spec.non_compete_months:
        notes.append(f"The contract has a {spec.non_compete_months}-month post-employment non-compete. Whether it can be enforced is a legal question; see the case-law check for that clause.")
    if spec.confidentiality_years:
        notes.append(f"Confidentiality continues for {spec.confidentiality_years} years after the last day.")
    events = [{"date": notice_date.isoformat(), "kind": "notice", "label": "Resignation notice given", "clause": "notice"},
              {"date": last_day.isoformat(), "kind": "last_day", "label": "Last working day", "clause": "notice"}]
    return {"scenario": "resignation", "notice_days_applied": days, "last_working_day": last_day.isoformat(),
            "salary_for_notice_period": pay, "events": events, "notes": notes, "disclaimer": NOT_LEGAL}


def bond_exit(spec: EmploymentSpec, leave_date: date) -> dict:
    notes = []
    if not (spec.training_bond_amount and spec.training_bond_months):
        return {"scenario": "bond_exit", "claimable_under_contract": 0, "events": [],
                "notes": ["This contract has no training bond."], "disclaimer": NOT_LEGAL}
    bond_end = spec.start_date + relativedelta(months=spec.training_bond_months)
    claim = 0
    if leave_date < bond_end:
        if spec.bond_pro_rata:
            total_days = (bond_end - spec.start_date).days
            remaining = (bond_end - leave_date).days
            claim = round(spec.training_bond_amount * remaining / total_days)
            notes.append(f"Leaving before the bond ends ({bond_end.isoformat()}), the contract's pro-rata bond gives {inr(claim)}.")
        else:
            claim = spec.training_bond_amount
            notes.append(f"Leaving before the bond ends ({bond_end.isoformat()}), the contract names {inr(claim)} in full.")
        notes.append("Whether the named amount can be recovered in full is a legal question; see the Section 74 case-law check for this clause.")
    else:
        notes.append(f"The bond period ended on {bond_end.isoformat()}, so no bond amount is claimable under the contract.")
    return {"scenario": "bond_exit", "bond_end": bond_end.isoformat(), "claimable_under_contract": claim,
            "events": [{"date": bond_end.isoformat(), "kind": "bond_end", "label": "Bond period ends", "clause": "training_bond"}],
            "notes": notes, "disclaimer": NOT_LEGAL}


def simulate(spec: EmploymentSpec, s: dict) -> dict:
    t = s.get("type")
    if t == "resignation":
        return resignation(spec, date.fromisoformat(s["notice_date"]))
    if t == "bond_exit":
        return bond_exit(spec, date.fromisoformat(s["leave_date"]))
    raise ValueError(f"Unknown scenario type {t!r}")


def key_dates(spec: EmploymentSpec) -> list[dict]:
    out = [{"date": spec.start_date, "title": "Joining date"}]
    if spec.probation_months:
        out.append({"date": spec.start_date + relativedelta(months=spec.probation_months), "title": "Probation ends"})
    if spec.training_bond_months:
        out.append({"date": spec.start_date + relativedelta(months=spec.training_bond_months), "title": "Training bond period ends"})
    return out


def lint(spec: EmploymentSpec) -> list[dict]:
    f = []
    if spec.non_compete_months:
        f.append({"clause_key": "non_compete", "severity": "high", "message": f"A {spec.non_compete_months}-month post-employment non-compete is commonly challenged under Section 27 of the Contract Act. See the case-law check."})
    if spec.training_bond_amount and spec.training_bond_months and not spec.bond_pro_rata:
        f.append({"clause_key": "training_bond", "severity": "high", "message": "A flat bond amount regardless of months served is more exposed to a challenge as a penalty under Section 74."})
    if spec.confidentiality_years is None:
        f.append({"clause_key": "parties_role", "severity": "medium", "message": "No confidentiality clause."})
    if spec.probation_months and spec.probation_notice_days is None:
        f.append({"clause_key": "probation", "severity": "low", "message": "Probation is mentioned without a probation notice period."})
    f.append({"clause_key": "remuneration", "severity": "low", "message": "Check which labour code provisions apply to this employee and employer before relying on these terms."})
    return f


SCENARIOS = [
    {"type": "resignation", "label": "Employee resigns", "inputs": [
        {"name": "notice_date", "label": "Notice date", "kind": "date", "default": "2027-03-01"}]},
    {"type": "bond_exit", "label": "Employee leaves early (bond)", "inputs": [
        {"name": "leave_date", "label": "Last day", "kind": "date", "default": "2027-06-30"}]},
]

SAMPLE = {
    "contract_type": "employment", "state": "Telangana", "city": "Hyderabad", "employer_name": "Nimbus Analytics Pvt Ltd",
    "employee_name": "Karthik Reddy", "designation": "Software Engineer", "start_date": "2026-12-15",
    "monthly_salary": 85000, "notice_period_days": 60, "ip_to_employer": True, "probation_months": 6,
    "probation_notice_days": 15, "confidentiality_years": 3, "non_solicit_months": 12, "non_compete_months": 12,
    "training_bond_amount": 150000, "training_bond_months": 18, "bond_pro_rata": False, "provenance": {},
}

EMPLOYMENT_TYPE = TypeDef(
    key="employment", title="Employment / NDA", doc_title="EMPLOYMENT AGREEMENT", spec_cls=EmploymentSpec,
    required=REQUIRED, questions=QUESTIONS, labels=LABELS, party_a="employer", party_b="employee",
    party_a_field="employer_name", party_b_field="employee_name", clauses=EMPLOYMENT, money_fields=("monthly_salary",),
    context=context, obligations=obligations, simulate=simulate, scenarios=SCENARIOS, key_dates=key_dates, lint=lint,
    sample=SAMPLE, intake_hint="Employment agreement with confidentiality terms for an employee in India.",
)
