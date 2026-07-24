from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil


@dataclass(frozen=True, slots=True)
class NecPoint:
    bearing_deg: float
    relative_gain_db: float
    absolute_gain_db: float


@dataclass(frozen=True, slots=True)
class NecPattern:
    points: tuple[NecPoint, ...]
    source: str


@dataclass(frozen=True, slots=True)
class NecModelParameters:
    frequency_hz: int | None
    polarization: str
    antenna_height_m: float | None
    ground_model: str
    orientation_deg: float
    source: str


@dataclass(frozen=True, slots=True)
class NecBaseline:
    azimuth: NecPattern
    elevation: NecPattern
    parameters: NecModelParameters
    front_to_back_db: float | None


def detect_nec2c() -> Path | None:
    found = shutil.which("nec2c.exe") or shutil.which("nec2c")
    return Path(found).resolve() if found else None


def parse_nec_output(text: str, theta_deg: float = 90.0, tolerance: float = 0.2) -> NecPattern:
    """Parse the normal NEC radiation-pattern table at one elevation cut."""
    in_pattern = False
    values: list[tuple[float, float]] = []
    for line in text.splitlines():
        upper = line.upper()
        if "RADIATION PATTERNS" in upper:
            in_pattern = True
            continue
        if not in_pattern:
            continue
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", line)
        if len(numbers) < 5:
            continue
        try:
            theta, phi, total_gain = float(numbers[0]), float(numbers[1]), float(numbers[4])
        except ValueError:
            continue
        if abs(theta - theta_deg) <= tolerance and total_gain > -900:
            values.append((phi % 360.0, total_gain))
    if len(values) < 2:
        raise ValueError("No usable NEC radiation-pattern azimuth cut was found.")
    by_bearing: dict[float, float] = {}
    for bearing, gain in values:
        by_bearing[bearing] = max(gain, by_bearing.get(bearing, float("-inf")))
    peak = max(by_bearing.values())
    points = tuple(
        NecPoint(bearing, max(-60.0, gain - peak), gain)
        for bearing, gain in sorted(by_bearing.items())
    )
    return NecPattern(points, "NEC normal radiation-pattern output")


def parse_nec_baseline(
    text: str,
    *,
    frequency_hz: int | None = None,
    polarization: str = "documented in NEC source",
    antenna_height_m: float | None = None,
    ground_model: str = "documented in NEC source",
    orientation_deg: float = 0.0,
    source: str = "NEC normal radiation-pattern output",
    tolerance: float = 0.2,
) -> NecBaseline:
    """Parse aligned azimuth and elevation cuts with explicit provenance.

    The azimuth cut is the horizontal ``theta=90°`` pattern. The elevation cut
    follows the requested orientation. If a frequency is not supplied, the
    first normal NEC ``FREQUENCY`` line is used when present.
    """
    rows = _radiation_rows(text)
    azimuth_rows = [
        ((phi + orientation_deg) % 360.0, gain)
        for theta, phi, gain in rows
        if abs(theta - 90.0) <= tolerance
    ]
    elevation_rows = [
        (theta, gain)
        for theta, phi, gain in rows
        if _angular_distance(phi, 0.0) <= tolerance
    ]
    if len(azimuth_rows) < 2 or len(elevation_rows) < 2:
        raise ValueError("NEC output does not contain usable azimuth and elevation cuts.")
    azimuth = _pattern_from_rows(azimuth_rows, source + " · azimuth")
    elevation = _pattern_from_rows(elevation_rows, source + " · elevation")
    parsed_frequency = frequency_hz or _frequency_from_output(text)
    front = _gain_at(azimuth, orientation_deg)
    back = _gain_at(azimuth, (orientation_deg + 180.0) % 360.0)
    front_to_back = (
        front.absolute_gain_db - back.absolute_gain_db
        if front is not None and back is not None
        else None
    )
    return NecBaseline(
        azimuth,
        elevation,
        NecModelParameters(
            parsed_frequency,
            polarization.strip() or "unspecified",
            antenna_height_m,
            ground_model.strip() or "unspecified",
            orientation_deg % 360.0,
            source,
        ),
        front_to_back,
    )


def _radiation_rows(text: str) -> list[tuple[float, float, float]]:
    in_pattern = False
    rows = []
    for line in text.splitlines():
        if "RADIATION PATTERNS" in line.upper():
            in_pattern = True
            continue
        if not in_pattern:
            continue
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", line)
        if len(numbers) < 5:
            continue
        try:
            theta, phi, gain = float(numbers[0]), float(numbers[1]), float(numbers[4])
        except ValueError:
            continue
        if gain > -900:
            rows.append((theta, phi % 360.0, gain))
    return rows


def _pattern_from_rows(
    rows: list[tuple[float, float]], source: str
) -> NecPattern:
    by_angle: dict[float, float] = {}
    for angle, gain in rows:
        by_angle[angle] = max(gain, by_angle.get(angle, float("-inf")))
    peak = max(by_angle.values())
    return NecPattern(
        tuple(
            NecPoint(angle, max(-60.0, gain - peak), gain)
            for angle, gain in sorted(by_angle.items())
        ),
        source,
    )


def _frequency_from_output(text: str) -> int | None:
    match = re.search(
        r"FREQUENCY\s*(?:=|:)?\s*([-+]?\d+(?:\.\d+)?)\s*(MHZ|KHZ|HZ)?",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None
    value = float(match.group(1))
    unit = (match.group(2) or "MHZ").upper()
    multiplier = {"HZ": 1, "KHZ": 1_000, "MHZ": 1_000_000}[unit]
    return round(value * multiplier)


def _gain_at(pattern: NecPattern, angle: float) -> NecPoint | None:
    return min(
        pattern.points,
        key=lambda point: _angular_distance(point.bearing_deg, angle),
        default=None,
    )


def _angular_distance(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)
