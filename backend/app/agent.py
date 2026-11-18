"""'Ask your contract': a tool-using agent that answers questions about THIS agreement.
It can read clauses, read terms, run the deterministic time machine and read verified evidence.
Its answer is then checked in code: cited clause keys must exist and every figure in the answer must appear
in a tool result or in the contract. Anything that fails is reported as a warning next to the answer."""
from __future__ import annotations

import json
import re

from .textutil import numbers

MAX_STEPS = 6

TOOLS = [
    {"name": "list_clauses", "description": "List the clause keys and titles in this agreement.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "get_clause", "description": "Get the exact current text of one clause.",
     "parameters": {"type": "object", "properties": {"clause_key": {"type": "string"}}, "required": ["clause_key"]}},
    {"name": "get_terms", "description": "Get the agreed terms (amounts, dates, periods) as structured data.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "simulate", "description": "Run the deterministic time machine for a what-if scenario and get dates, amounts and notes. "
     "Always use this for any question about timing, fees, notice, refunds or termination.",
     "parameters": {"type": "object", "properties": {"scenario": {"type": "object", "description": "must include 'type' plus that scenario's inputs"}},
                    "required": ["scenario"]}},
    {"name": "get_evidence", "description": "Get the verified court-judgment evidence already gathered for a clause (may be empty).",
     "parameters": {"type": "object", "properties": {"clause_key": {"type": "string"}}, "required": ["clause_key"]}},
]

SYSTEM = (
    "You answer questions about ONE specific {kind} using only the tools provided. Rules: "
    "(1) Use tools to read clauses. {simulation_rule} Never do date or money arithmetic yourself. "
    "(2) Cite every clause you rely on as [clause:key]. "
    "(3) If the agreement does not say something, say so plainly. "
    "(4) Do not state legal conclusions or predict what a court will do; for legal questions describe what the evidence "
    "tool returned, say whether it is empty, and suggest asking a lawyer. "
    "(5) Keep answers short and in plain words. {party_a} = party A, {party_b} = party B.\n"
    "Available what-if scenarios: {scenarios}"
)


def scenario_help(td) -> str:
    if not td.scenarios:
        return "None are configured for this agreement type; do not calculate dates or amounts."
    return "; ".join(
        f"{s['type']} (inputs: {', '.join(i['name'] for i in s['inputs']) or 'none'}"
        + (f"; fixed: {s['fixed']}" if s.get("fixed") else "") + ")" for s in td.scenarios)


def run_tool(contract, td, name: str, args: dict) -> str:
    try:
        if name == "list_clauses":
            out = [{"key": c.key, "title": c.title} for c in contract.clauses]
        elif name == "get_clause":
            c = next((x for x in contract.clauses if x.key == args.get("clause_key")), None)
            out = {"key": c.key, "title": c.title, "text": c.text} if c else {"error": "No such clause key."}
        elif name == "get_terms":
            out = contract.spec.model_dump(mode="json", exclude={"provenance"}, exclude_none=True)
        elif name == "simulate":
            out = td.simulate(contract.spec, args.get("scenario") or {})
        elif name == "get_evidence":
            ev = [e for e in contract.evidence if e.clause_key == args.get("clause_key") and e.status == "verified"]
            out = [{"title": e.title, "court": e.court, "date": e.date, "passage": e.passage[:500], "url": e.url} for e in ev] or {"note": "No verified evidence gathered for this clause yet."}
        else:
            out = {"error": f"Unknown tool {name}"}
    except (ValueError, KeyError, TypeError) as e:
        out = {"error": f"Invalid input: {e}"}
    return json.dumps(out, ensure_ascii=False, default=str)


def verify_answer(answer: str, valid_keys: set[str], corpus: str) -> tuple[list[str], list[str]]:
    cited = re.findall(r"\[clause:([A-Za-z0-9_]+)\]", answer)
    valid = sorted({k for k in cited if k in valid_keys})
    warnings = [f"Cited clause '{k}' does not exist in this agreement." for k in sorted(set(cited) - valid_keys)]
    body = re.sub(r"\[clause:[A-Za-z0-9_]+\]", "", answer)
    unverified = sorted(numbers(body, min_len=2) - numbers(corpus, min_len=2), key=float)
    if unverified:
        warnings.append("These figures in the answer were not found in the agreement or in a tool result, so check them: " + ", ".join(unverified))
    return valid, warnings


async def ask(llm, contract, td, question: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM.format(
            kind=td.title.lower(), party_a=td.party_a, party_b=td.party_b,
            scenarios=scenario_help(td),
            simulation_rule=(
                "Always use the deterministic simulator for timing, fees, notice, refunds or termination."
                if td.scenarios else
                "No deterministic what-if simulator is available for this type. Do not calculate dates or amounts; "
                "quote the written terms and say when the agreement does not specify a result."
            ),
        )},
        {"role": "user", "content": question},
    ]
    corpus = [json.dumps(contract.spec.model_dump(mode="json"), default=str)] + [c.text for c in contract.clauses]
    trace, final = [], None
    for _ in range(MAX_STEPS):
        msg = await llm.chat(messages, TOOLS)
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            final = msg.content or ""
            break
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]})
        for c in calls:
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(contract, td, c.function.name, args)
            corpus.append(result)
            trace.append({"tool": c.function.name, "args": args, "result": result[:600]})
            messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
    if final is None:
        return {"answer": "I could not finish answering within the step limit. Try a narrower question.", "citations": [], "trace": trace, "warnings": []}
    citations, warnings = verify_answer(final, {c.key for c in contract.clauses}, "\n".join(corpus))
    if not trace:
        warnings.append("The assistant answered without reading the agreement or running a scenario, so treat this answer with caution.")
    return {"answer": final, "citations": citations, "trace": trace, "warnings": warnings}
