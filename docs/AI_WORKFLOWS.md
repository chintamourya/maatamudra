# AI workflows and models used

**Model:** Azure OpenAI `gpt-5-mini` deployment (reasoning effort low), set through `AZURE_OPENAI_DEPLOYMENT`. Case law: Indian Kanoon API, or Tavily web search limited to indiankanoon.org when no Indian Kanoon token is set.
All model output is parsed into Pydantic schemas with structured outputs. No free text is consumed as data.

## Where AI is used, and where it is deliberately not

| Step | AI or code | Why |
|---|---|---|
| Understand the user's description | LLM extracts into a typed spec; provenance recorded (user / worked out / suggested); state/UT must be explicitly provided | Plain-language input; the model may not invent terms or assume a jurisdiction |
| Ask for missing terms | Code (required-field list per contract type) | Predictable, testable |
| Draft the agreement | Code fills our own clause templates from the spec | The model cannot add or alter a term |
| Find case law | Indian Kanoon search, docmeta, docfragment (code) | Real sources |
| Judge whether a passage supports a legal point | LLM, conservative, must quote the passage | Reading comprehension |
| Accept the judgment as evidence | Code: metadata resolves + passage came from the API + judge says supports + quote found in passage | The model cannot make a citation "verified" by itself |
| Review a clause | LLM: advocate for party A, advocate for party B, neutral reviewer | Surfaces both sides' risk |
| Guard the review | Code: neutral reviewer may cite only verified evidence ids we supply; invented ids dropped; proposals adding new numbers flagged and cannot be auto-accepted | Prevents silent term changes |
| Structural risk checks | Code (`lint`) | Reliable, no hallucination |
| Time machine | Code, deterministic, evaluates the contract's own rental, freelance or employment terms | Testable; no invented thresholds. The six common first-pass agreement types do not yet have scenario simulators |
| Read an uploaded agreement | Code extracts and segments text; LLM guesses the type, labels segments with keys from OUR clause list (unknown keys dropped), extracts terms | Works on contracts the user did not draft |
| Gaps in an uploaded agreement | Code compares matched clauses to the clause library | Reproducible |
| Contradictions in terms | Code (`consistency.py`); errors block drafting | Cannot be talked around |
| Consequence map | Code sweeps the simulator over time | Finds dead zones and cliffs a person misses |
| Ask your contract | LLM with tools (list/get clause, terms, simulate, evidence); code then verifies cited clause keys and that every figure appears in a tool result or the contract; warnings shown | Natural questions, grounded answers |
| Explain in Telugu / Hindi | LLM; code checks every number against the clause and flags differences | Accessibility without silent number drift |
| Retry a failed case-law search | LLM proposes alternative queries (one bounded retry); results still go through the same verification | Higher recall, same trust rule |
| Execution steps | Code + official source links; steps tick only with human-entered evidence | Never claims legal validity |

## Pipelines

**Verification:** clause proposition → Indian Kanoon search (cached) → for each candidate: docmeta → docfragment → LLM judge → quote check → store evidence row with status `verified | unsupported | contradicts | unresolved`.

**Review:** clause + verified evidence + statute summaries → advocate A, advocate B (parallel) → neutral reviewer → redline (word diff) → human accepts or rejects.

**Time machine:** spec → obligations compiler → scenario simulator → dated timeline + amounts + notes.

## Reliability evidence
Automated tests (`cd backend && pytest`): verifier downgrades invented quotes and unresolvable sources; simulator arithmetic for rental, freelance and employment; all registered agreement types compile, lint and export; invented evidence ids are dropped; number-changing redlines return 409; execution flags need evidence; contradictory terms block drafting; the agent's invented figures and citations are flagged; explanations with changed numbers are flagged; uploaded-contract clause keys are constrained; reformulation is bounded.
Limitations are stated in `README.md` and `docs/SUBMISSION.md`.
