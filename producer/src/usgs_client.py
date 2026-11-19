import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


FEED_URL = os.environ.get(
    "USGS_FEED_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
)
TIMEOUT_SECONDS = float(os.environ.get("USGS_REQUEST_TIMEOUT_SECONDS", "30"))
MAX_ATTEMPTS = int(os.environ.get("USGS_MAX_ATTEMPTS", "3"))
ORIGINALS_DIR = Path(
    os.environ.get(
        "USGS_ORIGINALS_DIR",
        "/evidence/002-ingesta-usgs-persistencia/originals",
    )
)
LIVE_ORIGINAL_RETENTION_DAYS = int(os.environ.get("USGS_LIVE_ORIGINAL_RETENTION_DAYS", "30"))


def fetch_feed() -> tuple[dict, dict]:
    requested_at = datetime.now(timezone.utc)
    request = Request(FEED_URL, headers={"Accept": "application/geo+json"})
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
                payload = json.loads(body.decode("utf-8"))
                received_at = datetime.now(timezone.utc)
                metadata = {
                    "url": FEED_URL,
                    "requested_at": requested_at.isoformat(),
                    "received_at": received_at.isoformat(),
                    "http_status": response.status,
                    "duration_ms": int((received_at - requested_at).total_seconds() * 1000),
                    "record_count": len(payload.get("features", [])),
                    "attempts": attempt,
                }
                return payload, metadata
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 and exc.code != 429:
                break
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt < MAX_ATTEMPTS:
            time.sleep(2**(attempt - 1))
    raise RuntimeError(f"USGS feed failed after {MAX_ATTEMPTS} attempts: {last_error}") from last_error


def save_original(payload: dict, metadata: dict, run_id: str) -> Path:
    directory = ORIGINALS_DIR / run_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "response.json"
    path.write_text(
        json.dumps(
            {"metadata": metadata, "payload": payload},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    cutoff = time.time() - LIVE_ORIGINAL_RETENTION_DAYS * 86400
    for old_path in ORIGINALS_DIR.glob("*/response.json"):
        if old_path != path and old_path.stat().st_mtime < cutoff:
            old_path.unlink()
            if not any(old_path.parent.iterdir()):
                old_path.parent.rmdir()
    return path


def save_latest_live_fetch(metadata: dict, run_id: str) -> Path:
    """Publish the last successful, preserved feed response for API freshness."""
    path = ORIGINALS_DIR.parent / "latest-live-fetch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps({
                "run_id": run_id,
                "received_at": metadata["received_at"],
                "record_count": metadata["record_count"],
            }) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
