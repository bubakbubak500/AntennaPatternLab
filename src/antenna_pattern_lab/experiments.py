from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .models import representative_frequency_hz, theoretical_azimuth_model
from .profiles import AntennaProfile


@dataclass(frozen=True, slots=True)
class ExperimentGoal:
    band: str
    bearing_deg: int
    min_distance_km: int
    max_distance_km: int
    max_swr: float

    def validated(self) -> "ExperimentGoal":
        if not self.band.strip():
            raise ValueError("Band is required.")
        if not 0 <= self.bearing_deg < 360:
            raise ValueError("Bearing must be between 0 and 359 degrees.")
        if self.min_distance_km < 0 or self.max_distance_km <= self.min_distance_km:
            raise ValueError("Distance range is invalid.")
        if not 1.0 <= self.max_swr <= 10.0:
            raise ValueError("Maximum SWR must be between 1.0 and 10.0.")
        return self


@dataclass(frozen=True, slots=True)
class ExperimentRecommendation:
    profile_a_id: int
    profile_b_id: int
    basis: str
    notes: tuple[str, ...]


def recommend_next_experiment(
    profiles: Iterable[AntennaProfile], goal: ExperimentGoal, mode: str = "FT8"
) -> ExperimentRecommendation | None:
    """Choose a useful A/B contrast without claiming a predicted gain.

    The simplified model is used only to rank candidates at the requested
    bearing. It does not estimate real-world improvement or enforce SWR.
    """
    goal = goal.validated()
    available = [profile for profile in profiles if profile.id is not None]
    if len(available) < 2:
        return None
    frequency_hz = representative_frequency_hz(goal.band, mode)
    ranked: list[tuple[float, AntennaProfile]] = []
    for profile in available:
        model = theoretical_azimuth_model(profile, frequency_hz)
        if model is None:
            continue
        point = min(
            model.points,
            key=lambda item: abs(((item.bearing_deg - goal.bearing_deg + 180) % 360) - 180),
        )
        ranked.append((point.relative_gain_db, profile))
    if len(ranked) >= 2:
        ranked.sort(key=lambda item: (item[0], item[1].id))
        profile_a = ranked[0][1]
        profile_b = ranked[-1][1]
        basis = "model_contrast"
    else:
        profile_a, profile_b = available[:2]
        basis = "available_profiles"
    return ExperimentRecommendation(
        profile_a_id=int(profile_a.id),
        profile_b_id=int(profile_b.id),
        basis=basis,
        notes=("verify_swr", "keep_power_constant", "alternate_profiles", "no_gain_claim"),
    )


@dataclass(frozen=True, slots=True)
class TxSessionSummary:
    id: int
    started_at: datetime
    ended_at: datetime | None
    profile_id: int | None
    profile_name: str
    mode: str
    frequency_hz: int
    rotator_start_azimuth_deg: float | None
    rotator_start_elevation_deg: float | None
    rotator_end_azimuth_deg: float | None
    rotator_end_elevation_deg: float | None
    rotator_max_deviation_deg: float | None
    power_w: float | None
    spot_count: int
    unique_receivers: int
    average_snr_db: float | None

    @property
    def duration_seconds(self) -> float | None:
        if self.ended_at is None:
            return None
        return max(0.0, (self.ended_at - self.started_at).total_seconds())

    @property
    def quality_flags(self) -> tuple[str, ...]:
        flags = []
        if self.ended_at is None:
            flags.append("open")
        if self.profile_id is None:
            flags.append("no_profile")
        if self.spot_count == 0:
            flags.append("no_spots")
        if self.duration_seconds is not None and self.duration_seconds < 5:
            flags.append("short")
        if (
            self.rotator_max_deviation_deg is not None
            and self.rotator_max_deviation_deg > 3.0
        ):
            flags.append("rotator_moved")
        return tuple(flags)

    @property
    def quality_score(self) -> int:
        penalties = {
            "open": 15,
            "no_profile": 35,
            "no_spots": 35,
            "short": 15,
            "rotator_moved": 20,
        }
        return max(0, 100 - sum(penalties[flag] for flag in self.quality_flags))


class AlternationProtocol:
    """State machine for a confirm-before-recording A/B switching protocol."""

    def __init__(self, profile_a_id: int, profile_b_id: int, interval_seconds: int):
        if profile_a_id == profile_b_id:
            raise ValueError("A and B profiles must be different.")
        if interval_seconds < 1:
            raise ValueError("Interval must be positive.")
        self.profile_ids = (profile_a_id, profile_b_id)
        self.interval_seconds = interval_seconds
        self.target_index = 0
        self.active_index: int | None = None
        self.remaining_seconds = 0
        self.state = "idle"

    @property
    def target_profile_id(self) -> int:
        return self.profile_ids[self.target_index]

    @property
    def active_profile_id(self) -> int | None:
        return None if self.active_index is None else self.profile_ids[self.active_index]

    def start(self) -> int:
        self.target_index = 0
        self.active_index = None
        self.remaining_seconds = 0
        self.state = "awaiting_confirmation"
        return self.target_profile_id

    def confirm_switch(self) -> int:
        if self.state != "awaiting_confirmation":
            raise RuntimeError("No antenna switch is awaiting confirmation.")
        self.active_index = self.target_index
        self.remaining_seconds = self.interval_seconds
        self.state = "running"
        return self.active_profile_id

    def tick(self, elapsed_seconds: int = 1) -> int | None:
        if self.state != "running":
            return None
        self.remaining_seconds = max(0, self.remaining_seconds - max(0, elapsed_seconds))
        if self.remaining_seconds:
            return None
        self.target_index = 1 - int(self.active_index)
        self.state = "awaiting_confirmation"
        return self.target_profile_id

    def stop(self) -> None:
        self.state = "idle"
        self.remaining_seconds = 0
        self.active_index = None
