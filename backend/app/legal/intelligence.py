"""Explainable, deliberately conservative contract checks for the hackathon MVP.
Findings are prompts for review, not determinations of validity or enforceability.
"""
from __future__ import annotations
from .jurisdictions import CENTRAL_LAWS, get_jurisdiction

ACTS = {
    "contract_act_1872": "Indian Contract Act, 1872",
    "transfer_property_act_1882": "Transfer of Property Act, 1882",
    "registration_act_1908": "Registration Act, 1908",
    "it_act_2000": "Information Technology Act, 2000",
    "msmed_act_2006": "Micro, Small and Medium Enterprises Development Act, 2006",
    "arbitration_act_1996": "Arbitration and Conciliation Act, 1996",
    "copyright_act_1957": "Copyright Act, 1957",
}

def _finding(fid: str, category: str, severity: str, title: str, message: str, basis: list[str],
             source: str = "https://www.indiacode.nic.in/", action: str = "Confirm the current provision and facts before relying on this finding.") -> dict:
    return {"id": fid, "category": category, "severity": severity, "title": title,
            "message": message, "legal_basis": basis, "source_url": source,
            "verification": "source_linked_not_individually_verified", "recommended_action": action}

def analyze_contract(spec, clauses: list, state_catalogue: list[dict]) -> dict:
    state = getattr(spec, "state", None)
    selected = get_jurisdiction(state)
    findings: list[dict] = []
    ct = spec.contract_type
    non_compete = getattr(spec, "non_compete_months", None)
    if non_compete and non_compete > 0:
        findings.append(_finding("restraint_of_trade", "statutory_risk", "high", "Post-term non-compete requires legal review",
            "A restriction on carrying on a lawful profession, trade or business may raise an issue under section 27 of the Indian Contract Act, 1872. Assess the exact wording, duration, scope and facts; do not assume enforceability.",
            ["Indian Contract Act, 1872, section 27"], action="Ask an Indian advocate to review the restriction and consider narrower confidentiality, IP and non-solicitation protections where appropriate."))
    if ct == "rental_agreement":
        term = getattr(spec, "term_months", None)
        if term and term > 12:
            findings.append(_finding("lease_registration", "execution_risk", "high", "Lease may require a registered instrument",
                "A lease exceeding one year can engage section 107 of the Transfer of Property Act, 1882 and compulsory-registration provisions. Confirm the exact instrument, applicable amendments and execution facts.",
                ["Transfer of Property Act, 1882, section 107", "Registration Act, 1908, section 17"], action="Verify the applicable state rules and registration procedure with the relevant Registration Department before execution."))
        findings.append(_finding("rental_stamp_duty", "execution_risk", "medium", "State stamp duty must be checked",
            f"Stamp duty depends on the instrument and applicable state/UT law. VACHAN does not calculate or certify the amount for {state or 'an unspecified jurisdiction'}.",
            ["Applicable stamp legislation and state/UT amendments"], action="Check the current official state/UT stamp schedule or e-stamping portal. Do not infer that an 11-month term is stamp-duty exempt."))
    if ct in {"freelance_service", "sale_purchase"}:
        findings.append(_finding("msme_status_check", "statutory_risk", "medium", "Check micro/small enterprise supplier status",
            "If the supplier is a qualifying micro or small enterprise with the required registration, sections 15–16 of the MSMED Act may apply: the agreed payment period is subject to a 45-day ceiling, and delayed payment can attract statutory compound interest with monthly rests at three times the RBI bank rate. Eligibility, acceptance date and current statutory text must be checked; the contract data does not establish them.",
            ["Micro, Small and Medium Enterprises Development Act, 2006, sections 15–16"], action="Ask whether the supplier holds applicable Udyam registration and verify the current statutory requirements before calculating a due date."))
    if ct == "employment":
        findings.append(_finding("employment_rules", "statutory_risk", "medium", "Employment terms need establishment-specific review",
            "Employment obligations may depend on worker/employee classification, establishment, headcount, applicable labour-code provisions and Central/State rules. This prototype does not decide applicability.",
            ["Applicable labour codes, rules and notifications"], source="https://labour.gov.in/", action="Confirm the establishment category, worker classification, applicable rules and current commencement notifications."))
    if not state:
        findings.append(_finding("jurisdiction_missing", "missing", "high", "State/UT not specified",
            "State-specific amendments, stamp duty and registration procedures cannot be assessed until the relevant jurisdiction is identified.",
            ["Applicable State/UT legislation"], action="Select the relevant state/UT and, where relevant, the property or place of execution."))
    elif not selected:
        findings.append(_finding("jurisdiction_unrecognised", "missing", "medium", "Jurisdiction needs confirmation",
            "The supplied jurisdiction did not match the application's India state/UT catalogue.", ["Applicable State/UT legislation"]))
    else:
        findings.append(_finding("state_rules_coverage", "coverage_gap", "info", f"{state}: official state portal identified; instrument rules need verification",
            "VACHAN has identified the Government of India Department of Land Resources registration portal directory entry and checked whether this jurisdiction appears in NeSL's digital document execution e-stamping directory. This verifies official discovery routes, not stamp-duty rates, rent-control applicability, exemptions or every instrument-specific rule.",
            ["Applicable State/UT stamp legislation and Gazette notifications", "Registration Department portal"],
            source=(selected.get("registration_portal") or "https://ngdrs.gov.in/NGDRS_Website/state_ut_links.php"),
            action="Open the official Registration Department portal and confirm the current Gazette/schedule for this instrument before execution."))
    findings.append(_finding("electronic_execution_scope", "execution_risk", "info", "Electronic execution is instrument-specific",
        "Electronic-contract recognition does not mean every document can be executed electronically. Check the Information Technology Act exclusions and any separate stamp, registration, witnessing or sector requirements.",
        ["Information Technology Act, 2000, sections 4, 5, 10A and First Schedule"], action="Confirm whether this instrument is eligible for the proposed electronic execution route."))
    return {
        "jurisdiction": {"country": "India", "state_ut": state, "catalogue_match": bool(selected),
                         "coverage": "official_portal_sources_catalogued_not_substantive_rules_verified" if selected else "not_selected",
                         "registration_portal": selected.get("registration_portal") if selected else None,
                         "registration_portal_status": selected.get("registration_portal_status") if selected else None,
                         "digital_e_stamp_status": selected.get("digital_e_stamp_status") if selected else None,
                         "state_rules_verified": False if selected else None},
        "central_laws_catalogue": CENTRAL_LAWS,
        "findings": findings,
        "summary": {"total": len(findings), "high": sum(f["severity"] == "high" for f in findings),
                    "medium": sum(f["severity"] == "medium" for f in findings),
                    "coverage_gaps": sum(f["category"] == "coverage_gap" for f in findings)},
        "notice": "AI-assisted legal information only. Findings are issue-spotting prompts, not legal advice, a legal opinion, or a certification that an agreement is valid or enforceable. State/UT rules and current amendments must be independently verified."
    }
