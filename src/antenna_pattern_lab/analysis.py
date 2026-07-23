from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp, log10
from random import Random
from statistics import median
from typing import Iterable, Mapping

from .domain import Spot
from .geo import grid_distance_and_bearing


@dataclass(frozen=True, slots=True)
class LocatedSpot:
    spot: Spot
    distance_km: float
    bearing_deg: float


@dataclass(frozen=True, slots=True)
class Sector:
    center_deg: float
    count: int
    unique_receivers: int
    median_snr_db: float | None
    best_snr_db: int | None
    max_distance_km: float | None
    quality_score: float
    quality_label: str
    confidence_low_db: float | None
    confidence_high_db: float | None
    time_block_count: int


@dataclass(frozen=True, slots=True)
class SmoothedPatternPoint:
    """A circular power-domain estimate at one bearing.

    ``level_db`` is intentionally ``None`` outside the angular support of the
    observations. Missing sectors therefore never become an artificial deep
    null at the centre of a polar chart.
    """

    bearing_deg: float
    level_db: float | None
    support: float


@dataclass(frozen=True, slots=True)
class ReceiverStability:
    receiver_call: str
    report_count: int
    comparable_blocks: int
    relative_baseline_db: float | None
    variability_mad_db: float | None
    reliability_weight: float
    stability_label: str


@dataclass(frozen=True, slots=True)
class ControlTrendPoint:
    block_index: int
    adjustment_db: float
    receiver_count: int


@dataclass(frozen=True, slots=True)
class ReceiverControlGroup:
    receiver_calls: tuple[str, ...]
    angular_sector_count: int
    comparable_block_count: int
    ready: bool
    reason_code: str
    trend: tuple[ControlTrendPoint, ...]


@dataclass(frozen=True, slots=True)
class PairedSpot:
    receiver_call: str
    bearing_deg: float
    time_gap_seconds: float
    snr_a_db: int
    snr_b_db: int
    observed_at: datetime | None = None

    @property
    def delta_db(self) -> int:
        return self.snr_b_db - self.snr_a_db


@dataclass(frozen=True, slots=True)
class AbComparison:
    pairs: list[PairedSpot]
    median_delta_db: float | None
    unique_receivers: int
    confidence_low_db: float | None = None
    confidence_high_db: float | None = None
    pair_median_delta_db: float | None = None


@dataclass(frozen=True, slots=True)
class MeasurementRecommendation:
    ready: bool
    target_pairs: int
    target_receivers: int
    additional_pairs: int
    additional_receivers: int
    estimated_additional_hours: float | None


@dataclass(frozen=True, slots=True)
class AbSector:
    center_deg: float
    count: int
    unique_receivers: int
    median_delta_db: float | None
    confidence_low_db: float | None
    confidence_high_db: float | None


def locate_spot(spot: Spot, fallback_tx_grid: str = "") -> LocatedSpot | None:
    tx_grid = spot.tx_grid or fallback_tx_grid
    if not tx_grid or not spot.rx_grid:
        return None
    try:
        distance, bearing = grid_distance_and_bearing(tx_grid, spot.rx_grid)
    except ValueError:
        return None
    return LocatedSpot(spot=spot, distance_km=distance, bearing_deg=bearing)


def sector_profile(
    spots: Iterable[LocatedSpot], sector_width_deg: int = 10
) -> list[Sector]:
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Šířka sektoru musí být kladný dělitel 360.")
    buckets: list[list[LocatedSpot]] = [[] for _ in range(360 // sector_width_deg)]
    for item in spots:
        index = min(int(item.bearing_deg // sector_width_deg), len(buckets) - 1)
        buckets[index].append(item)

    result: list[Sector] = []
    for index, bucket in enumerate(buckets):
        snrs = [item.spot.snr_db for item in bucket]
        distances = [item.distance_km for item in bucket]
        unique_receivers = len({item.spot.rx_call for item in bucket})
        quality_score, quality_label = sector_quality(len(bucket), unique_receivers)
        confidence_low, confidence_high = bootstrap_median_interval(snrs, samples=500)
        time_blocks = {
            int(item.spot.observed_at.timestamp()) // (30 * 60) for item in bucket
        }
        result.append(
            Sector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                count=len(bucket),
                unique_receivers=unique_receivers,
                median_snr_db=float(median(snrs)) if snrs else None,
                best_snr_db=max(snrs) if snrs else None,
                max_distance_km=max(distances) if distances else None,
                quality_score=quality_score,
                quality_label=quality_label,
                confidence_low_db=confidence_low,
                confidence_high_db=confidence_high,
                time_block_count=len(time_blocks),
            )
        )
    return result


def smooth_sector_pattern(
    sectors: Iterable[Sector],
    *,
    step_deg: int = 2,
    kernel_width_deg: float | None = None,
    max_gap_deg: float | None = None,
) -> list[SmoothedPatternPoint]:
    """Interpolate observed sectors on a circle without inventing point nulls.

    SNR is a power ratio, so the kernel regression is performed in linear
    power and converted back to dB afterwards. Sector sample count and quality
    modestly influence the estimate. Bearings too far from every observation
    remain unsupported instead of being forced to -30 dB.
    """

    items = list(sectors)
    if step_deg <= 0 or 360 % step_deg:
        raise ValueError("Pattern step must be a positive divisor of 360.")
    observed = [
        sector
        for sector in items
        if sector.median_snr_db is not None and sector.count > 0
    ]
    if not observed:
        return [
            SmoothedPatternPoint(float(bearing), None, 0.0)
            for bearing in range(0, 361, step_deg)
        ]
    centers = sorted(sector.center_deg % 360.0 for sector in items)
    sector_spacing = (
        min(
            (centers[(index + 1) % len(centers)] - centers[index]) % 360.0
            for index in range(len(centers))
        )
        if len(centers) > 1
        else 10.0
    )
    sigma = float(kernel_width_deg or max(18.0, sector_spacing * 1.35))
    gap_limit = float(max_gap_deg or max(55.0, sigma * 2.75))
    if sigma <= 0 or not 0 < gap_limit <= 180:
        raise ValueError("Kernel width and maximum gap must be positive.")

    result: list[SmoothedPatternPoint] = []
    for bearing in range(0, 361, step_deg):
        distances = [
            abs((bearing - sector.center_deg + 180.0) % 360.0 - 180.0)
            for sector in observed
        ]
        nearest = min(distances)
        if nearest > gap_limit:
            result.append(SmoothedPatternPoint(float(bearing), None, 0.0))
            continue
        weighted_power = 0.0
        weight_sum = 0.0
        kernel_sum = 0.0
        for sector, distance in zip(observed, distances):
            kernel = exp(-0.5 * (distance / sigma) ** 2)
            reliability = max(0.25, sector.quality_score) * (sector.count ** 0.5)
            weight = kernel * reliability
            weighted_power += weight * (10.0 ** (float(sector.median_snr_db) / 10.0))
            weight_sum += weight
            kernel_sum += kernel
        level_db = 10.0 * log10(max(weighted_power / weight_sum, 1e-12))
        support = min(1.0, kernel_sum / 1.5)
        result.append(SmoothedPatternPoint(float(bearing), level_db, support))
    return result


def time_normalized_sector_profile(
    spots: Iterable[LocatedSpot],
    sector_width_deg: int = 10,
    block_minutes: int = 30,
) -> list[Sector]:
    """Give each time block equal weight before combining sector SNR values."""
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    if block_minutes <= 0:
        raise ValueError("Time block must be positive.")
    sector_count = 360 // sector_width_deg
    buckets: list[dict[int, list[LocatedSpot]]] = [dict() for _ in range(sector_count)]
    for item in spots:
        sector_index = min(int(item.bearing_deg // sector_width_deg), sector_count - 1)
        block = int(item.spot.observed_at.timestamp()) // (block_minutes * 60)
        buckets[sector_index].setdefault(block, []).append(item)
    result = []
    for index, blocks in enumerate(buckets):
        items = [item for block_items in blocks.values() for item in block_items]
        block_medians = [
            float(median(item.spot.snr_db for item in block_items))
            for block_items in blocks.values()
        ]
        unique_receivers = len({item.spot.rx_call for item in items})
        quality_score, quality_label = sector_quality(len(blocks), unique_receivers)
        low, high = bootstrap_median_interval(block_medians, samples=500)
        result.append(
            Sector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                count=len(items),
                unique_receivers=unique_receivers,
                median_snr_db=(float(median(block_medians)) if block_medians else None),
                best_snr_db=(max(item.spot.snr_db for item in items) if items else None),
                max_distance_km=(max(item.distance_km for item in items) if items else None),
                quality_score=quality_score,
                quality_label=quality_label,
                confidence_low_db=low,
                confidence_high_db=high,
                time_block_count=len(blocks),
            )
        )
    return result


def trend_adjusted_sector_profile(
    spots: Iterable[LocatedSpot],
    sector_width_deg: int = 10,
    block_minutes: int = 30,
    smoothing_blocks: int = 3,
) -> list[Sector]:
    """Remove a robust, slowly varying common SNR trend before sectoring.

    A global median is calculated per time block and smoothed with neighboring
    blocks. Each report is shifted back to the overall median. This addresses a
    shared temporal drift only; it cannot identify receiver-specific changes.
    """
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    if block_minutes <= 0 or smoothing_blocks < 1 or smoothing_blocks % 2 == 0:
        raise ValueError("Block length must be positive and smoothing window odd.")
    items = list(spots)
    sector_count = 360 // sector_width_deg
    if not items:
        return sector_profile([], sector_width_deg)
    block_seconds = block_minutes * 60
    by_block: dict[int, list[int]] = {}
    for item in items:
        block = int(item.spot.observed_at.timestamp()) // block_seconds
        by_block.setdefault(block, []).append(item.spot.snr_db)
    block_medians = {block: float(median(values)) for block, values in by_block.items()}
    radius = smoothing_blocks // 2
    trend = {
        block: float(
            median(
                value
                for neighbor, value in block_medians.items()
                if abs(neighbor - block) <= radius
            )
        )
        for block in block_medians
    }
    baseline = float(median(item.spot.snr_db for item in items))
    buckets: list[list[tuple[LocatedSpot, float]]] = [[] for _ in range(sector_count)]
    for item in items:
        block = int(item.spot.observed_at.timestamp()) // block_seconds
        adjusted = item.spot.snr_db - trend[block] + baseline
        index = min(int(item.bearing_deg // sector_width_deg), sector_count - 1)
        buckets[index].append((item, adjusted))
    result = []
    for index, bucket in enumerate(buckets):
        adjusted_values = [value for _item, value in bucket]
        original_items = [item for item, _value in bucket]
        unique_receivers = len({item.spot.rx_call for item in original_items})
        quality_score, quality_label = sector_quality(len(bucket), unique_receivers)
        low, high = bootstrap_median_interval(adjusted_values, samples=500)
        result.append(
            Sector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                count=len(bucket),
                unique_receivers=unique_receivers,
                median_snr_db=(float(median(adjusted_values)) if adjusted_values else None),
                best_snr_db=(round(max(adjusted_values)) if adjusted_values else None),
                max_distance_km=(max(item.distance_km for item in original_items) if original_items else None),
                quality_score=quality_score,
                quality_label=quality_label,
                confidence_low_db=low,
                confidence_high_db=high,
                time_block_count=len(
                    {
                        int(item.spot.observed_at.timestamp()) // block_seconds
                        for item in original_items
                    }
                ),
            )
        )
    return result


def receiver_stability(
    spots: Iterable[LocatedSpot],
    *,
    block_minutes: int = 30,
    minimum_receivers_per_block: int = 3,
    minimum_comparable_blocks: int = 3,
) -> list[ReceiverStability]:
    """Estimate receiver variability without erasing directional level.

    Every receiver is first collapsed to one median per time block. A block is
    comparable only when at least ``minimum_receivers_per_block`` receivers
    reported, and its reference is the median of those receiver medians. The
    MAD of a receiver's residuals around its own long-term residual measures
    variation relative to the common propagation trend.

    ``relative_baseline_db`` is descriptive only. It deliberately is not
    subtracted from the directional data because receiver sensitivity and
    actual antenna gain at the receiver bearing cannot be separated from these
    observations alone.
    """
    if block_minutes <= 0:
        raise ValueError("Block length must be positive.")
    if minimum_receivers_per_block < 2 or minimum_comparable_blocks < 2:
        raise ValueError("Receiver and block minima must be at least two.")
    items = list(spots)
    block_seconds = block_minutes * 60
    by_block_receiver: dict[int, dict[str, list[int]]] = {}
    report_counts: dict[str, int] = {}
    for item in items:
        call = item.spot.rx_call
        block = int(item.spot.observed_at.timestamp()) // block_seconds
        by_block_receiver.setdefault(block, {}).setdefault(call, []).append(
            item.spot.snr_db
        )
        report_counts[call] = report_counts.get(call, 0) + 1

    residuals: dict[str, list[float]] = {}
    for receiver_values in by_block_receiver.values():
        if len(receiver_values) < minimum_receivers_per_block:
            continue
        receiver_medians = {
            call: float(median(values))
            for call, values in receiver_values.items()
        }
        common_level = float(median(receiver_medians.values()))
        for call, value in receiver_medians.items():
            residuals.setdefault(call, []).append(value - common_level)

    result = []
    for call in sorted(report_counts):
        values = residuals.get(call, [])
        if len(values) < minimum_comparable_blocks:
            result.append(
                ReceiverStability(
                    receiver_call=call,
                    report_count=report_counts[call],
                    comparable_blocks=len(values),
                    relative_baseline_db=None,
                    variability_mad_db=None,
                    reliability_weight=0.5,
                    stability_label="insufficient",
                )
            )
            continue
        baseline = float(median(values))
        mad = float(median(abs(value - baseline) for value in values))
        weight = max(0.25, 1.0 / (1.0 + (mad / 4.0) ** 2))
        label = "stable" if mad <= 3.0 else "variable" if mad <= 6.0 else "unstable"
        result.append(
            ReceiverStability(
                receiver_call=call,
                report_count=report_counts[call],
                comparable_blocks=len(values),
                relative_baseline_db=baseline,
                variability_mad_db=mad,
                reliability_weight=weight,
                stability_label=label,
            )
        )
    return result


def receiver_balanced_sector_profile(
    spots: Iterable[LocatedSpot],
    sector_width_deg: int = 10,
    block_minutes: int = 30,
    *,
    block_adjustments: Mapping[int, float] | None = None,
) -> tuple[list[Sector], list[ReceiverStability]]:
    """Build a sector profile with one activity-capped contribution per RX.

    Repeated reports from one receiver are collapsed to its sector median.
    Receiver medians are combined using bounded stability weights, so a very
    active station cannot dominate and an unstable station is reduced but
    never silently discarded.
    """
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    items = list(spots)
    stability = receiver_stability(items, block_minutes=block_minutes)
    weights = {item.receiver_call: item.reliability_weight for item in stability}
    sector_count = 360 // sector_width_deg
    buckets: list[list[LocatedSpot]] = [[] for _ in range(sector_count)]
    for item in items:
        index = min(int(item.bearing_deg // sector_width_deg), sector_count - 1)
        buckets[index].append(item)

    result = []
    block_seconds = block_minutes * 60
    for index, bucket in enumerate(buckets):
        by_receiver: dict[str, list[float]] = {}
        for item in bucket:
            block = int(item.spot.observed_at.timestamp()) // block_seconds
            adjustment = (
                float(block_adjustments.get(block, 0.0))
                if block_adjustments is not None
                else 0.0
            )
            by_receiver.setdefault(item.spot.rx_call, []).append(
                item.spot.snr_db - adjustment
            )
        receiver_values = [
            (float(median(values)), weights.get(call, 0.5))
            for call, values in by_receiver.items()
        ]
        values = [value for value, _weight in receiver_values]
        unique_receivers = len(receiver_values)
        quality_score, quality_label = sector_quality(len(bucket), unique_receivers)
        low, high = bootstrap_median_interval(values, samples=500)
        result.append(
            Sector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                count=len(bucket),
                unique_receivers=unique_receivers,
                median_snr_db=(
                    weighted_median(receiver_values) if receiver_values else None
                ),
                best_snr_db=(round(max(values)) if values else None),
                max_distance_km=(
                    max(item.distance_km for item in bucket) if bucket else None
                ),
                quality_score=quality_score,
                quality_label=quality_label,
                confidence_low_db=low,
                confidence_high_db=high,
                time_block_count=len(
                    {
                        int(item.spot.observed_at.timestamp()) // block_seconds
                        for item in bucket
                    }
                ),
            )
        )
    return result, stability


def control_group_adjusted_sector_profile(
    spots: Iterable[LocatedSpot],
    sector_width_deg: int = 10,
    block_minutes: int = 30,
    *,
    minimum_control_receivers: int = 3,
    control_sector_width_deg: int = 60,
    minimum_control_sectors: int = 3,
    minimum_control_blocks: int = 3,
) -> tuple[list[Sector], list[ReceiverStability], ReceiverControlGroup]:
    """Remove only a common time shift supported by stable, diverse RX.

    Stable receivers are selected by :func:`receiver_stability`. Their own
    long-term medians are retained as receiver baselines; only their concurrent
    deviations from those baselines form the control trend. Requiring several
    receivers, angular sectors and time blocks prevents a single direction or
    station from masquerading as a common propagation change.
    """
    if minimum_control_receivers < 2 or minimum_control_sectors < 2:
        raise ValueError("Control group minima must be at least two.")
    if minimum_control_blocks < 2:
        raise ValueError("Control group needs at least two time blocks.")
    if control_sector_width_deg <= 0 or 360 % control_sector_width_deg:
        raise ValueError("Control sector width must divide 360.")
    items = list(spots)
    stability = receiver_stability(items, block_minutes=block_minutes)
    stable_calls = {
        item.receiver_call
        for item in stability
        if item.stability_label == "stable"
    }
    bearings: dict[str, list[float]] = {}
    for item in items:
        if item.spot.rx_call in stable_calls:
            bearings.setdefault(item.spot.rx_call, []).append(item.bearing_deg)
    angular_sectors = {
        int((median(values) % 360.0) // control_sector_width_deg)
        for values in bearings.values()
    }
    selected_calls = tuple(sorted(bearings))

    if len(selected_calls) < minimum_control_receivers:
        group = ReceiverControlGroup(
            selected_calls, len(angular_sectors), 0, False, "receivers", ()
        )
        profile, _metrics = receiver_balanced_sector_profile(
            items, sector_width_deg, block_minutes
        )
        return profile, stability, group
    if len(angular_sectors) < minimum_control_sectors:
        group = ReceiverControlGroup(
            selected_calls, len(angular_sectors), 0, False, "directions", ()
        )
        profile, _metrics = receiver_balanced_sector_profile(
            items, sector_width_deg, block_minutes
        )
        return profile, stability, group

    block_seconds = block_minutes * 60
    receiver_baselines = {
        call: float(
            median(
                item.spot.snr_db
                for item in items
                if item.spot.rx_call == call
            )
        )
        for call in selected_calls
    }
    by_block_receiver: dict[int, dict[str, list[int]]] = {}
    for item in items:
        call = item.spot.rx_call
        if call not in receiver_baselines:
            continue
        block = int(item.spot.observed_at.timestamp()) // block_seconds
        by_block_receiver.setdefault(block, {}).setdefault(call, []).append(
            item.spot.snr_db
        )
    raw_trend = {}
    receiver_counts = {}
    for block, receiver_values in by_block_receiver.items():
        if len(receiver_values) < 2:
            continue
        deviations = [
            float(median(values)) - receiver_baselines[call]
            for call, values in receiver_values.items()
        ]
        raw_trend[block] = float(median(deviations))
        receiver_counts[block] = len(receiver_values)
    if len(raw_trend) < minimum_control_blocks:
        group = ReceiverControlGroup(
            selected_calls,
            len(angular_sectors),
            len(raw_trend),
            False,
            "blocks",
            (),
        )
        profile, _metrics = receiver_balanced_sector_profile(
            items, sector_width_deg, block_minutes
        )
        return profile, stability, group

    centre = float(median(raw_trend.values()))
    adjustments = {
        block: value - centre for block, value in raw_trend.items()
    }
    trend = tuple(
        ControlTrendPoint(block, adjustments[block], receiver_counts[block])
        for block in sorted(adjustments)
    )
    group = ReceiverControlGroup(
        selected_calls,
        len(angular_sectors),
        len(trend),
        True,
        "ready",
        trend,
    )
    profile, _metrics = receiver_balanced_sector_profile(
        items,
        sector_width_deg,
        block_minutes,
        block_adjustments=adjustments,
    )
    return profile, stability, group


def weighted_median(values_and_weights: Iterable[tuple[float, float]]) -> float:
    values = sorted(
        (float(value), max(0.0, float(weight)))
        for value, weight in values_and_weights
    )
    if not values or sum(weight for _value, weight in values) <= 0:
        raise ValueError("Weighted median requires a positive total weight.")
    total = sum(weight for _value, weight in values)
    cumulative = 0.0
    for index, (value, weight) in enumerate(values):
        cumulative += weight
        if cumulative * 2 > total:
            return value
        if cumulative * 2 == total and index + 1 < len(values):
            return (value + values[index + 1][0]) / 2.0
    return values[-1][0]


def sector_quality(count: int, unique_receivers: int) -> tuple[float, str]:
    """Estimate descriptive sector quality from sample and RX diversity.

    This is intentionally a coverage indicator, not a statistical confidence
    probability. Ten reports from five independent receivers reach full score.
    """
    if count <= 0 or unique_receivers <= 0:
        return 0.0, "none"
    score = min(count / 10.0, unique_receivers / 5.0, 1.0)
    if count >= 10 and unique_receivers >= 5:
        return score, "high"
    if count >= 5 and unique_receivers >= 3:
        return score, "medium"
    return score, "low"


def filter_located_spots(
    spots: Iterable[LocatedSpot],
    *,
    hours: int | None = None,
    min_distance_km: float | None = None,
    max_distance_km: float | None = None,
    solar_period: str = "all",
    tx_longitude_deg: float = 0.0,
    now: datetime | None = None,
) -> list[LocatedSpot]:
    """Apply the shared time and distance view filters."""
    cutoff = None
    if hours is not None:
        reference = now or datetime.now(timezone.utc)
        cutoff = reference - timedelta(hours=hours)
    if solar_period not in ("all", "day", "night"):
        raise ValueError("Solar period must be all, day, or night.")
    result = []
    for item in spots:
        observed = item.spot.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        if cutoff is not None and observed < cutoff:
            continue
        if min_distance_km is not None and item.distance_km < min_distance_km:
            continue
        if max_distance_km is not None and item.distance_km >= max_distance_km:
            continue
        if solar_period != "all":
            utc_observed = observed.astimezone(timezone.utc)
            utc_hour = (
                utc_observed.hour
                + utc_observed.minute / 60.0
                + utc_observed.second / 3600.0
            )
            solar_hour = (utc_hour + tx_longitude_deg / 15.0) % 24.0
            is_day = 6.0 <= solar_hour < 18.0
            if solar_period == "day" and not is_day:
                continue
            if solar_period == "night" and is_day:
                continue
        result.append(item)
    return result


def compare_profile_spots(
    spots_a: Iterable[Spot],
    spots_b: Iterable[Spot],
    fallback_tx_grid: str = "",
    max_gap_seconds: int = 30 * 60,
) -> AbComparison:
    """Greedily pair nearest A/B reports from the same RX and band."""
    located_a = [item for spot in spots_a if (item := locate_spot(spot, fallback_tx_grid))]
    located_b = [item for spot in spots_b if (item := locate_spot(spot, fallback_tx_grid))]
    candidates: dict[tuple[str, str], list[LocatedSpot]] = {}
    for item in located_b:
        candidates.setdefault((item.spot.rx_call, item.spot.band), []).append(item)
    used: set[str] = set()
    pairs: list[PairedSpot] = []
    for item_a in sorted(located_a, key=lambda item: item.spot.observed_at):
        possible = [
            item
            for item in candidates.get((item_a.spot.rx_call, item_a.spot.band), [])
            if item.spot.source_key not in used
        ]
        if not possible:
            continue
        item_b = min(
            possible,
            key=lambda item: abs((item.spot.observed_at - item_a.spot.observed_at).total_seconds()),
        )
        gap = abs((item_b.spot.observed_at - item_a.spot.observed_at).total_seconds())
        if gap > max_gap_seconds:
            continue
        used.add(item_b.spot.source_key)
        pairs.append(
            PairedSpot(
                receiver_call=item_a.spot.rx_call,
                bearing_deg=item_a.bearing_deg,
                time_gap_seconds=gap,
                snr_a_db=item_a.spot.snr_db,
                snr_b_db=item_b.spot.snr_db,
                observed_at=item_a.spot.observed_at + (
                    item_b.spot.observed_at - item_a.spot.observed_at
                ) / 2,
            )
        )
    deltas = [pair.delta_db for pair in pairs]
    receiver_deltas = receiver_median_deltas(pairs)
    confidence_low, confidence_high = bootstrap_median_interval(receiver_deltas)
    return AbComparison(
        pairs=pairs,
        median_delta_db=float(median(receiver_deltas)) if receiver_deltas else None,
        unique_receivers=len({pair.receiver_call for pair in pairs}),
        confidence_low_db=confidence_low,
        confidence_high_db=confidence_high,
        pair_median_delta_db=float(median(deltas)) if deltas else None,
    )


def receiver_median_deltas(pairs: Iterable[PairedSpot]) -> list[float]:
    """Collapse repeated reports so every receiver has equal statistical weight."""
    grouped: dict[str, list[int]] = {}
    for pair in pairs:
        grouped.setdefault(pair.receiver_call, []).append(pair.delta_db)
    return [float(median(values)) for values in grouped.values()]


def recommend_ab_measurement(
    comparison: AbComparison,
    *,
    target_pairs: int = 30,
    target_receivers: int = 8,
) -> MeasurementRecommendation:
    pair_count = len(comparison.pairs)
    additional_pairs = max(0, target_pairs - pair_count)
    additional_receivers = max(0, target_receivers - comparison.unique_receivers)
    estimated_hours = None
    timestamps = sorted(
        pair.observed_at for pair in comparison.pairs if pair.observed_at is not None
    )
    if additional_pairs and len(timestamps) >= 3:
        span_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600.0
        if span_hours >= 0.25:
            rate = (len(timestamps) - 1) / span_hours
            if rate > 0:
                estimated_hours = additional_pairs / rate
    return MeasurementRecommendation(
        ready=additional_pairs == 0 and additional_receivers == 0,
        target_pairs=target_pairs,
        target_receivers=target_receivers,
        additional_pairs=additional_pairs,
        additional_receivers=additional_receivers,
        estimated_additional_hours=estimated_hours,
    )


def bootstrap_median_interval(
    values: Iterable[float], *, samples: int = 2000, confidence: float = 0.95
) -> tuple[float | None, float | None]:
    """Return a deterministic percentile-bootstrap interval for the median.

    Fewer than three observations are deliberately reported as insufficient.
    The interval describes sampling uncertainty only; it cannot correct changing
    propagation, receiver calibration, power, or antenna switching bias.
    """
    data = [float(value) for value in values]
    if len(data) < 3:
        return None, None
    if samples < 100:
        raise ValueError("Bootstrap requires at least 100 samples.")
    if not 0.0 < confidence < 1.0:
        raise ValueError("Confidence must be between zero and one.")
    random = Random(0xA17E)
    estimates = sorted(
        float(median(random.choices(data, k=len(data)))) for _ in range(samples)
    )
    tail = (1.0 - confidence) / 2.0
    low_index = max(0, round(tail * (samples - 1)))
    high_index = min(samples - 1, round((1.0 - tail) * (samples - 1)))
    return estimates[low_index], estimates[high_index]


def ab_sector_profile(
    pairs: Iterable[PairedSpot], sector_width_deg: int = 45
) -> list[AbSector]:
    """Summarize paired A/B deltas in azimuth sectors."""
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    buckets: list[list[PairedSpot]] = [
        [] for _ in range(360 // sector_width_deg)
    ]
    for pair in pairs:
        index = min(int((pair.bearing_deg % 360) // sector_width_deg), len(buckets) - 1)
        buckets[index].append(pair)
    result: list[AbSector] = []
    for index, bucket in enumerate(buckets):
        deltas = receiver_median_deltas(bucket)
        low, high = bootstrap_median_interval(deltas)
        result.append(
            AbSector(
                center_deg=index * sector_width_deg + sector_width_deg / 2,
                count=len(bucket),
                unique_receivers=len({pair.receiver_call for pair in bucket}),
                median_delta_db=float(median(deltas)) if deltas else None,
                confidence_low_db=low,
                confidence_high_db=high,
            )
        )
    return result
