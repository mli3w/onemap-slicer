"""Tests for exporter module."""

import os
import tempfile

import numpy as np
import pytest
import trimesh

from onemap_slicer.exporter import (
    export_glb,
    export_mesh,
    export_ply,
)


def create_simple_mesh():
    """Create a simple triangle mesh for testing."""
    vertices = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, 0.5, 1]], dtype=np.float64)
    faces = np.array([[0, 1, 2], [0, 1, 3], [1, 2, 3], [0, 2, 3]])
    return trimesh.Trimesh(vertices=vertices, faces=faces)


def create_mesh_with_vertex_colors():
    """Create a mesh with vertex colors."""
    mesh = create_simple_mesh()
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


class TestExportPly:
    """Tests for PLY export."""

    def test_export_ply_creates_file(self):
        """PLY export should create a file."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.ply")
            result = export_ply(mesh, path)

            assert os.path.exists(result)
            assert result.endswith(".ply")

    def test_export_ply_with_colors(self):
        """PLY export should include vertex colors when present."""
        mesh = create_mesh_with_vertex_colors()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_colors.ply")
            result = export_ply(mesh, path)

            assert os.path.exists(result)
            # Reload and check colors are preserved
            loaded = trimesh.load(result)
            assert loaded.visual is not None

    def test_export_ply_appends_extension(self):
        """PLY export should add .ply extension if missing."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "no_extension")
            result = export_ply(mesh, path)

            assert result.endswith(".ply")
            assert os.path.exists(result)

    def test_export_ply_scene(self):
        """PLY export should handle Scene objects."""
        mesh = create_simple_mesh()
        scene = trimesh.Scene(geometry={"mesh": mesh})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "scene.ply")
            result = export_ply(scene, path)

            assert os.path.exists(result)

    def test_export_ply_invalid_type_raises(self):
        """PLY export should raise ValueError for invalid types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "invalid.ply")
            with pytest.raises(ValueError, match="Cannot export type"):
                export_ply("not a mesh", path)


class TestExportGlb:
    """Tests for GLB export."""

    def test_export_glb_creates_file(self):
        """GLB export should create a file."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.glb")
            result = export_glb(mesh, path)

            assert os.path.exists(result)
            assert result.endswith(".glb")

    def test_export_glb_appends_extension(self):
        """GLB export should add .glb extension if missing."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "no_extension")
            result = export_glb(mesh, path)

            assert result.endswith(".glb")
            assert os.path.exists(result)

    def test_export_glb_scene(self):
        """GLB export should handle Scene objects."""
        mesh = create_simple_mesh()
        scene = trimesh.Scene(geometry={"mesh": mesh})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "scene.glb")
            result = export_glb(scene, path)

            assert os.path.exists(result)

    def test_export_glb_invalid_type_raises(self):
        """GLB export should raise ValueError for invalid types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "invalid.glb")
            with pytest.raises(ValueError, match="Cannot export type"):
                export_glb("not a mesh", path)


class TestExportMesh:
    """Tests for export_mesh dispatcher."""

    def test_export_mesh_ply_dispatch(self):
        """export_mesh should dispatch to PLY export."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            result = export_mesh(mesh, path, format="ply")

            assert result.endswith(".ply")
            assert os.path.exists(result)

    def test_export_mesh_glb_dispatch(self):
        """export_mesh should dispatch to GLB export."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            result = export_mesh(mesh, path, format="glb")

            assert result.endswith(".glb")
            assert os.path.exists(result)

    def test_export_mesh_3mf_dispatch(self):
        """export_mesh should dispatch to 3MF export."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            result = export_mesh(mesh, path, format="3mf")

            assert result.endswith(".3mf")
            assert os.path.exists(result)

    def test_export_mesh_stl_dispatch(self):
        """export_mesh should dispatch to STL export."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            result = export_mesh(mesh, path, format="stl")

            assert result.endswith(".stl")
            assert os.path.exists(result)

    def test_export_mesh_invalid_format_raises(self):
        """export_mesh should raise ValueError for invalid formats."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            with pytest.raises(ValueError, match="Unsupported format"):
                export_mesh(mesh, path, format="invalid")

    def test_export_mesh_case_insensitive(self):
        """export_mesh should handle format case-insensitively."""
        mesh = create_simple_mesh()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test")
            result = export_mesh(mesh, path, format="PLY")

            assert result.endswith(".ply")
