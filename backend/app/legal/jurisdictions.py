"""Pan-India jurisdiction source registry. Portal verification is not substantive-law verification."""
from __future__ import annotations
import json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "jurisdictions.json"
_JURISDICTIONS = json.loads(_DATA.read_text(encoding="utf-8"))
STATES_AND_UTS = [x["name"] for x in _JURISDICTIONS]

CENTRAL_LAWS = [
 {"id":"contract_act_1872","name":"Indian Contract Act, 1872","topics":["formation","capacity","consent","consideration","breach","damages"],"source":"https://www.indiacode.nic.in/handle/123456789/12845","status":"official_IndiaCode_source_identified; apply current amendments and facts"},
 {"id":"specific_relief_act_1963","name":"Specific Relief Act, 1963","topics":["specific performance","injunctions","relief"],"source":"https://www.indiacode.nic.in/","status":"official_source_catalogued; provision-level review required"},
 {"id":"it_act_2000","name":"Information Technology Act, 2000","topics":["electronic records","electronic signatures","electronic contracts","exclusions"],"source":"https://www.indiacode.nic.in/indiacode/handle/123456789/1999?locale=en","status":"official_IndiaCode_source_identified; check First Schedule exclusions"},
 {"id":"indian_stamp_act_1899","name":"Indian Stamp Act, 1899 and applicable State/UT stamp legislation","topics":["stamp duty","instruments"],"source":"https://www.indiacode.nic.in/","status":"state schedules/amendments are instrument-specific; no duty amount is calculated by this prototype"},
 {"id":"registration_act_1908","name":"Registration Act, 1908 and applicable State/UT amendments","topics":["compulsory registration","leases","documents"],"source":"https://www.indiacode.nic.in/","status":"instrument facts and state amendments must be checked"},
 {"id":"transfer_property_act_1882","name":"Transfer of Property Act, 1882","topics":["leases","immovable property"],"source":"https://www.indiacode.nic.in/","status":"official central source catalogue; transaction-specific review required"},
 {"id":"arbitration_act_1996","name":"Arbitration and Conciliation Act, 1996","topics":["arbitration agreement","dispute resolution"],"source":"https://www.indiacode.nic.in/","status":"official central source catalogue; clause-specific review required"},
 {"id":"copyright_act_1957","name":"Copyright Act, 1957","topics":["copyright","assignment","licensing"],"source":"https://www.indiacode.nic.in/","status":"official central source catalogue; assignment formalities require review"},
 {"id":"sale_goods_act_1930","name":"Sale of Goods Act, 1930","topics":["sale of goods","conditions and warranties","delivery","title and risk"],"source":"https://www.indiacode.nic.in/indiacode/bitstream/123456789/2390/1/193003.pdf","status":"official India Code text identified; transaction terms and amendments require review"},
 {"id":"partnership_act_1932","name":"Indian Partnership Act, 1932","topics":["partnership formation","partner duties","authority","dissolution"],"source":"https://www.indiacode.nic.in/handle/123456789/12849?view_type=browse","status":"official India Code text identified; state amendments and firm registration requirements require review"},
 {"id":"consumer_protection_act_2019","name":"Consumer Protection Act, 2019","topics":["consumer rights","unfair trade practices","product liability"],"source":"https://www.indiacode.nic.in/","status":"potentially relevant depending on parties and transaction; applicability is fact-specific"},
 {"id":"companies_act_2013","name":"Companies Act, 2013","topics":["company governance","shareholder arrangements","board powers"],"source":"https://www.mca.gov.in/","status":"relevant to company-side authority and corporate approvals; not a substitute for contract-law analysis"},
 {"id":"msmed_act_2006","name":"Micro, Small and Medium Enterprises Development Act, 2006","topics":["micro and small enterprise payments","delayed payment"],"source":"https://www.indiacode.nic.in/","status":"eligibility, supplier status and current statutory text require verification"},
 {"id":"labour_codes","name":"Four Labour Codes and applicable Central/State rules","topics":["employment","wages","social security","industrial relations","occupational safety"],"source":"https://labour.gov.in/offerings/schemes-and-services/details/labour-codes-gzNzQzMtQWa","status":"four codes effective 2025-11-21; applicable central/state rules and transitional provisions require fact-specific verification"},
 {"id":"dpdp_act_2023","name":"Digital Personal Data Protection Act, 2023 and Rules, 2025","topics":["personal data","privacy","data processing"],"source":"https://egazette.gov.in/WriteReadData/2025/267647.pdf","status":"phased commencement; verify provisions against G.S.R. 843(E) and Rules G.S.R. 846(E)"},
]

def list_jurisdictions() -> list[dict]:
    return [dict(x) for x in _JURISDICTIONS]

def get_jurisdiction(name: str | None) -> dict | None:
    if not name: return None
    return next((dict(x) for x in _JURISDICTIONS if x["name"].casefold()==name.strip().casefold()), None)
