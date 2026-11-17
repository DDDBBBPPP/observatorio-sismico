import json
import os
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import connection


app = FastAPI(title="Observatorio Sísmico API", version="1.0")
origins = [
    item.strip()
    for item in os.environ.get(
        "CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200"
    ).split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "ngrok-skip-browser-warning"],
)

LATEST_LIVE_FETCH = Path(os.environ.get(
    "USGS_LATEST_FETCH_PATH",
    "/evidence/002-ingesta-usgs-persistencia/latest-live-fetch.json",
))


def parse_window(
    start: datetime | None, end: datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end_value = end or now
    start_value = start or end_value - timedelta(hours=24)
    if start_value.tzinfo is None:
        start_value = start_value.replace(tzinfo=timezone.utc)
    if end_value.tzinfo is None:
        end_value = end_value.replace(tzinfo=timezone.utc)
    start_value = start_value.astimezone(timezone.utc)
    end_value = end_value.astimezone(timezone.utc)
    if start_value >= end_value:
        raise HTTPException(status_code=400, detail="start debe ser anterior a end")
    return start_value, end_value


def filters(
    start_ms: int,
    end_ms: int,
    min_mag: float | None,
    country_id: str | None,
    alias: str = "c",
    real_only: bool = True,
) -> tuple[str, list[Any]]:
    clauses = [f"{alias}.event_time >= %s", f"{alias}.event_time < %s"]
    if real_only:
        clauses.insert(0, f"{alias}.is_synthetic = FALSE")
    params: list[Any] = [start_ms, end_ms]
    if min_mag is not None:
        clauses.append(f"{alias}.mag IS NOT NULL AND {alias}.mag >= %s")
        params.append(min_mag)
    if country_id == "UNASSIGNED":
        clauses.append(f"{alias}.country_id IS NULL")
    elif country_id:
        clauses.append(f"{alias}.country_id = %s")
        params.append(country_id)
    return " AND ".join(clauses), params


def last_ingestion(cursor) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT run_id, finished_at, records_accepted, records_rejected, mode
        FROM ingestion_run
        WHERE source = 'usgs' AND load_type = 'live_feed' AND status = 'completed'
          AND run_id NOT LIKE 'controlled-%'
        ORDER BY finished_at DESC NULLS LAST
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "run_id": row[0],
        "finished_at": row[1].isoformat() if row[1] else None,
        "records_accepted": row[2],
        "records_rejected": row[3],
        "mode": row[4],
    }


def last_source_fetch() -> dict[str, Any] | None:
    """Read the last successful USGS poll, including polls with no new events."""
    try:
        value = json.loads(LATEST_LIVE_FETCH.read_text(encoding="utf-8"))
        received_at = datetime.fromisoformat(value["received_at"])
        if received_at.tzinfo is None:
            return None
        return {
            "run_id": str(value["run_id"]),
            "received_at": received_at.astimezone(timezone.utc).isoformat(),
            "record_count": int(value["record_count"]),
        }
    except (OSError, ValueError, TypeError, KeyError):
        return None


def last_source_fetch_ms(source_fetch: dict[str, Any] | None, ingestion: dict[str, Any] | None) -> int | None:
    if source_fetch:
        return int(datetime.fromisoformat(source_fetch["received_at"]).timestamp() * 1000)
    if ingestion and ingestion["finished_at"]:
        return int(datetime.fromisoformat(ingestion["finished_at"]).timestamp() * 1000)
    return None


def database_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"PostgreSQL no disponible: {exc}")


def histogram(values: list[float], boundaries: list[float], labels: list[str]) -> list[dict[str, Any]]:
    counts = [0] * len(labels)
    for value in values:
        counts[bisect_right(boundaries, value)] += 1
    return [{"label": label, "count": count} for label, count in zip(labels, counts)]


@app.get("/api/salud")
def health() -> dict[str, Any]:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                ingestion = last_ingestion(cursor)
        return {
            "service": "api",
            "state": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ingestion": ingestion or {"state": "not_started"},
            "source_last_fetch": last_source_fetch() or {"state": "not_started"},
        }
    except Exception as exc:
        raise database_error(exc) from exc


@app.get("/api/eventos")
def events(
    start: datetime | None = None,
    end: datetime | None = None,
    min_mag: float | None = Query(default=None, ge=-10, le=20),
    country_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=1000, ge=1, le=5000),
    mode: str = Query(default="live", pattern="^(live|replay)$"),
) -> dict[str, Any]:
    start_value, end_value = parse_window(start, end)
    start_ms = int(start_value.timestamp() * 1000)
    end_ms = int(end_value.timestamp() * 1000)
    where, params = filters(start_ms, end_ms, min_mag, country_id, real_only=mode == "live")
    table = "event_current" if mode == "live" else "replay_event_current"
    join = "JOIN event_version v ON v.event_version_id = c.event_version_id" if mode == "live" else ""
    extra = "v.mode, v.load_type, NULL::timestamptz" if mode == "live" else "'replay', 'historical_replay', c.replay_at"
    offset = (page - 1) * page_size
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table} c WHERE {where}", params)
                total = cursor.fetchone()[0]
                cursor.execute(
                    f"""
                    SELECT c.event_id, c.event_time, c.current_updated, c.mag, c.place,
                           c.longitude, c.latitude, c.depth_km, c.country_id, c.country_name,
                           c.original_jsonb, {extra}
                    FROM {table} c
                    {join}
                    WHERE {where}
                    ORDER BY event_time DESC NULLS LAST, event_id
                    LIMIT %s OFFSET %s
                    """,
                    [*params, page_size, offset],
                )
                rows = cursor.fetchall()
                ingestion = last_ingestion(cursor)
        features = []
        for row in rows:
            original = row[10] or {}
            properties = original.get("properties") or {}
            features.append(
                {
                    "type": "Feature",
                    "id": row[0],
                    "geometry": {
                        "type": "Point",
                        "coordinates": [row[5], row[6], row[7]],
                    },
                    "properties": {
                        "mag": row[3],
                        "magType": properties.get("magType"),
                        "place": row[4],
                        "time": row[1],
                        "updated": row[2],
                        "country_id": row[8],
                        "country_name": row[9],
                        "mode": row[11],
                        "load_type": row[12],
                        "replay_at": row[13].isoformat() if row[13] else None,
                    },
                }
            )
        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": int(datetime.now(timezone.utc).timestamp() * 1000),
                "last_ingestion": last_source_fetch_ms(last_source_fetch(), ingestion),
                "last_source_fetch": last_source_fetch_ms(last_source_fetch(), None),
                "mode": mode,
                "count": len(features),
                "total": total,
                "page": page,
                "page_size": page_size,
                "truncated": offset + len(features) < total,
                "filters": {
                    "start": start_value.isoformat(),
                    "end": end_value.isoformat(),
                    "min_mag": min_mag,
                    "country_id": country_id,
                },
            },
            "features": features,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise database_error(exc) from exc


@app.get("/api/estadisticas")
def statistics(
    start: datetime | None = None,
    end: datetime | None = None,
    min_mag: float | None = Query(default=None, ge=-10, le=20),
    country_id: str | None = None,
    mode: str = Query(default="live", pattern="^(live|replay)$"),
) -> dict[str, Any]:
    start_value, end_value = parse_window(start, end)
    start_ms = int(start_value.timestamp() * 1000)
    end_ms = int(end_value.timestamp() * 1000)
    where, params = filters(start_ms, end_ms, min_mag, country_id, real_only=mode == "live")
    table = "event_current" if mode == "live" else "replay_event_current"
    historical_where, historical_params = filters(
        int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),
        int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),
        max(4.0, min_mag) if min_mag is not None else 4.0,
        country_id,
        alias="v",
    )
    comparison_mag = max(4.0, min_mag) if min_mag is not None else 4.0
    comparison_where, comparison_params = filters(
        start_ms, end_ms, comparison_mag, country_id, real_only=mode == "live"
    )
    if mode == "live":
        comparison_where += " AND c.load_type = 'live_feed'"
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT date_trunc('hour', to_timestamp(c.event_time / 1000.0)),
                           COUNT(*)
                    FROM {table} c WHERE {where}
                    GROUP BY 1 ORDER BY 1
                    """,
                    params,
                )
                hourly = [
                    {"hour_utc": row[0].isoformat(), "count": row[1]}
                    for row in cursor.fetchall()
                ]
                cursor.execute(
                    f"""
                    SELECT COALESCE(c.country_id, 'UNASSIGNED'), COALESCE(c.country_name, 'Sin país asignado'),
                           COUNT(*)
                    FROM {table} c WHERE {where}
                    GROUP BY 1, 2 ORDER BY 3 DESC, 1
                    """,
                    params,
                )
                countries = [
                    {"country_id": row[0], "country_name": row[1], "count": row[2]}
                    for row in cursor.fetchall()
                ]
                cursor.execute(
                    f"                    SELECT c.mag, c.depth_km FROM {table} c WHERE {where}",
                    params,
                )
                distribution = cursor.fetchall()
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT v.event_id)
                    FROM event_version v
                    WHERE v.mode = 'historical' AND v.load_type = 'historical_initial'
                      AND {historical_where}
                    """,
                    historical_params,
                )
                historical_count = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table} c WHERE {comparison_where}",
                    comparison_params,
                )
                comparison_count = cursor.fetchone()[0]
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT c.event_id), COUNT(*) FILTER (WHERE c.mag IS NULL),
                           COUNT(*) FILTER (WHERE c.depth_km IS NULL)
                    FROM {table} c WHERE {where}
                    """,
                    params,
                )
                count, null_mag, null_depth = cursor.fetchone()
        days = (datetime(2026, 1, 1) - datetime(2025, 1, 1)).days
        return {
            "period": {
                "start": start_value.isoformat(),
                "end": end_value.isoformat(),
                "timezone": "UTC",
            },
            "mode": mode,
            "filters": {"min_mag": min_mag, "country_id": country_id},
            "units": {"time": "UTC", "depth": "km", "counts": "events"},
            "count": count,
            "hourly_utc": hourly,
            "countries": countries,
            "distributions": {
                "magnitude": {
                    "bins": histogram([row[0] for row in distribution if row[0] is not None],
                                      [0, 2, 4, 6, 8], ["<0", "0–<2", "2–<4", "4–<6", "6–<8", "≥8"]),
                    "null_count": null_mag,
                },
                "depth_km": {
                    "bins": histogram([row[1] for row in distribution if row[1] is not None],
                                      [0, 70, 300], ["<0", "0–<70", "70–<300", "≥300"]),
                    "null_count": null_depth,
                },
            },
            "historical_comparison": {
                "year": 2025,
                "filters_equivalent": True,
                "events": historical_count,
                "current_window_events": comparison_count,
                "min_mag": comparison_mag,
                "window_days": (end_value - start_value).total_seconds() / 86400,
                "days_in_denominator": days,
                "average_daily_including_zero_days": historical_count / days,
                "average_for_window": historical_count / days * (end_value - start_value).total_seconds() / 86400,
            },
        }
    except Exception as exc:
        raise database_error(exc) from exc
