import os
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point


class CountryCatalog:
    """Assign WGS84 points using boundary-inclusive catalog matching."""

    def __init__(self) -> None:
        path = Path(os.environ.get("COUNTRY_CATALOG_PATH", "/app/catalog/paises.geojson"))
        self.frame = gpd.read_file(path).to_crs("EPSG:4326")

    def assign(self, longitude: float, latitude: float) -> dict:
        point = Point(longitude, latitude)
        candidate_indexes = self.frame.sindex.query(point, predicate="intersects")
        candidates = self.frame.iloc[candidate_indexes]
        # covers includes points on borders; stable sorting makes overlaps
        # deterministic and preserves the multiple-match reason.
        matches = candidates[candidates.geometry.covers(point)]
        if matches.empty:
            return {
                "country_id": None,
                "country_name": None,
                "status": "unassigned",
                "reason": "no_catalog_match",
            }
        matches = matches.sort_values("ADM0_A3")
        row = matches.iloc[0]
        return {
            "country_id": row["ADM0_A3"],
            "country_name": row["NAME"],
            "status": "multiple_matches" if len(matches) > 1 else "assigned",
            "reason": "boundary_multiple_matches" if len(matches) > 1 else "point_covers_country",
        }
