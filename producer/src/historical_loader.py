import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = os.environ.get(
    "USGS_HISTORICAL_URL",
    "https://earthquake.usgs.gov/fdsnws/event/1/query",
)
OUTPUT_DIR = Path(
    os.environ.get(
        "USGS_HISTORICAL_DIR",
        "/evidence/002-ingesta-usgs-persistencia/historical",
    )
)
LIMIT = int(os.environ.get("USGS_HISTORICAL_LIMIT", "20000"))
TIMEOUT = float(os.environ.get("USGS_REQUEST_TIMEOUT_SECONDS", "30"))
HISTORICAL_FILTERS = {
    "minmagnitude": 4,
    "eventtype": "earthquake",
    "orderby": "time-asc",
}


def _request(start: datetime, end: datetime) -> tuple[dict, dict]:
    params = {
        "format": "geojson",
        "starttime": start.isoformat().replace("+00:00", "Z"),
        "endtime": end.isoformat().replace("+00:00", "Z"),
        "limit": LIMIT,
        **HISTORICAL_FILTERS,
    }
    query = urlencode(params)
    requested = datetime.now(timezone.utc)
    with urlopen(Request(f"{BASE_URL}?{query}"), timeout=TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    received = datetime.now(timezone.utc)
    return payload, {
        "url": BASE_URL,
        "parameters": params,
        "requested_at": requested.isoformat(),
        "received_at": received.isoformat(),
        "http_status": response.status,
        "duration_ms": int((received - requested).total_seconds() * 1000),
        "record_count": len(payload.get("features", [])),
        "metadata_count": payload.get("metadata", {}).get("count"),
    }


def _intervals(start: datetime, end: datetime):
    queue = [(start, end)]
    while queue:
        current_start, current_end = queue.pop(0)
        payload, metadata = _request(current_start, current_end)
        count = metadata["metadata_count"] or metadata["record_count"]
        if count >= LIMIT and current_end - current_start > timedelta(hours=1):
            midpoint = current_start + (current_end - current_start) / 2
            queue.insert(0, (midpoint, current_end))
            queue.insert(0, (current_start, midpoint))
            continue
        yield current_start, current_end, payload, metadata


def load_year(year: int = 2025) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / f"{year}-minmag4-earthquake-manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {
            "year": year,
            "filters": {
                "scope": "world",
                "minmagnitude": 4,
                "eventtype": "earthquake",
                "starttime": f"{year}-01-01T00:00:00Z",
                "endtime": f"{year + 1}-01-01T00:00:00Z",
            },
            "intervals": [],
            "versions": {},
        }
    )
    for month in range(1, 13):
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
        if any(item["interval_start"] == start.isoformat() for item in manifest["intervals"]):
            continue
        for interval_start, interval_end, payload, metadata in _intervals(start, end):
            key = interval_start.isoformat()
            if any(item["interval_start"] == key for item in manifest["intervals"]):
                continue
            interval_dir = OUTPUT_DIR / "minmag4-earthquake" / key.replace(":", "").replace("+00:00", "Z")
            interval_dir.mkdir(parents=True, exist_ok=True)
            (interval_dir / "response.json").write_text(
                json.dumps({"metadata": metadata, "payload": payload}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            for feature in payload.get("features", []):
                properties = feature.get("properties") or {}
                identifier = feature.get("id")
                updated = properties.get("updated")
                if identifier and isinstance(updated, int):
                    manifest["versions"][f"{identifier}:{updated}"] = {
                        "interval_start": key,
                        "interval_end": interval_end.isoformat(),
                    }
            manifest["intervals"].append(
                {
                    "interval_start": key,
                    "interval_end": interval_end.isoformat(),
                    "record_count": metadata["record_count"],
                    "metadata_count": metadata["metadata_count"],
                    "path": str(interval_dir / "response.json"),
                }
            )
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
