# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

onemap-slicer extracts 3D building models from OneMap Singapore and exports them as print-ready 3MF/STL files. It processes OGC 3D Tiles (B3DM format with Draco-compressed glTF) into meshes suitable for 3D printing.

## Commands

```bash
# Install dependencies and setup dev environment
uv sync

# Run CLI (interactive mode)
uv run onemap-slicer "Marina Bay Sands" -o mbs.3mf

# List search results
uv run onemap-slicer "Tanjong Pagar" --list-results

# Non-interactive mode (for scripts/CI)
uv run onemap-slicer "Marina Bay" --result-index 0 --no-interactive

# Export specific building from tile
uv run onemap-slicer "UOB Plaza" --list                    # See building indices
uv run onemap-slicer "UOB Plaza" --building-index 0 -o uob.3mf

# Run tests
uv run pytest

# Run single test
uv run pytest tests/test_module.py::test_function -v

# Format code
uv run ruff format

# Lint code
uv run ruff check

# Lint and auto-fix
uv run ruff check --fix

# Note: A Claude hook auto-formats Python files after edits
```

## Architecture

The pipeline flows: **Search → Tileset → B3DM → GLB → Mesh → Export**

```
cli.py           # Entry point, argument parsing, orchestrates pipeline
    ↓
onemap_api.py    # API client: search buildings, load tileset.json (ETag cached), find tiles by lat/lng
    ↓
b3dm_parser.py   # Parse B3DM binary format: extract header, batch table metadata, embedded GLB
    ↓
mesh_processor.py # Draco decompression (via gltf-transform), mesh loading (trimesh), repair (pymeshfix)
    ↓
exporter.py      # Export to 3MF (preferred for Bambu Studio) or STL
```

### Key Technical Details

- **Coordinate systems**: OneMap uses WGS84 lat/lng for search, ECEF for tile bounding volumes, radians for regions in tileset.json
- **B3DM format**: 28-byte header → feature table → batch table (building metadata) → embedded GLB
- **Batch IDs**: `_BATCHID` vertex attribute links mesh faces to buildings in batch table (used for isolating specific buildings)
- **Tileset caching**: `load_tileset()` uses ETag-based HTTP caching to `~/Library/Caches/onemap-slicer/` (or platform equivalent)
- **Draco decompression**: Requires Node.js with `@gltf-transform/cli` (invoked via npx)

### Data Flow for Tile Finding

`find_tiles()` traverses the tileset tree recursively, checking if each node's bounding volume contains the target lat/lng. It handles nested tileset.json files and sorts results by geometric error (lower = higher detail).

### CLI Flags

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file path (default: building.3mf) |
| `-f, --format` | Output format: 3mf or stl (default: 3mf) |
| `-s, --scale` | Scale factor or ratio (default: 1:1000) |
| `--lod` | Level of detail: low, medium, high (default: high) |
| `--list` | List buildings in tile (don't export) |
| `--list-results` | List all search results and exit |
| `--result-index N` | Select Nth search result (skips interactive menu) |
| `--building-index N` | Export only Nth building from tile |
| `--no-interactive` | Disable interactive menus (for scripts/CI) |
| `--debug` | Show debug information |
