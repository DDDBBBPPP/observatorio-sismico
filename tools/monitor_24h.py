"""Local, bounded 24-hour sampler. Run from the repository root."""
import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


SERVICES = ("kafka", "postgres", "producer", "consumer", "api")
DEFAULT_OUTPUT = Path("evidence/002-ingesta-usgs-persistencia/monitor-24h.jsonl")


def command(*args: str, timeout: int = 20) -> str:
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=True)
    return result.stdout.strip()


def api(path: str) -> dict:
    with urlopen(f"http://127.0.0.1:8000{path}", timeout=8) as response:
        return json.load(response)


def sample() -> dict:
    result = {"sampled_at": datetime.now(timezone.utc).isoformat(), "services": {}, "errors": []}
    try:
        rows = command("docker", "compose", "ps", "--format", "json")
        parsed = json.loads(rows) if rows.startswith("[") else [json.loads(line) for line in rows.splitlines()]
        by_service = {row.get("Service"): row for row in parsed}
        for service in SERVICES:
            row = by_service.get(service, {})
            result["services"][service] = {"state": row.get("State", "missing"), "health": row.get("Health", "unknown")}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result["errors"].append(f"docker_ps:{exc}")
    try:
        health = api("/api/salud")
        result["source_last_fetch"] = health.get("source_last_fetch")
        result["last_ingestion_run"] = health.get("ingestion")
        live = api("/api/estadisticas?mode=live")
        result["counts"] = {"live_24h": live.get("count"), "historical_2025": live.get("historical_comparison", {}).get("events")}
    except (OSError, ValueError, KeyError) as exc:
        result["errors"].append(f"api:{exc}")
    try:
        script = "import json;from persistence import connect;c=connect();cur=c.cursor();cur.execute(\"SELECT (SELECT count(*) FROM event_current WHERE load_type='live_feed' AND is_synthetic=false),(SELECT count(*) FROM replay_event_current),(SELECT count(*) FROM quarantine_record)\");print(json.dumps(cur.fetchone()));c.close()"
        raw = command("docker", "compose", "exec", "-T", "consumer", "python", "-c", "import sys;sys.path.insert(0,'/app/src');" + script)
        current, replay, quarantined = json.loads(raw.splitlines()[-1])
        result.setdefault("counts", {}).update({"live_total": current, "replay_total": replay, "quarantined_total": quarantined})
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result["errors"].append(f"database:{exc}")
    error_file = Path("evidence/002-ingesta-usgs-persistencia/live-errors.jsonl")
    result["live_fetch_errors_total"] = sum(1 for _ in error_file.open(encoding="utf-8")) if error_file.exists() else 0
    try:
        raw = command("docker", "compose", "exec", "-T", "kafka", "/opt/kafka/bin/kafka-consumer-groups.sh", "--bootstrap-server", "localhost:9092", "--group", "observatorio-consumer", "--describe", timeout=25)
        lags = []
        for line in raw.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[0] == "observatorio-consumer" and parts[5].isdigit():
                lags.append(int(parts[5]))
        result["consumer_lag_messages"] = sum(lags) if lags else None
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result["errors"].append(f"consumer_lag:{exc}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Take one smoke sample and exit")
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument("--duration-hours", type=float, default=24)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.interval_seconds < 1 or args.duration_hours <= 0:
        parser.error("Interval and duration must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.duration_hours * 3600
    while True:
        start = time.monotonic()
        record = sample()
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps({"sampled_at": record["sampled_at"], "errors": record["errors"], "output": str(args.output)}, ensure_ascii=False), flush=True)
        if args.once or time.monotonic() >= deadline:
            break
        time.sleep(min(max(0, args.interval_seconds - (time.monotonic() - start)), max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    main()
