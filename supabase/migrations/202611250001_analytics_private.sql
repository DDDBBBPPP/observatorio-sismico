-- T001: isolated analytical copy. Apply to Supabase, never to local ingestion DB.
create schema if not exists analytics_private;
revoke all on schema analytics_private from public, anon, authenticated, service_role;

create table if not exists analytics_private.event_snapshot (
    event_id text primary key,
    updated_ms bigint not null check (updated_ms > 0),
    event_time_ms bigint not null check (event_time_ms > 0),
    mag double precision,
    depth_km double precision,
    country_id text,
    country_name text,
    eligible boolean not null,
    check (length(event_id) between 1 and 128),
    check (country_id is null or length(country_id) between 1 and 16),
    check (country_name is null or length(country_name) <= 200),
    check (mag is null or (mag > '-Infinity'::float8 and mag < 'Infinity'::float8)),
    check (depth_km is null or (depth_km > '-Infinity'::float8 and depth_km < 'Infinity'::float8)),
    check (eligible = coalesce(mag >= 4, false))
);

-- A row means that this complete UTC day has been reconciled with local PostgreSQL
-- and copied to Supabase. T002/T003 will populate it only after verification.
create table if not exists analytics_private.coverage_day (
    day_utc date primary key,
    reconciled_at timestamptz not null,
    synced_at timestamptz not null
);

-- T003 will advance this only after a successful, verified sync cycle.
create table if not exists analytics_private.sync_state (
    singleton boolean primary key default true check (singleton),
    last_synced_at timestamptz not null
);

create index if not exists event_snapshot_eligible_time_idx
    on analytics_private.event_snapshot (event_time_ms, event_id)
    where eligible;

alter table analytics_private.event_snapshot enable row level security;
alter table analytics_private.coverage_day enable row level security;
alter table analytics_private.sync_state enable row level security;

revoke all on all tables in schema analytics_private from public, anon, authenticated, service_role;
revoke all on all sequences in schema analytics_private from public, anon, authenticated, service_role;
alter default privileges in schema analytics_private revoke all on tables from public, anon, authenticated, service_role;
alter default privileges in schema analytics_private revoke all on sequences from public, anon, authenticated, service_role;
