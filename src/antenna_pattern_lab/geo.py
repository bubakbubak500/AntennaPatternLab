from __future__ import annotations

from math import acos, asin, atan2, cos, degrees, radians, sin, sqrt
import re

EARTH_RADIUS_KM = 6371.0088
_GRID_RE = re.compile(r"^[A-R]{2}(?:\d{2}(?:[A-X]{2}(?:\d{2})?)?)?$", re.IGNORECASE)


def maidenhead_to_latlon(locator: str) -> tuple[float, float]:
    """Return the center latitude/longitude of a 2, 4, 6 or 8-char grid."""
    grid = locator.strip().upper()
    if len(grid) not in (2, 4, 6, 8) or not _GRID_RE.fullmatch(grid):
        raise ValueError(f"Neplatný Maidenhead lokátor: {locator!r}")

    lon = (ord(grid[0]) - ord("A")) * 20.0 - 180.0
    lat = (ord(grid[1]) - ord("A")) * 10.0 - 90.0
    lon_size, lat_size = 20.0, 10.0

    if len(grid) >= 4:
        lon += int(grid[2]) * 2.0
        lat += int(grid[3]) * 1.0
        lon_size, lat_size = 2.0, 1.0
    if len(grid) >= 6:
        lon += (ord(grid[4]) - ord("A")) * (2.0 / 24.0)
        lat += (ord(grid[5]) - ord("A")) * (1.0 / 24.0)
        lon_size, lat_size = 2.0 / 24.0, 1.0 / 24.0
    if len(grid) == 8:
        lon += int(grid[6]) * (2.0 / 240.0)
        lat += int(grid[7]) * (1.0 / 240.0)
        lon_size, lat_size = 2.0 / 240.0, 1.0 / 240.0

    return lat + lat_size / 2.0, lon + lon_size / 2.0


def distance_and_bearing(
    origin: tuple[float, float], destination: tuple[float, float]
) -> tuple[float, float]:
    """Great-circle distance in km and initial bearing in degrees."""
    lat1, lon1 = map(radians, origin)
    lat2, lon2 = map(radians, destination)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    distance = 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))
    y = sin(dlon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    bearing = (degrees(atan2(y, x)) + 360.0) % 360.0
    return distance, bearing


def grid_distance_and_bearing(origin_grid: str, destination_grid: str) -> tuple[float, float]:
    return distance_and_bearing(
        maidenhead_to_latlon(origin_grid), maidenhead_to_latlon(destination_grid)
    )


def great_circle_segments(
    origin: tuple[float, float],
    destination: tuple[float, float],
    point_count: int = 81,
) -> list[list[tuple[float, float]]]:
    """Return latitude/longitude segments for a great-circle route.

    The result is split at the antimeridian so an equirectangular map never
    draws a misleading line across the whole world.
    """
    if point_count < 2:
        raise ValueError("Great-circle path needs at least two points.")

    def unit_vector(point: tuple[float, float]) -> tuple[float, float, float]:
        latitude, longitude = map(radians, point)
        return (
            cos(latitude) * cos(longitude),
            cos(latitude) * sin(longitude),
            sin(latitude),
        )

    start = unit_vector(origin)
    end = unit_vector(destination)
    dot = max(-1.0, min(1.0, sum(a * b for a, b in zip(start, end))))
    angle = acos(dot)
    sin_angle = sin(angle)
    points: list[tuple[float, float]] = []
    for index in range(point_count):
        fraction = index / (point_count - 1)
        if abs(sin_angle) < 1e-12:
            vector = tuple(
                (1.0 - fraction) * a + fraction * b
                for a, b in zip(start, end)
            )
        else:
            left = sin((1.0 - fraction) * angle) / sin_angle
            right = sin(fraction * angle) / sin_angle
            vector = tuple(left * a + right * b for a, b in zip(start, end))
        x, y, z = vector
        length = sqrt(x * x + y * y + z * z) or 1.0
        x, y, z = x / length, y / length, z / length
        points.append((degrees(atan2(z, sqrt(x * x + y * y))), degrees(atan2(y, x))))

    segments: list[list[tuple[float, float]]] = [[]]
    for point in points:
        if segments[-1] and abs(point[1] - segments[-1][-1][1]) > 180:
            segments.append([])
        segments[-1].append(point)
    return [segment for segment in segments if len(segment) >= 2]
