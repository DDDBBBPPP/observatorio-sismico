import json
from pathlib import Path


class IngestionState:
    def __init__(self, path: Path):
        self.path = path
        self.values = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def has_version(self, event_id: str, updated: int) -> bool:
        return self.values.get(event_id) == updated

    def should_publish(self, event_id: str, updated: int) -> bool:
        latest = self.values.get(event_id)
        return latest is None or updated > latest

    def record_version(self, event_id: str, updated: int) -> None:
        self.values[event_id] = updated
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.values, indent=2) + "\n", encoding="utf-8")
