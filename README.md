# మాటముద్ర · MAATAMUDRA

**Agreements. Commitments. Clarity.**

Maatamudra is an open-source hackathon prototype for AI-assisted agreement creation, review, explanation and negotiation for people in India. It supports citizen, advocate and business-oriented workflows through one shared contract engine.

## What is implemented

- Conversational contract intake and deterministic document compilation.
- Nine agreement starters: rental, freelance/service, employment, NDA, sale/purchase, partnership, private loan, IP licence and MOU.
- Upload and review of text-based PDF, DOCX and TXT agreements.
- Clause-level evidence retrieval and case-law citation checks.
- AI Studio for proactive agreement review, source-traceable findings, and approval-based clause rewrite proposals.
- Two-sided adversarial review with a neutral proposed redline.
- Deterministic consistency checks, consequence simulation, obligation extraction and exports.
- Pan-India catalogue of all 28 States and 8 Union Territories.
- Indian legal context report with source-linked issue spotting and explicit state-rule coverage gaps.
- English, Hindi and Telugu voice input/explanation paths where supported by the configured model/browser.

## Important scope statement

Pan-India availability means users can select any Indian State or Union Territory and receive central-law issue spotting plus transparent jurisdiction coverage information. It does **not** mean this repository contains a fully verified legal rules database for every State/UT. Stamp duty, registration, tenancy, employment and sector-specific rules must be checked against current official sources. Maatamudra does not certify legal validity, calculate every state's stamp duty, provide legal advice, or automatically register or execute documents.

The legal intelligence endpoint deliberately labels its findings as review prompts. A source URL or statute catalogue entry is not proof that the rule has been checked against the latest amendment. Have an Indian advocate verify contract templates and legal rules before relying on them.

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cd ..
cp .env.example .env  # Windows: copy .env.example .env
# Fill only the provider credentials you intend to use.
uvicorn app.main:app --app-dir backend --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Vite app uses the same-origin API by default. For a separate backend, set `VITE_API_URL` to its base URL.

## Word add-in (new)

Review agreements inside Microsoft Word: clause concerns, comments, and balanced rewrites applied as tracked changes.
It is served by the same backend at `/addin`; get the manifest at `/addin/manifest.xml`. See [docs/WORD_ADDIN.md](docs/WORD_ADDIN.md).

## Useful API routes

- `GET /api/health`
- `GET /api/types`
- `GET /api/jurisdictions` — all Indian States and UTs; catalogue presence is not verification.
- `GET /api/legal/coverage` — central-law catalogue and jurisdiction coverage.
- `POST /api/intake`
- `POST /api/contracts`
- `GET /api/contracts/{id}/legal-intelligence`
- `POST /api/contracts/{id}/review`
- `POST /api/contracts/{id}/evidence/{clause_key}`
- `GET /api/contracts/{id}/lint`
- `GET /api/contracts/{id}/docx`
- `GET /addin/manifest.xml` and `POST /api/addin/rewrite` — Word add-in

Interactive API documentation is available at `/docs` when the backend is running.

## Environment and secrets

Copy `.env.example` to `.env`. Never commit `.env`, API keys, database URLs or production credentials. The uploaded development archive contained a populated `.env`; it has been excluded from this cleaned build. **Rotate any credentials that were present in the previously shared archive before using them again.**

## Tests

```bash
cd backend
pytest -q
```

## Open source

Publishing this general-purpose open-source drafting and legal-information prototype does not itself require a government licence or certification. This is distinct from regulated activities or third-party services such as eSign, government registration, professional legal practice and access to proprietary datasets. Maatamudra does not claim government approval.

Released under the MIT License. Third-party datasets, court content, APIs, fonts and model services remain subject to their own licences and terms. Do not redistribute content unless its terms permit it.

## Safety and privacy

Treat uploaded agreements as sensitive. This hackathon prototype is not a production security-reviewed system. Do not upload real Aadhaar, PAN, bank, medical, employment or confidential client information to a public demo. Use synthetic or redacted examples. Do not expose a public deployment with shared persistent storage until authentication and per-user authorization are implemented.


## Hackathon demo integrations

- `POST /api/translate`: LLM-based translation for user-facing explanations. It is not certified legal translation.
- `POST /api/demo/auth/session`: simulated role/identity flow only; no authentication or authorization is performed.
- `POST /api/demo/signing/session`: simulated signing-provider hand-off only; no identity verification or signature is applied.
- Scanned PDF review: PyMuPDF text extraction with Tesseract OCR fallback (up to 30 pages and 10 MB). Extraction method is returned in the analysis response. Docker installs English, Hindi and Telugu Tesseract packs; install other packs separately if needed.
- Language support: LLM explanations and on-demand translation cover all 22 Scheduled Indian Languages plus English. Browser voice input/output still depends on browser/device language support. Translation returns a number-integrity check and is not certified legal translation.

See [Legal Research and Template Review](docs/LEGAL_RESEARCH_AND_TEMPLATE_REVIEW.md) for the verified scope and explicit limitations of the 36-jurisdiction source registry. See the [End-to-End User Guide](docs/USER_GUIDE.md) for a complete walkthrough of every workspace and feature. The in-app **How to use Maatamudra** button opens the same guided manual.

## Startup viability and market research

The workspace includes a **Market viability & revenue** button. It opens a dated India contract-tech research snapshot with market signals, customer segments, market gaps, competitor positioning, an editable three-scenario user/revenue model, indicative pricing, unit-economics hypotheses, and a four-stage research-validation backlog.

The snapshot is served from `backend/data/market_research.json` via `GET /api/market-research`. Update the dated evidence and assumptions there as new primary research is collected. The dashboard is not a live web crawler; refresh reloads the curated snapshot from the backend. Public MSME registrations are not treated as unique active buyers, and every Maatamudra-specific conversion, reachable-market, price, CAC, churn and margin input is explicitly a hypothesis until validated with customer interviews and paid pilots.

## Playbook-based legal review (new)

Maatamudra includes contextual playbook review and NDA GREEN/YELLOW/RED pre-screening inspired by the workflow patterns in Anthropic's open-source legal knowledge-work plugin. See `docs/LEGAL_PLUGIN_ADAPTATION.md` and `docs/USER_GUIDE.md`. The default playbook is illustrative, not legal advice or a lawyer-approved policy; customise `backend/data/legal_playbook.json` before production use.
