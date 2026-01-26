# Change: Add Color Export Support

## Why

OneMap 3D tiles contain photo-realistic textures (PBR materials) that are currently discarded during export. Users who want to visualize or display (rather than print) building models lose this valuable visual data. Adding PLY and GLB export formats with color preservation enables:
- Visualization in tools like MeshLab, Blender, or web viewers
- Archival of building appearance alongside geometry
- Use cases beyond 3D printing (presentations, digital twins)

## What Changes

- **New export formats**: Add PLY (with baked vertex colors) and GLB (with preserved textures)
- **New CLI flag**: `--with-colors` to enable color preservation during export
- **New mesh processing functions**: Color detection, texture-to-vertex-color baking, and color-preserving repair
- **Modified prepare_for_print()**: Add `preserve_colors` parameter to use lightweight repair when colors matter

## Impact

- Affected specs: `export` (new capability)
- Affected code:
  - `src/onemap_slicer/mesh_processor.py` - New color functions, modified `prepare_for_print()`
  - `src/onemap_slicer/exporter.py` - New `export_ply()`, `export_glb()`, updated `export_mesh()`
  - `src/onemap_slicer/cli.py` - New `--with-colors` flag, color pipeline logic
  - `CLAUDE.md` - Documentation updates
  - `tests/` - New test files for exporter and mesh processor
