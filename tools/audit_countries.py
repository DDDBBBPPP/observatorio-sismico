"""Compare one saved USGS feed with API, statistics and PostgreSQL for a fixed UTC window."""
import json
import hashlib
import argparse
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "evidence/002-ingesta-usgs-persistencia/audit-country-20261117"
START = datetime.fromisoformat("2026-11-17T12:00:00+00:00")
END = datetime.fromisoformat("2026-11-17T23:00:00+00:00")
DB_CODE = """import json,sys;sys.path.insert(0,'/app/src');from persistence import connect
c=connect();cur=c.cursor();cur.execute('''SELECT c.event_id,c.event_time,c.mag,c.longitude,c.latitude,c.country_id,c.country_name,c.country_assignment_status,c.country_assignment_reason,v.source_response_id FROM event_current c JOIN event_version v ON v.event_version_id=c.event_version_id WHERE c.is_synthetic=false AND c.event_time >= %s AND c.event_time < %s ORDER BY c.event_id''',(int(sys.argv[1]),int(sys.argv[2])));print(json.dumps(cur.fetchall()));c.close()"""
POLYGON_CODE = """import json,sys;from shapely.geometry import Point,shape
catalog=json.load(open('/app/catalog/paises.geojson',encoding='utf-8'))
items=json.loads(sys.argv[1])
for item in items:
 point=Point(item['longitude'],item['latitude']); matches=[{'code':f['properties']['ADM0_A3'],'name':f['properties'].get('NAME_ES') or f['properties'].get('NAME')} for f in catalog['features'] if shape(f['geometry']).covers(point)];item['polygon_matches']=matches
print(json.dumps(items))"""
CANADA_CODE = """import json,sys;sys.path.insert(0,'/app/src');from persistence import connect
c=connect();cur=c.cursor();cur.execute(\"SELECT event_id,longitude,latitude,country_id,country_name,country_assignment_status,country_assignment_reason FROM event_current WHERE country_id='CAN' AND is_synthetic=false ORDER BY event_time DESC LIMIT 2\");print(json.dumps(cur.fetchall()));c.close()"""


def api(path: str, params: dict) -> dict:
    with urlopen("http://127.0.0.1:8000" + path + "?" + urlencode(params), timeout=20) as response:
        return json.load(response)


def event_rows(params: dict) -> tuple[list[dict], dict]:
    result = []
    page = 1
    while True:
        document = api("/api/eventos", {**params, "page": page, "page_size": 1000})
        result.extend(document["features"])
        if not document["metadata"]["truncated"]:
            return result, document["metadata"]
        page += 1


def docker_python(code: str, *args: str) -> object:
    result = subprocess.run(["docker", "compose", "exec", "-T", "consumer", "python", "-c", code, *args],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=30)
    return json.loads(result.stdout.splitlines()[-1])


def unique_by_id(features: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in features if isinstance(item.get("id"), str)}


def main(audit_dir: Path = AUDIT, start: datetime = START, end: datetime = END,
         write_result: bool = False) -> None:
    snapshot_path = audit_dir / "all_day.geojson"
    source_metadata = json.loads((audit_dir / "source-metadata.json").read_text(encoding="utf-8"))
    if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != source_metadata["sha256"]:
        raise ValueError("La instantánea USGS cambió desde la auditoría")
    original = json.loads(snapshot_path.read_text(encoding="utf-8"))
    start_ms, end_ms = (int(value.timestamp() * 1000) for value in (start, end))
    in_window = [feature for feature in original["features"] if start_ms <= (feature.get("properties") or {}).get("time", -1) < end_ms]
    earthquakes = [feature for feature in in_window if (feature.get("properties") or {}).get("type") == "earthquake"]
    source = unique_by_id(earthquakes)
    rows = docker_python(DB_CODE, str(start_ms), str(end_ms))
    database = {row[0]: row for row in rows}
    results = {"source": source_metadata,
               "window_utc": {"start": start.isoformat(), "end": end.isoformat()},
               "original": {"features_total": len(original["features"]), "features_in_window": len(in_window),
                            "unique_ids_in_window": len(unique_by_id(in_window)), "earthquakes_in_window": len(earthquakes),
                            "unique_earthquake_ids": len(source)}}
    for label, minimum in (("all", None), ("mag_ge_4", 4)):
        params = {"mode": "live", "start": start.isoformat(), "end": end.isoformat()}
        if minimum is not None:
            params["min_mag"] = minimum
        events, metadata = event_rows(params)
        stats = api("/api/estadisticas", params)
        api_ids = {item["id"] for item in events}
        api_by_id = {item["id"]: item for item in events}
        db_rows = {identifier: row for identifier, row in database.items() if minimum is None or row[2] is not None and row[2] >= minimum}
        source_ids = {identifier for identifier, feature in source.items() if minimum is None or (feature["properties"].get("mag") is not None and feature["properties"]["mag"] >= minimum)}
        country_counts = {item["country_id"]: item["count"] for item in stats["countries"]}
        api_countries = Counter(item["properties"].get("country_id") or "UNASSIGNED" for item in events)
        db_countries = Counter(row[5] or "UNASSIGNED" for row in db_rows.values())
        results[label] = {"original_unique_earthquake_ids": len(source_ids), "api_total": metadata["total"],
                          "api_unique_ids": len(api_ids), "stats_count": stats["count"], "db_unique_ids": len(db_rows),
                          "country_sum": sum(country_counts.values()), "country_counts": country_counts,
                          "api_country_counts_match_stats": dict(api_countries) == country_counts,
                          "db_country_counts_match_stats": dict(db_countries) == country_counts,
                          "original_missing_in_api": sorted(source_ids - api_ids),
                          "api_not_in_snapshot": sorted(api_ids - source_ids),
                          "api_not_in_db": sorted(api_ids - db_rows.keys()),
                          "db_not_in_api": sorted(db_rows.keys() - api_ids)}
        filtered_checks = {}
        for country in ("USA", "UNASSIGNED"):
            country_events, country_metadata = event_rows({**params, "country_id": country})
            country_stats = api("/api/estadisticas", {**params, "country_id": country})
            expected_country = country_counts.get(country, 0)
            assert len(country_events) == country_metadata["total"] == country_stats["count"] == expected_country
            filtered_checks[country] = expected_country
        results[label]["filtered_checks"] = filtered_checks
        results[label]["country_mismatched_ids"] = sorted(identifier for identifier in api_ids & db_rows.keys()
            if api_by_id[identifier]["properties"].get("country_id") != db_rows[identifier][5])
        assert len(api_ids) == metadata["total"] == stats["count"] == len(db_rows) == sum(country_counts.values())
        assert api_countries == db_countries == country_counts
        assert not results[label]["api_not_in_db"] and not results[label]["db_not_in_api"]
        assert not results[label]["country_mismatched_ids"]
    chosen = []
    for code, limit in (("USA", 3), ("CAN", 3), ("UNASSIGNED", 4)):
        candidates = [row for row in rows if (row[5] or "UNASSIGNED") == code]
        for row in candidates[:limit]:
            chosen.append({"event_id": row[0], "longitude": row[3], "latitude": row[4],
                           "country_id": row[5], "country_name": row[6], "status": row[7],
                           "reason": row[8], "source_response_id": row[9]})
    if not any(item["country_id"] == "CAN" for item in chosen):
        for row in docker_python(CANADA_CODE):
            chosen.append({"event_id": row[0], "longitude": row[1], "latitude": row[2],
                           "country_id": row[3], "country_name": row[4], "status": row[5],
                           "reason": row[6], "outside_audit_window": True})
    results["examples"] = docker_python(POLYGON_CODE, json.dumps(chosen))
    for item in results["examples"]:
        codes = [match["code"] for match in item["polygon_matches"]]
        assert (item["country_id"] in codes) if item["country_id"] else not codes, item
    original_usa = [source[identifier] for identifier, row in database.items() if identifier in source and row[5] == "USA"]
    results["usa_source_profile"] = {"count_in_snapshot_window": len(original_usa),
                                     "below_magnitude_4": sum((item["properties"].get("mag") or 0) < 4 for item in original_usa),
                                     "alaska_place_mentions": sum("Alaska" in (item["properties"].get("place") or "") for item in original_usa),
                                     "networks": dict(Counter(item["properties"].get("net") or "ND" for item in original_usa))}
    if write_result:
        (audit_dir / "audit-result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"original": results["original"],
                      "all": {key: value for key, value in results["all"].items() if key not in ("country_counts",)},
                      "mag_ge_4": {key: value for key, value in results["mag_ge_4"].items() if key not in ("country_counts",)},
                      "countries_all": results["all"]["country_counts"],
                      "countries_mag_ge_4": results["mag_ge_4"]["country_counts"],
                      "examples": results["examples"], "usa_source_profile": results["usa_source_profile"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, default=AUDIT)
    parser.add_argument("--start", default=START.isoformat())
    parser.add_argument("--end", default=END.isoformat())
    parser.add_argument("--write-result", action="store_true", help="Replace the saved result for this snapshot")
    arguments = parser.parse_args()
    window_start = datetime.fromisoformat(arguments.start)
    window_end = datetime.fromisoformat(arguments.end)
    if window_start.tzinfo is None or window_end.tzinfo is None or window_start >= window_end:
        parser.error("La ventana debe tener zona horaria y start < end")
    main(arguments.audit_dir, window_start, window_end, arguments.write_result)
