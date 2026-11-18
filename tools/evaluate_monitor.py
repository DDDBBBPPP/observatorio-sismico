"""Evaluate the 24-hour JSONL without declaring completion before 24 real hours."""
import argparse
import json
from datetime import datetime
from pathlib import Path


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate(path: Path, interval_seconds: int = 300) -> dict:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise ValueError("El monitor aún no tiene muestras")
    times = [parse_time(item["sampled_at"]) for item in records]
    gaps = [{"after": times[index - 1].isoformat(), "before": times[index].isoformat(),
             "seconds": round((times[index] - times[index - 1]).total_seconds(), 1)}
            for index in range(1, len(times))
            if (times[index] - times[index - 1]).total_seconds() > interval_seconds * 1.5]
    unhealthy = [{"at": item["sampled_at"], "services": [name for name, state in item.get("services", {}).items()
                  if state.get("state") != "running" or state.get("health") != "healthy"]}
                 for item in records]
    unhealthy = [item for item in unhealthy if item["services"]]
    freshness = []
    for item, timestamp in zip(records, times):
        fetched = (item.get("source_last_fetch") or {}).get("received_at")
        if fetched:
            freshness.append((timestamp - parse_time(fetched)).total_seconds())
    lags = [item["consumer_lag_messages"] for item in records if isinstance(item.get("consumer_lag_messages"), int)]
    duration = (times[-1] - times[0]).total_seconds()
    errors = [item for item in records if item.get("errors")]
    return {"first_sample_utc": times[0].isoformat(), "last_sample_utc": times[-1].isoformat(),
            "elapsed_hours": round(duration / 3600, 3), "samples": len(records),
            "expected_samples_for_elapsed": int(duration // interval_seconds) + 1,
            "gaps_over_450_seconds": gaps, "unhealthy_samples": unhealthy,
            "samples_with_errors": len(errors), "max_source_fetch_age_seconds": round(max(freshness), 1) if freshness else None,
            "samples_over_10_minute_fetch_age": sum(age > 600 for age in freshness),
            "max_consumer_lag_messages": max(lags) if lags else None,
            "samples_without_lag_measurement": len(records) - len(lags),
            "complete_24h": duration >= 24 * 3600}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=Path("evidence/002-ingesta-usgs-persistencia/monitor-24h.jsonl"))
    args = parser.parse_args()
    print(json.dumps(evaluate(args.path), ensure_ascii=False, indent=2))
