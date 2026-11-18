"""Config, LLM parameters, Tavily fallback and the Postgres repository."""
import os
from types import SimpleNamespace

import httpx
import pytest

from app import config
from app.db import PgRepo, Repo
from app.legal import kanoon as kmod
from app.legal import verifier as v
from app.legal.kanoon import KanoonClient, KanoonError
from tests.test_verifier import FakeLLM, PASSAGE


def test_env_aliases_and_blank_values(monkeypatch):
    monkeypatch.delenv("AZURE_OPENAI_CHAT_DEPLOYMENT", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "")
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "not-a-number")
    monkeypatch.setenv("DATABASE_URL", '"postgresql://u:p@h:5432/postgres"')
    s = config.Settings()
    assert s.chat_deployment == "gpt-5-mini" and s.reasoning_effort == "" and s.llm_timeout == 90
    assert s.database_url == "postgresql://u:p@h:5432/postgres"  # quotes stripped


def test_dotenv_does_not_override_real_environment(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text("VACHAN_TEST_X=from_file\nVACHAN_TEST_Y=from_file\n")
    monkeypatch.setenv("VACHAN_TEST_X", "from_env")
    from dotenv import load_dotenv
    load_dotenv(f, override=False)
    assert os.environ["VACHAN_TEST_X"] == "from_env" and os.environ["VACHAN_TEST_Y"] == "from_file"
    monkeypatch.delenv("VACHAN_TEST_Y")


async def test_llm_sends_reasoning_model_parameters(monkeypatch):
    from app.llm import LLM
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int

    seen = {}

    class FakeCompletions:
        async def parse(self, **kw):
            seen.update(kw)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, parsed=Out(x=1)))])

    llm = LLM()
    llm._client = SimpleNamespace(beta=SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())))
    import asyncio
    llm._sem = asyncio.Semaphore(2)
    monkeypatch.setattr("app.llm.settings", SimpleNamespace(chat_deployment="gpt-5-mini", max_completion_tokens=999, reasoning_effort="low"))
    assert (await llm.structured("s", "u", Out)).x == 1
    assert seen["model"] == "gpt-5-mini" and seen["max_completion_tokens"] == 999 and seen["reasoning_effort"] == "low"
    assert "temperature" not in seen and "max_tokens" not in seen


# ---- Tavily fallback ----------------------------------------------------
TAVILY = {"results": [
    {"url": "https://indiankanoon.org/doc/1234/", "title": "X vs Y on 4 March, 2003 - Indian Kanoon", "content": PASSAGE},
    {"url": "https://indiankanoon.org/doc/1234/", "title": "dup", "content": "dup"},
    {"url": "https://indiankanoon.org/search/?formInput=q", "title": "search page", "content": "x"},
    {"url": "https://example.com/blog", "title": "blog", "content": "x"}]}


@pytest.fixture
def tavily_mode(monkeypatch):
    monkeypatch.setattr(kmod, "settings", SimpleNamespace(kanoon_token="", tavily_key="tvly-test", tavily_depth="basic"))
    orig = httpx.AsyncClient

    def handler(request):
        assert request.url == kmod.TAVILY_URL and request.headers["authorization"] == "Bearer tvly-test"
        body = __import__("json").loads(request.content)
        assert body["include_domains"] == ["indiankanoon.org"]
        return httpx.Response(200, json=TAVILY)

    monkeypatch.setattr(kmod.httpx, "AsyncClient", lambda **kw: orig(transport=httpx.MockTransport(handler), **kw))


async def test_tavily_fallback_end_to_end(tavily_mode):
    k = KanoonClient(Repo())
    assert k.mode == "tavily"
    res = await k.search("section 74 penalty")
    assert [d["tid"] for d in res["docs"]] == ["1234"]  # only the judgment page, de-duplicated
    meta = await k.docmeta("1234")
    assert meta["title"] == "X vs Y on 4 March, 2003" and meta["publishdate"] == "4 March, 2003"
    ev = await v.verify_proposition("late_payment", "prop", ["section 74 penalty"], k, FakeLLM())
    assert ev[0].status == "verified" and ev[0].source == "tavily" and ev[0].passage == PASSAGE


async def test_no_source_configured_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(kmod, "settings", SimpleNamespace(kanoon_token="", tavily_key="", tavily_depth="basic"))
    k = KanoonClient(Repo())
    assert k.mode == "none"
    with pytest.raises(KanoonError, match="No case-law source"):
        await k.search("x")


async def test_warm_cache_works_without_any_key(monkeypatch):
    monkeypatch.setattr(kmod, "settings", SimpleNamespace(kanoon_token="", tavily_key="", tavily_depth="basic"))
    repo = Repo()
    k = KanoonClient(repo)
    await repo.cache_set("tavily-doc-9", {"title": "T", "date": None, "content": "c"})
    assert (await k.docmeta("9"))["title"] == "T"


# ---- Postgres ------------------------------------------------------------
PG = os.getenv("TEST_DATABASE_URL")


@pytest.mark.skipif(not PG, reason="set TEST_DATABASE_URL to run against a real Postgres")
async def test_pg_repo_roundtrip():
    repo = PgRepo(PG)
    await repo.init()
    try:
        await repo.save_contract("c1", {"id": "c1", "x": 1, "updated_at": "a"})
        await repo.save_contract("c1", {"id": "c1", "x": 2, "updated_at": "b"})  # upsert
        assert (await repo.get_contract("c1"))["x"] == 2 and await repo.get_contract("nope") is None
        assert any(c["id"] == "c1" for c in await repo.list_contracts())
        await repo.cache_set("k", {"a": [1, 2]})
        await repo.cache_set("k", {"a": [3]})
        assert await repo.cache_get("k") == {"a": [3]} and await repo.cache_get("zz") is None
        await repo.audit("c1", "one", {"n": 1})
        await repo.audit("c1", "two")
        log = await repo.audit_for("c1")
        assert [a["action"] for a in log] == ["one", "two"] and log[0]["payload"] == {"n": 1}
        async with repo.pool.connection() as conn:  # RLS is on for every Vachan table
            cur = await conn.execute("SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE 'vachan_%' AND relkind='r'")
            rows = await cur.fetchall()
        assert len(rows) == 3 and all(r[1] for r in rows)
    finally:
        async with repo.pool.connection() as conn:
            await conn.execute("DROP TABLE vachan_contracts, vachan_kanoon_cache, vachan_audit_log")
        await repo.close()


async def test_pg_init_failure_is_raised_so_app_can_fall_back():
    bad = PgRepo("postgresql://u:p@127.0.0.1:1/none")
    with pytest.raises(Exception):
        await bad.init()
