# Submission pack: AI for Lawyers Hackathon, PS-03 Contract Automation

Code freeze: **Dec 1, 2026, 09:18 IST**. Presentation: **5 minutes max**. Teams up to 5.
The page asks for: project description, deployed demo link, GitHub repo. Its overview also lists sample legal outputs,
an explanation of AI workflows and models, a demo video and a pitch deck.

## Checklist
| Item | Where | Status |
|---|---|---|
| Project description | below | draft, edit |
| Deployed demo link | `docs/DEPLOY.md` | you deploy |
| GitHub repository | `docs/DEPLOY.md` step 1 | you push |
| Sample legal outputs | `samples/` (3 Word agreements, calendar files, machine-readable terms) | generated; re-export with verified case law once keys are set |
| AI workflows and models | `docs/AI_WORKFLOWS.md` | done (gpt-5-mini) |
| Demo video (<= 5 min) | script below | you record |
| Pitch deck | outline below | you build (ask me to generate the .pptx) |

## Project description (about 150 words, edit freely)
Maatamudra turns a plain-language description into an Indian agreement (nine types: rental, freelance/service, employment, NDA, sale, partnership, loan, IP licence, MOU) built only from
the terms the user gives. Risky clauses are checked against real Indian Kanoon judgments; a citation is marked verified only
if the source resolves, the passage comes from the API, a model confirms it supports the point, and its quote is found in that
passage. Each clause is reviewed from both parties' sides by separate AI roles and a neutral reviewer, producing a redline the
user accepts or rejects. A deterministic "time machine" shows what the agreement's own terms say when rent or an invoice is late,
when someone terminates, or when an employee leaves during a bond. The output is a Word file with a legal-evidence annexure, a
calendar of key dates, machine-readable terms and a tamper-evident fingerprint. Maatamudra never shows a "legally valid" badge: stamp,
registration and signing steps tick only when a human records evidence.

## How it maps to the scoring
Weights below are from the live event page (re-check before submitting; the organizers may change them).
| Criterion (weight) | What to show |
|---|---|
| Technical Implementation (40%) | Deployed app + Word add-in on one backend; structured LLM output validated by Pydantic; deterministic consistency checks; citation verification against Indian Kanoon; number-integrity guard that blocks unsafe rewrites; 113 passing tests; benchmark results |
| Innovation (30%) | Review a received agreement inside Word and accept a balanced redline as a tracked change; two-sided adversarial review; consequence map / time machine; India-aware legal context with explicit coverage gaps |
| User Experience (20%) | Word task pane (no context switch), guided web workspace, English/Hindi/Telugu explanations, visible verification status on every finding |
| Impact (10%) | Citizens, MSMEs and advocates; lawyer-in-the-loop trust model; honest scope statement; avoid unsupported market-size claims |

## 5-minute demo script
1. **0:00-0:30, problem.** A freelancer gets a service agreement with a 24-month non-compete and open-ended liability. She cannot tell what is risky.
2. **0:30-1:15, check what she received.** *Check one I received*: paste or upload the agreement. Show the type found, the terms extracted, the flags and the missing basics. Click *Open full review*. (Backup: *Draft a new agreement* with *Use sample details*.)
3. **1:15-2:15, evidence.** Open the Evidence tab on *Restriction on competing work*. Show the statute card ("needs verification" is shown, not hidden), run *Find and check case law*, open a verified judgment and its retrieved passage. Say what verified means.
4. **2:15-3:15, review.** Review tab: automatic checks flag the non-compete. Run review, show both parties' risks, the redline, accept it. Show that a proposal that changes numbers cannot be accepted.
5. **3:15-4:15, time machine and ask.** Show the consequence map (the dead zone and the cliff), then type a question in *Ask* ("What if the client pays 45 days late?"): show the answer, the tool trace and that its figures were checked. Mention contradictory terms are blocked.
6. **4:15-5:00, reach and outputs.** *Explain* in Telugu with read-aloud (numbers checked against the English); download the Word file with the evidence annexure, calendar and machine-readable terms; mention the fingerprint. Close on the nine agreement starters and state clearly that the Pan-India state/UT catalogue is available, but state-specific legal rules remain unverified unless explicitly marked.

Record a backup video of the same flow in case live calls fail. Warm the case-law cache first.

## Pitch deck outline (8 slides)
1. Problem: people sign agreements they cannot assess; lawyers lose hours on first drafts.
2. Solution: draft, check, review, simulate, execute.
3. Demo screenshot: clause with its law and evidence.
4. How verification works (the four conditions).
5. Two-sided review and guardrails.
6. Time machine and machine-readable terms.
7. Architecture and stack: Azure OpenAI, Supabase, FastAPI, React; which steps are AI and which are code.
8. Honest limits, roadmap, ask.

## Honest limits (say them; judges reward trust)
Assistive tool, not legal advice. Six new agreement starters (NDA, sale/purchase, partnership, simple private loan, IP licence and MoU) are conservative first-pass templates, not comprehensive Indian-law coverage. Their scenario simulators are not implemented yet. Statute summaries and state rules are marked unverified until checked against official sources.
Stamp duty and registration rules are not hardcoded. Case-law relevance is judged by a model, then constrained by code; a lawyer
should confirm. No user login yet. When the Tavily fallback supplies case law, the passage is a web-search snippet and court or date may be missing; say which source you used and open the judgment to confirm. Nine agreement starters are available, but this is not exhaustive nationwide coverage; six new types do not yet have deterministic scenario simulators, and the Pan-India state/UT catalogue is available, but state-specific legal rules remain unverified unless explicitly marked. Telugu and Hindi explanations are model-written: have a native reader check them before you demo; read-aloud depends on the browser and installed voices. The upload review reads text only (no OCR) and its clause labels are model judgements a lawyer should confirm. Benchmark is small: report only numbers you actually measured.

## 13-day plan (today is Nov 18)
- Nov 18-20: set keys, run everything live, fix breakages; verify statutes and Telangana rules from official sources.
- Nov 21-24: warm the case-law cache for demo clauses; have a lawyer or law student review the clause library and sample outputs.
- Nov 25-27: deploy; add Supabase Auth if time allows; benchmark 10-15 seeded-issue contracts and record real results.
- Nov 28-29: record the demo video; build the deck.
- Nov 30: dry run the 5-minute demo; submit with a day to spare. Freeze is Dec 1, 09:18 IST.
