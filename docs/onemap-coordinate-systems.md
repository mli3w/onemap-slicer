# OneMap Coordinate Systems - Test Results

**Date:** 2026-01-26
**Test Method:** Browser automation (agent-browser) + API testing

## Overview

This document records the findings from investigating OneMap's 2D and 3D mapping systems to verify coordinate system mappings for STL file generation.

## Test Methodology

### Tools Used
- `agent-browser` for web UI exploration
- `curl` for API testing
- Python for coordinate conversion verification

### Test Locations
- Marina Bay Sands (Postal: 018971)
- Capital Tower (Postal: 068912)

---

## Coordinate Systems

OneMap uses three coordinate systems:

| System | EPSG Code | Format | Usage |
|--------|-----------|--------|-------|
| WGS84 | 4326 | Lat/Lon in degrees | Search API, user-facing coordinates |
| SVY21 | 3414 | X/Y in meters | Singapore local projected system |
| ECEF | - | X/Y/Z in meters | 3D tile RTC_CENTER values |

---

## Test Results

### 1. Search API Response

**Endpoint:** `https://www.onemap.gov.sg/api/common/elastic/search`

**Request:**
```
?searchVal=018971&returnGeom=Y&getAddrDetails=Y
```

**Response (Marina Bay Sands):**
```json
{
  "SEARCHVAL": "MARINA BAY SANDS",
  "ADDRESS": "1 BAYFRONT AVENUE MARINA BAY SANDS SINGAPORE 018971",
  "POSTAL": "018971",
  "X": "30791.9564761138",
  "Y": "29426.4935135301",
  "LATITUDE": "1.28239713771706",
  "LONGITUDE": "103.85840539166"
}
```

**Interpretation:**
- `X`, `Y`: SVY21 coordinates (meters, Easting/Northing)
- `LATITUDE`, `LONGITUDE`: WGS84 coordinates (degrees)

### 2. Coordinate Conversion API

**Requires:** `ONEMAP_ACCESS_TOKEN` in Authorization header

#### SVY21 to WGS84 (EPSG:3414 → EPSG:4326)

**Endpoint:** `https://www.onemap.gov.sg/api/common/convert/3414to4326`

**Request:**
```
?X=30791.9564761138&Y=29426.4935135301
```

**Response:**
```json
{
  "latitude": 1.2823971377170602,
  "longitude": 103.85840539165964
}
```

**Result:** Matches search API WGS84 values ✓

#### WGS84 to SVY21 (EPSG:4326 → EPSG:3414)

**Endpoint:** `https://www.onemap.gov.sg/api/common/convert/4326to3414`

**Request:**
```
?latitude=1.2823971377170602&longitude=103.85840539165964
```

**Response:**
```json
{
  "Y": 29426.493513530084,
  "X": 30791.95647611392
}
```

**Result:** Round-trip conversion accurate ✓

### 3. 3D Tileset Analysis

**Tileset URL:** `https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json`

#### Tileset Metadata
```json
{
  "asset": { "version": "1.0" },
  "geometricError": 1415.278047721736,
  "root": {
    "boundingVolume": {
      "region": [1.808261515600449, 0.020244349664616, 1.816148694181278, 0.025685831653167, 0, 288.5591944550538]
    },
    "refine": "ADD"
  }
}
```

#### Bounding Region (WGS84 radians → degrees)

| Bound | Radians | Degrees |
|-------|---------|---------|
| West | 1.8083 | 103.606° |
| East | 1.8161 | 104.058° |
| South | 0.0202 | 1.160° |
| North | 0.0257 | 1.472° |

**Coverage:** Entire Singapore island ✓

#### Refine Strategy
- Mode: `ADD` (additive)
- Implication: Parent AND child geometry must be collected at all levels

### 4. b3dm Tile Format

**Sample Tile:** `6/34/11_5.b3dm` (288,952 bytes)

#### Header Structure
```
Offset  Field                    Value
0-3     Magic                    "b3dm"
4-7     Version                  1
8-11    Byte Length              288,952
12-15   Feature Table JSON Len   92
16-19   Feature Table Bin Len    0
20-23   Batch Table JSON Len     21,584
24-27   Batch Table Bin Len      0
28+     Feature Table JSON       {"BATCH_LENGTH":111,"RTC_CENTER":[...]}
```

#### RTC_CENTER (ECEF coordinates)
```json
{
  "RTC_CENTER": [-1526387.24909381, 6191102.52657946, 144507.18179012]
}
```

#### ECEF to WGS84 Conversion
```
Input (ECEF):
  X: -1,526,387.25 m
  Y:  6,191,102.53 m
  Z:    144,507.18 m

Output (WGS84):
  Latitude:  1.306990°
  Longitude: 103.849797°
  Height:    ~0 m
```

**Result:** Converts to valid Singapore coordinates ✓

---

## 2D Map UI Analysis

### Rendering Stack
- **Library:** Leaflet 1.9.4
- **Tile Format:** PNG raster tiles
- **Tile URL Pattern:** `https://www.onemap.gov.sg/maps/tiles/{style}/{z}/{x}/{y}.png`

### Available Basemaps
- Default
- Original
- Grey
- Grey Lite
- Night
- Orthophoto
- Land Lot

### Land Query Feature
- Uses MK (Mukim) / TS (Town Subdivision) lot identifiers
- Based on SVY21 coordinate reference system

---

## 3D Map UI Analysis

### Rendering Stack
- **Library:** Cesium (loaded from `/cesium/`)
- **WebGL:** WebGL2
- **Tile Format:** Cesium 3D Tiles (b3dm)

### Features
- Shadow Analysis (time-of-day shadows)
- Window View (first-person from buildings)
- Field of View adjustment

### Tile Loading Pattern
```
https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/{level}/{x}/{y}_{z}.b3dm
```

---

## Coordinate Pipeline for STL Generation

```
┌─────────────────────────────────────────────────────────────┐
│ User Input                                                   │
│   Address / Postal Code / Polygon                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ Search API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ WGS84 (EPSG:4326)                                           │
│   Latitude/Longitude in degrees                             │
│   Example: lat=1.2824°, lon=103.8584°                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ Convert to radians for tile lookup
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3D Tileset Traversal                                        │
│   Bounding regions in WGS84 radians                         │
│   Find overlapping tiles (ADD refine = all levels)          │
└─────────────────────┬───────────────────────────────────────┘
                      │ Fetch b3dm tiles
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ ECEF + RTC                                                   │
│   RTC_CENTER: tile origin in ECEF meters                    │
│   Vertex positions: relative to RTC_CENTER                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Transform to common reference
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ ENU (East-North-Up)                                         │
│   Local tangent plane at reference point                    │
│   All tiles merged to same ENU origin                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ Rotate for 3D printing convention
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ STL Coordinates                                             │
│   X = East                                                  │
│   Y = Up                                                    │
│   Z = North                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Verification Summary

| Test | Status | Notes |
|------|--------|-------|
| Search API returns dual coords | ✓ | SVY21 (X,Y) + WGS84 (lat,lon) |
| SVY21 ↔ WGS84 conversion | ✓ | Requires auth token |
| Tileset bounds cover Singapore | ✓ | [103.61°, 104.06°] × [1.16°, 1.47°] |
| b3dm RTC_CENTER valid | ✓ | ECEF converts to Singapore coords |
| Tile refine mode | ✓ | ADD = collect all levels |
| Leaflet 2D rendering | ✓ | v1.9.4 |
| Cesium 3D rendering | ✓ | WebGL2 |

---

## Implementation Notes

### Codebase Alignment

The existing codebase correctly implements coordinate transformations:

| File | Purpose |
|------|---------|
| `shared/coordinates/wgs84-ecef.ts` | WGS84 ↔ ECEF conversion |
| `shared/coordinates/enu.ts` | ECEF ↔ ENU transformation |
| `server/onemap.ts` | Tile discovery using WGS84 radians |
| `server/b3dm-parser.ts` | Extracts RTC_CENTER from tiles |
| `server/geo-transform.ts` | Merges tiles to common ENU |

### API Authentication

The coordinate conversion API requires authentication:
```bash
curl -H "Authorization: $ONEMAP_ACCESS_TOKEN" \
  "https://www.onemap.gov.sg/api/common/convert/3414to4326?X=...&Y=..."
```

Token stored in `.env` as `ONEMAP_ACCESS_TOKEN`.
