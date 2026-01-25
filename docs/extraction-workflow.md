# Building Extraction Workflow for 3D Printing

Guide to extracting 3D building models from OneMap for 3D printing (STL/3MF).

## Overview

```
Search Building → Get Coordinates → Find Tile → Download B3DM → Extract glTF → Decompress Draco → Isolate Building → Convert to STL
```

## Step 1: Search for Building

```bash
curl "https://www.onemap.gov.sg/omapi/ss/search?searchVal=Marina+Bay+Sands&returnGeom=Y&getAddrDetails=Y" | jq
```

Extract latitude and longitude from results.

## Step 2: Find Containing Tile

Parse `tileset.json` to find tiles containing the coordinates:

```python
import json
import math
import urllib.request

def find_tiles_for_building(lat, lng):
    """Find all 3D tiles containing a lat/lng coordinate."""

    tileset_url = "https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/tileset.json"

    with urllib.request.urlopen(tileset_url) as response:
        tileset = json.load(response)

    lat_rad = math.radians(lat)
    lng_rad = math.radians(lng)

    def point_in_region(lat_rad, lng_rad, region):
        west, south, east, north = region[0], region[1], region[2], region[3]
        return west <= lng_rad <= east and south <= lat_rad <= north

    def find_tiles(node, path="root"):
        tiles = []
        if 'boundingVolume' in node and 'region' in node['boundingVolume']:
            region = node['boundingVolume']['region']
            if point_in_region(lat_rad, lng_rad, region):
                if 'content' in node:
                    tiles.append({
                        'uri': node['content']['uri'],
                        'geometricError': node.get('geometricError', 0)
                    })
                for i, child in enumerate(node.get('children', [])):
                    tiles.extend(find_tiles(child, f"{path}/child{i}"))
        return tiles

    return find_tiles(tileset['root'])

# Example: Find MBS tiles
tiles = find_tiles_for_building(1.2844, 103.8610)
# Sort by geometric error (lowest = highest detail)
tiles.sort(key=lambda x: x['geometricError'])
print(tiles[0])  # Highest detail tile
```

## Step 3: Download B3DM Tile

```python
import urllib.request

base_url = "https://www.onemap.gov.sg/omapi/tilesets/sg_noterrain_tiles/"
tile_uri = "7/79/9_2.b3dm"  # High-detail MBS tile

urllib.request.urlretrieve(base_url + tile_uri, "building.b3dm")
```

## Step 4: Extract glTF from B3DM

```python
import struct
import json

def extract_gltf_from_b3dm(b3dm_path, output_glb_path):
    """Extract embedded glTF from B3DM file."""

    with open(b3dm_path, 'rb') as f:
        # Parse header
        magic = f.read(4).decode('ascii')
        assert magic == 'b3dm', f"Invalid B3DM magic: {magic}"

        version = struct.unpack('<I', f.read(4))[0]
        byte_length = struct.unpack('<I', f.read(4))[0]
        feature_table_json_len = struct.unpack('<I', f.read(4))[0]
        feature_table_bin_len = struct.unpack('<I', f.read(4))[0]
        batch_table_json_len = struct.unpack('<I', f.read(4))[0]
        batch_table_bin_len = struct.unpack('<I', f.read(4))[0]

        # Calculate glTF offset
        gltf_offset = (28 + feature_table_json_len + feature_table_bin_len +
                       batch_table_json_len + batch_table_bin_len)

        # Extract glTF
        f.seek(gltf_offset)
        gltf_data = f.read()

        with open(output_glb_path, 'wb') as gf:
            gf.write(gltf_data)

        return gltf_offset, len(gltf_data)

def get_building_metadata(b3dm_path):
    """Extract building metadata from B3DM batch table."""

    with open(b3dm_path, 'rb') as f:
        # Skip to batch table
        f.seek(12)  # Skip magic, version, byte_length
        feature_table_json_len = struct.unpack('<I', f.read(4))[0]
        feature_table_bin_len = struct.unpack('<I', f.read(4))[0]
        batch_table_json_len = struct.unpack('<I', f.read(4))[0]

        f.seek(28 + feature_table_json_len + feature_table_bin_len)
        batch_table_json = f.read(batch_table_json_len).decode('utf-8').strip('\x00')

        return json.loads(batch_table_json)

# Usage
extract_gltf_from_b3dm("building.b3dm", "building.glb")
metadata = get_building_metadata("building.b3dm")
print(metadata['gml:name'])  # List of building names
```

## Step 5: Decompress Draco

The glTF uses Draco compression and must be decompressed before further processing.

### Option A: gltf-transform (Node.js)

```bash
npx @gltf-transform/cli draco decompress building.glb building_decompressed.glb
```

### Option B: Blender Python

```python
import bpy

# Import GLB
bpy.ops.import_scene.gltf(filepath="building.glb")

# Export without Draco
bpy.ops.export_scene.gltf(
    filepath="building_decompressed.glb",
    export_format='GLB',
    export_draco_mesh_compression_enable=False
)
```

### Option C: Python with pygltflib + DracoPy

```python
import pygltflib
import DracoPy

# Load glTF
gltf = pygltflib.GLTF2().load("building.glb")

# Decompress Draco meshes
for mesh in gltf.meshes:
    for primitive in mesh.primitives:
        if primitive.extensions and 'KHR_draco_mesh_compression' in primitive.extensions:
            # Decompress using DracoPy
            draco_data = primitive.extensions['KHR_draco_mesh_compression']
            # ... decompression logic
```

## Step 6: Isolate Specific Building

Each vertex has a `_BATCHID` attribute linking it to a building in the batch table.

```python
import numpy as np
from pygltflib import GLTF2

def isolate_building(glb_path, building_index, output_path):
    """Extract a single building by batch ID."""

    gltf = GLTF2().load(glb_path)

    for mesh in gltf.meshes:
        for primitive in mesh.primitives:
            # Get _BATCHID accessor
            batch_id_accessor_idx = primitive.attributes._BATCHID
            accessor = gltf.accessors[batch_id_accessor_idx]

            # Read batch IDs
            buffer_view = gltf.bufferViews[accessor.bufferView]
            buffer = gltf.buffers[buffer_view.buffer]
            # ... extract and filter vertices where batch_id == building_index

    # Save filtered mesh
    gltf.save(output_path)
```

## Step 7: Convert to STL/3MF

### Option A: Blender

```python
import bpy

# Import decompressed GLB
bpy.ops.import_scene.gltf(filepath="building_decompressed.glb")

# Select all meshes
bpy.ops.object.select_all(action='SELECT')

# Export as STL
bpy.ops.export_mesh.stl(filepath="building.stl")

# Or export as 3MF
bpy.ops.export_mesh.threemf(filepath="building.3mf")
```

### Option B: trimesh (Python)

```python
import trimesh

# Load GLB
scene = trimesh.load("building_decompressed.glb")

# Combine all meshes
if isinstance(scene, trimesh.Scene):
    mesh = trimesh.util.concatenate(scene.dump())
else:
    mesh = scene

# Export STL
mesh.export("building.stl")

# Export 3MF
mesh.export("building.3mf")
```

## Step 8: Prepare for Printing

```python
import trimesh

mesh = trimesh.load("building.stl")

# Scale to printable size (e.g., 1:1000 scale)
scale_factor = 0.001  # 280m building → 28cm print
mesh.apply_scale(scale_factor)

# Center on build plate
mesh.vertices -= mesh.centroid

# Ensure watertight
if not mesh.is_watertight:
    trimesh.repair.fix_normals(mesh)
    trimesh.repair.fill_holes(mesh)

# Export final
mesh.export("building_printable.stl")
```

## Complete Pipeline Script

```python
#!/usr/bin/env python3
"""
OneMap Building Extractor for 3D Printing
"""

import struct
import json
import urllib.request
import math
import subprocess
import tempfile
import os

class OneMapExtractor:
    BASE_URL = "https://www.onemap.gov.sg/omapi/"

    def search_building(self, query):
        """Search for a building by name."""
        url = f"{self.BASE_URL}ss/search?searchVal={query}&returnGeom=Y&getAddrDetails=Y"
        with urllib.request.urlopen(url) as response:
            return json.load(response)

    def find_tiles(self, lat, lng):
        """Find 3D tiles containing coordinates."""
        url = f"{self.BASE_URL}tilesets/sg_noterrain_tiles/tileset.json"
        with urllib.request.urlopen(url) as response:
            tileset = json.load(response)

        lat_rad, lng_rad = math.radians(lat), math.radians(lng)

        def search(node):
            tiles = []
            if 'boundingVolume' in node and 'region' in node['boundingVolume']:
                r = node['boundingVolume']['region']
                if r[0] <= lng_rad <= r[2] and r[1] <= lat_rad <= r[3]:
                    if 'content' in node:
                        tiles.append((node['content']['uri'], node.get('geometricError', 0)))
                    for child in node.get('children', []):
                        tiles.extend(search(child))
            return tiles

        return sorted(search(tileset['root']), key=lambda x: x[1])

    def download_tile(self, tile_uri, output_path):
        """Download a B3DM tile."""
        url = f"{self.BASE_URL}tilesets/sg_noterrain_tiles/{tile_uri}"
        urllib.request.urlretrieve(url, output_path)

    def extract_glb(self, b3dm_path, glb_path):
        """Extract glTF from B3DM."""
        with open(b3dm_path, 'rb') as f:
            f.seek(12)
            ftjl = struct.unpack('<I', f.read(4))[0]
            ftbl = struct.unpack('<I', f.read(4))[0]
            btjl = struct.unpack('<I', f.read(4))[0]
            btbl = struct.unpack('<I', f.read(4))[0]

            f.seek(28 + ftjl + ftbl + btjl + btbl)
            with open(glb_path, 'wb') as out:
                out.write(f.read())

    def get_metadata(self, b3dm_path):
        """Get building metadata from B3DM."""
        with open(b3dm_path, 'rb') as f:
            f.seek(12)
            ftjl = struct.unpack('<I', f.read(4))[0]
            ftbl = struct.unpack('<I', f.read(4))[0]
            btjl = struct.unpack('<I', f.read(4))[0]

            f.seek(28 + ftjl + ftbl)
            return json.loads(f.read(btjl).decode('utf-8').strip('\x00'))

# Usage
if __name__ == "__main__":
    extractor = OneMapExtractor()

    # 1. Search
    results = extractor.search_building("Marina Bay Sands")
    building = results['results'][0]
    lat, lng = float(building['LATITUDE']), float(building['LONGITUDE'])

    # 2. Find best tile
    tiles = extractor.find_tiles(lat, lng)
    best_tile = tiles[0][0]  # Lowest geometric error

    # 3. Download
    extractor.download_tile(best_tile, "building.b3dm")

    # 4. Extract
    extractor.extract_glb("building.b3dm", "building.glb")

    # 5. Get metadata
    meta = extractor.get_metadata("building.b3dm")
    print("Buildings in tile:", meta['gml:name'])
```

## Dependencies

```
# Python packages
pip install pygltflib trimesh numpy

# Node.js tools
npm install -g @gltf-transform/cli

# Or use Blender (free, includes all needed functionality)
# https://www.blender.org/download/
```

## Troubleshooting

### "KHR_draco_mesh_compression required"
The glTF requires Draco decompression. Use gltf-transform or Blender to decompress first.

### Missing buildings in extracted mesh
Buildings are batched by `_BATCHID`. Ensure you're filtering by the correct batch index from the metadata.

### Mesh not watertight
Use `trimesh.repair.fill_holes()` or Blender's "Make Manifold" feature before printing.

### Scale issues
OneMap uses real-world meters. Apply appropriate scale factor (e.g., 1:1000) for printing.

## Advanced: Multi-Tile Building Extraction

Some building complexes (like Suntec City) span multiple tiles. This section documents how to extract and combine buildings from different tiles.

### The Problem

Large building complexes may be split across tile boundaries. For example, Suntec City's 5 towers are distributed across 2 different tiles:

| Tile | Buildings |
|------|-----------|
| Tile 1 (search: "Suntec City") | Tower One, Tower Five |
| Tile 2 (search: "Suntec Tower Two") | Tower Two, Tower Three, Tower Four |

### Solution: Extract by gml:id

Each building in a tile has a unique `gml:id` in the batch table metadata. This ID appears in the GLB geometry names, allowing us to extract specific buildings.

#### Step 1: Identify Building IDs

First, get the `gml:id` for each target building from the batch table:

```python
from onemap_slicer.onemap_api import search_buildings, load_tileset, find_tiles, get_tile_data
from onemap_slicer.b3dm_parser import parse_header, extract_metadata, get_building_names

def get_building_ids(query, result_index=0):
    """Get gml:id for all buildings in a tile."""
    results = search_buildings(query)
    location = results[result_index]

    tileset = load_tileset()
    tiles = find_tiles(tileset, location['lat'], location['lng'])
    tile_data = get_tile_data(tiles[0]['uri'])

    header = parse_header(tile_data)
    metadata = extract_metadata(tile_data, header)
    batch_table = metadata.get('batch_table', {})

    names = get_building_names(metadata)
    gml_ids = batch_table.get('gml:id', [])

    return list(zip(names, gml_ids))

# Example: Find Suntec towers in each tile
print("Tile 1 (Suntec City):")
for name, gml_id in get_building_ids("Suntec City", result_index=1):
    if name and 'SUNTEC' in name.upper():
        print(f"  {name}: {gml_id}")

print("\nTile 2 (Suntec Tower Two):")
for name, gml_id in get_building_ids("Suntec Tower Two", result_index=0):
    if name and 'SUNTEC' in name.upper():
        print(f"  {name}: {gml_id}")
```

Output:
```
Tile 1 (Suntec City):
  SUNTEC TOWER ONE: SLA_BLDG2_04d573f1-aed4-471d-bfa4-759ecdec771b
  SUNTEC TOWER FIVE: SLA_BLDG2_1a2bd984-a7d6-4a5a-b553-db591b97b36b

Tile 2 (Suntec Tower Two):
  SUNTEC TOWER TWO: SLA_BLDG2_e8d3e6df-4f2f-4be4-9adb-2e7c5e958b77
  SUNTEC TOWER THREE: SLA_BLDG2_da2bc05d-fea0-4a97-a1fa-42711a3b7f20
  SUNTEC TOWER FOUR: SLA_BLDG2_bdf8a43d-df18-4111-a7a8-55e83260fd96
```

#### Step 2: Extract Buildings by gml:id

The `gml:id` appears in GLB geometry names (e.g., `Batched_Building_SLA_BLDG2_04d573f1-...Mesh`). Filter geometries by matching these IDs:

```python
import trimesh
import tempfile
import os
import numpy as np

from onemap_slicer.b3dm_parser import parse_header, extract_glb
from onemap_slicer.mesh_processor import decompress_draco

def extract_buildings_by_id(query, result_index, target_gml_ids):
    """Extract specific buildings from a tile by their gml:id."""
    results = search_buildings(query)
    location = results[result_index]

    tileset = load_tileset()
    tiles = find_tiles(tileset, location['lat'], location['lng'])
    tile_data = get_tile_data(tiles[0]['uri'])

    header = parse_header(tile_data)
    glb_data = extract_glb(tile_data, header)

    with tempfile.TemporaryDirectory() as tmpdir:
        glb_path = os.path.join(tmpdir, "tile.glb")
        decompressed_path = os.path.join(tmpdir, "tile_decompressed.glb")

        with open(glb_path, 'wb') as f:
            f.write(glb_data)

        result_path = decompress_draco(glb_path, decompressed_path)
        scene = trimesh.load(result_path)

        extracted = []
        for geom_name, geom in scene.geometry.items():
            for gml_id in target_gml_ids:
                if gml_id in geom_name:
                    extracted.append(geom)
                    break

        return extracted
```

#### Step 3: Combine and Export

```python
# Define target buildings
suntec_tower_ids = {
    # Tile 1
    "SLA_BLDG2_04d573f1-aed4-471d-bfa4-759ecdec771b",  # Tower One
    "SLA_BLDG2_1a2bd984-a7d6-4a5a-b553-db591b97b36b",  # Tower Five
    # Tile 2
    "SLA_BLDG2_e8d3e6df-4f2f-4be4-9adb-2e7c5e958b77",  # Tower Two
    "SLA_BLDG2_da2bc05d-fea0-4a97-a1fa-42711a3b7f20",  # Tower Three
    "SLA_BLDG2_bdf8a43d-df18-4111-a7a8-55e83260fd96",  # Tower Four
}

# Extract from both tiles
all_meshes = []
all_meshes.extend(extract_buildings_by_id("Suntec City", 1, suntec_tower_ids))
all_meshes.extend(extract_buildings_by_id("Suntec Tower Two", 0, suntec_tower_ids))

# Combine meshes
combined = trimesh.util.concatenate(all_meshes)

# Prepare for printing (scale 1:1000, center on build plate)
scale = 0.001
combined.apply_scale(scale)

bounds = combined.bounds
center_xy = (bounds[0][:2] + bounds[1][:2]) / 2
min_z = bounds[0][2]
combined.apply_translation([-center_xy[0], -center_xy[1], -min_z])

# Export
combined.export("suntec_5_towers.3mf")
```

### Complete Multi-Tile Extraction Script

```python
#!/usr/bin/env python3
"""
Extract buildings spanning multiple tiles.

Example: Extract all 5 Suntec City towers.
"""

import tempfile
import os
import trimesh
import numpy as np

from onemap_slicer.onemap_api import search_buildings, load_tileset, find_tiles, get_tile_data
from onemap_slicer.b3dm_parser import parse_header, extract_glb, extract_metadata, get_building_names
from onemap_slicer.mesh_processor import decompress_draco


def find_building_gml_ids(query, result_index, name_filter):
    """Find gml:ids for buildings matching a name filter."""
    results = search_buildings(query)
    location = results[result_index]

    tileset = load_tileset()
    tiles = find_tiles(tileset, location['lat'], location['lng'])
    tile_data = get_tile_data(tiles[0]['uri'])

    header = parse_header(tile_data)
    metadata = extract_metadata(tile_data, header)
    batch_table = metadata.get('batch_table', {})

    names = get_building_names(metadata)
    gml_ids = batch_table.get('gml:id', [])

    matching = {}
    for i, name in enumerate(names):
        if name and name_filter(name) and i < len(gml_ids):
            matching[gml_ids[i]] = name

    return matching


def extract_meshes_by_gml_id(query, result_index, target_ids):
    """Extract geometries matching target gml:ids."""
    results = search_buildings(query)
    location = results[result_index]

    tileset = load_tileset()
    tiles = find_tiles(tileset, location['lat'], location['lng'])
    tile_data = get_tile_data(tiles[0]['uri'])

    header = parse_header(tile_data)
    glb_data = extract_glb(tile_data, header)

    with tempfile.TemporaryDirectory() as tmpdir:
        glb_path = os.path.join(tmpdir, "tile.glb")
        decompressed_path = os.path.join(tmpdir, "decompressed.glb")

        with open(glb_path, 'wb') as f:
            f.write(glb_data)

        result_path = decompress_draco(glb_path, decompressed_path)
        scene = trimesh.load(result_path)

        meshes = []
        for geom_name, geom in scene.geometry.items():
            for gml_id, building_name in target_ids.items():
                if gml_id in geom_name:
                    print(f"  Extracted: {building_name}")
                    meshes.append(geom)
                    break

        return meshes


def extract_multi_tile_complex(tile_configs, output_path, scale=0.001):
    """
    Extract buildings from multiple tiles and combine.

    Args:
        tile_configs: List of (query, result_index, gml_ids_dict) tuples
        output_path: Output 3MF/STL path
        scale: Scale factor (default 1:1000)
    """
    all_meshes = []

    for query, result_index, target_ids in tile_configs:
        print(f"\nProcessing: {query}")
        meshes = extract_meshes_by_gml_id(query, result_index, target_ids)
        all_meshes.extend(meshes)

    if not all_meshes:
        raise ValueError("No meshes extracted")

    # Combine
    combined = trimesh.util.concatenate(all_meshes)
    print(f"\nCombined: {len(combined.vertices)} vertices, {len(combined.faces)} faces")

    # Scale
    combined.apply_scale(scale)

    # Center on XY, place on Z=0
    bounds = combined.bounds
    center_xy = (bounds[0][:2] + bounds[1][:2]) / 2
    min_z = bounds[0][2]
    combined.apply_translation(np.array([-center_xy[0], -center_xy[1], -min_z]))

    # Export
    combined.export(output_path)
    print(f"\nExported: {output_path}")

    return combined


if __name__ == "__main__":
    # Example: Extract all 5 Suntec City towers

    # First, find the gml:ids for Suntec towers in each tile
    tile1_towers = find_building_gml_ids(
        "Suntec City", 1,
        lambda name: 'SUNTEC TOWER' in name.upper()
    )

    tile2_towers = find_building_gml_ids(
        "Suntec Tower Two", 0,
        lambda name: 'SUNTEC TOWER' in name.upper()
    )

    print("Towers found:")
    for gml_id, name in {**tile1_towers, **tile2_towers}.items():
        print(f"  {name}: {gml_id}")

    # Extract and combine
    extract_multi_tile_complex(
        tile_configs=[
            ("Suntec City", 1, tile1_towers),
            ("Suntec Tower Two", 0, tile2_towers),
        ],
        output_path="suntec_5_towers.3mf",
        scale=0.001  # 1:1000
    )
```

### Why _BATCHID Isolation Doesn't Work

The `isolate_building()` function in `mesh_processor.py` attempts to filter by `_BATCHID` vertex attribute. However, trimesh doesn't preserve this attribute when loading GLB files. The geometry-name-based approach above is more reliable.

### Other Multi-Building Complexes

This technique works for any building complex spanning multiple tiles:

| Complex | Tiles to Search |
|---------|-----------------|
| Suntec City (5 towers) | "Suntec City", "Suntec Tower Two" |
| Marina Bay Financial Centre | "MBFC Tower 1", "MBFC Tower 2", "MBFC Tower 3" |
| Raffles City | "Raffles City Tower", "Swissotel The Stamford" |

Use `--list` to discover buildings in each tile, then extract by `gml:id`.
