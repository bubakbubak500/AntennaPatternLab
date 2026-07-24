from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from statistics import median
from typing import Iterable

from .propagation import PropagationSnapshot, operational_context


@dataclass(frozen=True, slots=True)
class PropagationRecord:
    observed_at: datetime
    band: str
    mode: str
    power_w: float | None
    rx_call: str
    bearing_deg: float
    snr_db: float
    tx_session_id: int | None = None


@dataclass(frozen=True, slots=True)
class ComparabilityGroup:
    band: str
    mode: str
    power_w: float | None
    receiver_network_hash: str
    record_count: int
    receiver_count: int


@dataclass(frozen=True, slots=True)
class ConditionInterval:
    started_at: datetime
    record_count: int
    receiver_count: int
    tx_session_count: int
    median_snr_db: float | None
    median_change_db: float | None
    snapshot_id: int | None
    flags: tuple[str, ...]
    direct_comparison_suitable: bool


@dataclass(frozen=True, slots=True)
class SensitivityCase:
    omitted: str
    omitted_value: str
    remaining_count: int
    max_sector_median_change_db: float | None


@dataclass(frozen=True, slots=True)
class CampaignPropagationAnalysis:
    groups: tuple[ComparabilityGroup, ...]
    intervals: tuple[ConditionInterval, ...]
    sensitivity: tuple[SensitivityCase, ...]
    warnings: tuple[str, ...]


def analyze_campaign_conditions(
    records: Iterable[PropagationRecord],
    snapshots: Iterable[PropagationSnapshot],
    *,
    block_minutes: int = 30,
    sector_width: int = 30,
) -> CampaignPropagationAnalysis:
    items = sorted(records, key=lambda item: item.observed_at)
    context_snapshots = sorted(snapshots, key=lambda item: item.observed_at)
    if not items:
        return CampaignPropagationAnalysis((), (), (), ("no_records",))

    grouped: dict[tuple[str, str, float | None, str], list[PropagationRecord]] = {}
    blocks: dict[int, list[PropagationRecord]] = {}
    for item in items:
        block = int(item.observed_at.timestamp()) // (block_minutes * 60)
        blocks.setdefault(block, []).append(item)
    block_receivers = {
        block: frozenset(item.rx_call for item in values)
        for block, values in blocks.items()
    }
    previous_receivers: frozenset[str] | None = None
    previous_median: float | None = None
    intervals = []
    significant_network_change = False
    for block, values in sorted(blocks.items()):
        receivers = block_receivers[block]
        network_hash = _network_hash(receivers)
        for item in values:
            key = (item.band, item.mode, item.power_w, network_hash)
            grouped.setdefault(key, []).append(item)
        flags: list[str] = []
        current_median = median(item.snr_db for item in values)
        if previous_receivers is not None:
            union = receivers | previous_receivers
            overlap = len(receivers & previous_receivers) / len(union) if union else 1
            if overlap < 0.5:
                flags.append("receiver_network_changed")
                significant_network_change = True
        previous_receivers = receivers
        median_change = (
            current_median - previous_median
            if previous_median is not None
            else None
        )
        previous_median = current_median
        started = datetime.fromtimestamp(
            block * block_minutes * 60,
            tz=values[0].observed_at.tzinfo,
        )
        snapshot = _nearest_snapshot(started, context_snapshots)
        if snapshot is None:
            flags.append("missing_conditions")
        else:
            if snapshot.stale:
                flags.append("stale_conditions")
            if (snapshot.kp_index or 0) >= 5 or (snapshot.geomagnetic_scale or 0) >= 1:
                flags.append("geomagnetic_disturbance")
            if (snapshot.radio_blackout_scale or 0) >= 1:
                flags.append("radio_blackout")
            context = operational_context(snapshot)
            if context.proton_scale:
                flags.append("polar_cap_absorption_risk")
        intervals.append(
            ConditionInterval(
                started,
                len(values),
                len(receivers),
                len(
                    {
                        item.tx_session_id
                        for item in values
                        if item.tx_session_id is not None
                    }
                ),
                current_median,
                median_change,
                snapshot.id if snapshot else None,
                tuple(flags),
                not flags,
            )
        )
    groups = tuple(
        ComparabilityGroup(
            key[0],
            key[1],
            key[2],
            key[3],
            len(values),
            len({item.rx_call for item in values}),
        )
        for key, values in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2] or -1, item[0][3]),
        )
    )
    dimensions = {
        (item.band, item.mode, item.power_w)
        for item in items
    }
    warnings = []
    if len(dimensions) > 1:
        warnings.append("mixed_band_mode_or_power")
    if significant_network_change:
        warnings.append("receiver_network_changed")
    if any(not interval.direct_comparison_suitable for interval in intervals):
        warnings.append("conditions_not_comparable")
    return CampaignPropagationAnalysis(
        groups,
        tuple(intervals),
        sensitivity_analysis(items, sector_width=sector_width),
        tuple(warnings),
    )


def sensitivity_analysis(
    records: Iterable[PropagationRecord],
    *,
    sector_width: int = 30,
) -> tuple[SensitivityCase, ...]:
    items = list(records)
    if not items:
        return ()
    receiver_levels: dict[str, list[float]] = {}
    hours: dict[str, list[PropagationRecord]] = {}
    sectors: dict[int, list[PropagationRecord]] = {}
    for item in items:
        receiver_levels.setdefault(item.rx_call, []).append(item.snr_db)
        hour = item.observed_at.strftime("%Y-%m-%d %H:00 UTC")
        hours.setdefault(hour, []).append(item)
        sector = int(item.bearing_deg % 360 // sector_width) * sector_width
        sectors.setdefault(sector, []).append(item)
    strongest_rx = max(
        receiver_levels,
        key=lambda receiver: (median(receiver_levels[receiver]), receiver),
    )
    busiest_hour = max(hours, key=lambda hour: (len(hours[hour]), hour))
    busiest_sector = max(
        sectors, key=lambda sector: (len(sectors[sector]), sector)
    )
    base = _sector_medians(items, sector_width)
    cases = (
        ("receiver", strongest_rx, [item for item in items if item.rx_call != strongest_rx]),
        (
            "time",
            busiest_hour,
            [
                item
                for item in items
                if item.observed_at.strftime("%Y-%m-%d %H:00 UTC") != busiest_hour
            ],
        ),
        (
            "direction",
            f"{busiest_sector:03d}–{(busiest_sector + sector_width) % 360:03d}°",
            [
                item
                for item in items
                if int(item.bearing_deg % 360 // sector_width) * sector_width
                != busiest_sector
            ],
        ),
    )
    return tuple(
        SensitivityCase(
            kind,
            value,
            len(remaining),
            _maximum_change(base, _sector_medians(remaining, sector_width)),
        )
        for kind, value, remaining in cases
    )


def _nearest_snapshot(
    at: datetime,
    snapshots: list[PropagationSnapshot],
) -> PropagationSnapshot | None:
    candidates = [
        snapshot
        for snapshot in snapshots
        if abs(snapshot.observed_at - at) <= timedelta(hours=2)
    ]
    return min(candidates, key=lambda item: abs(item.observed_at - at)) if candidates else None


def _network_hash(receivers: frozenset[str]) -> str:
    return sha256("\n".join(sorted(receivers)).encode("utf-8")).hexdigest()[:12]


def _sector_medians(
    items: Iterable[PropagationRecord],
    width: int,
) -> dict[int, float]:
    values: dict[int, list[float]] = {}
    for item in items:
        sector = int(item.bearing_deg % 360 // width) * width
        values.setdefault(sector, []).append(item.snr_db)
    return {sector: median(levels) for sector, levels in values.items()}


def _maximum_change(
    before: dict[int, float],
    after: dict[int, float],
) -> float | None:
    shared = set(before) & set(after)
    return max((abs(before[key] - after[key]) for key in shared), default=None)
