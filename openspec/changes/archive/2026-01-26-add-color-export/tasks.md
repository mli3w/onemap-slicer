## 1. Mesh Processor - Color Functions

- [x] 1.1 Add `has_visual_data(mesh)` function to detect textures or vertex colors
- [x] 1.2 Add `bake_vertex_colors(mesh)` function to convert TextureVisuals to vertex colors
- [x] 1.3 Add `lightweight_repair(mesh)` function for color-preserving mesh repair
- [x] 1.4 Modify `prepare_for_print()` to accept `preserve_colors` parameter

## 2. Exporter - New Formats

- [x] 2.1 Add `export_ply()` function for PLY export with vertex colors
- [x] 2.2 Add `export_glb()` function for GLB export with preserved textures
- [x] 2.3 Update `export_mesh()` to dispatch PLY and GLB formats

## 3. CLI Integration

- [x] 3.1 Add `--with-colors` CLI flag
- [x] 3.2 Expand format choices to include `ply` and `glb`
- [x] 3.3 Add validation: warn and switch format if `--with-colors` used with 3MF/STL
- [x] 3.4 Add color processing pipeline before `prepare_for_print()`

## 4. Documentation

- [x] 4.1 Update CLAUDE.md CLI flags table with `--with-colors` and new formats
- [x] 4.2 Add Color Export section to CLAUDE.md explaining usage and limitations

## 5. Testing

- [x] 5.1 Create `tests/test_mesh_processor.py` with color function tests
- [x] 5.2 Create `tests/test_exporter.py` with export format tests
- [x] 5.3 Verify existing 3MF/STL exports still work (regression test)

## 6. Manual Verification

- [x] 6.1 Test PLY export with colors using real OneMap data (Funan - 833 KB)
- [x] 6.2 Test GLB export with textures using real OneMap data (Funan - 16 MB)
- [x] 6.3 Verify exported files open correctly in MeshLab and glTF viewers
