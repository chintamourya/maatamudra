"""Pan-India execution guidance. Portal discovery is not a legal determination or duty calculation."""
from __future__ import annotations
import json
from pathlib import Path
from ..models import ExecutionStatus, RentalSpec

RULES = json.loads((Path(__file__).resolve().parents[2] / "data" / "state_rules.json").read_text(encoding="utf-8"))

def checklist(spec: RentalSpec, status: ExecutionStatus) -> dict:
    state = (spec.state or "").strip().casefold()
    rules = RULES.get(state)
    if not rules:
        return {"supported": False, "message": f"Select a recognised Indian State/UT before generating execution guidance (received: {spec.state}).", "items": [], "status": status.model_dump()}
    is_rental = spec.contract_type == "rental_agreement"
    items = [
      {"id":"stamp_duty","title":"Stamp duty on the instrument","guidance":rules["stamp_duty"]["guidance"],"source_url":rules["stamp_duty"]["source_url"],"rule_status":rules["stamp_duty"]["rule_status"],"done":status.stamp_duty_verified,"action":"Confirm the exact instrument article and current duty in the applicable Gazette/official portal; record the official receipt."},
      {"id":"registration","title":"Registration requirement","guidance":rules["registration"]["guidance"] + (" For a lease exceeding one year, examine section 107 of the Transfer of Property Act, 1882 and section 17 of the Registration Act, 1908, plus applicable amendments." if is_rental and getattr(spec,"term_months",0) and spec.term_months>12 else " Do not infer an exemption solely from an 11-month term." if is_rental else " Check whether the instrument or transaction is subject to compulsory registration."),"source_url":rules["registration"]["source_url"],"rule_status":rules["registration"]["rule_status"],"done":status.registration_completed,"action":"Confirm with the relevant Sub-Registrar/official portal or an Indian advocate."},
      {"id":"signing","title":"Signing and witnesses","guidance":rules["signing"]["guidance"],"source_url":rules["signing"]["source_url"],"rule_status":rules["signing"]["rule_status"],"done":status.signed_by_parties,"action":"Choose wet-signature or a legally eligible electronic-signature route after confirming instrument exclusions."},
    ]
    if spec.contract_type == "employment":
      items.append({"id":"labour_law","title":"Employment and labour-law applicability","guidance":"The four Labour Codes were made effective from 21 November 2025. The relevant provisions, applicable Central/State rules, notifications, establishment classification and worker category must be checked for this employment relationship.","source_url":"https://labour.gov.in/offerings/schemes-and-services/details/labour-codes-gzNzQzMtQWa","rule_status":"central_codes_source_identified_state_and_fact_specific_rules_require_review","done":False,"action":"Check current Ministry and State Gazette rules for the establishment and employee category."})
    items.append({"id":"lawyer","title":"Human legal review","guidance":"Have an Indian advocate review the final agreement where the transaction, amount, property, employment or risk warrants it. AI review is not lawyer certification.","source_url":None,"rule_status":"recommended_human_review","done":status.legal_review_completed,"action":"Share the final draft and source-linked findings with the reviewing advocate."})
    return {"supported":True,"state":rules["name"],"items":items,"status":status.model_dump(),"source_registry":rules["sources"],"disclaimer":"Pan-India official portal discovery is provided. Stamp rates, exemptions, registration obligations and legal conclusions are not certified; verify the current instrument-specific Gazette and facts."}
