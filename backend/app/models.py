"""Core Pydantic models. The contract spec is the single source of truth:
clauses, obligations and the simulator are all derived from it."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SpecFields(BaseModel):
    """Every field optional so partial intake is representable."""
    state: Optional[str] = None
    city: Optional[str] = None
    landlord_name: Optional[str] = None
    tenant_name: Optional[str] = None
    property_address: Optional[str] = None
    start_date: Optional[date] = None
    term_months: Optional[int] = Field(None, ge=1, le=120)
    monthly_rent: Optional[int] = Field(None, gt=0)
    security_deposit: Optional[int] = Field(None, ge=0)
    due_day: Optional[int] = Field(None, ge=1, le=28)
    notice_days: Optional[int] = Field(None, ge=0, le=365)
    # Optional mechanisms: if absent, the clause is omitted and the simulator
    # reports "the contract defines no such mechanism" (we never invent terms).
    grace_days: Optional[int] = Field(None, ge=0, le=60)
    late_fee_per_day: Optional[int] = Field(None, ge=0)
    default_threshold_days: Optional[int] = Field(None, ge=1, le=365)
    cure_days: Optional[int] = Field(None, ge=0, le=90)
    deposit_refund_days: Optional[int] = Field(None, ge=0, le=180)
    lock_in_months: Optional[int] = Field(None, ge=0, le=60)
    maintenance_monthly: Optional[int] = Field(None, ge=0)
    annual_escalation_pct: Optional[float] = Field(None, ge=0, le=50)


class RentalSpec(SpecFields):
    contract_type: Literal["rental_agreement"] = "rental_agreement"
    # field -> "user" | "inferred" | "suggested_default"
    provenance: dict[str, str] = Field(default_factory=dict)


class FreelanceSpec(BaseModel):
    contract_type: Literal["freelance_service"] = "freelance_service"
    state: Optional[str] = None
    city: Optional[str] = None
    client_name: Optional[str] = None
    freelancer_name: Optional[str] = None
    services_description: Optional[str] = None
    start_date: Optional[date] = None
    delivery_date: Optional[date] = None
    total_fee: Optional[int] = Field(None, gt=0)
    payment_due_days: Optional[int] = Field(None, ge=0, le=180)
    ip_ownership: Optional[Literal["client_on_full_payment", "freelancer_retains"]] = None
    termination_notice_days: Optional[int] = Field(None, ge=0, le=180)
    advance_percent: Optional[int] = Field(None, ge=0, le=100)
    late_interest_pct_per_month: Optional[float] = Field(None, ge=0, le=10)
    revision_rounds: Optional[int] = Field(None, ge=0, le=20)
    confidentiality_years: Optional[int] = Field(None, ge=0, le=20)
    non_compete_months: Optional[int] = Field(None, ge=0, le=60)
    liability_cap_multiple: Optional[float] = Field(None, gt=0, le=20)
    kill_fee_percent: Optional[int] = Field(None, ge=0, le=100)
    provenance: dict[str, str] = Field(default_factory=dict)


class EmploymentSpec(BaseModel):
    contract_type: Literal["employment"] = "employment"
    state: Optional[str] = None
    city: Optional[str] = None
    employer_name: Optional[str] = None
    employee_name: Optional[str] = None
    designation: Optional[str] = None
    start_date: Optional[date] = None
    monthly_salary: Optional[int] = Field(None, gt=0)
    notice_period_days: Optional[int] = Field(None, ge=0, le=365)
    ip_to_employer: Optional[bool] = None
    probation_months: Optional[int] = Field(None, ge=0, le=24)
    probation_notice_days: Optional[int] = Field(None, ge=0, le=90)
    confidentiality_years: Optional[int] = Field(None, ge=0, le=20)
    non_solicit_months: Optional[int] = Field(None, ge=0, le=60)
    non_compete_months: Optional[int] = Field(None, ge=0, le=60)
    training_bond_amount: Optional[int] = Field(None, ge=0)
    training_bond_months: Optional[int] = Field(None, ge=0, le=60)
    bond_pro_rata: Optional[bool] = None
    provenance: dict[str, str] = Field(default_factory=dict)


class CommonAgreementFields(BaseModel):
    state: Optional[str] = None
    city: Optional[str] = None
    provenance: dict[str, str] = Field(default_factory=dict)


class NdaSpec(CommonAgreementFields):
    contract_type: Literal["nda"] = "nda"
    discloser_name: Optional[str] = None
    recipient_name: Optional[str] = None
    mutual: Optional[bool] = None
    purpose: Optional[str] = None
    effective_date: Optional[date] = None
    term_months: Optional[int] = Field(None, ge=1, le=120)
    confidentiality_years: Optional[int] = Field(None, ge=1, le=20)


class SalePurchaseSpec(CommonAgreementFields):
    contract_type: Literal["sale_purchase"] = "sale_purchase"
    seller_name: Optional[str] = None
    buyer_name: Optional[str] = None
    goods_description: Optional[str] = None
    quantity: Optional[str] = None
    total_price: Optional[int] = Field(None, gt=0)
    tax_treatment: Optional[Literal["included", "exclusive", "not_specified"]] = None
    delivery_date: Optional[date] = None
    delivery_place: Optional[str] = None
    payment_trigger: Optional[Literal["invoice", "delivery", "acceptance"]] = None
    payment_due_days: Optional[int] = Field(None, ge=0, le=365)
    inspection_days: Optional[int] = Field(None, ge=0, le=90)
    risk_transfer: Optional[Literal["on_delivery", "on_acceptance"]] = None


class PartnershipSpec(CommonAgreementFields):
    contract_type: Literal["partnership"] = "partnership"
    partner_a_name: Optional[str] = None
    partner_b_name: Optional[str] = None
    other_partners: Optional[str] = None
    business_description: Optional[str] = None
    start_date: Optional[date] = None
    duration: Optional[str] = None
    capital_contributions: Optional[str] = None
    profit_loss_shares: Optional[str] = None
    management_rules: Optional[str] = None
    withdrawal_notice_days: Optional[int] = Field(None, ge=0, le=365)


class PrivateLoanSpec(CommonAgreementFields):
    contract_type: Literal["private_loan"] = "private_loan"
    lender_name: Optional[str] = None
    borrower_name: Optional[str] = None
    principal_amount: Optional[int] = Field(None, gt=0)
    purpose: Optional[str] = None
    disbursement_date: Optional[date] = None
    annual_interest_rate_pct: Optional[float] = Field(None, ge=0, le=100)
    repayment_schedule: Optional[str] = None
    final_due_date: Optional[date] = None
    security_terms: Optional[str] = None


class IpLicenceSpec(CommonAgreementFields):
    contract_type: Literal["ip_licence"] = "ip_licence"
    licensor_name: Optional[str] = None
    licensee_name: Optional[str] = None
    licensed_material: Optional[str] = None
    permitted_use: Optional[str] = None
    territory: Optional[str] = None
    effective_date: Optional[date] = None
    term_months: Optional[int] = Field(None, ge=1, le=120)
    exclusive: Optional[bool] = None
    licence_fee: Optional[int] = Field(None, ge=0)
    fee_terms: Optional[str] = None
    sublicensing_allowed: Optional[bool] = None


class MouSpec(CommonAgreementFields):
    contract_type: Literal["mou"] = "mou"
    party_a_name: Optional[str] = None
    party_b_name: Optional[str] = None
    purpose: Optional[str] = None
    scope: Optional[str] = None
    responsibilities: Optional[str] = None
    costs_and_funding: Optional[str] = None
    effective_date: Optional[date] = None
    term_months: Optional[int] = Field(None, ge=1, le=120)
    binding_status: Optional[Literal["non_binding", "binding", "selected_terms_binding"]] = None
    binding_terms: Optional[str] = None


Spec = Annotated[
    Union[
        RentalSpec, FreelanceSpec, EmploymentSpec, NdaSpec, SalePurchaseSpec,
        PartnershipSpec, PrivateLoanSpec, IpLicenceSpec, MouSpec,
    ],
    Field(discriminator="contract_type"),
]


def missing_fields(spec) -> list[str]:
    from .types import REGISTRY  # lazy: types import this module

    return REGISTRY[spec.contract_type].missing(spec)


class Redline(BaseModel):
    clause_key: str
    original: str
    proposed: str
    risk_to_party_a: str
    risk_to_party_b: str
    legal_question: str
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)
    warning: Optional[str] = None  # e.g. proposal changes numbers -> cannot auto-accept
    status: Literal["pending", "accepted", "rejected"] = "pending"


class Clause(BaseModel):
    key: str
    title: str
    text: str
    original_text: str
    risk: Literal["low", "medium", "high"] = "low"
    legal_basis: list[str] = Field(default_factory=list)
    evidence_queries: list[str] = Field(default_factory=list)
    version: int = 1
    status: Literal["draft", "revised"] = "draft"


class Evidence(BaseModel):
    id: str
    clause_key: str
    proposition: str
    source_kind: Literal["judgment"] = "judgment"
    source_id: str
    title: Optional[str] = None
    court: Optional[str] = None
    date: Optional[str] = None
    url: str
    passage: str = ""
    judge_reason: str = ""
    query: Optional[str] = None
    source: Optional[str] = None  # 'indiankanoon' (API) or 'tavily' (web-search snippet)
    # verified only if: metadata resolved + passage retrieved + judge says supports
    # + the judge's supporting quote is found inside the retrieved passage.
    status: Literal["verified", "unsupported", "contradicts", "unresolved"]
    retrieved_at: str = Field(default_factory=now)


class Obligation(BaseModel):
    id: str
    kind: str
    party: str
    clause_key: str
    description: str
    rule: dict = Field(default_factory=dict)


class ExecutionStatus(BaseModel):
    """Every flag defaults to False. A flag flips only when a human records
    evidence for it. Nothing is ever auto-marked valid."""
    draft_prepared: bool = True
    legal_review_completed: bool = False
    stamp_duty_verified: bool = False
    stamp_duty_paid: bool = False
    registration_completed: bool = False
    signed_by_parties: bool = False
    notes: dict[str, str] = Field(default_factory=dict)


class CopilotSuggestion(BaseModel):
    id: str
    clause_key: str
    expected_version: int
    original_text: str
    proposed_text: str
    rationale: str
    number_integrity: bool
    created_at: str = Field(default_factory=now)
    status: Literal["pending", "applied", "dismissed", "stale"] = "pending"


class CopilotTermSuggestion(BaseModel):
    id: str
    field: str
    expected_value: Any
    proposed_value: Any
    expected_terms: dict[str, Any]
    expected_clause_versions: dict[str, int]
    rationale: str
    created_at: str = Field(default_factory=now)
    status: Literal["pending", "applied", "dismissed", "stale"] = "pending"


class Contract(BaseModel):
    id: str
    spec: Spec
    clauses: list[Clause] = Field(default_factory=list)
    redlines: list[Redline] = Field(default_factory=list)
    copilot_suggestions: list[CopilotSuggestion] = Field(default_factory=list)
    copilot_term_suggestions: list[CopilotTermSuggestion] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    execution: ExecutionStatus = Field(default_factory=ExecutionStatus)
    source: Optional[dict] = None  # set when opened from an uploaded document
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
