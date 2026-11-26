# Contributing to MAATAMUDRA

MAATAMUDRA is an open-source hackathon prototype. Contributions are welcome in contract templates, accessibility, Indian-language UX, test coverage, document extraction, legal-source metadata and explainable rule checks.

## Contribution principles

1. Do not add a legal rule without a source URL, provision reference, jurisdiction, effective-date context and verification status.
2. Never mark a rule verified merely because an LLM generated or summarized it.
3. Keep deterministic checks separate from model-generated explanations.
4. Do not allow an AI proposal to silently alter money, dates, durations, percentages or party identities.
5. Use synthetic or redacted contracts in tests. Never commit real client documents or personal data.
6. Add tests for new rules, including negative and edge cases.
7. Preserve the distinction between central legislation and State/UT amendments.

## Pull requests

Describe the user problem, implementation, legal/source basis where relevant, limitations and tests run. Legal template or rule changes should be reviewed by a qualified Indian legal professional before being presented as verified.
