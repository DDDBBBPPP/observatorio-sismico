import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg


MIGRATION = Path(__file__).parent / "migrations" / "001_ingestion_schema.sql"


def connect() -> psycopg.Connection:
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "observatorio"),
        user=os.environ.get("POSTGRES_USER", "observatorio"),
        password=os.environ.get("POSTGRES_PASSWORD", "local-development-only"),
    )


def ensure_schema(connection: psycopg.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(MIGRATION.read_text(encoding="utf-8"))
    connection.commit()


def prune_live_response_payloads(connection: psycopg.Connection) -> int:
    """Keep query metadata and event originals; expire full live feed copies."""
    days = int(os.environ.get("USGS_LIVE_ORIGINAL_RETENTION_DAYS", "30"))
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE source_response AS response
            SET payload_jsonb = '{}'::jsonb
            FROM ingestion_run AS run
            WHERE response.run_id = run.run_id
              AND run.load_type = 'live_feed'
              AND response.received_at < now() - make_interval(days => %s)
              AND response.payload_jsonb <> '{}'::jsonb
            """,
            (days,),
        )
        changed = cursor.rowcount
    connection.commit()
    return changed


def start_ingestion_run(
    connection: psycopg.Connection,
    run_id: str,
    load_type: str,
    mode: str,
    records_seen: int = 0,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_run
                (run_id, source, load_type, mode, started_at, status, records_seen)
            VALUES (%s, 'usgs', %s, %s, %s, 'running', %s)
            ON CONFLICT (run_id) DO UPDATE SET
                status = 'running',
                finished_at = NULL,
                records_seen = EXCLUDED.records_seen,
                error = NULL
            """,
            (run_id, load_type, mode, datetime.now(timezone.utc), records_seen),
        )
    connection.commit()


def finish_ingestion_run(
    connection: psycopg.Connection,
    run_id: str,
    records_seen: int,
    records_accepted: int,
    records_rejected: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ingestion_run
            SET status = 'completed',
                finished_at = %s,
                records_seen = %s,
                records_accepted = %s,
                records_rejected = %s
            WHERE run_id = %s
            """,
            (
                datetime.now(timezone.utc),
                records_seen,
                records_accepted,
                records_rejected,
                run_id,
            ),
        )
    connection.commit()


def persist_live_event(
    connection: psycopg.Connection, payload: dict, country: dict, commit: bool = True
) -> str:
    now = datetime.now(timezone.utc)
    event = payload["event"]
    properties = event.get("properties") or {}
    coordinates = event.get("geometry", {}).get("coordinates") or []
    run_id = payload["run_id"]
    response_id = payload["provenance"]["source_response_id"]
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_run
                (run_id, source, load_type, mode, started_at, status, records_seen)
            VALUES (%s, 'usgs', %s, %s, %s, 'running', %s)
            ON CONFLICT (run_id) DO NOTHING
            """,
            (
                run_id,
                payload["provenance"].get("load_type", "live_feed"),
                payload.get("mode", "live"),
                now,
                payload["provenance"]["record_count"],
            ),
        )
        cursor.execute(
            """
            INSERT INTO source_response
                (response_id, run_id, url, requested_at, received_at,
                 http_status, duration_ms, record_count, payload_jsonb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (response_id) DO NOTHING
            """,
            (
                response_id,
                run_id,
                payload["provenance"]["url"],
                payload["provenance"]["requested_at"],
                payload["provenance"]["received_at"],
                payload["provenance"]["http_status"],
                payload["provenance"]["duration_ms"],
                payload["provenance"]["record_count"],
                json.dumps(payload["provenance"]["original"]),
            ),
        )
        cursor.execute(
            """
            INSERT INTO event_version
                (event_id, updated, event_time, mag, place, longitude, latitude,
                 depth_km, source_response_id, run_id, mode, ingested_at,
                 original_jsonb, normalized_jsonb, source, load_type, is_synthetic,
                 country_id, country_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id, updated) DO NOTHING
            RETURNING event_version_id
            """,
            (
                payload["event_id"],
                payload["updated"],
                properties.get("time"),
                properties.get("mag"),
                properties.get("place"),
                coordinates[0],
                coordinates[1],
                coordinates[2] if len(coordinates) > 2 else None,
                response_id,
                run_id,
                payload.get("mode", "live"),
                now,
                json.dumps(event),
                json.dumps(
                    {
                        "event_id": payload["event_id"],
                        "updated": payload["updated"],
                        "source": "usgs",
                    }
                ),
                payload.get("source", "usgs"),
                payload["provenance"].get("load_type", "live_feed"),
                payload.get("source") != "usgs" or payload["event_id"].startswith("controlled-"),
                country["country_id"],
                country["country_name"],
            ),
        )
        inserted = cursor.fetchone()
        if inserted:
            cursor.execute(
                """
                INSERT INTO event_current
                    (event_id, event_version_id, current_updated, event_time, mag,
                     place, longitude, latitude, depth_km, country_id, country_name,
                     country_assignment_status, country_assignment_reason,
                     original_jsonb, normalized_jsonb, source, load_type, is_synthetic)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE SET
                    event_version_id = EXCLUDED.event_version_id,
                    current_updated = EXCLUDED.current_updated,
                    event_time = EXCLUDED.event_time,
                    mag = EXCLUDED.mag,
                    place = EXCLUDED.place,
                    longitude = EXCLUDED.longitude,
                    latitude = EXCLUDED.latitude,
                    depth_km = EXCLUDED.depth_km,
                    country_id = EXCLUDED.country_id,
                    country_name = EXCLUDED.country_name,
                    country_assignment_status = EXCLUDED.country_assignment_status,
                    country_assignment_reason = EXCLUDED.country_assignment_reason,
                    original_jsonb = EXCLUDED.original_jsonb,
                    normalized_jsonb = EXCLUDED.normalized_jsonb
                    ,source = EXCLUDED.source
                    ,load_type = EXCLUDED.load_type
                    ,is_synthetic = EXCLUDED.is_synthetic
                WHERE event_current.current_updated < EXCLUDED.current_updated
                """,
                (
                    payload["event_id"],
                    inserted[0],
                    payload["updated"],
                    properties.get("time"),
                    properties.get("mag"),
                    properties.get("place"),
                    coordinates[0],
                    coordinates[1],
                    coordinates[2] if len(coordinates) > 2 else None,
                    country["country_id"],
                    country["country_name"],
                    country["status"],
                    country["reason"],
                    json.dumps(event),
                    json.dumps({"event_id": payload["event_id"], "updated": payload["updated"]}),
                    payload.get("source", "usgs"),
                    payload["provenance"].get("load_type", "live_feed"),
                    payload.get("source") != "usgs" or payload["event_id"].startswith("controlled-"),
                ),
            )
        cursor.execute(
            """
            UPDATE ingestion_run
            SET status = 'completed', finished_at = %s,
                records_accepted = records_accepted + %s
            WHERE run_id = %s
            """,
            (now, 1 if inserted else 0, run_id),
        )
    if commit:
        connection.commit()
    return "accepted" if inserted else "duplicate_version"


def persist_quarantine(
    connection: psycopg.Connection, payload: dict, reason: str, commit: bool = True
) -> None:
    now = datetime.now(timezone.utc)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_run
                (run_id, source, load_type, mode, started_at, status,
                 records_seen, records_rejected)
            VALUES (%s, 'usgs', %s, %s, %s, 'completed', %s, 1)
            ON CONFLICT (run_id) DO UPDATE SET
                records_rejected = ingestion_run.records_rejected + 1
            """,
            (
                payload["run_id"],
                payload["provenance"].get("load_type", "live_feed"),
                payload.get("mode", "live"),
                now,
                payload["provenance"]["record_count"],
            ),
        )
        cursor.execute(
            """
            INSERT INTO quarantine_record
                (run_id, source_response_id, event_id, stage, reason_code,
                 reason_detail, created_at, original_jsonb, payload_reference)
            VALUES (%s, %s, %s, 'validation', %s, %s, %s, %s, %s)
            """,
            (
                payload["run_id"],
                payload["provenance"]["source_response_id"],
                payload.get("event_id"),
                reason,
                "live event failed validation",
                now,
                json.dumps(payload.get("event")),
                payload["provenance"].get("url"),
            ),
        )
    if commit:
        connection.commit()


def persist_bad_message(connection: psycopg.Connection, topic: str, partition: int,
                        offset: int, reason: str, raw: bytes) -> None:
    """Record a poison Kafka message independently of its untrusted envelope."""
    run_id = f"quarantine-{topic}-{partition}-{offset}"
    now = datetime.now(timezone.utc)
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO ingestion_run (run_id, source, load_type, mode, started_at,
                                       finished_at, status, records_seen, records_rejected)
            VALUES (%s, 'usgs', 'kafka_quarantine', 'live', %s, %s, 'completed', 1, 1)
            ON CONFLICT (run_id) DO NOTHING
        """, (run_id, now, now))
        cursor.execute("""
            INSERT INTO quarantine_record (run_id, source_response_id, event_id, stage,
                                           reason_code, reason_detail, created_at,
                                           original_jsonb, payload_reference)
            SELECT %s, NULL, NULL, 'kafka', %s, %s, %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM quarantine_record WHERE run_id=%s)
        """, (run_id, reason, "invalid Kafka message", now,
              json.dumps({"raw_utf8": raw.decode("utf-8", errors="replace")[:10000]}),
              f"{topic}:{partition}:{offset}", run_id))
    connection.commit()


def persist_replay_event(connection: psycopg.Connection, payload: dict, country: dict) -> str:
    event = payload["event"]
    properties = event["properties"]
    coordinates = event["geometry"]["coordinates"]
    values = (
        payload["event_id"], payload["updated"], properties.get("time"),
        properties.get("mag"), properties.get("place"), coordinates[0],
        coordinates[1], coordinates[2] if len(coordinates) > 2 else None,
        country["country_id"], country["country_name"], json.dumps(event),
        payload["replay_at"],
    )
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO replay_event_version
              (event_id, updated, event_time, mag, place, longitude, latitude,
               depth_km, country_id, country_name, original_jsonb, replay_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (event_id, updated) DO NOTHING RETURNING event_id
        """, values)
        inserted = cursor.fetchone() is not None
        if inserted:
            cursor.execute("""
                INSERT INTO replay_event_current
                  (event_id, current_updated, event_time, mag, place, longitude, latitude,
                   depth_km, country_id, country_name, original_jsonb, replay_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (event_id) DO UPDATE SET
                  current_updated=EXCLUDED.current_updated, event_time=EXCLUDED.event_time,
                  mag=EXCLUDED.mag, place=EXCLUDED.place, longitude=EXCLUDED.longitude,
                  latitude=EXCLUDED.latitude, depth_km=EXCLUDED.depth_km,
                  country_id=EXCLUDED.country_id, country_name=EXCLUDED.country_name,
                  original_jsonb=EXCLUDED.original_jsonb, replay_at=EXCLUDED.replay_at
                WHERE replay_event_current.current_updated < EXCLUDED.current_updated
            """, values)
    connection.commit()
    return "accepted" if inserted else "duplicate_version"
