# మాటముద్ర · MAATAMUDRA

**Agreements. Commitments. Clarity.**

Maatamudra is an open-source hackathon prototype for AI-assisted agreement creation, review, explanation and negotiation for people in India. It supports citizen, advocate and business-oriented workflows through one shared contract engine.

## What is implemented

- Conversational contract intake and deterministic document compilation.
- Nine agreement starters: rental, freelance/service, employment, NDA, sale/purchase, partnership, private loan, IP licence and MOU.
- Upload and review of PDF, DOCX and TXT agreements, with OCR fallback for scanned PDFs.
- Clause-level evidence retrieval and case-law citation checks.
- One-click synthetic freelancer agreement demo for quickly exploring the PS-03 drafting and review flow.
- AI Studio for proactive agreement review, source-traceable findings, and approval-based clause rewrite proposals.
- Two-sided adversarial review with a neutral proposed redline.
- Deterministic consistency checks, consequence simulation, obligation extraction and exports.
- Pan-India catalogue of all 28 States and 8 Union Territories.
- Indian legal context report with source-linked issue spotting and explicit state-rule coverage gaps.
- English, Hindi and Telugu voice input/explanation paths where supported by the configured model/browser.

## Important scope statement

Pan-India availability means users can select any Indian State or Union Territory and receive central-law issue spotting plus transparent jurisdiction coverage information. It does **not** mean this repository contains a fully verified legal rules database for every State/UT. Stamp duty, registration, tenancy, employment and sector-specific rules must be checked against current official sources. Maatamudra does not certify legal validity, calculate every state's stamp duty, provide legal advice, or automatically register or execute documents.

The legal intelligence endpoint deliberately labels its findings as review prompts. A source URL or statute catalogue entry is not proof that the rule has been checked against the latest amendment. Have an Indian advocate verify contract templates and legal rules before relying on them.

## Word add-in

Review agreements inside Microsoft Word: clause concerns, comments, and balanced rewrites applied as tracked changes.
It is served by the same backend at `/addin`; get the manifest at `/addin/manifest.xml`. See [docs/WORD_ADDIN.md](docs/WORD_ADDIN.md).

## Open source

Publishing this general-purpose open-source drafting and legal-information prototype does not itself require a government licence or certification. This is distinct from regulated activities or third-party services such as eSign, government registration, professional legal practice and access to proprietary datasets. Maatamudra does not claim government approval.

Released under the MIT License. Third-party datasets, court content, APIs, fonts and model services remain subject to their own licences and terms. Do not redistribute content unless its terms permit it.

## Safety and privacy

Treat uploaded agreements as sensitive. This hackathon prototype is not a production security-reviewed system. Do not upload real Aadhaar, PAN, bank, medical, employment or confidential client information to a public demo. Use synthetic or redacted examples. Do not expose a public deployment with shared persistent storage until authentication and per-user authorization are implemented.


## Demo features and limitations

- Identity and signing-provider flows are simulations; they do not authenticate users or apply a signature.
- Scanned PDF review uses OCR, which may misread text. Check extracted details against the original.
- AI explanations and translations are informational, not certified legal translations. Check names, amounts, dates and legal references against the original.

Read the [End-to-End User Guide](docs/USER_GUIDE.md) for a walkthrough. The in-app **How to use Maatamudra** button opens the same guide. See [Legal Research and Template Review](docs/LEGAL_RESEARCH_AND_TEMPLATE_REVIEW.md) for the scope and limitations of the legal-source registry.

## Startup viability and market research

The workspace includes a **Market viability & revenue** dashboard with a curated India contract-tech research snapshot, customer segments, competitor context, editable scenarios and a research-validation backlog. It is not a live web crawler, and Maatamudra-specific business inputs are hypotheses rather than measured traction.

## Playbook-based legal review

Maatamudra includes contextual playbook review and NDA GREEN/YELLOW/RED pre-screening. The default playbook is illustrative, not legal advice or a lawyer-approved policy. See the [User Guide](docs/USER_GUIDE.md) for how to use these features.

## Hackathon materials

The [submission pack](docs/SUBMISSION.md) summarizes the PS-03 demo and pitch. The [AI workflow overview](docs/AI_WORKFLOWS.md) explains how AI and deterministic checks are used.
