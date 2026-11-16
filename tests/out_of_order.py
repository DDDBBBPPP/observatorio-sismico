"""Rollback-only integration check: initial, newer, older, duplicate."""
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, "/app/src")
from persistence import connect, persist_live_event  # noqa: E402
from validation import validate_live_event  # noqa: E402

suffix = uuid4().hex
event_id = f"controlled-out-of-order-{suffix}"
run_id = f"controlled-out-of-order-run-{suffix}"
response_id = f"controlled-out-of-order-response-{suffix}"
now = datetime.now(timezone.utc).isoformat()
country = {"country_id": None, "country_name": None,
           "status": "unassigned", "reason": "no_catalog_match"}


def message(updated, magnitude):
    event = {"type": "Feature", "id": event_id,
             "properties": {"type": "earthquake", "time": 1794787200000,
                            "updated": updated, "mag": magnitude, "place": "Control transaccional"},
             "geometry": {"type": "Point", "coordinates": [0, 0, 10]}}
    valid, reason = validate_live_event(event)
    assert valid, reason
    return {"run_id": run_id, "event_id": event_id, "updated": updated,
            "source": "synthetic-test", "mode": "live", "event": event,
            "provenance": {"source_response_id": response_id, "load_type": "live_feed",
                           "record_count": 1, "url": "test://out-of-order",
                           "requested_at": now, "received_at": now,
                           "http_status": 200, "duration_ms": 0, "original": {}}}


connection = connect()
try:
    assert persist_live_event(connection, message(1000, 1.0), country, commit=False) == "accepted"
    assert persist_live_event(connection, message(3000, 3.0), country, commit=False) == "accepted"
    assert persist_live_event(connection, message(2000, 2.0), country, commit=False) == "accepted"
    assert persist_live_event(connection, message(2000, 2.0), country, commit=False) == "duplicate_version"
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_updated, mag, is_synthetic FROM event_current WHERE event_id=%s", (event_id,))
        assert cursor.fetchone() == (3000, 3.0, True)
        cursor.execute("SELECT count(*) FROM event_version WHERE event_id=%s", (event_id,))
        assert cursor.fetchone()[0] == 3
    print("out-of-order: passed; current=3000, versions=3, duplicate unchanged; rollback")
finally:
    connection.rollback()
    connection.close()
