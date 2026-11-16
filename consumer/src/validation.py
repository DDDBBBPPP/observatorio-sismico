import math


def validate_live_event(feature: dict) -> tuple[bool, str]:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if not feature.get("id"):
        return False, "missing_event_id"
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
    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
    except (TypeError, ValueError):
        return False, "invalid_coordinates"
    if not math.isfinite(longitude) or not math.isfinite(latitude) or not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        return False, "coordinates_out_of_range"
    for value, reason in ((properties.get("mag"), "invalid_magnitude"),
                          (coordinates[2] if len(coordinates) > 2 else None, "invalid_depth")):
        if value is not None:
            try:
                if not math.isfinite(float(value)):
                    return False, reason
            except (TypeError, ValueError):
                return False, reason
    return True, ""
