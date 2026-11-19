"""Check compact live provenance, original integrity and legacy compatibility."""
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "producer" / "src"))
sys.path.insert(0, str(ROOT / "consumer" / "src"))
from event_model import build_live_event  # noqa: E402
import message_contract  # noqa: E402


with TemporaryDirectory() as temporary:
    root = Path(temporary).resolve()
    message_contract.ORIGINALS = root
    features = [{"type": "Feature", "id": f"test-{i}",
                 "properties": {"type": "earthquake", "updated": i, "time": i,
                                "place": "A long place name repeated across the feed"},
                 "geometry": {"type": "Point", "coordinates": [0, 0, 10]}}
                for i in range(100)]
    original = {"type": "FeatureCollection", "features": features}
    path = root / "response.json"
    path.write_text(json.dumps({"metadata": {}, "payload": original}), encoding="utf-8")
    message = build_live_event(features[0], "run-test", "response-test")
    message["provenance"].update({"original_reference": str(path),
                                  "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    compact_size = len(json.dumps(message).encode())
    assert message_contract.original_for(message) == original
    legacy = build_live_event(features[0], "run-test", "response-test")
    legacy["provenance"]["original"] = original
    assert message_contract.original_for(legacy) == original
    legacy_size = len(json.dumps(legacy).encode())
    message["provenance"]["original_sha256"] = "0" * 64
    try:
        message_contract.original_for(message)
    except ValueError as exc:
        assert str(exc) == "original_sha256_mismatch"
    else:
        raise AssertionError("Tampered original was accepted")
    print(json.dumps({"compact_bytes": compact_size, "legacy_bytes": legacy_size,
                      "reduction_percent": round(100 * (1 - compact_size / legacy_size), 1)}))
