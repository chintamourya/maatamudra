"""Conservative first-pass templates for frequently used Indian agreements.
These are user-driven starting points, not state-specific legal advice."""
from __future__ import annotations

from datetime import date

from ..contracts.compiler import inr
from ..contracts.library import ClauseDef
from ..models import (
    IpLicenceSpec, MouSpec, NdaSpec, Obligation, PartnershipSpec,
    PrivateLoanSpec, SalePurchaseSpec,
)
from .base import TypeDef


def _context(spec) -> dict:
    data = {key: value for key, value in spec.model_dump().items() if value is not None}
    for key, value in data.items():
        if isinstance(value, date):
            data[key] = value.strftime("%d %B %Y")
    for key in ("total_price", "principal_amount", "licence_fee"):
        if data.get(key) is not None:
            data[key] = inr(data[key])
    data["place"] = spec.city or spec.state or "the place of execution"
    data["other_partners_text"] = (
        f" and {spec.other_partners}" if getattr(spec, "other_partners", None) else ""
    )
    data["mutual_text"] = (
        "Each party may disclose and receive confidential information"
        if getattr(spec, "mutual", False)
        else f"{getattr(spec, 'discloser_name', 'The Disclosing Party')} may disclose confidential information to "
        f"{getattr(spec, 'recipient_name', 'the Receiving Party')}"
    )
    data["tax_treatment_text"] = {
        "included": "The stated price includes taxes only to the extent expressly itemised in the invoice.",
        "exclusive": "Applicable taxes, if any, are additional to the stated price and must be itemised in the invoice.",
        "not_specified": "The parties have not specified whether taxes are included; confirm this before signing.",
    }.get(getattr(spec, "tax_treatment", None), "")
    data["payment_trigger_text"] = {
        "invoice": "the invoice is received",
        "delivery": "delivery",
        "acceptance": "acceptance of the goods",
    }.get(getattr(spec, "payment_trigger", None), "")
    data["interest_text"] = (
        "No interest is charged under the stated terms."
        if getattr(spec, "annual_interest_rate_pct", None) == 0
        else f"The stated interest rate is {getattr(spec, 'annual_interest_rate_pct', '')}% per annum. "
        "The parties should confirm how it is calculated and when it accrues."
    )
    data["risk_transfer_text"] = {
        "on_delivery": "Risk of loss passes on delivery at the stated place.",
        "on_acceptance": "Risk of loss passes when the Buyer accepts the goods after inspection.",
    }.get(getattr(spec, "risk_transfer", None), "")
    data["exclusive_text"] = "exclusive" if getattr(spec, "exclusive", False) else "non-exclusive"
    data["sublicensing_text"] = (
        "The Licensee may grant sublicences only with the Licensor's prior written consent."
        if not getattr(spec, "sublicensing_allowed", False)
        else "The Licensee may grant sublicences within the stated scope and remains responsible for its sublicensees."
    )
    data["binding_status_text"] = {
        "non_binding": "The parties record current intentions only; no obligation to complete the proposed transaction is intended.",
        "binding": "The parties state their intention that this MOU be binding according to its written terms.",
        "selected_terms_binding": "Only the terms identified below are intended to be binding; the remaining terms record current intentions only.",
    }.get(getattr(spec, "binding_status", None), "")
    return data


def _nda_obligations(spec: NdaSpec) -> list[Obligation]:
    return [Obligation(
        id="protect_information", kind="confidentiality",
        party="both" if spec.mutual else "recipient", clause_key="recipient_duties",
        description="Use and protect confidential information only for the stated purpose",
        rule={"purpose": spec.purpose, "confidentiality_years": spec.confidentiality_years},
    )]


def _no_simulation(spec, scenario: dict) -> dict:
    raise ValueError(f"No deterministic scenario is defined for {spec.contract_type}.")


def _dates(*fields):
    def collect(spec):
        return [{"date": getattr(spec, field), "title": title}
                for field, title in fields if getattr(spec, field) is not None]
    return collect


NDA_TYPE = TypeDef(
    key="nda", title="Non-disclosure agreement (NDA)", doc_title="NON-DISCLOSURE AGREEMENT",
    spec_cls=NdaSpec,
    required=["state", "discloser_name", "recipient_name", "mutual", "purpose", "effective_date", "term_months", "confidentiality_years"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to this agreement?",
        "discloser_name": "Who will disclose confidential information?",
        "recipient_name": "Who will receive it?",
        "mutual": "Will both parties share confidential information? (yes or no)",
        "purpose": "For what specific purpose may the information be used?",
        "effective_date": "When should the NDA start?",
        "term_months": "How many months will the NDA remain in force?",
        "confidentiality_years": "How many years should confidentiality continue after it ends?",
    },
    labels={
        "state": "State / UT", "city": "City", "discloser_name": "Disclosing party",
        "recipient_name": "Receiving party", "mutual": "Mutual", "purpose": "Purpose",
        "effective_date": "Effective date", "term_months": "Term (months)",
        "confidentiality_years": "Confidentiality after term (years)",
    },
    party_a="disclosing party", party_b="receiving party",
    party_a_field="discloser_name", party_b_field="recipient_name",
    clauses=[
        ClauseDef("parties", "Parties and purpose",
                  "This Non-Disclosure Agreement is made at {place} between {discloser_name} and {recipient_name}. "
                  "Confidential information may be used only for: {purpose}."),
        ClauseDef("confidential_information", "Confidential information",
                  "{mutual_text}. Confidential information means non-public information disclosed for the stated purpose, "
                  "whether in writing, orally or electronically, that is identified as confidential or would reasonably "
                  "be understood to be confidential."),
        ClauseDef("recipient_duties", "Use and protection",
                  "A receiving party shall use confidential information only for the stated purpose, protect it with "
                  "reasonable care, and disclose it only to personnel who need it for that purpose and are subject to "
                  "confidentiality duties."),
        ClauseDef("exceptions", "Information not covered",
                  "Confidential information does not include information the recipient can show was public without breach, "
                  "already lawfully known, independently developed without use of the information, or lawfully received "
                  "from another source without a confidentiality duty."),
        ClauseDef("required_disclosure", "Disclosure required by law",
                  "If disclosure is required by law, the receiving party may disclose only what is required and, where "
                  "lawfully permitted, shall give the disclosing party advance notice."),
        ClauseDef("return_information", "Return or destruction",
                  "On written request or expiry of this Agreement, each receiving party shall return or destroy the "
                  "confidential information, except a copy retained where required by law or routine secure backups."),
        ClauseDef("ownership", "No transfer of ownership",
                  "Disclosure does not transfer ownership or grant a licence to intellectual property, except the limited "
                  "right to use information for the stated purpose."),
        ClauseDef("term", "Term and continuing duties",
                  "This Agreement starts on {effective_date} and remains in force for {term_months} months. "
                  "Confidentiality duties continue for {confidentiality_years} years after it ends."),
        ClauseDef("disputes", "Disputes and execution",
                  "The parties should identify the courts and signing method appropriate to their transaction and the "
                  "applicable state requirements before signing. This draft does not determine stamp duty or registration."),
    ],
    money_fields=(), context=_context, obligations=_nda_obligations, simulate=_no_simulation,
    scenarios=[], key_dates=_dates(("effective_date", "NDA starts")), lint=lambda spec: [],
    sample={
        "contract_type": "nda", "state": "Telangana", "city": "Hyderabad",
        "discloser_name": "Aster Labs Private Limited", "recipient_name": "Mira Shah",
        "mutual": False, "purpose": "Evaluate a proposed software consulting engagement",
        "effective_date": "2026-12-01", "term_months": 12, "confidentiality_years": 3,
        "provenance": {},
    },
    intake_hint="One-way or mutual non-disclosure agreement (NDA) for a specific business purpose in India.",
)


def _sale_obligations(spec: SalePurchaseSpec) -> list[Obligation]:
    return [
        Obligation(id="deliver_goods", kind="deliver_goods", party="seller", clause_key="delivery",
                   description="Deliver the described goods by the agreed date and place",
                   rule={"date": spec.delivery_date.isoformat(), "place": spec.delivery_place}),
        Obligation(id="pay_price", kind="pay_price", party="buyer", clause_key="payment",
                   description="Pay the stated purchase price", rule={"amount": spec.total_price, "within_days": spec.payment_due_days}),
    ]


def _sale_lint(spec: SalePurchaseSpec) -> list[dict]:
    if spec.risk_transfer is None:
        return [{"clause_key": "risk", "severity": "medium", "message": "The agreement does not specify when risk of loss passes. Decide this with the other party and a lawyer."}]
    if spec.tax_treatment == "not_specified":
        return [{"clause_key": "price", "severity": "medium", "message": "Tax treatment is expressly left open. Confirm whether the price includes applicable taxes."}]
    return []


SALE_PURCHASE_TYPE = TypeDef(
    key="sale_purchase", title="Sale and purchase of goods", doc_title="GOODS SALE AGREEMENT",
    spec_cls=SalePurchaseSpec,
    required=["state", "seller_name", "buyer_name", "goods_description", "quantity", "total_price",
              "tax_treatment", "delivery_date", "delivery_place", "payment_trigger", "payment_due_days"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to this transaction?",
        "seller_name": "Who is selling the goods?",
        "buyer_name": "Who is buying them?",
        "goods_description": "Describe the goods, including model or quality if known.",
        "quantity": "What quantity is being sold?",
        "total_price": "What is the total price in rupees?",
        "tax_treatment": "Are applicable taxes included, additional, or not yet specified?",
        "delivery_date": "When must the goods be delivered?",
        "delivery_place": "Where will delivery take place?",
        "payment_due_days": "How many days after the agreed payment trigger is payment due?",
        "payment_trigger": "Is payment due after invoice, delivery, or acceptance?",
    },
    labels={
        "state": "State / UT", "city": "City", "seller_name": "Seller", "buyer_name": "Buyer",
        "goods_description": "Goods", "quantity": "Quantity", "total_price": "Total price (₹)",
        "tax_treatment": "Tax treatment", "delivery_date": "Delivery date", "delivery_place": "Delivery place",
        "payment_due_days": "Pay within (days)", "payment_trigger": "Payment trigger",
        "inspection_days": "Inspection period (days)",
        "risk_transfer": "Risk passes",
    },
    party_a="seller", party_b="buyer", party_a_field="seller_name", party_b_field="buyer_name",
    clauses=[
        ClauseDef("parties_goods", "Parties and goods",
                  "This agreement is made at {place} between {seller_name} (Seller) and {buyer_name} (Buyer). "
                  "The Seller agrees to sell and the Buyer agrees to buy: {quantity} of {goods_description}."),
        ClauseDef("price", "Price and taxes",
                  "The total purchase price is {total_price}. {tax_treatment_text}"),
        ClauseDef("payment", "Payment",
                  "The Buyer shall pay the stated price within {payment_due_days} days after {payment_trigger_text}."),
        ClauseDef("delivery", "Delivery",
                  "The Seller shall arrange delivery by {delivery_date} at {delivery_place}. The parties should record "
                  "any delivery, packaging or transport charges separately."),
        ClauseDef("inspection", "Inspection", "The Buyer may inspect the goods within {inspection_days} days after delivery "
                  "and notify the Seller in writing of any shortage or visible non-conformity.", ["inspection_days"], "medium"),
        ClauseDef("risk", "Risk of loss", "{risk_transfer_text}", ["risk_transfer"], "medium"),
        ClauseDef("condition", "Condition and agreed specifications",
                  "The goods must match the description and specifications expressly recorded in this agreement. "
                  "Any additional warranty, return right or remedy must be written here before signing."),
        ClauseDef("disputes", "Disputes and execution",
                  "The parties should confirm the applicable state requirements, dispute forum, stamp duty and signing "
                  "formalities with a lawyer before signing."),
    ],
    money_fields=("total_price",), context=_context, obligations=_sale_obligations, simulate=_no_simulation,
    scenarios=[], key_dates=_dates(("delivery_date", "Goods due for delivery")), lint=_sale_lint,
    sample={
        "contract_type": "sale_purchase", "state": "Telangana", "city": "Hyderabad",
        "seller_name": "Aster Office Supplies", "buyer_name": "Mira Shah",
        "goods_description": "ergonomic office chairs, model agreed in the purchase order",
        "quantity": "12 units", "total_price": 180000, "tax_treatment": "not_specified",
        "delivery_date": "2026-12-20", "delivery_place": "Madhapur, Hyderabad",
        "payment_trigger": "acceptance", "payment_due_days": 15,
        "inspection_days": 7, "risk_transfer": "on_delivery", "provenance": {},
    },
    intake_hint="Sale and purchase of goods in India. Extract only the goods, price, tax, payment and delivery terms actually stated.",
)


def _partnership_obligations(spec: PartnershipSpec) -> list[Obligation]:
    return [Obligation(id="contribute_capital", kind="contribute_capital", party="partners",
                       clause_key="capital", description="Make the agreed capital contributions",
                       rule={"terms": spec.capital_contributions})]


def _partnership_lint(spec: PartnershipSpec) -> list[dict]:
    return [
        {"clause_key": "profit_shares", "severity": "medium",
         "message": "Profit and loss shares are free text and are not checked to total 100%. Have a lawyer and accountant verify them."},
        {"clause_key": "registration", "severity": "medium",
         "message": "Partnership registration, tax and state stamp requirements are not determined by this draft. Confirm them before operating."},
    ]


PARTNERSHIP_TYPE = TypeDef(
    key="partnership", title="Partnership deed", doc_title="PARTNERSHIP DEED",
    spec_cls=PartnershipSpec,
    required=["state", "partner_a_name", "partner_b_name", "business_description", "start_date", "duration",
              "capital_contributions", "profit_loss_shares", "management_rules", "withdrawal_notice_days"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to the partnership?",
        "partner_a_name": "What is the first partner's full legal name?",
        "partner_b_name": "What is the second partner's full legal name?",
        "business_description": "What business will the partners carry on?",
        "start_date": "When should the partnership start?",
        "duration": "Is it for a fixed period or until dissolved? Describe the agreed duration.",
        "capital_contributions": "What will each partner contribute? State cash, assets or services clearly.",
        "profit_loss_shares": "How will profits and losses be shared? State each partner's percentage or agreed method.",
        "management_rules": "Who can make decisions, sign contracts and operate the business account?",
        "withdrawal_notice_days": "How many days' notice is required for a partner to withdraw?",
    },
    labels={
        "state": "State / UT", "city": "City", "partner_a_name": "Partner A", "partner_b_name": "Partner B",
        "other_partners": "Other partners", "business_description": "Business", "start_date": "Start",
        "duration": "Duration", "capital_contributions": "Capital contributions",
        "profit_loss_shares": "Profit/loss shares", "management_rules": "Management",
        "withdrawal_notice_days": "Withdrawal notice (days)",
    },
    party_a="partner A", party_b="partner B", party_a_field="partner_a_name", party_b_field="partner_b_name",
    clauses=[
        ClauseDef("partners_business", "Partners and business",
                  "This Partnership Deed is made at {place} between {partner_a_name} and {partner_b_name}"
                  "{other_partners_text}. The partners agree to carry on the following business: {business_description}."),
        ClauseDef("term", "Start and duration",
                  "The partnership starts on {start_date} and continues for {duration}, subject to this deed and applicable law."),
        ClauseDef("capital", "Capital contributions",
                  "The partners' agreed contributions are: {capital_contributions}. Any later contribution or change "
                  "must be recorded in writing and agreed by the partners."),
        ClauseDef("profit_shares", "Profit and loss sharing",
                  "The partners will share profits and losses as follows: {profit_loss_shares}. The partners must have "
                  "their accountant confirm the accounting method and that the shares are complete."),
        ClauseDef("management", "Management and authority",
                  "The partners' agreed decision-making and signing rules are: {management_rules}. A partner should "
                  "not assume authority beyond these written rules."),
        ClauseDef("withdrawal", "Withdrawal",
                  "A partner who wishes to withdraw shall give {withdrawal_notice_days} days' written notice. The "
                  "partners should record valuation, accounts, client handover and settlement arrangements before signing."),
        ClauseDef("records", "Accounts and records",
                  "The partnership shall keep accurate business, tax and financial records and make them available to "
                  "each partner on reasonable request."),
        ClauseDef("disputes", "Disputes and state formalities",
                  "The partners should obtain advice on registration, tax, stamp duty, dissolution and dispute resolution "
                  "for their state before signing or commencing business."),
    ],
    money_fields=(), context=_context, obligations=_partnership_obligations, simulate=_no_simulation,
    scenarios=[], key_dates=_dates(("start_date", "Partnership starts")), lint=_partnership_lint,
    sample={
        "contract_type": "partnership", "state": "Telangana", "city": "Hyderabad",
        "partner_a_name": "Mira Shah", "partner_b_name": "Arjun Rao",
        "other_partners": None, "business_description": "design and sale of handmade homeware",
        "start_date": "2027-01-01", "duration": "until dissolved under this deed",
        "capital_contributions": "Mira: ₹2,00,000 cash; Arjun: ₹1,00,000 cash and design services",
        "profit_loss_shares": "Mira 60%; Arjun 40%",
        "management_rules": "Both partners must approve borrowing and contracts above ₹1,00,000; either may approve ordinary purchases.",
        "withdrawal_notice_days": 60, "provenance": {},
    },
    intake_hint="A two-or-more person business partnership deed in India. Do not invent capital, sharing ratios or authority rules.",
)


def _loan_obligations(spec: PrivateLoanSpec) -> list[Obligation]:
    return [
        Obligation(id="disburse_loan", kind="disburse_loan", party="lender", clause_key="disbursement",
                   description="Disburse the agreed loan principal",
                   rule={"amount": spec.principal_amount, "date": spec.disbursement_date.isoformat()}),
        Obligation(id="repay_loan", kind="repay_loan", party="borrower", clause_key="repayment",
                   description="Repay according to the agreed schedule",
                   rule={"schedule": spec.repayment_schedule, "final_due_date": spec.final_due_date.isoformat()}),
    ]


def _loan_lint(spec: PrivateLoanSpec) -> list[dict]:
    return [{"clause_key": "legal_review", "severity": "high",
             "message": "This is a simple private-loan starting point, not for regulated lending, consumer credit or complex secured finance. Confirm applicable law, licensing, stamp duty, security perfection and tax with a lawyer."}]


PRIVATE_LOAN_TYPE = TypeDef(
    key="private_loan", title="Private loan agreement", doc_title="PRIVATE LOAN AGREEMENT",
    spec_cls=PrivateLoanSpec,
    required=["state", "lender_name", "borrower_name", "principal_amount", "purpose", "disbursement_date",
              "annual_interest_rate_pct", "repayment_schedule", "final_due_date", "security_terms"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to this loan?",
        "lender_name": "Who is lending the money?",
        "borrower_name": "Who is borrowing it?",
        "principal_amount": "What is the principal amount in rupees?",
        "purpose": "What is the stated purpose of the loan?",
        "disbursement_date": "When will the loan be disbursed?",
        "annual_interest_rate_pct": "What annual interest rate applies? Enter 0 if interest-free.",
        "repayment_schedule": "Describe the agreed instalments and payment dates.",
        "final_due_date": "When is the final repayment due?",
        "security_terms": "Describe the agreed security, or enter 'Unsecured'.",
    },
    labels={
        "state": "State / UT", "city": "City", "lender_name": "Lender", "borrower_name": "Borrower",
        "principal_amount": "Principal (₹)", "purpose": "Purpose", "disbursement_date": "Disbursement",
        "annual_interest_rate_pct": "Interest (% p.a.)", "repayment_schedule": "Repayment schedule",
        "final_due_date": "Final due date", "security_terms": "Security",
    },
    party_a="lender", party_b="borrower", party_a_field="lender_name", party_b_field="borrower_name",
    clauses=[
        ClauseDef("parties_loan", "Parties and purpose",
                  "This Private Loan Agreement is made at {place} between {lender_name} (Lender) and {borrower_name} "
                  "(Borrower). The stated purpose is: {purpose}."),
        ClauseDef("principal", "Principal and disbursement",
                  "The principal is {principal_amount}. The Lender shall disburse it on {disbursement_date} by a "
                  "traceable payment method, with receipt or transfer evidence retained by both parties."),
        ClauseDef("interest", "Interest",
                  "{interest_text}"),
        ClauseDef("repayment", "Repayment",
                  "The Borrower shall repay according to this schedule: {repayment_schedule}. The final due date is "
                  "{final_due_date}. No repayment calculation is inferred by this draft."),
        ClauseDef("security", "Security",
                  "Agreed security terms: {security_terms}. Any security over property or assets requires separate "
                  "legal review and may require registration or other formalities."),
        ClauseDef("default", "Missed payment",
                  "The parties must agree a written notice and cure process for a missed payment before signing. "
                  "This template does not invent a default fee or acceleration remedy."),
        ClauseDef("records", "Payment records",
                  "The parties shall keep evidence of disbursement and repayments and reconcile their records against "
                  "the written repayment schedule."),
        ClauseDef("disputes", "Disputes and legal review",
                  "This template is for a simple private bilateral loan only. Confirm lending regulation, state stamp "
                  "duty, tax and any security formalities with a lawyer before signing."),
    ],
    money_fields=("principal_amount",), context=_context, obligations=_loan_obligations,
    simulate=_no_simulation, scenarios=[],
    key_dates=_dates(("disbursement_date", "Loan disbursement"), ("final_due_date", "Final repayment due")),
    lint=_loan_lint,
    sample={
        "contract_type": "private_loan", "state": "Telangana", "city": "Hyderabad",
        "lender_name": "Mira Shah", "borrower_name": "Arjun Rao", "principal_amount": 200000,
        "purpose": "purchase of equipment for a small business", "disbursement_date": "2026-12-01",
        "annual_interest_rate_pct": 0, "repayment_schedule": "₹20,000 on the first day of each month for 10 months",
        "final_due_date": "2027-10-01", "security_terms": "Unsecured", "provenance": {},
    },
    intake_hint="A simple private loan between two parties in India. Do not treat this as regulated consumer or commercial lending.",
)


def _licence_obligations(spec: IpLicenceSpec) -> list[Obligation]:
    if spec.licence_fee == 0:
        return []
    return [Obligation(id="pay_licence_fee", kind="pay_licence_fee", party="licensee",
                       clause_key="fees", description="Pay the agreed licence fee",
                       rule={"amount": spec.licence_fee, "terms": spec.fee_terms})]


def _licence_lint(spec: IpLicenceSpec) -> list[dict]:
    return [{"clause_key": "rights", "severity": "medium",
             "message": "Confirm ownership, any pre-existing third-party rights, registration formalities and whether the written licence scope matches the intended use."}]


IP_LICENCE_TYPE = TypeDef(
    key="ip_licence", title="Intellectual property licence", doc_title="INTELLECTUAL PROPERTY LICENCE",
    spec_cls=IpLicenceSpec,
    required=["state", "licensor_name", "licensee_name", "licensed_material", "permitted_use", "territory",
              "effective_date", "term_months", "exclusive", "licence_fee", "fee_terms", "sublicensing_allowed"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to this licence?",
        "licensor_name": "Who owns or controls the material being licensed?",
        "licensee_name": "Who will receive the licence?",
        "licensed_material": "Describe the specific work, software, brand or other material.",
        "permitted_use": "What exactly may the licensee do with it?",
        "territory": "Where may the material be used?",
        "effective_date": "When should the licence start?",
        "term_months": "How many months will it last?",
        "exclusive": "Is the licence exclusive? (yes or no)",
        "licence_fee": "What is the total licence fee in rupees? Enter 0 if no fee.",
        "fee_terms": "When and how is the fee paid? Enter 'No fee' if the licence is free.",
        "sublicensing_allowed": "May the licensee grant sublicences? (yes or no)",
    },
    labels={
        "state": "State / UT", "city": "City", "licensor_name": "Licensor", "licensee_name": "Licensee",
        "licensed_material": "Licensed material", "permitted_use": "Permitted use", "territory": "Territory",
        "effective_date": "Effective date", "term_months": "Term (months)", "exclusive": "Exclusive",
        "licence_fee": "Fee (₹)", "fee_terms": "Fee terms", "sublicensing_allowed": "Sublicensing allowed",
    },
    party_a="licensor", party_b="licensee", party_a_field="licensor_name", party_b_field="licensee_name",
    clauses=[
        ClauseDef("parties_rights", "Parties and licensed material",
                  "This IP Licence is made at {place} between {licensor_name} (Licensor) and {licensee_name} "
                  "(Licensee). It covers only this material: {licensed_material}."),
        ClauseDef("scope", "Scope and permitted use",
                  "The Licensee may use the material only for: {permitted_use}. The territory is {territory}, and "
                  "the licence is {exclusive_text}. Uses outside this written scope are not granted."),
        ClauseDef("term", "Term",
                  "The licence starts on {effective_date} and continues for {term_months} months unless ended earlier "
                  "under a written agreement."),
        ClauseDef("fees", "Fee and payment",
                  "The licence fee is {licence_fee}. Payment terms: {fee_terms}."),
        ClauseDef("sublicensing", "Sublicensing",
                  "{sublicensing_text}"),
        ClauseDef("ownership", "Ownership and changes",
                  "Except for the limited permission expressly stated here, ownership remains with the party that "
                  "owned the material before this licence. The parties should separately record ownership of any "
                  "modifications, adaptations or new work."),
        ClauseDef("termination", "Termination and return",
                  "The parties should agree a written breach notice and cure period. On expiry or termination, the "
                  "Licensee must stop uses not otherwise permitted and follow any agreed return or deletion process."),
        ClauseDef("disputes", "Disputes and execution",
                  "Confirm ownership evidence, tax, applicable state stamp duty and any recordal formalities with a "
                  "lawyer before signing."),
    ],
    money_fields=("licence_fee",), context=_context, obligations=_licence_obligations,
    simulate=_no_simulation, scenarios=[], key_dates=_dates(("effective_date", "Licence starts")),
    lint=_licence_lint,
    sample={
        "contract_type": "ip_licence", "state": "Telangana", "city": "Hyderabad",
        "licensor_name": "Mira Shah", "licensee_name": "Aster Labs Private Limited",
        "licensed_material": "Mira's inventory management software, version 1.4",
        "permitted_use": "internal inventory tracking at the licensee's Indian offices",
        "territory": "India", "effective_date": "2026-12-01", "term_months": 12,
        "exclusive": False, "licence_fee": 50000, "fee_terms": "within 15 days of invoice",
        "sublicensing_allowed": False, "provenance": {},
    },
    intake_hint="An intellectual-property licence in India, such as software, content, brand or know-how. This is not a real-estate lease.",
)


def _mou_lint(spec: MouSpec) -> list[dict]:
    return [{"clause_key": "binding_status", "severity": "high",
             "message": "An MOU's binding effect depends on its wording and context. Have a lawyer review the stated binding status and any selected binding terms."}]


def _mou_obligations(spec: MouSpec) -> list[Obligation]:
    return [Obligation(id="carry_out_mou_roles", kind="collaboration",
                       party="both", clause_key="responsibilities",
                       description="Record and review the responsibilities stated in the MoU",
                       rule={"responsibilities": spec.responsibilities, "scope": spec.scope})]


MOU_TYPE = TypeDef(
    key="mou", title="Memorandum of understanding (MoU)", doc_title="MEMORANDUM OF UNDERSTANDING",
    spec_cls=MouSpec,
    required=["state", "party_a_name", "party_b_name", "purpose", "scope", "responsibilities",
              "costs_and_funding", "effective_date", "term_months", "binding_status", "binding_terms"],
    questions={
        "state": "Which Indian state or Union Territory is relevant to this MoU?",
        "party_a_name": "What is the first party's full legal name?",
        "party_b_name": "What is the second party's full legal name?",
        "purpose": "What is the purpose of the proposed collaboration?",
        "scope": "What work or activity is in scope?",
        "responsibilities": "What will each party do?",
        "costs_and_funding": "How will costs, funding and expenses be handled?",
        "effective_date": "When should the MoU start?",
        "term_months": "How many months will it remain in effect?",
        "binding_status": "Is it intended to be non-binding, binding, or binding only for selected terms?",
        "binding_terms": "List the terms intended to bind, or explicitly write 'None' if there are none.",
    },
    labels={
        "state": "State / UT", "city": "City", "party_a_name": "Party A", "party_b_name": "Party B",
        "purpose": "Purpose", "scope": "Scope", "responsibilities": "Responsibilities",
        "costs_and_funding": "Costs and funding", "effective_date": "Effective date",
        "term_months": "Term (months)", "binding_status": "Intended status", "binding_terms": "Binding terms",
    },
    party_a="party A", party_b="party B", party_a_field="party_a_name", party_b_field="party_b_name",
    clauses=[
        ClauseDef("parties_purpose", "Parties and purpose",
                  "This Memorandum of Understanding is made at {place} between {party_a_name} and {party_b_name} "
                  "to record their understanding about: {purpose}."),
        ClauseDef("scope", "Scope",
                  "The proposed collaboration covers: {scope}. Any expansion should be agreed in writing."),
        ClauseDef("responsibilities", "Responsibilities",
                  "The parties' stated responsibilities are: {responsibilities}."),
        ClauseDef("costs", "Costs and funding",
                  "The parties' stated arrangement for costs and funding is: {costs_and_funding}. No additional "
                  "payment obligation is added by this draft."),
        ClauseDef("term", "Term",
                  "This MoU starts on {effective_date} and continues for {term_months} months unless ended earlier "
                  "by written agreement."),
        ClauseDef("binding_status", "Intended binding status",
                  "{binding_status_text} Terms identified by the parties as intended to bind: {binding_terms}. "
                  "The legal effect of an MoU depends on its complete wording and circumstances; obtain legal review."),
        ClauseDef("confidentiality", "Confidential information",
                  "This MoU does not itself create a confidentiality duty unless the parties expressly identify one "
                  "above as an intended binding term or sign a separate NDA."),
        ClauseDef("disputes", "Disputes and execution",
                  "Before signing, identify the governing-law and dispute terms, state stamp duty and any formalities "
                  "with a lawyer."),
    ],
    money_fields=(), context=_context, obligations=_mou_obligations, simulate=_no_simulation,
    scenarios=[], key_dates=_dates(("effective_date", "MoU starts")), lint=_mou_lint,
    sample={
        "contract_type": "mou", "state": "Telangana", "city": "Hyderabad",
        "party_a_name": "Aster Labs Private Limited", "party_b_name": "Mira Shah",
        "purpose": "explore a pilot for digitising inventory records",
        "scope": "a 60-day pilot at one Mumbai office",
        "responsibilities": "Aster provides access to sample records; Mira configures the pilot and provides training.",
        "costs_and_funding": "Each party bears its own costs; no payment is committed.",
        "effective_date": "2026-12-01", "term_months": 2, "binding_status": "non_binding",
        "binding_terms": "None", "provenance": {},
    },
    intake_hint="A memorandum of understanding for a proposed collaboration in India. Ask whether it is intended to be binding; do not assume.",
)


COMMON_TYPES = (NDA_TYPE, SALE_PURCHASE_TYPE, PARTNERSHIP_TYPE, PRIVATE_LOAN_TYPE, IP_LICENCE_TYPE, MOU_TYPE)
