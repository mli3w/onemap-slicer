# OneMap 3D Technical Specification

Research conducted: 2026-01-26

## Overview

OneMap (onemap.gov.sg) is Singapore's authoritative national map platform operated by SLA (Singapore Land Authority). It provides both 2D and 3D map visualization of Singapore, including detailed 3D building models.

## 2D Map System

### Tile Service

- **Base URL**: `https://www.onemap.gov.sg/maps/tiles/`
- **Tile Format**: PNG images
- **Tile Scheme**: XYZ (Slippy map tilenames)

### Tile URL Patterns

```
Standard:  https://www.onemap.gov.sg/maps/tiles/Default/{z}/{x}/{y}.png
HD:        https://www.onemap.gov.sg/maps/tiles/Default_HD/{z}/{x}/{y}.png
```

### Example

```bash
# Zoom 18, Marina Bay area
curl "https://www.onemap.gov.sg/maps/tiles/Default/18/206697/130135.png" -o tile.png
```

## 3D Map System

### Technology Stack

| Component | Technology |
|-----------|------------|
| 3D Engine | CesiumJS |
| Tile Format | OGC 3D Tiles 1.0 |
| Model Format | B3DM (Batched 3D Model) |
| Geometry Format | glTF 2.0 (binary GLB) |
| Compression | Draco mesh compression |
| Terrain | Cesium Ion terrain service |

### 3D Tiles Endpoint

```
Tileset Index: https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json
Tile Pattern:  https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/{level}/{x}/{y}_{lod}.b3dm
```

### Tile Hierarchy (LOD - Level of Detail)

| Level | Coverage | Geometric Error | Use Case |
|-------|----------|-----------------|----------|
| 3-4 | ~1km | 500-700 | Regional overview |
| 5-6 | ~200m | 150-350 | City view |
| 7+ | ~50m | 4-70 | Close-up, high detail |

Lower geometric error = higher detail geometry (better for 3D printing).

## B3DM File Format

B3DM (Batched 3D Model) is Cesium's format for streaming 3D building data.

### File Structure

```
Offset  Size    Field
------  ----    -----
0       4       Magic ("b3dm")
4       4       Version (1)
8       4       Total byte length
12      4       Feature table JSON length
16      4       Feature table binary length
20      4       Batch table JSON length
24      4       Batch table binary length
28      var     Feature table JSON
...     var     Feature table binary
...     var     Batch table JSON
...     var     Batch table binary
...     var     Embedded glTF (GLB binary)
```

### Feature Table

Contains per-tile metadata:

```json
{
  "BATCH_LENGTH": 22,
  "RTC_CENTER": [-1526497.04, 6191131.12, 142118.41]
}
```

- `BATCH_LENGTH`: Number of buildings in the tile
- `RTC_CENTER`: Relative-to-center coordinates for precision

### Batch Table

Contains per-building metadata as parallel arrays:

```json
{
  "gml:name": ["UOB PLAZA", "OCBC CENTRE", ...],
  "gml:id": ["SLA_BLDG2_9274f3a4-...", ...],
  "Height": [280.08, 197.3, ...],
  "bldg:storeysaboveground": [93, 66, ...],
  "Latitude": [1.2853, 1.2852, ...],
  "Longitude": [103.8506, 103.8492, ...],
  "bldg:class": ["3000", "3000", ...],
  "bldg:function": ["1150", "1150", ...],
  "bldg:usage": ["2270", "2270", ...],
  "bldg:measuredheight": [280.084, 197.3, ...],
  "core:creationdate": ["2025-06-08", ...]
}
```

### Embedded glTF

The glTF model uses:

- **Version**: glTF 2.0
- **Format**: Binary GLB
- **Extensions**: `KHR_draco_mesh_compression` (required)
- **Attributes**: `POSITION`, `NORMAL`, `TEXCOORD_0`, `_BATCHID`

The `_BATCHID` attribute links mesh vertices to buildings in the batch table.

## Search API

### Endpoint

```
GET https://www.onemap.gov.sg/omapi/ss/search
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| searchVal | Search query (building name, address, postal code) |
| returnGeom | Return geometry (Y/N) |
| getAddrDetails | Return address details (Y/N) |
| pageNum | Page number for pagination |

### Example Request

```bash
curl "https://www.onemap.gov.sg/omapi/ss/search?searchVal=Marina+Bay+Sands&returnGeom=Y&getAddrDetails=Y&pageNum=1"
```

### Response Format

```json
{
  "found": 14,
  "totalNumPages": 2,
  "pageNum": 1,
  "results": [
    {
      "SEARCHVAL": "MARINA BAY SANDS",
      "BLK_NO": "1",
      "ROAD_NAME": "BAYFRONT AVENUE",
      "BUILDING": "MARINA BAY SANDS",
      "ADDRESS": "1 BAYFRONT AVENUE MARINA BAY SANDS SINGAPORE 018971",
      "POSTAL": "018971",
      "X": "31059.46",
      "Y": "29543.38",
      "LATITUDE": "1.28345419690844",
      "LONGITUDE": "103.860809048956"
    }
  ]
}
```

Note: X/Y coordinates are in SVY21 projection (Singapore's local coordinate system).

## Coordinate Systems

| System | Description | Usage |
|--------|-------------|-------|
| WGS84 | Latitude/Longitude | Search API results, batch table |
| SVY21 | Singapore local projection | X/Y in search results |
| ECEF | Earth-Centered, Earth-Fixed | RTC_CENTER in feature table |
| Radians | Angular measure | Bounding volumes in tileset.json |

## Sample Buildings Discovered

| Building | Height | Storeys | Tile |
|----------|--------|---------|------|
| UOB Plaza | 280.1m | 93 | 6/38/5_3.b3dm |
| Raffles City Tower | 226.7m | 76 | 6/38/6_4.b3dm |
| OCBC Centre | 197.3m | 66 | 6/37/5_4.b3dm |
| Tower 2 (MBS) | 181.0m | 61 | 7/79/9_2.b3dm |
| Tower 3 (MBS) | 183.4m | 61 | 6/39/5_4.b3dm |
| ArtScience Museum | 60.4m | 20 | 6/39/5_4.b3dm |
| MBS Casino | 45.2m | 15 | 7/79/9_2.b3dm |

## Building Classification Codes

Based on CityGML standard:

| Field | Example | Meaning |
|-------|---------|---------|
| bldg:class | 3000 | Commercial/Office |
| bldg:function | 1150 | Specific function code |
| bldg:usage | 2270 | Usage category |

## API Rate Limits & Terms

- No explicit rate limits documented
- Data is copyrighted by SLA
- Check [Terms of Use](https://www.onemap.gov.sg/termsofuse) for commercial usage
- Map Data copyright 2026 SLA

## References

- [OneMap Official Site](https://www.onemap.gov.sg)
- [OneMap 3D View](https://www.onemap.gov.sg/3d)
- [CesiumJS Documentation](https://cesium.com/learn/cesiumjs/ref-doc/)
- [3D Tiles Specification](https://github.com/CesiumGS/3d-tiles)
- [glTF 2.0 Specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- [Draco Compression](https://google.github.io/draco/)
