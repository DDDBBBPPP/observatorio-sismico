"""Kafka envelope checks and verified access to locally preserved USGS responses."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from validation import validate_live_event


ORIGINALS = Path("/evidence/002-ingesta-usgs-persistencia/originals").resolve()
_cached_reference = None
_cached_payload = None
_cached_features = None


def validate_envelope(payload: object, topic: str, live_topic: str, replay_topic: str) -> str | None:
    if not isinstance(payload, dict):
        return "invalid_envelope"
    mode = "live" if topic == live_topic else "replay" if topic == replay_topic else None
    if payload.get("schema") != "observatorio.event-envelope.v1" or payload.get("source") != "usgs" or payload.get("mode") != mode:
        return "invalid_envelope"
    if not isinstance(payload.get("run_id"), str) or not payload["run_id"]:
        return "missing_run_id"
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict) or provenance.get("run_id") != payload["run_id"] or not isinstance(provenance.get("source_response_id"), str):
        return "invalid_provenance"
    if mode == "live":
        required = ("url", "requested_at", "received_at", "http_status", "duration_ms", "record_count")
        if any(provenance.get(field) is None for field in required):
            return "invalid_provenance"
        if not isinstance(provenance["url"], str) or not isinstance(provenance["http_status"], int) or not isinstance(provenance["duration_ms"], int) or not isinstance(provenance["record_count"], int):
            return "invalid_provenance"
        try:
            if any(datetime.fromisoformat(provenance[field]).tzinfo is None for field in ("requested_at", "received_at")):
                return "invalid_provenance"
        except (TypeError, ValueError):
            return "invalid_provenance"
        if "original" not in provenance and (not isinstance(provenance.get("original_reference"), str) or not isinstance(provenance.get("original_sha256"), str)):
            return "missing_original_reference"
    event = payload.get("event")
    if not isinstance(event, dict):
        return "invalid_event"
    valid, reason = validate_live_event(event)
    if not valid:
        return reason
    if payload.get("event_id") != event["id"] or payload.get("updated") != event["properties"]["updated"]:
        return "envelope_event_mismatch"
    if mode == "replay":
        try:
            if datetime.fromisoformat(payload["replay_at"]).tzinfo is None:
                return "invalid_replay_at"
        except (KeyError, TypeError, ValueError):
            return "invalid_replay_at"
    return None


def original_for(payload: dict) -> dict:
    """Legacy envelopes carry the full response; new ones carry a checked file reference."""
    global _cached_reference, _cached_payload, _cached_features
    provenance = payload["provenance"]
    if "original" in provenance:
        return provenance["original"]
    reference = Path(provenance["original_reference"]).resolve()
    if not reference.is_relative_to(ORIGINALS):
        raise ValueError("original_reference_outside_evidence")
    digest = provenance["original_sha256"]
    if (str(reference), digest) != _cached_reference:
        raw = reference.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("original_sha256_mismatch")
        document = json.loads(raw)
        original = document["payload"]
        if not isinstance(original.get("features"), list):
            raise ValueError("invalid_original")
        _cached_reference = (str(reference), digest)
        _cached_payload = original
        _cached_features = {feature.get("id"): feature for feature in original["features"] if isinstance(feature, dict)}
    event = payload["event"]
    if _cached_features.get(event.get("id")) != event:
        raise ValueError("event_missing_from_original")
    return _cached_payload
