"""Thin Azure OpenAI wrapper. All LLM output is parsed into Pydantic models;
nothing downstream consumes free text as data. Works with reasoning models such as gpt-5-mini
(uses max_completion_tokens and reasoning_effort, sends no temperature)."""
from __future__ import annotations

import asyncio
from typing import Type, TypeVar

from pydantic import BaseModel

from .config import settings

T = TypeVar("T", bound=BaseModel)


class LLMNotConfigured(RuntimeError):
    pass


class LLM:
    def __init__(self):
        self._client = None
        self._sem = None

    def _get(self):
        if self._client is None:
            if not (settings.azure_endpoint and settings.azure_key and settings.chat_deployment):
                raise LLMNotConfigured(
                    "Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT (see .env.example).")
            from openai import AsyncAzureOpenAI

            self._client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_endpoint, api_key=settings.azure_key,
                api_version=settings.azure_api_version, timeout=settings.llm_timeout, max_retries=settings.llm_retries)
            self._sem = asyncio.Semaphore(max(1, settings.llm_concurrency))
        return self._client

    def _extra(self) -> dict:
        extra = {"max_completion_tokens": settings.max_completion_tokens}
        if settings.reasoning_effort:
            extra["reasoning_effort"] = settings.reasoning_effort
        return extra

    async def structured(self, system: str, user: str, schema: Type[T]) -> T:
        client = self._get()
        async with self._sem:  # review fans out several calls; keep within rate limits
            resp = await client.beta.chat.completions.parse(
                model=settings.chat_deployment,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format=schema, **self._extra())
        msg = resp.choices[0].message
        if getattr(msg, "refusal", None):
            raise RuntimeError(f"Model refused: {msg.refusal}")
        if msg.parsed is None:
            raise RuntimeError("Model returned no parsable output (try raising LLM_MAX_COMPLETION_TOKENS)")
        return msg.parsed

    async def complete_text(self, system: str, user: str) -> str:
        """Return plain text for translation/explanation; callers must treat it as non-authoritative."""
        client = self._get()
        async with self._sem:
            resp = await client.chat.completions.create(
                model=settings.chat_deployment,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                **self._extra())
        content = resp.choices[0].message.content
        if not content:
            raise RuntimeError("Model returned empty text")
        return content.strip()

    async def chat(self, messages: list[dict], tools: list[dict]):
        """One tool-calling turn. Returns the assistant message (content and/or tool_calls)."""
        client = self._get()
        async with self._sem:
            resp = await client.chat.completions.create(
                model=settings.chat_deployment, messages=messages,
                tools=[{"type": "function", "function": t} for t in tools], tool_choice="auto", **self._extra())
        return resp.choices[0].message
