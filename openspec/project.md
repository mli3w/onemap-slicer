# Project Context

## Purpose
OneMap Slicer extracts 3D building models from Singapore's OneMap database and exports them as print-ready 3MF/STL files for 3D printing. It processes OGC 3D Tiles (B3DM format with Draco-compressed glTF) into watertight meshes suitable for slicing software like Bambu Studio, PrusaSlicer, or Cura.

## Tech Stack
- **Language**: Python 3.10+
- **Package Manager**: uv
- **Core Libraries**:
  - `trimesh` - Mesh loading and manipulation
  - `pymeshfix` - Mesh repair for watertight prints
  - `numpy`, `scipy`, `networkx` - Numerical operations and graph algorithms
  - `requests` - HTTP client for OneMap API
  - `rich` - Terminal formatting and progress display
  - `questionary` - Interactive CLI menus
  - `lxml` - XML processing for 3MF export
  - `platformdirs` - Cross-platform cache directory handling
- **External Runtime**: Node.js 18+ (for `@gltf-transform/cli` Draco decompression)
- **Dev Tools**: pytest, pytest-cov, ruff

## Project Conventions

### Code Style
- **Formatter/Linter**: ruff
- **Line length**: 100 characters
- **Quote style**: Double quotes
- **Import sorting**: isort via ruff
- **Target Python**: 3.10
- **Lint rules**: pycodestyle (E/W), pyflakes (F), isort (I), pyupgrade (UP), flake8-bugbear (B), flake8-simplify (SIM)
- Auto-formatting hook runs after edits

### Architecture Patterns
Pipeline architecture with clear separation of concerns:
```
cli.py           → Entry point, argument parsing, orchestrates pipeline
    ↓
onemap_api.py    → API client: search, tileset loading (ETag cached), tile finding
    ↓
b3dm_parser.py   → Parse B3DM binary: header, batch table metadata, embedded GLB
    ↓
mesh_processor.py → Draco decompression (via npx), mesh loading, repair
    ↓
exporter.py      → Export to 3MF (preferred) or STL
```

### Testing Strategy
- **Framework**: pytest with pytest-cov
- **Run tests**: `uv run pytest`
- **Run single test**: `uv run pytest tests/test_module.py::test_function -v`
- Tests should be added to the `tests/` directory

### Git Workflow
- **Branch**: Main branch development
- **Commit style**: Imperative mood, concise description (e.g., "Add building names to 3MF objects")
- **No prefix conventions** observed in existing commits

## Domain Context

### Coordinate Systems
- **WGS84**: Lat/lng for OneMap search queries
- **ECEF**: Earth-centered coordinates for tile bounding volumes
- **Radians**: Used in tileset.json region definitions

### 3D Tiles Format
- **B3DM**: Batched 3D Model format (OGC standard)
  - 28-byte header → feature table → batch table → embedded GLB
- **Batch Table**: Contains building metadata (names, IDs)
- **Batch IDs**: `_BATCHID` vertex attribute links mesh faces to buildings
- **Draco Compression**: glTF meshes are Draco-compressed, requiring Node.js decompression

### Tile Finding
`find_tiles()` traverses the tileset tree recursively, checking bounding volume containment. Results sorted by geometric error (lower = higher detail).

## Important Constraints
- **Node.js dependency**: Required for Draco decompression via `@gltf-transform/cli`
- **Single tile limitation**: Currently exports only one tile per search; large complexes spanning multiple tiles may be incomplete
- **Source data quality**: Some OneMap models have geometry issues requiring mesh repair

## External Dependencies

### OneMap API
- Search endpoint for building queries
- Tileset.json for 3D tile metadata
- B3DM tile downloads
- ETag-based HTTP caching to `~/Library/Caches/onemap-slicer/` (or platform equivalent)

### Node.js Tools
- `@gltf-transform/cli` - Draco decompression (invoked via `npx`)
