from datetime import datetime, timezone
from typing import Any


VALID_STATES = {"starting", "ready", "completed", "failed", "unavailable"}


def service_status(state: str, symptom: str | None = None) -> dict[str, Any]:
    if state not in VALID_STATES:
        raise ValueError(f"Estado no válido: {state}")
    result: dict[str, Any] = {
        "state": state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if symptom:
        result["symptom"] = symptom
    return result
