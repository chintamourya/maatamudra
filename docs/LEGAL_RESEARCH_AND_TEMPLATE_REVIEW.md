# VACHAN legal research and template review (hackathon scope)

Research snapshot: 18 November 2026. This is an AI-assisted research and engineering review, not an advocate's opinion or lawyer certification.

## What is verified in this release

1. The Department of Land Resources / NGDRS State-UT directory was checked and the 36 current States/UTs in the VACHAN catalogue were matched to the directory. The directory lists no registration portal for Nagaland or Sikkim; those entries intentionally have a null portal rather than an invented URL.
2. NeSL's public Digital Document Execution (DDE) directory was checked. 30 of the 36 jurisdiction entries appear in that directory. The JSON records whether each jurisdiction appears. `not_listed_on_NeSL_DDE_directory_check_state_channel` does not mean e-stamping is unavailable; it means only that the jurisdiction was not listed on that particular NeSL DDE page. Other state/SHCIL/GRAS channels may apply.
3. Central law sources are linked to India Code or the relevant Government of India department. The Indian Contract Act and IT Act have direct India Code records.
4. The Ministry of Labour and Employment lists the four Labour Codes and Central Rules. PIB states the four Codes were made effective from 21 November 2025. State rule commencement and transitional applicability must still be checked for the establishment and facts.
5. DPDP commencement is phased. G.S.R. 843(E), 13 November 2025, and DPDP Rules G.S.R. 846(E), 13 November 2025, must be read together; do not mark every substantive obligation as commenced on one date.

## State/UT coverage: precise boundary

This build verifies official registration-portal discovery links and NeSL DDE directory presence for all 36 jurisdictions. It does **not** claim that every State/UT's current stamp schedule, tenancy law, labour rules, registration exemption, or instrument-specific rate has been individually transcribed and validated. These depend on instrument type, value, term, parties, place of execution, amendments and Gazette notifications. The application therefore shows the official portal and a coverage warning rather than generating an unsupported duty figure.

The source registry is `backend/data/jurisdictions.json`. `verified_scope` and `not_verified` are deliberately explicit.

## Official research sources

- NGDRS, Department of Land Resources, State/UT registration links: https://ngdrs.gov.in/NGDRS_Website/state_ut_links.php
- NeSL, States & UTs for Digital e-Stamping (includes government order references): https://www.nesl.co.in/states-union-territories-for-digital-e-stamping/
- India Code, Indian Contract Act, 1872: https://www.indiacode.nic.in/handle/123456789/12845
- India Code, Information Technology Act, 2000: https://www.indiacode.nic.in/indiacode/handle/123456789/1999?locale=en
- Ministry of Labour & Employment, Labour Codes and Central Rules: https://labour.gov.in/offerings/schemes-and-services/details/labour-codes-gzNzQzMtQWa
- PIB, four Labour Codes effective 21 November 2025: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2194018
- Gazette, DPDP commencement notification G.S.R. 843(E): https://egazette.gov.in/WriteReadData/2025/267647.pdf
- Gazette, DPDP Rules 2025 G.S.R. 846(E): https://egazette.gov.in/WriteReadData/2025/267650.pdf

## Template review status

The existing contract schemas/templates were checked for common drafting structure, missing-term handling, deterministic consistency checks and legal issue-spotting prompts. They are **AI/research-reviewed for hackathon demonstration only; not lawyer-reviewed or certified**. Do not describe them as standard-form or guaranteed enforceable. Each agreement must be adapted to its transaction and facts.

### Template QA checklist

- Rental: parties, premises, term, rent, deposit, payment, maintenance, termination, possession, dispute resolution; stamp/registration and state tenancy requirements remain fact-specific.
- Freelance/service: scope, deliverables, acceptance, fees, expenses, IP assignment/licence, confidentiality, liability, termination, dispute resolution; check MSMED Act eligibility before applying delayed-payment provisions.
- Employment: role, place, wages, classification, hours, leave, probation, termination, statutory benefits and applicable Central/State labour rules; the four Codes' commencement does not itself resolve every establishment-specific rule.
- NDA: confidential information definition, exclusions, permitted disclosure, duration, return/deletion, remedies and data protection.
- Sale of goods: description, quantity, quality, delivery, inspection, title/risk, payment, warranties, rejection and remedies.
- Partnership: contributions, profit/loss, authority, books, duties, admission/retirement, dissolution and dispute resolution; check Partnership Act and any LLP/company structure.
- Private loan: principal, disbursement, repayment, interest, default, security/guarantees and applicable money-lending/sector laws.
- IP licence: identified IP, ownership, scope, territory, term, exclusivity, fees/royalties, sublicensing, infringement and termination.
- MOU: binding/non-binding intent per clause, scope, responsibilities, costs, duration, confidentiality, exclusivity and termination.

## Simulated modules

The demo identity and signing endpoints only illustrate an expected integration sequence. They do not authenticate users, verify identity, invoke a Certifying Authority, apply a signature, pay stamp duty or register a document.


## Public demo behavior

- OCR: PyMuPDF text extraction is attempted first. Image-only PDFs are rendered and passed to Tesseract. The demo limits PDFs to 30 pages and uploads to 10 MB. Docker installs English, Hindi and Telugu trained-data packs; other languages require their corresponding Tesseract data. The response reports `pymupdf_text` or `tesseract_ocr:<languages>`. OCR output must be visually checked against the scan.
- Translation: the LLM explanations and translation UI cover all 22 Scheduled Indian Languages plus English. The model is instructed to preserve numbers, names, section references and clause numbering. A deterministic number-integrity check flags numeric differences. This is not certified translation; the source-language contract controls unless the parties agree otherwise.
- Identity: demo endpoint only shows a mock role/session sequence. It does not authenticate or authorize anyone.
- Signing: demo endpoint only illustrates an authorized-provider hand-off and audit evidence. No signature is applied and no CCA service is invoked.
- Templates: schema and drafting checklist review is engineering/research QA, not review by a practising advocate.
