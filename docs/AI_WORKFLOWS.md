# AI workflows and models used

**Model:** Azure OpenAI `gpt-5-mini` (low reasoning effort). Case law comes from the Indian Kanoon API, with web search restricted to indiankanoon.org as a fallback.
Model responses that drive product actions are validated against structured formats before use.

## Where AI is used, and where it is deliberately not

| Step | AI or code | Why |
|---|---|---|
| Understand the user's description | LLM extracts into a typed spec; provenance recorded (user / worked out / suggested); state/UT must be explicitly provided | Plain-language input; the model may not invent terms or assume a jurisdiction |
| Ask for missing terms | Deterministic required-field checks | Predictable, testable |
| Draft the agreement | Product templates fill in user-provided terms | The model cannot add or alter a term |
| Find case law | Indian Kanoon API; restricted web-search fallback | Real, inspectable sources |
| Judge whether a passage supports a legal point | LLM must give a supporting quote | Reading comprehension |
| Accept the judgment as evidence | Source metadata, retrieved passage, model assessment and quoted text are checked together | The model cannot make a citation "verified" by itself |
| Review a clause | LLM: advocate for party A, advocate for party B, neutral reviewer | Surfaces both sides' risk |
| Guard the review | Only supplied verified evidence can be cited; unsupported new numbers are flagged and cannot be silently applied | Prevents silent term changes |
| Structural risk checks | Deterministic agreement checks | Reliable and repeatable |
| Time machine | Deterministic calculations based on the agreement's own rental, freelance or employment terms | No invented thresholds; other agreement types do not yet have scenario simulators |
| Read an uploaded agreement | Text extraction plus model-assisted classification and term extraction | Works on contracts the user did not draft |
| Gaps and contradictions | Deterministic comparison against the agreement's terms and clause library | Reproducible; blocking contradictions stop drafting |
| Consequence map | Deterministic scenario simulation over time | Highlights possible dead zones and cliffs |
| Ask your contract | LLM answers using agreement clauses, terms, simulations and evidence; cited facts are checked against those sources | Natural questions with grounded answers |
| Explain in Indian languages | LLM explanation; numbers are checked against the source clause | Accessibility without silent number drift |
| Retry a failed case-law search | LLM suggests a bounded alternative query; results go through the same verification | Higher recall, same trust rule |
| Execution steps | Official source links and user-recorded evidence | Never claims legal validity |

## Pipelines

**Verification:** clause proposition → Indian Kanoon search → source metadata and passage retrieval → LLM assessment and quote check → evidence status.

**Review:** clause + verified evidence + statute summaries → advocate A, advocate B (parallel) → neutral reviewer → redline (word diff) → human accepts or rejects.

**Time machine:** spec → obligations compiler → scenario simulator → dated timeline + amounts + notes.

## Reliability evidence
Automated tests cover citation and quote verification, deterministic simulations, agreement generation and exports, redline safeguards, execution evidence, contradictory terms, grounded answers, translation number checks and uploaded-agreement analysis.
Limitations are stated in `README.md` and `docs/SUBMISSION.md`.
