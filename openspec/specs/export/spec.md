# export Specification

## Purpose
TBD - created by archiving change add-color-export. Update Purpose after archive.
## Requirements
### Requirement: PLY Export with Vertex Colors

The system SHALL export meshes to PLY format with vertex colors when the `--with-colors` flag is specified.

#### Scenario: PLY export bakes textures to vertex colors
- **WHEN** user exports with `-f ply --with-colors` and the mesh has texture data
- **THEN** the system bakes textures to per-vertex RGBA colors using `mesh.visual.to_color()`
- **AND** exports to PLY format with embedded vertex colors

#### Scenario: PLY export preserves existing vertex colors
- **WHEN** user exports with `-f ply --with-colors` and the mesh already has vertex colors
- **THEN** the system preserves the existing vertex colors in the PLY output

#### Scenario: PLY export without color data
- **WHEN** user exports with `-f ply --with-colors` but the mesh has no visual data
- **THEN** the system warns that no color data was found
- **AND** exports a plain PLY without color attributes

### Requirement: GLB Export with Textures

The system SHALL export meshes to GLB format preserving original textures when the `--with-colors` flag is specified.

#### Scenario: GLB export preserves PBR materials
- **WHEN** user exports with `-f glb --with-colors` and the mesh has texture data
- **THEN** the system preserves the original textures and materials in GLB output

#### Scenario: GLB export without textures
- **WHEN** user exports with `-f glb` without `--with-colors`
- **THEN** the system exports geometry-only GLB without texture preservation

### Requirement: Color-Preserving Mesh Repair

The system SHALL use lightweight repair methods that preserve visual data when `--with-colors` is specified.

#### Scenario: Lightweight repair preserves vertex colors
- **WHEN** mesh preparation runs with `preserve_colors=True`
- **THEN** the system uses trimesh's built-in repair methods (fix_normals, fill_holes, remove degenerate faces)
- **AND** does not use pymeshfix which would discard vertex attributes

#### Scenario: Full repair for print-ready exports
- **WHEN** mesh preparation runs with `preserve_colors=False` (default)
- **THEN** the system uses pymeshfix for robust watertight repair (existing behavior)

### Requirement: Color Flag Validation

The system SHALL validate that the `--with-colors` flag is used with a compatible export format.

#### Scenario: Color flag with incompatible format shows warning
- **WHEN** user specifies `--with-colors` with `-f 3mf` or `-f stl`
- **THEN** the system prints a warning that colors require PLY or GLB format
- **AND** automatically switches the format to PLY

#### Scenario: Color flag with compatible format proceeds normally
- **WHEN** user specifies `--with-colors` with `-f ply` or `-f glb`
- **THEN** the system proceeds with color-preserving export without warnings

### Requirement: Visual Data Detection

The system SHALL detect whether a mesh contains visual data (textures or vertex colors).

#### Scenario: Detect TextureVisuals
- **WHEN** checking a mesh with `trimesh.visual.TextureVisuals`
- **THEN** `has_visual_data()` returns `True` if the mesh has a material or texture

#### Scenario: Detect ColorVisuals
- **WHEN** checking a mesh with `trimesh.visual.ColorVisuals`
- **THEN** `has_visual_data()` returns `True` if vertex colors are not all default/white

#### Scenario: Detect no visual data
- **WHEN** checking a mesh without textures or meaningful vertex colors
- **THEN** `has_visual_data()` returns `False`

