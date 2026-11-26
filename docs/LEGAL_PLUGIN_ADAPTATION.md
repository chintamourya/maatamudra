# MAATAMUDRA legal workflow improvements — reference adaptation

## Reference

Anthropic, `knowledge-work-plugins/legal`, pinned by the project brief to commit
`e91a134584eb798bac7fb0379358006a2b63b965`:
https://github.com/anthropics/knowledge-work-plugins/tree/e91a134584eb798bac7fb0379358006a2b63b965/legal

The upstream legal plugin describes playbook-based contract review, NDA pre-screening,
GREEN/YELLOW/RED risk routing, business-impact analysis, fallback redlines, escalation,
and a configurable local playbook. MAATAMUDRA adapts these workflow concepts to its own
FastAPI/Pydantic architecture and Indian agreement workflows. It does not install or run
Claude/Cowork commands, Anthropic connectors, or MCP servers, and this implementation
is not a port of Anthropic's runtime.

## What MAATAMUDRA now implements

- `backend/data/legal_playbook.json`: editable default negotiation positions, risk rubric,
escalation triggers and NDA checklist. Defaults are illustrative and expressly not legal
standards or counsel-approved positions.
- `backend/app/review/playbook.py`: playbook review orchestration and NDA triage.
- `GET /api/legal/playbook`: expose the current playbook to the UI.
- `POST /api/contracts/{id}/playbook-review`: contextual review using party-side,
deadline, focus areas and deal context; returns findings, negotiation priorities,
business impacts, fallback language and open questions.
- `POST /api/legal/nda-triage`: GREEN/YELLOW/RED pre-screen against a bounded checklist.
- The Negotiate & Review UI collects deal context, displays the playbook and presents
findings and redline suggestions. NDA agreements additionally expose the NDA pre-screen.

## Design decisions and guardrails

1. The playbook is treated as the customer's preference, never as law.
2. GREEN means only that no material issue was detected against this limited checklist;
it is not approval, enforceability or legal-validity certification.
3. YELLOW and RED require human review/escalation. No output auto-accepts a clause.
4. The LLM receives the supplied contract text and context, and must not invent facts,
statutory authorities, prices, dates or negotiated positions.
5. Indian statutory/case-law verification remains in MAATAMUDRA's existing India law and
Evidence modules. This review feature does not substitute foreign-law playbooks for
Indian law or imply that all State/UT rules are covered.
6. The default positions must be tailored to the user's organisation, contract category,
commercial risk tolerance and governing law before production use.

## Operational limitations

- This feature requires the configured Azure OpenAI-compatible structured-output service.
- The UI's default playbook is read-only in this build; administrators can edit the JSON
configuration in deployment source. A persisted tenant-specific playbook editor and
version history are future work.
- The NDA triage endpoint accepts text, not file uploads directly. Use the existing
upload/review extraction flow and pass extracted NDA text to the endpoint.
- The LLM's classification is bounded to GREEN/YELLOW/RED and checklist IDs, but all
substantive findings still require human review.

## Upstream workflow concepts

The reference legal plugin documents `/review-contract` (playbook-based review, context,
clause deviations, redlines and business impact) and `/triage-nda` (GREEN/YELLOW/RED
pre-screening). MAATAMUDRA maps those concepts to API endpoints and browser UI instead of
slash commands. See the upstream README and contract-review skill for the workflow model:
https://github.com/anthropics/knowledge-work-plugins/blob/main/legal/README.md
https://github.com/anthropics/knowledge-work-plugins/blob/main/legal/skills/contract-review/SKILL.md
