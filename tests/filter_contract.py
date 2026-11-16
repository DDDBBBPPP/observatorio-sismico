"""Read-only HTTP checks for a frozen window shared by events and statistics."""
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "http://127.0.0.1:8000"
end = datetime.now(timezone.utc).replace(microsecond=0)
start = end - timedelta(hours=24)
period = {"start": start.isoformat(), "end": end.isoformat()}
historical = {"start": "2025-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"}


def get(route, params):
    with urlopen(f"{BASE}{route}?{urlencode(params)}", timeout=15) as response:
        assert response.status == 200
        return json.load(response)


results = []
for label, extra in (
    ("USA", {"country_id": "USA"}),
    ("ESP", {"country_id": "ESP"}),
    ("mag4", {"min_mag": 4}),
    ("USA_mag4", {"country_id": "USA", "min_mag": 4}),
    ("UNASSIGNED", {"country_id": "UNASSIGNED"}),
):
    params = {**period, **extra, "mode": "live"}
    events = get("/api/eventos", {**params, "page_size": 5000})
    stats = get("/api/estadisticas", params)
    meta = events["metadata"]
    assert meta["total"] == stats["count"] == len(events["features"]), label
    assert meta["filters"]["country_id"] == stats["filters"]["country_id"] == extra.get("country_id"), label
    assert meta["filters"]["min_mag"] == stats["filters"]["min_mag"] == extra.get("min_mag"), label
    assert len({feature["id"] for feature in events["features"]}) == stats["count"], label
    assert sum(item["count"] for item in stats["countries"]) == stats["count"], label
    assert sum(item["count"] for item in stats["hourly_utc"]) == stats["count"], label
    for distribution in stats["distributions"].values():
        assert sum(item["count"] for item in distribution["bins"]) + distribution["null_count"] == stats["count"], label
    for feature in events["features"]:
        assert feature["properties"]["mode"] != "replay", label
        assert not feature["id"].startswith("controlled-"), label
        if extra.get("country_id") == "UNASSIGNED":
            assert feature["properties"]["country_id"] is None, label
        elif extra.get("country_id"):
            assert feature["properties"]["country_id"] == extra["country_id"], label
        if extra.get("min_mag") is not None:
            assert feature["properties"]["mag"] >= extra["min_mag"], label
    comparison = stats["historical_comparison"]
    threshold = max(4, extra.get("min_mag", 4))
    assert comparison["min_mag"] == threshold, label
    past = get("/api/eventos", {**historical, "min_mag": threshold,
                                **({"country_id": extra["country_id"]} if "country_id" in extra else {}),
                                "page_size": 1})
    assert comparison["events"] == past["metadata"]["total"], label
    if extra.get("min_mag") == 4:
        assert comparison["current_window_events"] == stats["count"], label
    else:
        assert comparison["current_window_events"] <= stats["count"], label
    results.append({"filter": label, "current": stats["count"], "historical": comparison["events"]})

replay_params = {"mode": "replay", "start": "2025-01-01T00:00:00Z", "end": "2025-02-01T00:00:00Z"}
replay = get("/api/eventos", replay_params)
replay_stats = get("/api/estadisticas", replay_params)
assert replay["metadata"]["total"] == replay_stats["count"] == 10
assert all(feature["properties"]["mode"] == "replay" and feature["properties"]["replay_at"]
           and 1735689600000 <= feature["properties"]["time"] < 1738368000000
           for feature in replay["features"])
replay_usa = get("/api/eventos", {**replay_params, "country_id": "USA"})
replay_usa_stats = get("/api/estadisticas", {**replay_params, "country_id": "USA"})
assert replay_usa["metadata"]["total"] == replay_usa_stats["count"]
assert all(feature["properties"]["country_id"] == "USA" and feature["properties"]["mode"] == "replay"
           for feature in replay_usa["features"])
replay_by_country = {}
for country in replay_stats["countries"]:
    code = country["country_id"]
    filtered = get("/api/eventos", {**replay_params, "country_id": code})
    filtered_stats = get("/api/estadisticas", {**replay_params, "country_id": code})
    assert filtered["metadata"]["total"] == filtered_stats["count"] == country["count"]
    assert all(feature["properties"]["mode"] == "replay" and
               feature["properties"]["country_id"] == (None if code == "UNASSIGNED" else code)
               for feature in filtered["features"])
    replay_by_country[code] = country["count"]
assert sum(replay_by_country.values()) == replay_stats["count"]
replay_november = get("/api/eventos", {"mode": "replay", "start": "2026-11-16T00:00:00Z",
                                      "end": "2026-11-17T00:00:00Z"})
assert replay_november["metadata"]["total"] == 0
print(json.dumps({"status": "passed", "filters": results, "replay": replay_stats["count"],
                  "replay_usa": replay_usa_stats["count"], "replay_by_country": replay_by_country,
                  "replay_november": 0}))
