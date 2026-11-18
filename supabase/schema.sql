-- OPTIONAL. Vachan creates these tables itself on start-up when DATABASE_URL is set.
-- Run this by hand only if your database role cannot create tables from the app.
-- Tables are prefixed vachan_ so they do not collide with another app (e.g. NyayaVedika) in the same database.
-- Row-level security is enabled with no policies: Supabase's public REST API cannot read them, while the direct
-- Postgres connection used by the backend can.
create table if not exists vachan_contracts (id text primary key, data jsonb not null, updated_at timestamptz not null default now());
create table if not exists vachan_kanoon_cache (key text primary key, value jsonb not null, cached_at timestamptz not null default now());
create table if not exists vachan_audit_log (id bigserial primary key, contract_id text not null, action text not null,
  payload jsonb not null default '{}', at timestamptz not null default now());
create index if not exists vachan_audit_contract on vachan_audit_log (contract_id, at);
alter table vachan_contracts enable row level security;
alter table vachan_kanoon_cache enable row level security;
alter table vachan_audit_log enable row level security;
