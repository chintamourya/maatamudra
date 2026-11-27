from fastapi.testclient import TestClient

from app import deps
from app.addin import AddinRewriteLLM
from app.db import Repo
from app.main import app
from tests.test_verifier import FakeKanoon

CLAUSE = "The Tenant shall pay monthly rent of 22000 on or before the 5th day of each month, failing which a late fee applies."


class RewriteLLM:
    def __init__(self, text):
        self.text = text

    async def structured(self, system, user, schema):
        assert schema is AddinRewriteLLM
        assert "flagged_concern" in user and CLAUSE in user
        return AddinRewriteLLM(proposed_text=self.text, rationale="Clarifies the payment timing.", tradeoffs=["Needs agreement."])


def _client(text):
    deps.services = deps.Services(llm=RewriteLLM(text), repo=Repo(), kanoon=FakeKanoon())
    return TestClient(app)


def test_manifest_uses_server_origin_and_is_valid_xml():
    import xml.dom.minidom
    c = TestClient(app)
    r = c.get("/addin/manifest.xml", headers={"x-forwarded-proto": "https", "x-forwarded-host": "demo.example.com"})
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    assert "https://demo.example.com/addin/taskpane.html" in r.text
    assert "{{BASE}}" not in r.text
    xml.dom.minidom.parseString(r.text)


def test_manifest_rejects_odd_host_header():
    r = TestClient(app).get("/addin/manifest.xml", headers={"x-forwarded-host": 'evil.com"><x'})
    assert 'evil.com"' not in r.text and "{{BASE}}" not in r.text


def test_taskpane_assets_are_served():
    c = TestClient(app)
    html = c.get("/addin/taskpane.html").text
    assert "Maatamudra" in html
    assert html.index('id="contractSetup"') < html.index('id="concerns"')
    assert 'id="btnShowDraft"' in html
    js_response = c.get("/addin/taskpane.js")
    assert js_response.status_code == 200
    js = js_response.text
    assert js.index('setStatus(n + " comment"') < js.index("function updateContractSetup()")
    assert c.get("/addin/icon-80.png").status_code == 200


def test_rewrite_ok_when_no_new_numbers():
    new = CLAUSE.replace("failing which a late fee applies", "failing which the late fee agreed in writing applies")
    r = _client(new).post("/api/addin/rewrite", json={"clause_text": CLAUSE, "concern": "Late fee is unspecified."})
    body = r.json()
    assert r.status_code == 200 and body["apply_allowed"] is True and body["number_integrity"] is True


def test_rewrite_blocked_when_model_invents_a_figure():
    r = _client(CLAUSE + " A late fee of 999 per day applies.").post(
        "/api/addin/rewrite", json={"clause_text": CLAUSE, "concern": "Late fee is unspecified."})
    body = r.json()
    assert body["apply_allowed"] is False and "999" in body["unmatched_numbers"]


def test_rewrite_validates_input():
    r = _client("x").post("/api/addin/rewrite", json={"clause_text": "too short"})
    assert r.status_code == 422
