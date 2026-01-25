"""OneMap API module for building search and tileset discovery."""

import json
import math
from pathlib import Path
from urllib.parse import urlencode

import requests
from platformdirs import user_cache_dir

# OneMap API endpoints
SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"
TILESET_URL = "https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json"

# Cache directory
CACHE_DIR = Path(user_cache_dir("onemap-slicer"))
TILESET_CACHE = CACHE_DIR / "tileset.json"
TILESET_ETAG = CACHE_DIR / "tileset.etag"


def search_buildings(query: str, max_results: int = 10) -> list[dict]:
    """
    Search for buildings by name, address, or postal code.

    Returns all matching results (up to max_results) with lat/lng coordinates.
    """
    params = {
        "searchVal": query,
        "returnGeom": "Y",
        "getAddrDetails": "Y",
        "pageNum": 1,
    }

    url = f"{SEARCH_URL}?{urlencode(params)}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()

    if data.get("found", 0) == 0:
        return []

    results = data.get("results", [])
    if not results:
        return []

    parsed_results = []
    for result in results[:max_results]:
        parsed_results.append(
            {
                "name": result.get("SEARCHVAL", query),
                "address": result.get("ADDRESS", ""),
                "postal": result.get("POSTAL", ""),
                "lat": float(result.get("LATITUDE", 0)),
                "lng": float(result.get("LONGITUDE", 0)),
            }
        )

    return parsed_results


def search_building(query: str, result_index: int = 0) -> dict | None:
    """
    Search for a building by name, address, or postal code.

    Returns the matching result at result_index (default: first result).
    """
    results = search_buildings(query)
    if not results:
        return None
    if result_index >= len(results):
        return None
    return results[result_index]


def load_tileset() -> dict:
    """Fetch and parse the root tileset.json with ETag caching."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    headers = {}
    cached_etag = None

    # Load cached ETag if available
    if TILESET_ETAG.exists():
        cached_etag = TILESET_ETAG.read_text().strip()
        headers["If-None-Match"] = cached_etag

    response = requests.get(TILESET_URL, headers=headers, timeout=30)

    # Return cached version if not modified
    if response.status_code == 304 and TILESET_CACHE.exists():
        return json.loads(TILESET_CACHE.read_text())

    response.raise_for_status()
    data = response.json()

    # Cache the response and ETag
    TILESET_CACHE.write_text(json.dumps(data))
    if etag := response.headers.get("etag"):
        TILESET_ETAG.write_text(etag)

    return data


def _haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two lat/lng points in meters."""
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _region_contains_point(region: list, lat: float, lng: float) -> bool:
    """
    Check if a bounding region contains a lat/lng point.

    Region format: [west, south, east, north, minHeight, maxHeight]
    """
    if len(region) < 4:
        return False

    west, south, east, north = region[:4]

    # Convert radians to degrees if needed (regions are in radians)
    if abs(west) < math.pi * 2 and abs(east) < math.pi * 2:
        west = math.degrees(west)
        south = math.degrees(south)
        east = math.degrees(east)
        north = math.degrees(north)

    return west <= lng <= east and south <= lat <= north


def _box_contains_point(box: list, lat: float, lng: float) -> bool:
    """
    Check if a bounding box contains a lat/lng point.

    Box is a 12-element array defining a oriented bounding box.
    For simplicity, we check if the point is within a rough bounding sphere.
    """
    # Box center is first 3 elements (ECEF coordinates)
    # For now, return True for valid boxes and let detailed matching happen later
    return len(box) >= 12


def _sphere_contains_point(sphere: list, lat: float, lng: float) -> bool:
    """
    Check if a bounding sphere likely contains a lat/lng point.

    Sphere format: [centerX, centerY, centerZ, radius] in ECEF
    """
    if len(sphere) < 4:
        return False

    # Convert lat/lng to ECEF
    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)
    R = 6378137  # WGS84 semi-major axis

    x = R * math.cos(lat_rad) * math.cos(lng_rad)
    y = R * math.cos(lat_rad) * math.sin(lng_rad)
    z = R * math.sin(lat_rad)

    # Check distance to sphere center
    cx, cy, cz, radius = sphere[:4]
    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)

    return dist <= radius * 1.5  # Add some margin


def _bounds_contain_point(bounds: dict, lat: float, lng: float) -> bool:
    """Check if any type of bounding volume contains the point."""
    if "region" in bounds:
        return _region_contains_point(bounds["region"], lat, lng)
    elif "box" in bounds:
        return _box_contains_point(bounds["box"], lat, lng)
    elif "sphere" in bounds:
        return _sphere_contains_point(bounds["sphere"], lat, lng)
    return True  # If no bounds, assume it might contain the point


def find_tiles(tileset: dict, lat: float, lng: float, base_url: str = None) -> list:
    """
    Traverse tileset tree and return matching tiles sorted by geometric error.

    Returns list of dicts with 'uri' and 'geometricError'.
    """
    if base_url is None:
        base_url = TILESET_URL.rsplit("/", 1)[0]

    matching_tiles = []

    def traverse(node: dict, current_base: str):
        bounds = node.get("boundingVolume", {})

        # Check if this node's bounds contain our point
        if not _bounds_contain_point(bounds, lat, lng):
            return

        # If this node has content, add it
        content = node.get("content", {})
        if "uri" in content or "url" in content:
            uri = content.get("uri") or content.get("url")

            # Handle relative URIs
            if not uri.startswith("http"):
                uri = f"{current_base}/{uri}"

            # Check if this is a nested tileset.json
            if uri.endswith(".json"):
                # Load nested tileset
                try:
                    nested_response = requests.get(uri, timeout=30)
                    nested_response.raise_for_status()
                    nested_tileset = nested_response.json()
                    nested_base = uri.rsplit("/", 1)[0]

                    if "root" in nested_tileset:
                        traverse(nested_tileset["root"], nested_base)
                except Exception:
                    pass
            else:
                matching_tiles.append(
                    {
                        "uri": uri,
                        "geometricError": node.get("geometricError", 0),
                    }
                )

        # Traverse children
        for child in node.get("children", []):
            traverse(child, current_base)

    root = tileset.get("root", {})
    traverse(root, base_url)

    def tile_sort_key(tile):
        # Primary: geometric error (lower = higher detail)
        error = tile["geometricError"]
        # Secondary: directory depth (higher = more specific tile)
        # Extract directory number from URI like ".../79/9_0.b3dm" -> 79
        try:
            parts = tile["uri"].split("/")
            dir_num = int(parts[-2])
        except (IndexError, ValueError):
            dir_num = 0
        # Negate dir_num so higher numbers sort first
        return (error, -dir_num)

    matching_tiles.sort(key=tile_sort_key)

    return matching_tiles


def get_tile_data(uri: str) -> bytes:
    """Download tile data (B3DM file)."""
    response = requests.get(uri, timeout=60)
    response.raise_for_status()
    return response.content
