from datetime import datetime, timezone
from time import time
from uuid import uuid4


def build_test_event() -> dict:
    identifier = uuid4().hex
    now_ms = int(time() * 1000)
    return {
        "schema": "observatorio.test-envelope.v1",
        "run_id": f"run-{identifier}",
        "source": "synthetic-test",
        "mode": "test",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "event": {
            "event_id": f"test-{identifier}",
            "event_type": "test-earthquake",
            "time": now_ms,
            "updated": now_ms,
            "mag": 4.2,
            "mag_type": "mw-test",
            "place": "Localizacion ficticia de prueba",
            "coordinates": [-3.7, 40.4, 12.0],
        },
    }


def build_live_event(feature: dict, run_id: str, response_id: str) -> dict:
    properties = feature.get("properties") or {}
    return {
        "schema": "observatorio.event-envelope.v1",
        "run_id": run_id,
        "source": "usgs",
        "mode": "live",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "event": feature,
        "event_id": feature["id"],
        "updated": properties["updated"],
        "provenance": {
            "run_id": run_id,
            "source_response_id": response_id,
            "load_type": "live_feed",
        },
    }
