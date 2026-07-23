from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path
import struct


@lru_cache(maxsize=1)
def load_land_polygons(path: str | Path | None = None) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Load polygon rings from the bundled Natural Earth ESRI shapefile."""
    source = (
        Path(path)
        if path is not None
        else Path(str(files("antenna_pattern_lab").joinpath("assets/ne_110m_land.shp")))
    )
    data = source.read_bytes()
    if len(data) < 100 or struct.unpack_from(">i", data, 0)[0] != 9994:
        raise ValueError("Invalid Natural Earth shapefile header.")

    polygons: list[tuple[tuple[float, float], ...]] = []
    offset = 100
    while offset + 8 <= len(data):
        _record_number, content_words = struct.unpack_from(">2i", data, offset)
        offset += 8
        content_size = content_words * 2
        content = memoryview(data)[offset : offset + content_size]
        offset += content_size
        if len(content) < 44:
            continue
        shape_type = struct.unpack_from("<i", content, 0)[0]
        if shape_type == 0:
            continue
        if shape_type != 5:
            raise ValueError(f"Unsupported world-map shape type: {shape_type}")
        part_count, point_count = struct.unpack_from("<2i", content, 36)
        parts_offset = 44
        points_offset = parts_offset + part_count * 4
        if (
            part_count < 1
            or point_count < 3
            or points_offset + point_count * 16 > len(content)
        ):
            continue
        starts = list(struct.unpack_from(f"<{part_count}i", content, parts_offset))
        starts.append(point_count)
        for start, end in zip(starts, starts[1:]):
            if end - start < 3:
                continue
            ring = tuple(
                struct.unpack_from("<2d", content, points_offset + index * 16)
                for index in range(start, end)
            )
            polygons.append(ring)
    return tuple(polygons)
