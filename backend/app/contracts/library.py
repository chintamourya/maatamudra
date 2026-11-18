"""Rental clause library. Clause text is our own drafting, kept as templates.
A clause renders only when every field it `requires` is present in the spec;
optional mechanisms are omitted rather than invented. Have a lawyer review this
library before real-world use."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClauseDef:
    key: str
    title: str
    template: str
    requires: list[str] = field(default_factory=list)
    risk: str = "low"
    legal_basis: list[str] = field(default_factory=list)
    evidence_queries: list[str] = field(default_factory=list)
    proposition: str = ""  # what we want case law to support for this clause


RENTAL: list[ClauseDef] = [
    ClauseDef(
        "parties_premises", "Parties and premises",
        "This Rental Agreement is made at {place} between {landlord_name} (the \"Landlord\") and "
        "{tenant_name} (the \"Tenant\"). The Landlord lets and the Tenant takes on rent the residential "
        "premises situated at {property_address} (the \"Premises\").",
        ["landlord_name", "tenant_name", "property_address"],
    ),
    ClauseDef(
        "term", "Term",
        "The tenancy begins on {start_date} and continues for {term_months} months, ending on {end_date}, "
        "unless ended earlier in accordance with this Agreement. Any renewal must be agreed in writing.",
        ["start_date", "term_months"],
    ),
    ClauseDef(
        "rent", "Rent",
        "The Tenant shall pay monthly rent of {monthly_rent} on or before the {due_day_ord} day of each month "
        "for that month, by bank transfer or another traceable mode, and the Landlord shall give a written receipt "
        "or acknowledgement for each payment.",
        ["monthly_rent", "due_day"],
    ),
    ClauseDef(
        "late_payment", "Late payment",
        "If rent is not paid within {grace_days} days after the due date, the Tenant shall pay a late fee of "
        "{late_fee_per_day} for each further day of delay until payment, as a genuine pre-estimate of the Landlord's "
        "loss from delayed receipt and not as a penalty.",
        ["grace_days", "late_fee_per_day"], "medium", ["contract_act_s74"],
        ["liquidated damages penalty reasonable compensation section 74 contract act"],
        "A stipulated late-payment sum is enforceable only to the extent of reasonable compensation for the loss.",
    ),
    ClauseDef(
        "default_cure", "Default and cure",
        "If rent remains unpaid for {default_threshold_days} days after the due date, the Landlord may serve a written "
        "default notice. The Tenant may cure the default by paying all dues within {cure_days} days of receiving "
        "the notice, failing which the Landlord may end the tenancy by written notice.",
        ["default_threshold_days", "cure_days"], "high", ["topa_s105_111", "telangana_rent_control"],
        ["tenant eviction non-payment of rent notice default lease"],
        "Termination of a tenancy for non-payment of rent requires a proper notice and is subject to applicable tenancy law.",
    ),
    ClauseDef(
        "security_deposit", "Security deposit",
        "The Tenant has paid or shall pay an interest-free refundable security deposit of {security_deposit}. "
        "The deposit is security for unpaid rent, utilities and damage beyond normal wear and tear, and is not "
        "to be treated as rent for any month.",
        ["security_deposit"], "medium", ["contract_act_s73"],
    ),
    ClauseDef(
        "deposit_refund", "Return of deposit",
        "The Landlord shall return the security deposit, less itemised lawful deductions supported by a written "
        "statement, within {deposit_refund_days} days after the Tenant hands back vacant possession.",
        ["security_deposit", "deposit_refund_days"], "medium", ["contract_act_s73"],
        ["refund of security deposit landlord tenant vacant possession"],
        "A landlord must return a security deposit on handover of possession, subject to lawful deductions.",
    ),
    ClauseDef(
        "maintenance", "Maintenance and utilities",
        "The Tenant shall pay maintenance charges of {maintenance_monthly} per month along with the rent and shall "
        "pay electricity, water and other usage charges directly to the provider.",
        ["maintenance_monthly"],
    ),
    ClauseDef(
        "escalation", "Rent escalation on renewal",
        "On any renewal agreed in writing, the monthly rent shall increase by {annual_escalation_pct}% over the "
        "rent payable immediately before the renewal.",
        ["annual_escalation_pct"], "medium",
    ),
    ClauseDef(
        "lock_in", "Lock-in period",
        "Neither party may end the tenancy during the first {lock_in_months} months from the start date. If the "
        "Tenant leaves earlier, the Tenant shall pay rent for the unexpired part of the lock-in period.",
        ["lock_in_months"], "medium", ["contract_act_s74", "contract_act_s73"],
        ["lock-in period lease early termination tenant liable rent"],
        "A lock-in clause requiring rent for the unexpired period is enforceable only as reasonable compensation.",
    ),
    ClauseDef(
        "termination_notice", "Termination by notice",
        "Either party may end this tenancy by giving the other at least {notice_days} days' written notice, subject "
        "to any lock-in period. On expiry of the notice the Tenant shall hand over vacant possession.",
        ["notice_days"], "high", ["topa_s105_111", "telangana_rent_control"],
        ["notice to quit termination of tenancy lease transfer of property act"],
        "A tenancy can be ended only by a valid notice of the period required by the contract and applicable law.",
    ),
    ClauseDef(
        "use_repairs", "Use and repairs",
        "The Tenant shall use the Premises only as a private residence, keep it in good condition, and shall not "
        "sublet or part with possession without the Landlord's written consent. The Landlord shall carry out "
        "structural repairs; the Tenant shall bear minor day-to-day repairs.",
    ),
    ClauseDef(
        "inspection", "Inspection",
        "The Landlord may inspect the Premises at reasonable times after giving the Tenant reasonable prior notice, "
        "except in an emergency.",
    ),
    ClauseDef(
        "disputes", "Disputes",
        "The parties shall first try to settle any dispute by discussion. Failing that, the courts having "
        "jurisdiction over the Premises shall have jurisdiction.",
    ),
    ClauseDef(
        "execution", "Execution",
        "This Agreement shall be executed on stamp paper or by e-stamping as required by the law applicable in "
        "{state}, and registered if the law requires it. Each party shall keep one signed copy.",
    ),
]
