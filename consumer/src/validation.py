import math


def validate_live_event(feature: dict) -> tuple[bool, str]:
    if not isinstance(feature, dict):
        return False, "invalid_event"
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return False, "invalid_event_structure"
    coordinates = geometry.get("coordinates")
    if not isinstance(feature.get("id"), str) or not feature["id"]:
        return False, "missing_event_id"
    if properties.get("place") is not None and not isinstance(properties["place"], str):
        return False, "invalid_place"
    if not isinstance(properties.get("updated"), int) or isinstance(properties.get("updated"), bool):
        return False, "invalid_updated"
    if properties.get("type") != "earthquake":
        return False, "non_earthquake"
    if not isinstance(properties.get("time"), int) or isinstance(properties.get("time"), bool):
        return False, "invalid_event_time"
    if geometry.get("type") != "Point":
        return False, "invalid_geometry_type"
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return False, "missing_coordinates"
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in coordinates[:2]):
        return False, "invalid_coordinates"
    longitude = float(coordinates[0])
    latitude = float(coordinates[1])
    if not math.isfinite(longitude) or not math.isfinite(latitude) or not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        return False, "coordinates_out_of_range"
    for value, reason in ((properties.get("mag"), "invalid_magnitude"),
                          (coordinates[2] if len(coordinates) > 2 else None, "invalid_depth")):
        if value is not None:
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                return False, reason
    return True, ""
