from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..contracts.library import ClauseDef


@dataclass
class TypeDef:
    key: str
    title: str                 # shown in the UI
    doc_title: str             # heading of the exported document
    spec_cls: type
    required: list[str]
    questions: dict[str, str]
    labels: dict[str, str]     # field -> UI label (also the list of fields shown)
    party_a: str               # e.g. "landlord"
    party_b: str
    party_a_field: str         # spec field holding party A's name
    party_b_field: str
    clauses: list[ClauseDef]
    money_fields: tuple
    context: Callable          # spec -> dict used to render clause templates
    obligations: Callable      # spec -> list[Obligation]
    simulate: Callable         # (spec, scenario dict) -> dict
    scenarios: list[dict]      # UI definitions of what-if scenarios
    key_dates: Callable        # spec -> [{"date": iso, "title": str}]
    lint: Callable             # spec -> [{"clause_key","severity","message"}]
    sample: dict               # fictional demo details
    intake_hint: str = ""
    exec_notes: list = field(default_factory=list)

    def missing(self, spec) -> list[str]:
        return [f for f in self.required if getattr(spec, f) is None]

    def meta(self) -> dict:
        return {
            "key": self.key, "title": self.title, "party_a": self.party_a, "party_b": self.party_b,
            "labels": self.labels, "required": self.required, "scenarios": self.scenarios,
            "sample": self.sample,
        }
