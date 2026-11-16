from ingestion_state import IngestionState


def new_earthquakes(payload: dict, state: IngestionState) -> tuple[list[dict], int]:
    events = []
    excluded = 0
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        if properties.get("type") != "earthquake":
            excluded += 1
            continue
        event_id = feature.get("id")
        updated = properties.get("updated")
        if not event_id or not isinstance(updated, int):
            excluded += 1
            continue
        if not state.should_publish(event_id, updated):
            continue
        events.append(feature)
    return events, excluded
