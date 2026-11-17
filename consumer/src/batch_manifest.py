"""Validate the downloaded USGS manifest before changing any database rows."""
import json
from datetime import datetime, timezone
from pathlib import Path


def validate_manifest(path: str) -> tuple[dict, list[dict], int]:
    manifest_path = Path(path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    filters = manifest.get("filters") or {}
    year = manifest.get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        raise ValueError("Año inválido en el manifiesto")
    if filters.get("minmagnitude") != 4 or filters.get("eventtype") != "earthquake" or filters.get("scope") != "world":
        raise ValueError("Filtros históricos incompatibles")
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    year_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    if filters.get("starttime") != year_start.isoformat().replace("+00:00", "Z") or filters.get("endtime") != year_end.isoformat().replace("+00:00", "Z"):
        raise ValueError("Periodo histórico incompatible")
    intervals = manifest.get("intervals")
    if not isinstance(intervals, list) or not intervals:
        raise ValueError("Manifiesto sin intervalos")
    ordered = sorted(intervals, key=lambda item: item["interval_start"])
    previous_end = year_start
    total = 0
    versions = {}
    for interval in ordered:
        start = datetime.fromisoformat(interval["interval_start"])
        end = datetime.fromisoformat(interval["interval_end"])
        if start != previous_end or not start < end or end > year_end:
            raise ValueError("Intervalos históricos incompletos o superpuestos")
        previous_end = end
        source = Path(interval["path"]).resolve()
        if not source.is_relative_to(manifest_path.parent):
            raise ValueError("Original fuera del directorio histórico")
        document = json.loads(source.read_text(encoding="utf-8"))
        features = document.get("payload", {}).get("features")
        count = interval.get("record_count")
        if not isinstance(features, list) or not isinstance(count, int) or count < 0 or len(features) != count:
            raise ValueError(f"Recuento incorrecto en {source}")
        metadata = document.get("metadata") or {}
        if metadata.get("record_count") != count or interval.get("metadata_count") != metadata.get("metadata_count"):
            raise ValueError(f"Metadatos incorrectos en {source}")
        for feature in features:
            properties = feature.get("properties") or {}
            identifier = feature.get("id")
            updated = properties.get("updated")
            if identifier and isinstance(updated, int) and not isinstance(updated, bool):
                versions[f"{identifier}:{updated}"] = {"interval_start": interval["interval_start"], "interval_end": interval["interval_end"]}
        total += count
    if previous_end != year_end:
        raise ValueError("El manifiesto no cubre el año completo")
    if manifest.get("versions") != versions:
        raise ValueError("Índice de versiones distinto de los originales")
    return manifest, ordered, total
