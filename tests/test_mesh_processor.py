"""Tests for mesh_processor color functions."""

import numpy as np
import trimesh

from onemap_slicer.mesh_processor import (
    bake_vertex_colors,
    has_visual_data,
    lightweight_repair,
    prepare_for_print,
)


def create_simple_mesh():
    """Create a simple triangle mesh for testing."""
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, 0.5, 1]], dtype=np.float64)
    faces = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 2, 3]])
    return trimesh.Trimesh(vertices=vertices, faces=faces)


def create_mesh_with_vertex_colors():
    """Create a mesh with vertex colors."""
    mesh = create_simple_mesh()
    # Set non-default vertex colors (red, green, blue, yellow)
    colors = np.array(
        [
            [255, 0, 0, 255],
            [0, 255, 0, 255],
            [0, 0, 255, 255],
            [255, 255, 0, 255],
        ],
        dtype=np.uint8,
    )
    mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=colors)
    return mesh


def create_mesh_with_default_colors():
    """Create a mesh with default white-ish colors."""
    mesh = create_simple_mesh()
    # All white colors (default)
    colors = np.array(
        [
            [200, 200, 200, 255],
            [200, 200, 200, 255],
            [200, 200, 200, 255],
            [200, 200, 200, 255],
        ],
        dtype=np.uint8,
    )
    mesh.visual = trimesh.visual.ColorVisuals(mesh=mesh, vertex_colors=colors)
    return mesh


class TestHasVisualData:
    """Tests for has_visual_data function."""

    def test_mesh_with_vertex_colors_returns_true(self):
        """Mesh with non-default vertex colors should return True."""
        mesh = create_mesh_with_vertex_colors()
        assert has_visual_data(mesh) is True

    def test_mesh_with_default_colors_returns_false(self):
        """Mesh with default white-ish colors should return False."""
        mesh = create_mesh_with_default_colors()
        assert has_visual_data(mesh) is False

    def test_plain_mesh_with_default_visual_returns_false(self):
        """Plain mesh with default ColorVisuals (trimesh auto-creates) should return False."""
        mesh = create_simple_mesh()
        # trimesh auto-creates ColorVisuals with default colors, which should be detected as "no visual data"
        assert has_visual_data(mesh) is False

    def test_non_trimesh_returns_false(self):
        """Non-Trimesh objects should return False."""
        assert has_visual_data("not a mesh") is False
        assert has_visual_data(None) is False
        assert has_visual_data({}) is False


class TestBakeVertexColors:
    """Tests for bake_vertex_colors function."""

    def test_color_visuals_unchanged(self):
        """Mesh with ColorVisuals should be returned as-is."""
        mesh = create_mesh_with_vertex_colors()
        result = bake_vertex_colors(mesh)
        assert isinstance(result.visual, trimesh.visual.ColorVisuals)

    def test_non_trimesh_unchanged(self):
        """Non-Trimesh objects should be returned as-is."""
        result = bake_vertex_colors("not a mesh")
        assert result == "not a mesh"

    def test_mesh_with_color_visuals_unchanged(self):
        """Mesh with ColorVisuals should be returned as-is (no conversion needed)."""
        mesh = create_simple_mesh()
        # trimesh auto-creates ColorVisuals, so it should remain ColorVisuals
        result = bake_vertex_colors(mesh)
        assert isinstance(result.visual, trimesh.visual.ColorVisuals)


class TestLightweightRepair:
    """Tests for lightweight_repair function."""

    def test_preserves_vertex_colors(self):
        """Lightweight repair should preserve vertex colors."""
        mesh = create_mesh_with_vertex_colors()

        result = lightweight_repair(mesh)

        # Colors should still be present
        assert isinstance(result.visual, trimesh.visual.ColorVisuals)
        assert result.visual.vertex_colors is not None

    def test_repairs_mesh(self):
        """Lightweight repair should fix mesh issues."""
        mesh = create_simple_mesh()
        result = lightweight_repair(mesh)

        # Should still be a valid mesh
        assert len(result.vertices) > 0
        assert len(result.faces) > 0

    def test_non_trimesh_unchanged(self):
        """Non-Trimesh objects should be returned as-is."""
        result = lightweight_repair("not a mesh")
        assert result == "not a mesh"


class TestPrepareForPrint:
    """Tests for prepare_for_print with preserve_colors parameter."""

    def test_preserve_colors_true_keeps_colors(self):
        """With preserve_colors=True, vertex colors should be preserved."""
        mesh = create_mesh_with_vertex_colors()

        result = prepare_for_print(mesh, scale=1.0, center=False, preserve_colors=True)

        # Colors should still be present
        assert result.visual is not None

    def test_preserve_colors_false_default(self):
        """Default behavior (preserve_colors=False) should use full repair."""
        mesh = create_simple_mesh()

        result = prepare_for_print(mesh, scale=1.0, center=False)

        # Should still be a valid mesh
        assert len(result.vertices) > 0
        assert len(result.faces) > 0

    def test_scale_applied(self):
        """Scale should be applied to the mesh."""
        mesh = create_simple_mesh()
        original_bounds = mesh.bounds.copy()

        result = prepare_for_print(mesh, scale=0.5, center=False, preserve_colors=True)

        # Bounds should be scaled
        assert np.allclose(result.bounds, original_bounds * 0.5)

    def test_centering(self):
        """Mesh should be centered on XY and placed on Z=0."""
        mesh = create_simple_mesh()
        # Offset the mesh
        mesh.apply_translation([10, 10, 10])

        result = prepare_for_print(mesh, scale=1.0, center=True, preserve_colors=True)

        # Should be centered on XY (centroid near 0,0)
        bounds = result.bounds
        center_xy = (bounds[0][:2] + bounds[1][:2]) / 2
        assert np.allclose(center_xy, [0, 0], atol=0.1)

        # Z minimum should be at 0
        assert np.isclose(bounds[0][2], 0, atol=0.01)
