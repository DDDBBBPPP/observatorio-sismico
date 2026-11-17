"""A manifest with one valid interval proves the batch has no fixed counts."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "consumer" / "src"))
from batch_manifest import validate_manifest  # noqa: E402


with TemporaryDirectory() as temporary:
    root = Path(temporary)
    response = root / "response.json"
    response.write_text(json.dumps({"metadata": {"record_count": 0, "metadata_count": 0},
                                    "payload": {"features": []}}), encoding="utf-8")
    manifest = {"year": 2025,
                "filters": {"scope": "world", "minmagnitude": 4,
                            "eventtype": "earthquake", "starttime": "2025-01-01T00:00:00Z",
                            "endtime": "2026-01-01T00:00:00Z"},
                "intervals": [{"interval_start": "2025-01-01T00:00:00+00:00",
                               "interval_end": "2026-01-01T00:00:00+00:00",
                               "record_count": 0, "metadata_count": 0,
                               "path": str(response)}], "versions": {}}
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    _, intervals, total = validate_manifest(str(path))
    assert len(intervals) == 1 and total == 0
    manifest["intervals"][0]["record_count"] = 1
    path.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        validate_manifest(str(path))
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid count accepted")
    print("manifest validation: one interval accepted, false count rejected")
