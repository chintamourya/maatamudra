"""Generate sample legal outputs for the submission from the real pipeline (no LLM, no network).
Run from the repo root:  python scripts/make_samples.py
Evidence annexes are empty here because case-law checks need your Indian Kanoon + Azure keys;
run them in the app and export the Word files again to include verified judgments."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import TypeAdapter  # noqa: E402

from app.contracts.compiler import compile_contract  # noqa: E402
from app.documents.docx_builder import build_docx  # noqa: E402
from app.extras import build_ics, fingerprint  # noqa: E402
from app.models import Spec  # noqa: E402
from app.types import REGISTRY  # noqa: E402

out = ROOT / "samples"
out.mkdir(exist_ok=True)
adapter = TypeAdapter(Spec)
for key, td in REGISTRY.items():
    c = compile_contract(adapter.validate_python(td.sample), contract_id=f"sample-{key}")
    (out / f"{key}.docx").write_bytes(build_docx(c))
    events = sorted(td.key_dates(c.spec), key=lambda e: e["date"])
    (out / f"{key}.ics").write_text(build_ics(c, events), encoding="utf-8")
    (out / f"{key}.terms.json").write_text(json.dumps({
        "fingerprint": fingerprint(c),
        "terms": c.spec.model_dump(mode="json", exclude={"provenance"}),
        "obligations": [o.model_dump() for o in c.obligations],
        "automatic_checks": td.lint(c.spec),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(key, len(c.clauses), "clauses,", len(c.obligations), "obligations")
