import pytest

from app.legal import verifier as v

PASSAGE = ("The court held that where a sum is stipulated as payable on breach, the party complaining "
           "of breach is entitled only to reasonable compensation not exceeding the amount named in the contract.")


class FakeKanoon:
    def __init__(self, meta_ok=True, passage=PASSAGE):
        self.meta_ok, self.passage = meta_ok, passage

    async def search(self, q, doctypes=None, page=0):
        return {"docs": [{"tid": 111, "title": "X v Y"}]}

    async def docmeta(self, d):
        if not self.meta_ok:
            raise v.KanoonError("nope")
        return {"title": "X v Y", "docsource": "Supreme Court of India", "publishdate": "2003-01-01"}

    async def docfragment(self, d, q):
        return {"headline": f"<b>{self.passage}</b>"}


class FakeLLM:
    def __init__(self, relation="supports", quote="entitled only to reasonable compensation", alt_queries=()):
        self.alt_queries = list(alt_queries)
        self.out = v.Judgement(relation=relation, supporting_quote=quote, reason="r")

    async def structured(self, system, user, schema):
        if schema is v.Queries:
            return v.Queries(queries=self.alt_queries)
        return self.out


async def run(kan, llm):
    return await v.verify_proposition("late_payment", "prop", ["q"], kan, llm)


async def test_verified_when_everything_checks_out():
    ev = await run(FakeKanoon(), FakeLLM())
    assert ev[0].status == "verified" and ev[0].court == "Supreme Court of India"
    assert ev[0].passage == PASSAGE  # passage is the API text, not model text


async def test_invented_quote_is_downgraded():
    ev = await run(FakeKanoon(), FakeLLM(quote="the tenant may be evicted without any notice whatsoever"))
    assert ev[0].status == "unsupported"


async def test_unresolvable_metadata_never_verified():
    assert (await run(FakeKanoon(meta_ok=False), FakeLLM()))[0].status == "unresolved"


async def test_short_passage_unsupported():
    assert (await run(FakeKanoon(passage="too short"), FakeLLM()))[0].status == "unsupported"


async def test_contradiction_is_surfaced():
    assert (await run(FakeKanoon(), FakeLLM(relation="contradicts")))[0].status == "contradicts"


async def test_unrelated_not_verified():
    assert (await run(FakeKanoon(), FakeLLM(relation="unrelated", quote="")))[0].status == "unsupported"


def test_quote_verification_requires_exact_normalized_substring():
    assert v.quote_in_passage("entitled only to reasonable compensation", PASSAGE)
    assert v.quote_in_passage("  ENTITLED   only to reasonable compensation  ", PASSAGE)
    assert not v.quote_in_passage("entitled only to reasonable damages", PASSAGE)
    assert not v.quote_in_passage("reasonable compensation", PASSAGE)
