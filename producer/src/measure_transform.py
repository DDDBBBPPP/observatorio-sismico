"""Measure only the in-memory live type/version filter, excluding Docker startup and I/O."""
import json
import statistics
import time
import tracemalloc
from pathlib import Path

from live_ingest import new_earthquakes


class EmptyState:
    def should_publish(self, event_id: str, updated: int) -> bool:
        return True


source = Path("/evidence/002-ingesta-usgs-persistencia/historical/minmag4-earthquake/2025-01-01T000000+0000/response.json")
features = json.loads(source.read_text(encoding="utf-8"))["payload"]["features"]
for size in (100, 500, 1000):
    sample = {"features": features[:size]}
    measurements = []
    peaks = []
    for _ in range(5):
        tracemalloc.start()
        start = time.perf_counter()
        output, excluded = new_earthquakes(sample, EmptyState())
        measurements.append((time.perf_counter() - start) * 1000)
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        assert len(output) + excluded == size
    print(json.dumps({"features": size, "median_ms": round(statistics.median(measurements), 3), "peak_python_kib": round(max(peaks) / 1024, 1)}), flush=True)
