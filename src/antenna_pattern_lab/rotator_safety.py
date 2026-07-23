from __future__ import annotations

from dataclasses import dataclass

from .profiles import AntennaProfile, expected_main_bearings


@dataclass(frozen=True, slots=True)
class RotatorSafety:
    severity: str
    warnings: tuple[str, ...]
    target_error_deg: float | None
    movement_deg: float


def mechanical_target(profile: AntennaProfile | None) -> float | None:
    if (
        profile is None
        or profile.orientation_deg is None
        or not expected_main_bearings(profile)
    ):
        return None
    return profile.orientation_deg % 360.0


def evaluate_rotator_safety(
    *,
    current_azimuth_deg: float | None,
    target_azimuth_deg: float | None,
    movement_deg: float = 0.0,
    transmitting: bool = False,
    movement_limit_deg: float = 3.0,
    target_tolerance_deg: float = 5.0,
) -> RotatorSafety:
    target_error = (
        angular_distance(current_azimuth_deg, target_azimuth_deg)
        if current_azimuth_deg is not None and target_azimuth_deg is not None
        else None
    )
    warnings = []
    if transmitting and movement_deg > movement_limit_deg:
        warnings.append("moving_during_tx")
    if target_error is not None and target_error > target_tolerance_deg:
        warnings.append("profile_mismatch")
    severity = (
        "error"
        if transmitting and warnings
        else "warning"
        if warnings
        else "none"
    )
    return RotatorSafety(
        severity=severity,
        warnings=tuple(warnings),
        target_error_deg=target_error,
        movement_deg=max(0.0, movement_deg),
    )


def angular_distance(first: float, second: float) -> float:
    return abs(((first - second + 180.0) % 360.0) - 180.0)
