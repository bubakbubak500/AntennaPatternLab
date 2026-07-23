from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil

from .analysis import LocatedSpot
from .campaigns import MeasurementCampaign, assess_campaign_progress
from .coverage import (
    analyze_angular_coverage,
    analyze_coverage_matrix,
    priority_matrix_cells,
    priority_sectors,
)
from .geo import maidenhead_to_latlon


@dataclass(frozen=True, slots=True)
class WindowCandidate:
    solar_slot: int
    score_percent: float
    report_count: int
    unique_receivers: int
    missing_priority_sectors: int
    distance_gap_percent: float

    @property
    def solar_label(self) -> str:
        start = self.solar_slot * 30
        end = (start + 30) % (24 * 60)
        return (
            f"{start // 60:02d}:{start % 60:02d}–"
            f"{end // 60:02d}:{end % 60:02d}"
        )

    @property
    def solar_period(self) -> str:
        return "day" if 12 <= self.solar_slot < 36 else "night"


@dataclass(frozen=True, slots=True)
class MeasurementWindowRecommendation:
    candidates: tuple[WindowCandidate, ...]
    recommended: WindowCandidate
    next_start_utc: datetime
    suggested_duration_minutes: int
    spot_rate_per_hour: float | None
    estimated_hours_to_numeric_goal: float | None
    target_bearings: tuple[float, ...]
    target_distance_codes: tuple[str, ...]
    confidence: str
    missing_goal_parts: tuple[str, ...]


def recommend_measurement_window(
    campaign: MeasurementCampaign,
    located: list[LocatedSpot],
    now: datetime | None = None,
) -> MeasurementWindowRecommendation:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    longitude = _longitude(campaign.tx_grid)
    slot_items: list[list[LocatedSpot]] = [[] for _ in range(48)]
    for item in located:
        slot_items[_solar_slot(item, longitude)].append(item)

    angular = analyze_angular_coverage(located, 30)
    weak_sectors = priority_sectors(angular, 3)
    weak_indices = {
        min(int(sector.center_deg // 30), 11)
        for sector in weak_sectors
    }
    matrix = analyze_coverage_matrix(located, 30)
    maximum_receivers = max(
        (len({item.spot.rx_call for item in items}) for items in slot_items),
        default=0,
    )
    maximum_reports = max((len(items) for items in slot_items), default=0)
    candidates: list[WindowCandidate] = []
    for slot, items in enumerate(slot_items):
        represented_sectors = {
            min(int(item.bearing_deg // 30), 11)
            for item in items
        }
        missing_weak = len(weak_indices - represented_sectors)
        period = "day" if 12 <= slot < 36 else "night"
        period_cells = [cell for cell in matrix if cell.solar_period == period]
        distance_gap = (
            100.0
            - sum(cell.completeness_percent for cell in period_cells)
            / len(period_cells)
        )
        receivers = len({item.spot.rx_call for item in items})
        gap_need = 0.65 * (missing_weak / max(1, len(weak_indices))) + 0.35 * (
            distance_gap / 100.0
        )
        availability = receivers / maximum_receivers if maximum_receivers else 0.0
        observed_yield = len(items) / maximum_reports if maximum_reports else 0.0
        # A gap says *what* should be measured, while receiver availability
        # says *when* the measurement has a realistic chance of collecting it.
        # Giving availability the larger share prevents an entirely unobserved
        # half-hour from winning solely because it contains no evidence yet.
        score = 100.0 * (
            0.45 * gap_need + 0.40 * availability + 0.15 * observed_yield
        )
        candidates.append(
            WindowCandidate(
                solar_slot=slot,
                score_percent=score,
                report_count=len(items),
                unique_receivers=receivers,
                missing_priority_sectors=missing_weak,
                distance_gap_percent=distance_gap,
            )
        )
    ranked = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score_percent,
                -candidate.unique_receivers,
                -candidate.report_count,
                candidate.solar_slot,
            ),
        )
    )
    recommended = ranked[0]

    progress = assess_campaign_progress(campaign, located)
    epoch_blocks = {
        int(item.spot.observed_at.timestamp()) // 1800
        for item in located
    }
    measured_hours = len(epoch_blocks) * 0.5
    rate = (
        len(located) / measured_hours
        if located and measured_hours > 0
        else None
    )
    remaining_spots = max(0, campaign.target_spots - len(located))
    remaining_blocks = max(0, campaign.target_time_blocks - len(epoch_blocks))
    estimates = [remaining_blocks * 0.5]
    if rate:
        estimates.append(remaining_spots / rate)
    estimated_hours = max(estimates) if estimates else None
    if progress.complete:
        estimated_hours = 0.0

    suggested_duration = min(
        120,
        max(
            30,
            int(ceil(max(0.5, estimated_hours or 0.5) * 2) * 30),
        ),
    )
    next_start = _next_utc_start(recommended.solar_slot, longitude, now)
    target_bearings = tuple(sector.center_deg for sector in weak_sectors)
    target_distances: list[str] = []
    for cell in priority_matrix_cells(
        [
            cell
            for cell in matrix
            if cell.solar_period == recommended.solar_period
        ],
        8,
    ):
        if cell.distance_code not in target_distances:
            target_distances.append(cell.distance_code)
        if len(target_distances) == 2:
            break
    confidence = (
        "high"
        if len(epoch_blocks) >= 8 and maximum_receivers >= 5
        else "medium"
        if len(epoch_blocks) >= 3 and maximum_receivers >= 2
        else "low"
    )
    return MeasurementWindowRecommendation(
        candidates=ranked,
        recommended=recommended,
        next_start_utc=next_start,
        suggested_duration_minutes=suggested_duration,
        spot_rate_per_hour=rate,
        estimated_hours_to_numeric_goal=estimated_hours,
        target_bearings=target_bearings,
        target_distance_codes=tuple(target_distances),
        confidence=confidence,
        missing_goal_parts=progress.missing,
    )


def _longitude(tx_grid: str) -> float:
    try:
        _latitude, longitude = maidenhead_to_latlon(tx_grid)
        return longitude
    except ValueError:
        return 0.0


def _solar_slot(item: LocatedSpot, fallback_longitude: float) -> int:
    longitude = _longitude(item.spot.tx_grid) if item.spot.tx_grid else fallback_longitude
    local_minutes = (
        item.spot.observed_at.hour * 60
        + item.spot.observed_at.minute
        + longitude * 4.0
    ) % (24 * 60)
    return int(local_minutes // 30)


def _next_utc_start(
    solar_slot: int,
    longitude: float,
    now: datetime,
) -> datetime:
    solar_minutes = solar_slot * 30
    utc_minutes = (solar_minutes - longitude * 4.0) % (24 * 60)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        minutes=round(utc_minutes)
    )
    if start <= now:
        start += timedelta(days=1)
    return start
