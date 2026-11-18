"""Storage. PgRepo uses DATABASE_URL (any Postgres; your Supabase connection string works) and creates its own
tables on start-up. Repo is the in-memory fallback used for tests and zero-setup runs.
Tables are prefixed vachan_ so they never collide with another app in the same database, and row-level security is
enabled on them so Supabase's public REST API cannot read them (the direct Postgres role bypasses RLS)."""
from __future__ import annotations

from typing import Optional

from .config import settings

DDL = [
    "CREATE TABLE IF NOT EXISTS vachan_contracts (id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now())",
    "CREATE TABLE IF NOT EXISTS vachan_kanoon_cache (key text PRIMARY KEY, value jsonb NOT NULL, cached_at timestamptz NOT NULL DEFAULT now())",
    "CREATE TABLE IF NOT EXISTS vachan_audit_log (id bigserial PRIMARY KEY, contract_id text NOT NULL, action text NOT NULL, "
    "payload jsonb NOT NULL DEFAULT '{}', at timestamptz NOT NULL DEFAULT now())",
    "CREATE INDEX IF NOT EXISTS vachan_audit_contract ON vachan_audit_log (contract_id, at)",
    "ALTER TABLE vachan_contracts ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE vachan_kanoon_cache ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE vachan_audit_log ENABLE ROW LEVEL SECURITY",
]


class Repo:
    """In-memory repository."""
    fallback_reason: Optional[str] = None

    def __init__(self):
        self._contracts: dict[str, dict] = {}
        self._cache: dict[str, dict] = {}
        self._audit: list[dict] = []

    @property
    def backend(self) -> str:
        return "memory"

    async def init(self) -> None: ...
    async def close(self) -> None: ...

    async def save_contract(self, contract_id: str, data: dict) -> None:
        self._contracts[contract_id] = data

    async def get_contract(self, contract_id: str) -> Optional[dict]:
        return self._contracts.get(contract_id)

    async def list_contracts(self) -> list[dict]:
        return sorted(self._contracts.values(), key=lambda c: c.get("updated_at", ""), reverse=True)[:50]

    async def cache_get(self, key: str) -> Optional[dict]:
        return self._cache.get(key)

    async def cache_set(self, key: str, value: dict) -> None:
        self._cache[key] = value

    async def audit(self, contract_id: str, action: str, payload: dict | None = None) -> None:
        self._audit.append({"contract_id": contract_id, "action": action, "payload": payload or {}})

    async def audit_for(self, contract_id: str) -> list[dict]:
        return [a for a in self._audit if a["contract_id"] == contract_id]


class PgRepo(Repo):
    def __init__(self, url: str, ssl_ca: str = ""):
        super().__init__()
        self.url, self.ssl_ca, self.pool = url, ssl_ca, None

    @property
    def backend(self) -> str:
        return "postgres"

    async def init(self) -> None:
        from psycopg_pool import AsyncConnectionPool

        kwargs = {"autocommit": True, "prepare_threshold": None, "connect_timeout": 10}
        if self.ssl_ca:
            kwargs.update(sslrootcert=self.ssl_ca, sslmode="verify-full")
        self.pool = AsyncConnectionPool(self.url, min_size=1, max_size=5, kwargs=kwargs, open=False)
        await self.pool.open(wait=True, timeout=15)
        async with self.pool.connection() as conn:
            for stmt in DDL:
                await conn.execute(stmt)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    async def _one(self, sql: str, params=()):
        async with self.pool.connection() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchone()

    async def _all(self, sql: str, params=()):
        async with self.pool.connection() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchall()

    async def save_contract(self, contract_id: str, data: dict) -> None:
        from psycopg.types.json import Jsonb

        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO vachan_contracts (id, data) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, updated_at = now()", (contract_id, Jsonb(data)))

    async def get_contract(self, contract_id: str) -> Optional[dict]:
        row = await self._one("SELECT data FROM vachan_contracts WHERE id = %s", (contract_id,))
        return row[0] if row else None

    async def list_contracts(self) -> list[dict]:
        return [r[0] for r in await self._all("SELECT data FROM vachan_contracts ORDER BY updated_at DESC LIMIT 50")]

    async def cache_get(self, key: str) -> Optional[dict]:
        row = await self._one("SELECT value FROM vachan_kanoon_cache WHERE key = %s", (key,))
        return row[0] if row else None

    async def cache_set(self, key: str, value: dict) -> None:
        from psycopg.types.json import Jsonb

        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO vachan_kanoon_cache (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, cached_at = now()", (key, Jsonb(value)))

    async def audit(self, contract_id: str, action: str, payload: dict | None = None) -> None:
        from psycopg.types.json import Jsonb

        async with self.pool.connection() as conn:
            await conn.execute("INSERT INTO vachan_audit_log (contract_id, action, payload) VALUES (%s, %s, %s)",
                               (contract_id, action, Jsonb(payload or {})))

    async def audit_for(self, contract_id: str) -> list[dict]:
        rows = await self._all("SELECT contract_id, action, payload, at FROM vachan_audit_log WHERE contract_id = %s ORDER BY at, id", (contract_id,))
        return [{"contract_id": r[0], "action": r[1], "payload": r[2], "at": r[3].isoformat()} for r in rows]


def make_repo() -> Repo:
    return PgRepo(settings.database_url, settings.database_ssl_ca) if settings.database_url else Repo()
