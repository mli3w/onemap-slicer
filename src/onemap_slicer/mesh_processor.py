"""Mesh processing module for Draco decompression and mesh operations."""

import os
import shutil
import subprocess
import tempfile

import numpy as np


def check_gltf_transform() -> bool:
    """Check if gltf-transform CLI is available."""
    try:
        result = subprocess.run(
            ["npx", "--yes", "@gltf-transform/cli", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def decompress_draco(glb_path: str, output_path: str | None = None) -> str:
    """
    Decompress Draco-compressed GLB using gltf-transform CLI.

    Args:
        glb_path: Path to input GLB file
        output_path: Optional output path. If None, creates a temp file.

    Returns:
        Path to decompressed GLB file.
    """
    if output_path is None:
        # Create temp file with same name pattern
        fd, output_path = tempfile.mkstemp(suffix=".glb")
        os.close(fd)

    try:
        result = subprocess.run(
            [
                "npx",
                "--yes",
                "@gltf-transform/cli",
                "dedup",
                glb_path,
                output_path,
                "--allow-empty",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            # Try without dedup, just copy (might already be decompressed)
            result = subprocess.run(
                [
                    "npx",
                    "--yes",
                    "@gltf-transform/cli",
                    "copy",
                    glb_path,
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

        if result.returncode != 0:
            # If gltf-transform fails, just use the original
            shutil.copy(glb_path, output_path)

        return output_path

    except subprocess.TimeoutExpired:
        # Timeout - just use original
        shutil.copy(glb_path, output_path)
        return output_path


def load_mesh(glb_path: str):
    """
    Load mesh from GLB file using trimesh.

    Returns a trimesh.Trimesh or trimesh.Scene object.
    """
    import trimesh

    # Try loading directly first
    try:
        mesh = trimesh.load(glb_path, force="mesh")
        if mesh is not None and hasattr(mesh, "vertices") and len(mesh.vertices) > 0:
            return mesh
    except Exception:
        pass

    # Try loading as scene and concatenating
    try:
        scene = trimesh.load(glb_path)

        if isinstance(scene, trimesh.Scene):
            # Extract all meshes from scene
            meshes = []
            for _name, geometry in scene.geometry.items():
                if isinstance(geometry, trimesh.Trimesh):
                    # Apply node transform if available
                    meshes.append(geometry)

            if meshes:
                return trimesh.util.concatenate(meshes)

        return scene

    except Exception as e:
        raise RuntimeError(f"Failed to load mesh from {glb_path}: {e}") from e


def isolate_building(mesh, batch_id: int):
    """
    Isolate a specific building by batch ID.

    The _BATCHID vertex attribute maps each face to a building.
    """
    import trimesh

    if not isinstance(mesh, trimesh.Trimesh):
        return mesh

    # Check for batch ID in vertex attributes
    if hasattr(mesh, "visual") and hasattr(mesh.visual, "vertex_attributes"):
        attrs = mesh.visual.vertex_attributes

        for attr_name in ["_BATCHID", "BATCHID", "batchId"]:
            if attr_name in attrs:
                batch_ids = attrs[attr_name]

                # Find faces where all vertices have the target batch ID
                face_batch_ids = batch_ids[mesh.faces]
                face_mask = np.all(face_batch_ids == batch_id, axis=1)

                if np.any(face_mask):
                    # Create submesh with only matching faces
                    submesh = mesh.submesh([np.where(face_mask)[0]], append=True)
                    return submesh

    # If no batch ID attribute found, return original
    return mesh


def repair_mesh(mesh):
    """
    Repair mesh using pymeshfix for watertight output.

    Args:
        mesh: Input trimesh object

    Returns:
        Repaired trimesh object with fixed topology.
    """
    import pymeshfix
    import trimesh

    try:
        meshfix = pymeshfix.MeshFix(mesh.vertices, mesh.faces)
        # Keep all components - building tiles have many separate structures
        meshfix.repair(verbose=False, remove_smallest_components=False)

        # Check if repair produced a valid mesh
        if len(meshfix.v) > 0 and len(meshfix.f) > 0:
            return trimesh.Trimesh(vertices=meshfix.v, faces=meshfix.f)
    except Exception:
        pass

    # Fallback: use trimesh's built-in repair methods
    try:
        mesh.fix_normals()
    except Exception:
        pass

    try:
        mesh.fill_holes()
    except Exception:
        pass

    try:
        # Remove degenerate faces (faces with < 3 unique vertices)
        mesh.update_faces(mesh.nondegenerate_faces())
    except Exception:
        pass

    try:
        # Remove duplicate faces
        mesh.update_faces(mesh.unique_faces())
    except Exception:
        pass

    try:
        mesh.remove_unreferenced_vertices()
    except Exception:
        pass

    return mesh


def prepare_for_print(mesh, scale: float = 0.001, center: bool = True):
    """
    Prepare mesh for 3D printing.

    Args:
        mesh: Input trimesh object
        scale: Scale factor (default 0.001 converts meters to mm at 1:1000)
        center: Whether to center the mesh at origin

    Returns:
        Processed trimesh ready for export.
    """
    import trimesh

    if not isinstance(mesh, trimesh.Trimesh):
        return mesh

    # Make a copy to avoid modifying original
    mesh = mesh.copy()

    # Use pymeshfix for robust repair
    mesh = repair_mesh(mesh)

    # Apply scale
    mesh.apply_scale(scale)

    # Center on XY plane, place on Z=0
    if center:
        bounds = mesh.bounds
        center_xy = (bounds[0][:2] + bounds[1][:2]) / 2
        min_z = bounds[0][2]

        translation = np.array([-center_xy[0], -center_xy[1], -min_z])
        mesh.apply_translation(translation)

    return mesh


def get_mesh_info(mesh) -> dict:
    """Get information about a mesh for debugging."""
    import trimesh

    info = {
        "type": type(mesh).__name__,
        "is_empty": True,
        "vertices": 0,
        "faces": 0,
        "bounds": None,
        "is_watertight": False,
        "volume": 0,
    }

    if isinstance(mesh, trimesh.Trimesh):
        info["is_empty"] = len(mesh.vertices) == 0
        info["vertices"] = len(mesh.vertices)
        info["faces"] = len(mesh.faces)

        if not info["is_empty"]:
            info["bounds"] = mesh.bounds.tolist()
            info["is_watertight"] = mesh.is_watertight
            if mesh.is_watertight:
                info["volume"] = float(mesh.volume)

    elif isinstance(mesh, trimesh.Scene):
        info["type"] = "Scene"
        info["geometry_count"] = len(mesh.geometry)
        info["geometry_names"] = list(mesh.geometry.keys())

        total_verts = 0
        total_faces = 0
        for geom in mesh.geometry.values():
            if hasattr(geom, "vertices"):
                total_verts += len(geom.vertices)
            if hasattr(geom, "faces"):
                total_faces += len(geom.faces)

        info["vertices"] = total_verts
        info["faces"] = total_faces
        info["is_empty"] = total_verts == 0

    return info


def inspect_glb(glb_path: str) -> dict:
    """Inspect a GLB file and return debug information."""
    import trimesh

    info = {
        "file_path": glb_path,
        "file_size": os.path.getsize(glb_path),
        "mesh_info": None,
        "error": None,
    }

    try:
        scene = trimesh.load(glb_path)
        info["mesh_info"] = get_mesh_info(scene)

        # Check for vertex attributes (batch IDs)
        if isinstance(scene, trimesh.Scene):
            for name, geom in scene.geometry.items():
                if hasattr(geom, "visual") and hasattr(geom.visual, "vertex_attributes"):
                    attrs = geom.visual.vertex_attributes
                    if attrs:
                        info.setdefault("vertex_attributes", {})[name] = list(attrs.keys())

    except Exception as e:
        info["error"] = str(e)

    return info
