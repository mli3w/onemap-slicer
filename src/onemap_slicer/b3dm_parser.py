"""B3DM (Batched 3D Model) parser for extracting GLB data."""

import json
import struct


class B3DMHeader:
    """B3DM file header structure."""

    MAGIC = b"b3dm"
    HEADER_SIZE = 28

    def __init__(
        self,
        version: int,
        byte_length: int,
        feature_table_json_length: int,
        feature_table_binary_length: int,
        batch_table_json_length: int,
        batch_table_binary_length: int,
    ):
        self.version = version
        self.byte_length = byte_length
        self.feature_table_json_length = feature_table_json_length
        self.feature_table_binary_length = feature_table_binary_length
        self.batch_table_json_length = batch_table_json_length
        self.batch_table_binary_length = batch_table_binary_length

    @property
    def glb_offset(self) -> int:
        """Calculate offset where GLB data starts."""
        return (
            self.HEADER_SIZE
            + self.feature_table_json_length
            + self.feature_table_binary_length
            + self.batch_table_json_length
            + self.batch_table_binary_length
        )


def parse_header(data: bytes) -> B3DMHeader:
    """
    Parse B3DM header from raw bytes.

    Header structure (28 bytes):
    - magic: 4 bytes ("b3dm")
    - version: uint32
    - byteLength: uint32
    - featureTableJSONByteLength: uint32
    - featureTableBinaryByteLength: uint32
    - batchTableJSONByteLength: uint32
    - batchTableBinaryByteLength: uint32
    """
    if len(data) < B3DMHeader.HEADER_SIZE:
        raise ValueError(f"Data too short for B3DM header: {len(data)} bytes")

    magic = data[:4]
    if magic != B3DMHeader.MAGIC:
        raise ValueError(f"Invalid B3DM magic: {magic!r}, expected {B3DMHeader.MAGIC!r}")

    (
        version,
        byte_length,
        feature_json_len,
        feature_bin_len,
        batch_json_len,
        batch_bin_len,
    ) = struct.unpack("<6I", data[4:28])

    if version != 1:
        raise ValueError(f"Unsupported B3DM version: {version}")

    return B3DMHeader(
        version=version,
        byte_length=byte_length,
        feature_table_json_length=feature_json_len,
        feature_table_binary_length=feature_bin_len,
        batch_table_json_length=batch_json_len,
        batch_table_binary_length=batch_bin_len,
    )


def extract_metadata(data: bytes, header: B3DMHeader | None = None) -> dict:
    """
    Extract batch table metadata from B3DM data.

    The batch table contains per-building metadata like names and heights.
    """
    if header is None:
        header = parse_header(data)

    metadata = {
        "feature_table": {},
        "batch_table": {},
        "batch_count": 0,
    }

    # Extract feature table JSON
    ft_start = B3DMHeader.HEADER_SIZE
    ft_end = ft_start + header.feature_table_json_length

    if header.feature_table_json_length > 0:
        try:
            ft_json = data[ft_start:ft_end].decode("utf-8").rstrip("\x00")
            metadata["feature_table"] = json.loads(ft_json) if ft_json.strip() else {}
            metadata["batch_count"] = metadata["feature_table"].get("BATCH_LENGTH", 0)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Extract batch table JSON
    bt_start = ft_end + header.feature_table_binary_length
    bt_end = bt_start + header.batch_table_json_length

    if header.batch_table_json_length > 0:
        try:
            bt_json = data[bt_start:bt_end].decode("utf-8").rstrip("\x00")
            metadata["batch_table"] = json.loads(bt_json) if bt_json.strip() else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    return metadata


def extract_glb(data: bytes, header: B3DMHeader | None = None) -> bytes:
    """
    Extract embedded GLB bytes from B3DM data.

    The GLB starts after all the table data.
    """
    if header is None:
        header = parse_header(data)

    glb_offset = header.glb_offset
    glb_data = data[glb_offset:]

    # Validate GLB magic
    if len(glb_data) < 4:
        raise ValueError("GLB data too short")

    glb_magic = glb_data[:4]
    if glb_magic != b"glTF":
        raise ValueError(f"Invalid GLB magic: {glb_magic!r}, expected b'glTF'")

    return glb_data


def get_building_names(metadata: dict) -> list:
    """Extract building names from batch table metadata."""
    batch_table = metadata.get("batch_table", {})

    # Common field names for building names (including GML/CityGML fields)
    name_fields = [
        "name",
        "Name",
        "NAME",
        "building_name",
        "BUILDING_NAME",
        "bldg_name",
        "gml:name",
        "gml_name",
        "GML_NAME",
        "bldg:name",
        "bldg_name",
    ]

    for field in name_fields:
        if field in batch_table:
            names = batch_table[field]
            if isinstance(names, list):
                return names

    return []


def get_batch_table_summary(metadata: dict) -> dict:
    """Get a summary of batch table contents for debugging."""
    batch_table = metadata.get("batch_table", {})
    summary = {}

    for key, value in batch_table.items():
        if isinstance(value, list):
            summary[key] = {
                "count": len(value),
                "sample": value[:3] if value else [],
                "type": type(value[0]).__name__ if value else "empty",
            }
        else:
            summary[key] = {"value": value, "type": type(value).__name__}

    return summary


def find_batch_id_by_name(metadata: dict, search_name: str) -> int | None:
    """
    Find the batch ID for a building by name.

    Returns the index (batch ID) if found, None otherwise.
    """
    names = get_building_names(metadata)
    search_lower = search_name.lower()

    for i, name in enumerate(names):
        if isinstance(name, str) and search_lower in name.lower():
            return i

    return None
