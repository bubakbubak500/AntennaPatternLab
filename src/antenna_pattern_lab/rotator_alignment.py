from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from .analysis import LocatedSpot, time_normalized_sector_profile
from .experiments import TxSessionSummary
from .profiles import AntennaProfile, expected_main_bearings


@dataclass(frozen=True, slots=True)
class RotatorAlignment:
    applicable: bool
    target_azimuth_deg: float | None
    actual_azimuth_deg: float | None
    empirical_peak_deg: float | None
    target_error_deg: float | None
    empirical_error_deg: float | None
    session_count: int
    spot_count: int
    unique_receivers: int
    confidence: str
    warnings: tuple[str, ...]


def analyze_rotator_alignment(
    profile: AntennaProfile,
    sessions: list[TxSessionSummary],
    located: list[LocatedSpot],
) -> RotatorAlignment:
    expected_bearings = expected_main_bearings(profile)
    target = (
        profile.orientation_deg % 360.0
        if profile.orientation_deg is not None and expected_bearings
        else None
    )
    actual_values = [
        session.rotator_start_azimuth_deg
        for session in sessions
        if session.rotator_start_azimuth_deg is not None
    ]
    actual, concentration = _circular_mean(actual_values)
    target_error = (
        _angular_distance(target, actual)
        if target is not None and actual is not None
        else None
    )

    receivers = len({item.spot.rx_call for item in located})
    blocks = len(
        {int(item.spot.observed_at.timestamp()) // 1800 for item in located}
    )
    sectors = time_normalized_sector_profile(located, 30)
    supported = [sector for sector in sectors if sector.count >= 3]
    empirical = None
    if len(located) >= 12 and receivers >= 3 and len(supported) >= 3:
        # Alignment must never use a peak extrapolated beyond observed angular
        # support. Choose only among evidence-backed sector centres; expected
        # bearings break equal-SNR ties but cannot create a new peak.
        best_level = max(
            sector.median_snr_db
            for sector in supported
            if sector.median_snr_db is not None
        )
        candidates = [
            sector
            for sector in supported
            if sector.median_snr_db is not None
            and sector.median_snr_db >= best_level - 0.5
        ]
        empirical = min(
            candidates,
            key=lambda sector: (
                min(
                    (
                        _angular_distance(sector.center_deg, expected)
                        for expected in expected_bearings
                    ),
                    default=0.0,
                ),
                sector.center_deg,
            ),
        ).center_deg
    empirical_error = (
        min(_angular_distance(empirical, expected) for expected in expected_bearings)
        if empirical is not None and expected_bearings
        else None
    )

    confidence = (
        "high"
        if len(located) >= 60 and receivers >= 8 and blocks >= 8
        else "medium"
        if len(located) >= 20 and receivers >= 4 and blocks >= 3
        else "low"
    )
    warnings = []
    if target_error is not None and target_error > 5.0:
        warnings.append("target_mismatch")
    if concentration is not None and concentration < 0.8:
        warnings.append("variable_position")
    if empirical_error is not None and empirical_error > 45.0:
        warnings.append("empirical_mismatch")
    if empirical is None:
        warnings.append("insufficient_empirical_data")
    return RotatorAlignment(
        applicable=bool(expected_bearings),
        target_azimuth_deg=target,
        actual_azimuth_deg=actual,
        empirical_peak_deg=empirical,
        target_error_deg=target_error,
        empirical_error_deg=empirical_error,
        session_count=len(actual_values),
        spot_count=len(located),
        unique_receivers=receivers,
        confidence=confidence,
        warnings=tuple(warnings),
    )


def _angular_distance(first: float, second: float) -> float:
    return abs(((first - second + 180.0) % 360.0) - 180.0)


def _circular_mean(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    x = sum(cos(radians(value)) for value in values)
    y = sum(sin(radians(value)) for value in values)
    length = hypot(x, y)
    if length < 1e-9:
        return None, 0.0
    return degrees(atan2(y, x)) % 360.0, length / len(values)
