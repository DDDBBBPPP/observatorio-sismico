\set ON_ERROR_STOP on

-- A new Supabase project supplies these roles; the disposable test DB does not.
create role anon nologin;
create role authenticated nologin;
create role service_role nologin;
grant usage on schema public to anon, authenticated, service_role;
alter default privileges in schema public grant all on tables to anon, authenticated;
alter default privileges in schema public grant execute on functions to anon, authenticated;

\ir ../supabase/migrations/202611250001_analytics_private.sql
\ir ../supabase/migrations/202611250002_analytics_rpc.sql

do $$
begin
    if not pg_catalog.has_function_privilege(
        'anon', 'public.analytics_events_page(bigint,bigint,double precision,bigint,text,integer)', 'EXECUTE'
    ) then raise exception 'anon cannot read bounded page'; end if;
    if pg_catalog.has_function_privilege(
        'anon', 'public.analytics_apply_event(text,bigint,bigint,double precision,double precision,text,text,text,text,text,boolean)', 'EXECUTE'
    ) then raise exception 'anon can write'; end if;
    if pg_catalog.has_function_privilege(
        'authenticated', 'public.analytics_apply_event(text,bigint,bigint,double precision,double precision,text,text,text,text,text,boolean)', 'EXECUTE'
    ) then raise exception 'authenticated can write'; end if;
    if pg_catalog.has_function_privilege(
        'authenticated', 'public.analytics_events_page(bigint,bigint,double precision,bigint,text,integer)', 'EXECUTE'
    ) then raise exception 'authenticated unexpectedly has public read'; end if;
    if not pg_catalog.has_function_privilege(
        'service_role', 'public.analytics_apply_event(text,bigint,bigint,double precision,double precision,text,text,text,text,text,boolean)', 'EXECUTE'
    ) then raise exception 'server cannot apply event'; end if;
    if pg_catalog.has_schema_privilege('anon', 'analytics_private', 'USAGE')
       or pg_catalog.has_schema_privilege('authenticated', 'analytics_private', 'USAGE')
       or pg_catalog.has_schema_privilege('service_role', 'analytics_private', 'USAGE')
    then raise exception 'private schema leaked'; end if;
    if pg_catalog.has_table_privilege('anon', 'analytics_private.event_snapshot', 'INSERT')
       or pg_catalog.has_table_privilege('anon', 'analytics_private.event_snapshot', 'UPDATE')
       or pg_catalog.has_table_privilege('anon', 'analytics_private.event_snapshot', 'DELETE')
    then raise exception 'anon has a direct write grant'; end if;
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'analytics_private' and table_name = 'event_snapshot'
          and column_name in ('original_jsonb', 'normalized_jsonb', 'replay_at', 'run_id')
    ) then raise exception 'sensitive columns copied'; end if;
    if pg_catalog.to_regclass('analytics_private.replay_event_current') is not null
       or pg_catalog.to_regclass('analytics_private.quarantine_record') is not null
       or pg_catalog.to_regclass('analytics_private.source_response') is not null
    then raise exception 'internal ingestion tables copied'; end if;
end;
$$;

set role anon;
do $$
declare denied boolean := false;
begin
    begin
        execute 'select count(*) from analytics_private.event_snapshot';
    exception when insufficient_privilege then denied := true;
    end;
    if not denied then raise exception 'anon read private events'; end if;

    denied := false;
    begin
        execute 'insert into analytics_private.coverage_day values (date ''2025-01-01'', now(), now())';
    exception when insufficient_privilege then denied := true;
    end;
    if not denied then raise exception 'anon wrote private coverage'; end if;

    denied := false;
    begin
        perform public.analytics_apply_event('x', 1, 1, 4, 1, null, null,
                                             'usgs', 'live', 'earthquake', false);
    exception when insufficient_privilege then denied := true;
    end;
    if not denied then raise exception 'anon invoked writer'; end if;
end;
$$;
reset role;

set role authenticated;
do $$
declare denied boolean := false;
begin
    begin
        execute 'select count(*) from analytics_private.sync_state';
    exception when insufficient_privilege then denied := true;
    end;
    if not denied then raise exception 'authenticated read sync control'; end if;
end;
$$;
reset role;

set role service_role;
do $$
begin
    if not public.analytics_apply_event('us-test-1', 100, 1735689600000, 4.6, 15,
                                         'ESP', 'España', 'usgs', 'historical', 'earthquake', false)
    then raise exception 'initial insert failed'; end if;
    if public.analytics_apply_event('us-test-1', 100, 1735689600000, 4.6, 15,
                                    'ESP', 'España', 'usgs', 'historical', 'earthquake', false)
    then raise exception 'duplicate version changed row'; end if;
    if not public.analytics_apply_event('us-test-1', 102, 1735689600000, 5.1, null,
                                         null, null, 'usgs', 'live', 'earthquake', false)
    then raise exception 'newer revision was not applied'; end if;
    if public.analytics_apply_event('us-test-1', 101, 1735689600000, 8.0, 20,
                                    'USA', 'Estados Unidos', 'usgs', 'live', 'earthquake', false)
    then raise exception 'older revision replaced newer'; end if;
end;
$$;

do $$
declare denied boolean := false;
begin
    begin
        perform public.analytics_apply_event('controlled-test', 103, 1735689600000, 9, 10,
                                             null, null, 'usgs', 'live', 'earthquake', true);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'synthetic accepted'; end if;

    denied := false;
    begin
        perform public.analytics_apply_event('controlled-test', 103, 1735689600000, 9, 10,
                                             null, null, 'usgs', 'live', 'earthquake', false);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'controlled ID accepted'; end if;

    denied := false;
    begin
        perform public.analytics_apply_event('us-replay', 103, 1735689600000, 9, 10,
                                             null, null, 'usgs', 'replay', 'earthquake', false);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'replay accepted'; end if;

    denied := false;
    begin
        perform public.analytics_apply_event('us-other-type', 103, 1735689600000, 9, 10,
                                             null, null, 'usgs', 'live', 'quarry blast', false);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'non-earthquake accepted'; end if;
end;
$$;
reset role;

-- Uncertified days are invisible, even when a source row exists.
set role anon;
do $$
begin
    if (select count(*) from public.analytics_events_page(1735689600000, 1735776000000)) <> 0
    then raise exception 'uncertified event was exposed'; end if;
end;
$$;
reset role;

insert into analytics_private.coverage_day values ('2025-01-01', now(), now());

set role anon;
do $$
declare row_count integer;
begin
    select count(*) into row_count
    from public.analytics_events_page(1735689600000, 1735776000000);
    if row_count <> 1 then raise exception 'certified event missing'; end if;
    if (select mag from public.analytics_events_page(1735689600000, 1735776000000)) <> 5.1
    then raise exception 'old revision leaked'; end if;
    if (select country_id from public.analytics_events_page(1735689600000, 1735776000000)) is not null
    then raise exception 'old country leaked'; end if;
    if (select count(*) from public.analytics_events_page(1735689600000, 1735776000000, 5.2)) <> 0
    then raise exception 'magnitude filter failed'; end if;
end;
$$;

do $$
declare denied boolean := false;
begin
    begin
        perform * from public.analytics_events_page(1735689600000, 1735776000000, 3.9);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'magnitude below 4 accepted'; end if;

    denied := false;
    begin
        perform * from public.analytics_events_page(1735689600000, 1735776000000, 4, null, null, 501);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'unbounded page accepted'; end if;

    denied := false;
    begin
        perform * from public.analytics_events_page(1735689600000, 1767484800000);
    exception when invalid_parameter_value then denied := true;
    end;
    if not denied then raise exception 'unbounded window accepted'; end if;
end;
$$;
reset role;

set role service_role;
do $$
begin
    if not public.analytics_apply_event('us-test-1', 104, 1735689600000, 3.8, 5,
                                         'ESP', 'España', 'usgs', 'live', 'earthquake', false)
    then raise exception 'threshold-crossing revision failed'; end if;
    if public.analytics_apply_event('us-test-1', 103, 1735689600000, 7.0, 5,
                                    'ESP', 'España', 'usgs', 'live', 'earthquake', false)
    then raise exception 'older revision revived removed event'; end if;
end;
$$;
reset role;

set role anon;
do $$
begin
    if (select count(*) from public.analytics_events_page(1735689600000, 1735776000000)) <> 0
    then raise exception 'below-threshold revision leaked'; end if;
end;
$$;
reset role;

do $$
begin
    if (select count(*) from analytics_private.event_snapshot) <> 1
       or (select updated_ms from analytics_private.event_snapshot where event_id='us-test-1') <> 104
    then raise exception 'identity or revision broken'; end if;
end;
$$;
