"""Curated statute store. Entries are loaded from data/statutes.json.
Anything with verified=false must be checked against India Code before the demo,
and the UI shows that status instead of hiding it."""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "statutes.json"


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def get_many(keys: list[str]) -> list[dict]:
    store = load()
    return [{"key": k, **store[k]} for k in keys if k in store]
