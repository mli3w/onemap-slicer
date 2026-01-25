"""Export module for STL and 3MF file formats."""

import os


def export_3mf(mesh, path: str) -> str:
    """
    Export mesh to 3MF format.

    3MF is the preferred format for Bambu Studio as it supports
    color, metadata, and multiple objects.

    Args:
        mesh: trimesh object to export
        path: Output file path

    Returns:
        Path to exported file.
    """
    import trimesh

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    # Ensure .3mf extension
    if not path.lower().endswith(".3mf"):
        path = path + ".3mf"

    if isinstance(mesh, (trimesh.Scene, trimesh.Trimesh)):
        mesh.export(path, file_type="3mf")
    else:
        raise ValueError(f"Cannot export type: {type(mesh)}")

    return path


def export_stl(mesh, path: str, binary: bool = True) -> str:
    """
    Export mesh to STL format.

    Args:
        mesh: trimesh object to export
        path: Output file path
        binary: Use binary STL format (smaller file size)

    Returns:
        Path to exported file.
    """
    import trimesh

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    # Ensure .stl extension
    if not path.lower().endswith(".stl"):
        path = path + ".stl"

    file_type = "stl" if binary else "stl_ascii"

    if isinstance(mesh, trimesh.Scene):
        # Concatenate all geometries for STL export
        meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if meshes:
            combined = trimesh.util.concatenate(meshes)
            combined.export(path, file_type=file_type)
        else:
            raise ValueError("No meshes found in scene")
    elif isinstance(mesh, trimesh.Trimesh):
        mesh.export(path, file_type=file_type)
    else:
        raise ValueError(f"Cannot export type: {type(mesh)}")

    return path


def export_mesh(mesh, path: str, format: str = "3mf") -> str:
    """
    Export mesh to specified format.

    Args:
        mesh: trimesh object to export
        path: Output file path
        format: Output format ('3mf' or 'stl')

    Returns:
        Path to exported file.
    """
    format = format.lower()

    if format == "3mf":
        return export_3mf(mesh, path)
    elif format == "stl":
        return export_stl(mesh, path)
    else:
        raise ValueError(f"Unsupported format: {format}. Use '3mf' or 'stl'.")


def get_export_info(path: str) -> dict:
    """Get information about an exported file."""
    info = {
        "path": path,
        "exists": os.path.exists(path),
        "size_bytes": 0,
        "size_human": "0 B",
    }

    if info["exists"]:
        size = os.path.getsize(path)
        info["size_bytes"] = size

        # Human-readable size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                info["size_human"] = f"{size:.1f} {unit}"
                break
            size /= 1024

    return info
