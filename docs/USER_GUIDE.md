# VACHAN User Guide — End-to-End

## 1. Before you begin

VACHAN is an assistive contract drafting and review prototype for India. Use synthetic or redacted information in the public demo. Do not upload Aadhaar, PAN, bank details, medical information, confidential client documents or live contracts containing personal data. A role selector is not authentication. A generated draft is not legal advice or a guarantee of enforceability.

## 2. Choose a workspace perspective

The top-right selector offers Citizen, Advocate and Business. It changes the selected product perspective for the demonstration. It does not create separate user accounts, enforce permissions, or isolate documents.

- **Citizen:** understand and prepare a personal agreement; identify questions for a qualified lawyer.
- **Advocate:** use drafting, clause analysis, evidence and proposed redlines as an initial research/workflow aid. Independently verify law and sources.
- **Business:** prepare repeatable commercial drafts, review counterparty terms and track obligations.

## 3. Create an agreement from scratch

1. In the centre pane, select **Create new**.
2. Choose the closest agreement starter: rental, freelance/service, employment, NDA, sale/purchase, partnership, private loan, IP licence or MOU.
3. Select the relevant State/UT when prompted. If governing law or location is uncertain, do not guess.
4. Describe the transaction in plain language. Include parties and capacities, scope, deliverables, payment and due dates, duration, deposits, warranties, confidentiality, IP ownership, termination, liability and dispute handling where relevant.
5. Submit the intake. Read the follow-up questions and answer only with agreed, accurate facts. The application should distinguish user-provided terms from suggested defaults.
6. Complete required fields and generate the draft.
7. Review the generated clauses in the centre pane. Select clauses individually and inspect the corresponding right-hand tools.
8. Correct names, dates, amounts, schedules, defined terms, annexures and cross-references before exporting.

## 4. Review an existing agreement

1. Select **Review a document**.
2. Upload a supported PDF, DOCX or TXT file, or paste text if that input is available.
3. Run analysis. The app identifies the likely agreement type, clause segments, possible issues and missing or worth-considering terms.
4. If a PDF is scanned, the backend may use OCR after text extraction. OCR can misread numbers, names, dates, tables, seals, handwritten text and signatures. Compare the extracted text against the original page images.
5. Review every flag in context. A flag is an issue-spotting prompt, not a legal conclusion.
6. Provide any requested clarifications, then open the review workspace if available.

## 5. Right-hand workspace tabs

- **AI Studio:** scan the whole agreement for ambiguity, contradictions, missing details and practical gaps; inspect the clauses and deterministic checks the AI used. Ask it to rewrite one clause, compare the proposed wording and apply it only after review. Proposals that change numbers cannot be applied automatically. This scan does not use external legal sources or establish legal validity.
- **Evidence:** inspect clause-level evidence and source references. Open the original source and check whether it supports the proposition and remains current.
- **India law:** view central-law context and the jurisdiction coverage notes. Pan-India selection does not mean every State/UT rule is comprehensively verified. Check current stamp duty, registration, tenancy, employment and sector-specific requirements locally.
- **Negotiate & review:** run the review, inspect proposed redlines and accept or reject each change deliberately. Re-read the complete clause after every change.
- **Time machine:** select a scenario and adjust inputs to explore consequences implied by the agreement's own terms. This is illustrative, not a forecast or judicial interpretation.
- **Ask:** ask a question about the current agreement. Verify the response against the document and cited material.
- **Explain:** request a plain-language explanation in a supported language. Machine translation is not certified legal translation; check all legal terms and numbers.
- **Execution:** inspect obligations and execution checklist items. Mark an item complete only after it has actually happened.

## 6. Exports and next steps

- **Export .docx:** download an editable copy of the draft.
- **Calendar:** export available dated obligations or reminders.
- **Terms JSON:** inspect structured obligations for integration or further analysis.
- **Execution checklist:** use it as a coordination aid, not proof that a legal formality has been satisfied.

Before signing, independently confirm party identity and authority, the final agreed version, stamp duty, execution formalities, witnesses/notarisation if applicable, registration requirements and any transaction-specific law. Arrange stamping, signing and registration through appropriate official or authorised channels.

## 7. Demo integrations

- **Demo identity flow:** returns a simulated identity/role response. It does not create an account, verify identity, authenticate a user or enforce permissions.
- **Signing-provider hand-off:** simulated only. It does not call a live CCA-licensed provider, perform Aadhaar eKYC, validate a DSC, apply a signature or issue a certificate.
- **Translation:** LLM-generated, not certified.
- **OCR:** fallible; manually verify the extracted text.
- **Market viability & revenue:** opens the business research snapshot, market gaps, customer segments, editable assumptions, three user/revenue scenarios, competitor hypotheses and validation sprints. Forecasts are hypotheses until tested with customer interviews and paid pilots. Refresh reloads the curated research data; it is not an automatic web crawler.

## 8. Recommended full hackathon demonstration

Use a fictional rental scenario and synthetic names/addresses:

1. Select Citizen and Create new.
2. Choose Rental Agreement and the relevant demo State/UT.
3. Enter fictional landlord/tenant details, rent, deposit, term, maintenance, notice period and handover conditions.
4. Answer follow-up questions and generate the draft.
5. Select the deposit, maintenance and termination clauses. Review evidence and India law coverage notes.
6. Run Negotiate & review and inspect suggested redlines before accepting or rejecting.
7. Open Time machine and test a late-payment or early-termination scenario.
8. Use Ask and Explain to demonstrate question answering and plain-language explanation.
9. Open Execution to inspect obligations; demonstrate that signing is only a simulation.
10. Export the DOCX and explain that a lawyer and the parties must review it and complete real-world formalities.
11. Open Market viability & revenue to explain target customers, market gaps, pricing assumptions and research validation plan.

## 9. Known limitations

VACHAN is a hackathon prototype and is not a production-secure document vault, law firm, government portal, e-stamp service, registration service or certified signing platform. Do not rely on generated text without professional review. Check current official sources for law and local formalities.
