"""Freeze the latest saved USGS all_day response and its exact 24 h UTC window."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/002-ingesta-usgs-persistencia"


def main(destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    state = json.loads((EVIDENCE / "latest-live-fetch.json").read_text(encoding="utf-8"))
    source = EVIDENCE / "originals" / state["run_id"] / "response.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    target = destination / "all_day.geojson"
    target.write_text(json.dumps(document["payload"], ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    end = datetime.fromisoformat(state["received_at"])
    result = {"run_id": state["run_id"], "received_at": state["received_at"],
              "metadata": document["metadata"], "source_response_path": str(source),
              "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "window_start": (end - timedelta(hours=24)).isoformat(),
              "window_end": end.isoformat()}
    (destination / "source-metadata.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(main(arguments.destination), ensure_ascii=False))
