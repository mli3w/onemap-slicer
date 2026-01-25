"""Export module for STL and 3MF file formats."""

import os
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# Attribution metadata
ATTRIBUTION = {
    "source": "OneMap Singapore (onemap.gov.sg)",
    "license": "Singapore Open Data License",
    "tool": "onemap-slicer",
}


def _inject_3mf_metadata(
    path: str,
    title: str | None = None,
    building_name: str | None = None,
) -> None:
    """
    Inject attribution metadata and object names into a 3MF file.

    3MF is a ZIP containing XML. We modify 3D/3dmodel.model to add metadata
    and set object names so they appear correctly in slicers.
    """
    # 3MF namespace
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

    # Read the 3MF (ZIP) file
    with zipfile.ZipFile(path, "r") as zf:
        model_path = "3D/3dmodel.model"
        if model_path not in zf.namelist():
            return  # Not a standard 3MF structure

        model_xml = zf.read(model_path)
        other_files = {name: zf.read(name) for name in zf.namelist() if name != model_path}

    # Parse and modify the XML
    ET.register_namespace("", ns["m"])
    root = ET.fromstring(model_xml)

    # Find or create metadata section (metadata goes directly under root)
    # Remove existing metadata with same names to avoid duplicates
    for meta in root.findall("m:metadata", ns):
        name = meta.get("name", "")
        if name in [
            "Title",
            "Designer",
            "Description",
            "Copyright",
            "LicenseTerms",
            "CreationDate",
        ]:
            root.remove(meta)

    # Add our metadata at the beginning (after any existing processing instructions)
    metadata_entries = [
        ("Title", title or building_name or "OneMap Building Export"),
        ("Designer", ATTRIBUTION["tool"]),
        ("Description", f"3D building model extracted from {ATTRIBUTION['source']}"),
        ("Copyright", ATTRIBUTION["source"]),
        ("LicenseTerms", ATTRIBUTION["license"]),
        ("CreationDate", datetime.now(timezone.utc).isoformat()),
    ]

    # Insert metadata elements at position 0 (they'll be reversed, so insert in reverse order)
    for name, value in reversed(metadata_entries):
        meta_elem = ET.Element("metadata", {"name": name})
        meta_elem.text = value
        root.insert(0, meta_elem)

    # Set object names so they appear correctly in slicers like Bambu Studio
    # The 'name' attribute on <object> elements is what slicers display
    object_name = building_name or title or "Building"
    resources = root.find("m:resources", ns)
    if resources is not None:
        for obj in resources.findall("m:object", ns):
            obj.set("name", object_name)

    # Write back the modified 3MF
    modified_xml = ET.tostring(root, encoding="unicode", xml_declaration=True)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(model_path, modified_xml)
        for name, data in other_files.items():
            zf.writestr(name, data)


def export_3mf(
    mesh,
    path: str,
    title: str | None = None,
    building_name: str | None = None,
) -> str:
    """
    Export mesh to 3MF format with attribution metadata.

    3MF is the preferred format for Bambu Studio as it supports
    color, metadata, and multiple objects.

    Args:
        mesh: trimesh object to export
        path: Output file path
        title: Optional title for the model
        building_name: Optional building name for metadata

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

    # Inject attribution metadata
    try:
        _inject_3mf_metadata(path, title=title, building_name=building_name)
    except Exception:
        pass  # Don't fail export if metadata injection fails

    return path


def _stl_header(building_name: str | None = None) -> bytes:
    """Generate an 80-byte STL header with attribution."""
    text = f"OneMap SG | {ATTRIBUTION['license']}"
    if building_name:
        text = f"{building_name[:30]} | {text}"

    # Pad or truncate to exactly 80 bytes
    header = text.encode("ascii", errors="replace")[:80]
    return header.ljust(80, b"\x00")


def export_stl(
    mesh,
    path: str,
    binary: bool = True,
    building_name: str | None = None,
) -> str:
    """
    Export mesh to STL format with attribution in header.

    Args:
        mesh: trimesh object to export
        path: Output file path
        binary: Use binary STL format (smaller file size)
        building_name: Optional building name for header

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

    # For binary STL, replace the header with attribution
    if binary and building_name:
        try:
            with open(path, "r+b") as f:
                f.write(_stl_header(building_name))
        except Exception:
            pass  # Don't fail if header replacement fails

    return path


def export_mesh(
    mesh,
    path: str,
    format: str = "3mf",
    building_name: str | None = None,
) -> str:
    """
    Export mesh to specified format with attribution.

    Args:
        mesh: trimesh object to export
        path: Output file path
        format: Output format ('3mf' or 'stl')
        building_name: Optional building name for metadata/header

    Returns:
        Path to exported file.
    """
    format = format.lower()

    if format == "3mf":
        return export_3mf(mesh, path, building_name=building_name)
    elif format == "stl":
        return export_stl(mesh, path, building_name=building_name)
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
