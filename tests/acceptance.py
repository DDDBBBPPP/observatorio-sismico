"""Read-only acceptance checks against the five running Compose services."""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        assert response.status == 200
        return json.load(response)


health = get("/api/salud")
assert health["state"] == "ready"
assert health["source_last_fetch"]["received_at"]
trace = health["trace"]
assert trace["last_new_event_persisted_at"] and trace["last_persisted_at"]
assert trace["last_new_event_persisted_at"] <= trace["last_persisted_at"]
assert trace["revisions_stored"] >= 0 and trace["quarantined"] >= 0
assert trace["duplicates_discarded"] is None and trace["consumer_lag_messages"] is None
period = "start=2025-01-01T00%3A00%3A00Z&end=2026-01-01T00%3A00%3A00Z&min_mag=4"
first = get(f"/api/eventos?{period}&page_size=7&page=1")
second = get(f"/api/eventos?{period}&page_size=7&page=2")
assert first["type"] == "FeatureCollection"
assert isinstance(first["metadata"]["last_ingestion"], int)
assert first["metadata"]["truncated"] and first["metadata"]["count"] == 7
assert second["metadata"]["total"] == first["metadata"]["total"]
assert {f["id"] for f in first["features"]}.isdisjoint(f["id"] for f in second["features"])
stats = get(f"/api/estadisticas?{period}")
assert stats["count"] == first["metadata"]["total"]
assert stats["historical_comparison"]["events"] == 18302
assert stats["historical_comparison"]["days_in_denominator"] == 365
assert stats["historical_comparison"]["min_mag"] == 4
assert stats["historical_comparison"]["current_window_events"] == 0
assert stats["units"]["depth"] == "km"
assert sum(item["count"] for item in stats["distributions"]["magnitude"]["bins"]) + stats["distributions"]["magnitude"]["null_count"] == stats["count"]
assert sum(item["count"] for item in stats["distributions"]["depth_km"]["bins"]) + stats["distributions"]["depth_km"]["null_count"] == stats["count"]
recent = get("/api/estadisticas")
assert recent["historical_comparison"]["min_mag"] == 4
assert recent["historical_comparison"]["current_window_events"] <= recent["count"]
replay_period = "mode=replay&start=2025-01-01T00%3A00%3A00Z&end=2025-02-01T00%3A00%3A00Z"
replay = get(f"/api/eventos?{replay_period}")
assert replay["metadata"]["mode"] == "replay" and replay["metadata"]["total"] == 10
assert all(f["properties"]["replay_at"] for f in replay["features"])
assert all(f["properties"]["mode"] == "replay" for f in replay["features"])
assert get(f"/api/estadisticas?{replay_period}")["count"] == 10
try:
    get("/api/eventos?start=2025-02-01T00:00:00Z&end=2025-01-01T00:00:00Z")
except urllib.error.HTTPError as error:
    assert error.code == 400
else:
    raise AssertionError("Expected HTTP 400 for inverted window")
request = urllib.request.Request(BASE + "/api/eventos", method="OPTIONS", headers={
    "Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "ngrok-skip-browser-warning"})
with urllib.request.urlopen(request, timeout=10) as response:
    assert response.status == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
print(json.dumps({"status": "passed", "historical_2025": 18302, "page_total": first["metadata"]["total"], "replay": 10}))
