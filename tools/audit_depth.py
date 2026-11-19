"""Compare fixed-window depth filters across API, statistics and PostgreSQL.

Read-only: never loads the historical source or changes database state.
"""
import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


def read_api(path, params):
    with urlopen(f"{BASE}{path}?{urlencode(params)}", timeout=15) as response:
        assert response.status == 200
        return json.load(response)


def sql_counts(table, start_ms, end_ms, lower, upper, historical=False, live_only=False, min_mag=None):
    clauses = [f"event_time >= {start_ms}", f"event_time < {end_ms}"]
    if historical:
        clauses += ["mode = 'historical'", "load_type = 'historical_initial'", "is_synthetic = FALSE", "mag >= 4"]
    elif table == "event_current":
        clauses.append("is_synthetic = FALSE")
    if live_only:
        clauses.append("load_type = 'live_feed'")
    if min_mag is not None:
        clauses.append(f"mag >= {min_mag}")
    if lower is not None:
        clauses.append(f"depth_km >= {lower}")
    if upper is not None:
        clauses.append(f"depth_km <= {upper}")
    expression = "COUNT(DISTINCT event_id)" if historical else "COUNT(*)"
    query = f"SELECT {expression}, COUNT(*) FILTER (WHERE depth_km IS NULL) FROM {table} WHERE {' AND '.join(clauses)}"
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "observatorio", "-d", "observatorio", "-At", "-F", "|", "-c", query],
        cwd=ROOT, capture_output=True, text=True, timeout=20, check=True,
    )
    count, nulls = result.stdout.strip().split("|")
    return int(count), int(nulls)


parser = argparse.ArgumentParser()
parser.add_argument("--start", help="ISO UTC start, inclusive")
parser.add_argument("--end", help="ISO UTC end, exclusive")
parser.add_argument("--output", type=Path)
args = parser.parse_args()
end = datetime.fromisoformat(args.end.replace("Z", "+00:00")) if args.end else datetime.now(timezone.utc).replace(microsecond=0)
start = datetime.fromisoformat(args.start.replace("Z", "+00:00")) if args.start else end - timedelta(hours=24)
assert start.tzinfo and end.tzinfo and start < end
start_ms, end_ms = (int(value.timestamp() * 1000) for value in (start, end))
historical_start = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
historical_end = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)

result = {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "window_utc": {"start": start.isoformat(), "end": end.isoformat()}, "cases": []}
for mode, table in (("live", "event_current"), ("replay", "replay_event_current")):
    period = {"start": start.isoformat(), "end": end.isoformat()} if mode == "live" else {"start": "2025-01-01T00:00:00Z", "end": "2025-02-01T00:00:00Z"}
    sql_start, sql_end = (start_ms, end_ms) if mode == "live" else (historical_start, int(datetime(2025, 2, 1, tzinfo=timezone.utc).timestamp() * 1000))
    for label, lower, upper in (("all", None, None), ("0-70", 0, 70), ("70-300", 70, 300), ("-20-0", -20, 0)):
        params = {**period, "mode": mode, "page_size": 5000}
        if lower is not None:
            params["min_depth_km"] = lower
        if upper is not None:
            params["max_depth_km"] = upper
        events = read_api("/api/eventos", params)
        stats = read_api("/api/estadisticas", params)
        db_count, db_nulls = sql_counts(table, sql_start, sql_end, lower, upper)
        historic_count, _ = sql_counts("event_version", historical_start, historical_end, lower, upper, historical=True)
        # Comparison always uses an effective minimum magnitude of four.
        comparable_params = {**params, "min_mag": 4, "page_size": 1}
        comparable_api = read_api("/api/eventos", comparable_params)["metadata"]["total"]
        comparable_db, _ = sql_counts(table, sql_start, sql_end, lower, upper,
                                       live_only=mode == "live", min_mag=4)
        assert events["metadata"]["total"] == stats["count"] == db_count
        assert len(events["features"]) == db_count
        assert stats["distributions"]["depth_km"]["null_count"] == db_nulls
        assert stats["historical_comparison"]["events"] == historic_count
        assert stats["historical_comparison"]["current_window_events"] == comparable_api == comparable_db
        assert all((lower is None or item["geometry"]["coordinates"][2] is not None and item["geometry"]["coordinates"][2] >= lower)
                   and (upper is None or item["geometry"]["coordinates"][2] is not None and item["geometry"]["coordinates"][2] <= upper)
                   for item in events["features"])
        result["cases"].append({"mode": mode, "range_km_inclusive": label, "api_events": db_count,
                                "postgres_events": db_count, "null_depths": db_nulls,
                                "historical_2025_comparison": historic_count,
                                "current_window_mag_ge_4": comparable_api, "postgres_current_window_mag_ge_4": comparable_db})

if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
