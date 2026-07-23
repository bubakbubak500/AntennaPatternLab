from __future__ import annotations

from dataclasses import dataclass

from .analysis import LocatedSpot
from .geo import maidenhead_to_latlon


DISTANCE_CODES = ("near", "mid", "dx", "ultra")


@dataclass(frozen=True, slots=True)
class TimeSlotComparison:
    slot_index: int
    blocks_a: int
    blocks_b: int

    @property
    def label(self) -> str:
        start_minutes = self.slot_index * 30
        end_minutes = (start_minutes + 30) % (24 * 60)
        return (
            f"{start_minutes // 60:02d}:{start_minutes % 60:02d}–"
            f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
        )


@dataclass(frozen=True, slots=True)
class CampaignComparability:
    slots: tuple[TimeSlotComparison, ...]
    occupied_slots_a: int
    occupied_slots_b: int
    common_slots: int
    time_overlap_percent: float
    block_count_a: int
    block_count_b: int
    block_balance_percent: float
    day_share_a_percent: float | None
    day_share_b_percent: float | None
    day_share_difference_points: float | None
    distance_overlap_percent: float
    receiver_overlap_percent: float
    missing_slots_a: tuple[str, ...]
    missing_slots_b: tuple[str, ...]
    quality: str
    warnings: tuple[str, ...]


def compare_campaign_conditions(
    located_a: list[LocatedSpot],
    located_b: list[LocatedSpot],
) -> CampaignComparability:
    slot_blocks_a = _solar_slot_blocks(located_a)
    slot_blocks_b = _solar_slot_blocks(located_b)
    occupied_a = {slot for slot, blocks in slot_blocks_a.items() if blocks}
    occupied_b = {slot for slot, blocks in slot_blocks_b.items() if blocks}
    common = occupied_a & occupied_b
    union = occupied_a | occupied_b
    time_overlap = 100.0 * len(common) / len(union) if union else 0.0

    blocks_a = sum(len(blocks) for blocks in slot_blocks_a.values())
    blocks_b = sum(len(blocks) for blocks in slot_blocks_b.values())
    block_balance = (
        100.0 * min(blocks_a, blocks_b) / max(blocks_a, blocks_b)
        if max(blocks_a, blocks_b)
        else 0.0
    )
    day_share_a = _day_share(slot_blocks_a)
    day_share_b = _day_share(slot_blocks_b)
    day_difference = (
        abs(day_share_a - day_share_b)
        if day_share_a is not None and day_share_b is not None
        else None
    )
    distance_overlap = _distribution_overlap(
        _distance_counts(located_a),
        _distance_counts(located_b),
    )
    receiver_overlap = _set_overlap(
        {item.spot.rx_call for item in located_a},
        {item.spot.rx_call for item in located_b},
    )
    slots = tuple(
        TimeSlotComparison(
            slot_index=index,
            blocks_a=len(slot_blocks_a[index]),
            blocks_b=len(slot_blocks_b[index]),
        )
        for index in range(48)
    )

    warnings: list[str] = []
    if not common:
        warnings.append("no_common_slots")
    elif time_overlap < 50:
        warnings.append("low_time_overlap")
    if block_balance < 60:
        warnings.append("block_imbalance")
    if day_difference is None or day_difference > 25:
        warnings.append("day_night_imbalance")
    if distance_overlap < 60:
        warnings.append("distance_imbalance")
    if receiver_overlap < 30:
        warnings.append("receiver_change")
    if blocks_a < 3:
        warnings.append("sparse_a")
    if blocks_b < 3:
        warnings.append("sparse_b")

    if (
        time_overlap >= 70
        and block_balance >= 70
        and day_difference is not None
        and day_difference <= 15
        and distance_overlap >= 70
        and receiver_overlap >= 40
    ):
        quality = "good"
    elif (
        time_overlap >= 40
        and block_balance >= 50
        and day_difference is not None
        and day_difference <= 30
        and distance_overlap >= 50
    ):
        quality = "medium"
    else:
        quality = "low"

    return CampaignComparability(
        slots=slots,
        occupied_slots_a=len(occupied_a),
        occupied_slots_b=len(occupied_b),
        common_slots=len(common),
        time_overlap_percent=time_overlap,
        block_count_a=blocks_a,
        block_count_b=blocks_b,
        block_balance_percent=block_balance,
        day_share_a_percent=day_share_a,
        day_share_b_percent=day_share_b,
        day_share_difference_points=day_difference,
        distance_overlap_percent=distance_overlap,
        receiver_overlap_percent=receiver_overlap,
        missing_slots_a=tuple(slots[index].label for index in sorted(occupied_b - occupied_a)),
        missing_slots_b=tuple(slots[index].label for index in sorted(occupied_a - occupied_b)),
        quality=quality,
        warnings=tuple(warnings),
    )


def _solar_slot_blocks(located: list[LocatedSpot]) -> dict[int, set[int]]:
    result = {index: set() for index in range(48)}
    for item in located:
        try:
            _latitude, longitude = maidenhead_to_latlon(item.spot.tx_grid)
        except ValueError:
            longitude = 0.0
        offset_seconds = round(longitude * 240)
        local_block = (int(item.spot.observed_at.timestamp()) + offset_seconds) // 1800
        result[local_block % 48].add(local_block)
    return result


def _day_share(slot_blocks: dict[int, set[int]]) -> float | None:
    total = sum(len(blocks) for blocks in slot_blocks.values())
    if not total:
        return None
    day = sum(
        len(slot_blocks[index])
        for index in range(12, 36)
    )
    return 100.0 * day / total


def _distance_counts(located: list[LocatedSpot]) -> dict[str, int]:
    counts = {code: 0 for code in DISTANCE_CODES}
    for item in located:
        if item.distance_km < 1000:
            code = "near"
        elif item.distance_km < 3000:
            code = "mid"
        elif item.distance_km < 8000:
            code = "dx"
        else:
            code = "ultra"
        counts[code] += 1
    return counts


def _distribution_overlap(a: dict[str, int], b: dict[str, int]) -> float:
    total_a, total_b = sum(a.values()), sum(b.values())
    if not total_a or not total_b:
        return 0.0
    return 100.0 * sum(
        min(a[key] / total_a, b[key] / total_b)
        for key in DISTANCE_CODES
    )


def _set_overlap(a: set[str], b: set[str]) -> float:
    union = a | b
    return 100.0 * len(a & b) / len(union) if union else 0.0
