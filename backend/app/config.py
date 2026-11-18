"""Settings come from real environment variables, with a local .env file loaded automatically as a fallback.
Secrets are never hardcoded in source: .env is git-ignored and docker-ignored, and a deployed app gets the same
variable names from its host's secret store."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / ".env", _ROOT / "backend" / ".env"):
    if _p.is_file():
        load_dotenv(_p, override=False)  # a real environment variable always wins


def _env(*names: str, default: str = "") -> str:
    for n in names:
        v = os.getenv(n)
        if v not in (None, ""):
            return v.strip().strip('"').strip("'")
    return default


def _int(*names: str, default: int) -> int:
    try:
        return int(_env(*names, default=str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    azure_endpoint: str = field(default_factory=lambda: _env("AZURE_OPENAI_ENDPOINT"))
    azure_key: str = field(default_factory=lambda: _env("AZURE_OPENAI_API_KEY"))
    azure_api_version: str = field(default_factory=lambda: _env("AZURE_OPENAI_API_VERSION", default="2024-12-01-preview"))
    chat_deployment: str = field(default_factory=lambda: _env("AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_CHAT_DEPLOYMENT"))
    reasoning_effort: str = field(default_factory=lambda: _env("LLM_REASONING_EFFORT"))
    max_completion_tokens: int = field(default_factory=lambda: _int("LLM_MAX_COMPLETION_TOKENS", default=16384))
    llm_timeout: int = field(default_factory=lambda: _int("LLM_REQUEST_TIMEOUT_SECONDS", default=90))
    llm_retries: int = field(default_factory=lambda: _int("LLM_CLIENT_MAX_RETRIES", default=1))
    llm_concurrency: int = field(default_factory=lambda: _int("VACHAN_LLM_CONCURRENCY", default=4))
    database_url: str = field(default_factory=lambda: _env("VACHAN_DATABASE_URL", "DATABASE_URL"))
    database_ssl_ca: str = field(default_factory=lambda: _env("DATABASE_SSL_CA"))
    kanoon_token: str = field(default_factory=lambda: _env("INDIANKANOON_API_TOKEN"))
    tavily_key: str = field(default_factory=lambda: _env("TAVILY_API_KEY"))
    tavily_depth: str = field(default_factory=lambda: _env("TAVILY_SEARCH_DEPTH", default="advanced"))
    cors_origins: list = field(default_factory=lambda: _env("CORS_ORIGINS", default="http://localhost:5173").split(","))


settings = Settings()
