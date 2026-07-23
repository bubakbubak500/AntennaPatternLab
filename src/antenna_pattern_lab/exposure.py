from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt

from .geo import grid_distance_and_bearing


@dataclass(frozen=True, slots=True)
class ActivityWindow:
    receiver_call: str
    receiver_grid: str
    band: str
    mode: str
    window_start: datetime
    report_count: int


@dataclass(frozen=True, slots=True)
class ExposureObservation:
    session_id: int
    profile_id: int | None
    receiver_call: str
    receiver_grid: str
    detected: bool
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class ExposureSector:
    center_deg: float
    opportunities: int
    detections: int
    unique_receivers: int
    detection_rate: float | None
    confidence_low: float | None
    confidence_high: float | None


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def exposure_sector_profile(
    observations: list[ExposureObservation], tx_grid: str, sector_width_deg: int = 30
) -> list[ExposureSector]:
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    buckets: list[list[ExposureObservation]] = [
        [] for _ in range(360 // sector_width_deg)
    ]
    for observation in observations:
        try:
            _distance, bearing = grid_distance_and_bearing(tx_grid, observation.receiver_grid)
        except ValueError:
            continue
        buckets[min(int(bearing // sector_width_deg), len(buckets) - 1)].append(observation)
    result = []
    for index, bucket in enumerate(buckets):
        detections = sum(item.detected for item in bucket)
        low, high = wilson_interval(detections, len(bucket))
        result.append(
            ExposureSector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                opportunities=len(bucket),
                detections=detections,
                unique_receivers=len({item.receiver_call for item in bucket}),
                detection_rate=(detections / len(bucket) if bucket else None),
                confidence_low=low,
                confidence_high=high,
            )
        )
    return result
