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
