-- Narrow RPC surface. Both functions are owned by the migration role (postgres
-- in Supabase), have a fixed empty search_path and fully qualified relations.

create or replace function public.analytics_apply_event(
    p_event_id text,
    p_updated_ms bigint,
    p_event_time_ms bigint,
    p_mag double precision,
    p_depth_km double precision,
    p_country_id text,
    p_country_name text,
    p_source text,
    p_mode text,
    p_event_type text,
    p_is_synthetic boolean
) returns boolean
language plpgsql volatile security definer set search_path = ''
as $$
begin
    if p_source is distinct from 'usgs'
       or p_mode not in ('live', 'historical') or p_mode is null
       or p_event_type is distinct from 'earthquake'
       or p_is_synthetic is distinct from false
       or p_event_id is null or p_event_id like 'controlled-%'
    then
        raise exception 'event is not an eligible real USGS earthquake'
            using errcode = '22023';
    end if;

    insert into analytics_private.event_snapshot
        (event_id, updated_ms, event_time_ms, mag, depth_km,
         country_id, country_name, eligible)
    values
        (p_event_id, p_updated_ms, p_event_time_ms, p_mag, p_depth_km,
         p_country_id, p_country_name, coalesce(p_mag >= 4, false))
    on conflict (event_id) do update set
        updated_ms = excluded.updated_ms,
        event_time_ms = excluded.event_time_ms,
        mag = excluded.mag,
        depth_km = excluded.depth_km,
        country_id = excluded.country_id,
        country_name = excluded.country_name,
        eligible = excluded.eligible
    where analytics_private.event_snapshot.updated_ms < excluded.updated_ms;

    return found; -- false for duplicate (event_id, updated) or older revision
end;
$$;

create or replace function public.analytics_events_page(
    p_start_ms bigint,
    p_end_ms bigint,
    p_min_mag double precision default 4,
    p_after_time_ms bigint default null,
    p_after_event_id text default null,
    p_limit integer default 200
) returns table (
    event_id text,
    event_time_ms bigint,
    mag double precision,
    depth_km double precision,
    country_id text,
    country_name text
)
language plpgsql stable security definer set search_path = ''
as $$
begin
    if p_start_ms is null or p_end_ms is null or p_start_ms <= 0
       or p_end_ms <= p_start_ms
       or p_end_ms - p_start_ms > 367::bigint * 86400000
       or p_min_mag is null or p_min_mag < 4
       or p_min_mag >= 'Infinity'::float8
       or p_limit is null or p_limit not between 1 and 500
       or ((p_after_time_ms is null) <> (p_after_event_id is null))
       or (p_after_event_id is not null and length(p_after_event_id) > 128)
    then
        raise exception 'invalid analytical read window, magnitude or page'
            using errcode = '22023';
    end if;

    return query
    select e.event_id, e.event_time_ms, e.mag, e.depth_km,
           e.country_id, e.country_name
    from analytics_private.event_snapshot e
    join analytics_private.coverage_day c
      on c.day_utc = (pg_catalog.to_timestamp(e.event_time_ms / 1000.0)
                      at time zone 'UTC')::date
    where e.eligible
      and e.event_time_ms >= p_start_ms and e.event_time_ms < p_end_ms
      and e.mag >= p_min_mag
      and (p_after_time_ms is null
           or (e.event_time_ms, e.event_id) > (p_after_time_ms, p_after_event_id))
    order by e.event_time_ms, e.event_id
    limit p_limit;
end;
$$;

-- Supabase projects can grant permissive defaults to new public functions.
revoke all on function public.analytics_apply_event(
    text, bigint, bigint, double precision, double precision,
    text, text, text, text, text, boolean
) from public, anon, authenticated, service_role;
revoke all on function public.analytics_events_page(
    bigint, bigint, double precision, bigint, text, integer
) from public, anon, authenticated, service_role;

grant execute on function public.analytics_apply_event(
    text, bigint, bigint, double precision, double precision,
    text, text, text, text, text, boolean
) to service_role;
grant execute on function public.analytics_events_page(
    bigint, bigint, double precision, bigint, text, integer
) to anon;
