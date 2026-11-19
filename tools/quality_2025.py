"""Reproduce recuentos anteriores a la transformación en los 12 originales USGS."""
import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json").read_text(encoding="utf-8"))
counts = Counter()
versions = set()
for interval in manifest["intervals"]:
    local_path = root / "evidence" / interval["path"].removeprefix("/evidence/")
    features = json.loads(local_path.read_text(encoding="utf-8"))["payload"]["features"]
    assert len(features) == interval["record_count"]
    for feature in features:
        p = feature.get("properties") or {}
        c = (feature.get("geometry") or {}).get("coordinates") or []
        counts["raw"] += 1
        counts["null_mag"] += p.get("mag") is None
        counts["null_depth"] += len(c) < 3 or c[2] is None
        counts["non_earthquake"] += p.get("type") != "earthquake"
        counts["below_mag4"] += p.get("mag") is not None and p["mag"] < 4
        counts["invalid_coordinates"] += (len(c) < 2 or not isinstance(c[0], (int, float)) or not isinstance(c[1], (int, float)) or not -180 <= c[0] <= 180 or not -90 <= c[1] <= 90)
        key = (feature.get("id"), p.get("updated"))
        counts["duplicate_version"] += key in versions
        versions.add(key)
print(json.dumps(dict(counts), sort_keys=True))
