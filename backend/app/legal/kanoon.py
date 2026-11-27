"""Case-law source. Preferred: the Indian Kanoon API (search, docmeta, docfragment).
Fallback when no Indian Kanoon token is set: Tavily web search restricted to indiankanoon.org, using the returned
page snippet as the passage. Either way the passage then goes through the same verification (a model must quote it).
Every response is cached in the repo so demos do not depend on live latency and spend stays low.
Runs on the backend only; tokens never reach the browser."""
from __future__ import annotations

import hashlib
import json
import re
from html import unescape

import httpx

from ..config import settings

BASE = "https://api.indiankanoon.org"
TAVILY_URL = "https://api.tavily.com/search"
_DOC = re.compile(r"indiankanoon\.org/doc/(\d+)")
_DATE = re.compile(r"\bon (\d{1,2} [A-Za-z]+, \d{4})\s*$")


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


class KanoonError(RuntimeError):
    pass


class KanoonClient:
    def __init__(self, repo):
        self.repo = repo

    @property
    def mode(self) -> str:
        return "indiankanoon" if settings.kanoon_token else ("tavily" if settings.tavily_key else "none")

    # ---- Indian Kanoon API ------------------------------------------------
    async def _post(self, path: str, params: dict) -> dict:
        key = hashlib.sha256((path + json.dumps(params, sort_keys=True)).encode()).hexdigest()
        cached = await self.repo.cache_get(key)
        if cached is not None:
            return cached
        if not settings.kanoon_token:
            raise KanoonError("No cached response and INDIANKANOON_API_TOKEN is not set.")
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(f"{BASE}{path}", params=params,
                                      headers={"Authorization": f"Token {settings.kanoon_token}", "Accept": "application/json"})
        except httpx.HTTPError as e:
            raise KanoonError("Indian Kanoon request failed. Check source availability and credentials.") from e
        if r.status_code != 200:
            raise KanoonError(f"Indian Kanoon {path} returned {r.status_code}")
        try:
            data = r.json()
        except ValueError as e:
            raise KanoonError("Indian Kanoon returned an invalid response.") from e
        await self.repo.cache_set(key, data)
        return data

    # ---- Tavily fallback ----------------------------------------------------
    async def _tavily_search(self, query: str) -> dict:
        key = "tavily-search-" + hashlib.sha256(query.encode()).hexdigest()
        cached = await self.repo.cache_get(key)
        if cached is not None:
            return cached
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(TAVILY_URL, headers={"Authorization": f"Bearer {settings.tavily_key}"}, json={
                    "query": query, "search_depth": settings.tavily_depth, "max_results": 8,
                    "include_domains": ["indiankanoon.org"]})
        except httpx.HTTPError as e:
            raise KanoonError("Tavily request failed. Check source availability and credentials.") from e
        if r.status_code != 200:
            raise KanoonError(f"Tavily search returned {r.status_code}")
        try:
            results = r.json().get("results", [])
        except (ValueError, AttributeError) as e:
            raise KanoonError("Tavily returned an invalid response.") from e
        docs, seen = [], set()
        for item in results:
            m = _DOC.search(item.get("url", ""))
            if not m or m.group(1) in seen:
                continue  # keep only judgment pages
            tid = m.group(1)
            seen.add(tid)
            title = strip_html(item.get("title", "")).replace(" - Indian Kanoon", "").strip()
            d = _DATE.search(title)
            await self.repo.cache_set(f"tavily-doc-{tid}", {"title": title, "date": d.group(1) if d else None,
                                                             "content": item.get("content", "")})
            docs.append({"tid": tid, "title": title, "docsource": None})
        out = {"docs": docs}
        await self.repo.cache_set(key, out)
        return out

    async def _tavily_doc(self, docid: str) -> dict:
        d = await self.repo.cache_get(f"tavily-doc-{docid}")
        if d is None:
            raise KanoonError("Document was not found in the search results.")
        return d

    # ---- public interface ---------------------------------------------------
    async def search(self, query: str, doctypes: str | None = None, page: int = 0) -> dict:
        if settings.kanoon_token:
            q = f"{query} doctypes: {doctypes}" if doctypes else query
            return await self._post("/search/", {"formInput": q, "pagenum": page})
        if settings.tavily_key:
            return await self._tavily_search(query)
        raise KanoonError("No case-law source configured: set INDIANKANOON_API_TOKEN (preferred) or TAVILY_API_KEY.")

    async def docmeta(self, docid: str) -> dict:
        if settings.kanoon_token:
            return await self._post(f"/docmeta/{docid}/", {})
        d = await self._tavily_doc(docid)
        return {"title": d["title"], "publishdate": d.get("date")}

    async def docfragment(self, docid: str, query: str) -> dict:
        if settings.kanoon_token:
            return await self._post(f"/docfragment/{docid}/", {"formInput": query})
        return {"headline": (await self._tavily_doc(docid)).get("content", "")}
