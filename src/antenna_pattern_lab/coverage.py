from __future__ import annotations

from dataclasses import dataclass

from .analysis import LocatedSpot, sector_profile
from .geo import maidenhead_to_latlon


DISTANCE_BANDS = (
    ("near", 0.0, 1000.0),
    ("mid", 1000.0, 3000.0),
    ("dx", 3000.0, 8000.0),
    ("ultra", 8000.0, None),
)


@dataclass(frozen=True, slots=True)
class CoverageSector:
    center_deg: float
    start_deg: float
    end_deg: float
    report_count: int
    unique_receivers: int
    time_block_count: int
    confidence_low_db: float | None
    confidence_high_db: float | None
    quality_label: str
    completeness_percent: float
    missing_utc_windows: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CoverageMatrixCell:
    bearing_center_deg: float
    distance_code: str
    solar_period: str
    report_count: int
    unique_receivers: int
    time_block_count: int
    completeness_percent: float


def analyze_angular_coverage(
    located: list[LocatedSpot], sector_width_deg: int = 30
) -> list[CoverageSector]:
    profile = sector_profile(located, sector_width_deg)
    buckets: list[list[LocatedSpot]] = [
        [] for _ in range(360 // sector_width_deg)
    ]
    for item in located:
        buckets[min(int(item.bearing_deg // sector_width_deg), len(buckets) - 1)].append(
            item
        )

    result: list[CoverageSector] = []
    for sector, items in zip(profile, buckets):
        represented_windows = {
            item.spot.observed_at.hour // 6 for item in items
        }
        missing_windows = tuple(
            f"{start:02d}–{start + 6:02d}"
            for index, start in enumerate((0, 6, 12, 18))
            if index not in represented_windows
        )
        report_component = min(1.0, sector.count / 10.0)
        receiver_component = min(1.0, sector.unique_receivers / 5.0)
        time_component = min(1.0, sector.time_block_count / 3.0)
        confidence_component = 0.0
        if (
            sector.confidence_low_db is not None
            and sector.confidence_high_db is not None
        ):
            width = sector.confidence_high_db - sector.confidence_low_db
            confidence_component = max(0.0, min(1.0, 1.0 - width / 20.0))
        completeness = 100.0 * (
            0.35 * report_component
            + 0.30 * receiver_component
            + 0.20 * time_component
            + 0.15 * confidence_component
        )
        result.append(
            CoverageSector(
                center_deg=sector.center_deg,
                start_deg=(sector.center_deg - sector_width_deg / 2) % 360,
                end_deg=(sector.center_deg + sector_width_deg / 2) % 360,
                report_count=sector.count,
                unique_receivers=sector.unique_receivers,
                time_block_count=sector.time_block_count,
                confidence_low_db=sector.confidence_low_db,
                confidence_high_db=sector.confidence_high_db,
                quality_label=sector.quality_label,
                completeness_percent=completeness,
                missing_utc_windows=missing_windows,
            )
        )
    return result


def priority_sectors(
    sectors: list[CoverageSector], limit: int = 3
) -> list[CoverageSector]:
    return sorted(
        sectors,
        key=lambda sector: (
            sector.completeness_percent,
            sector.report_count,
            sector.unique_receivers,
            sector.center_deg,
        ),
    )[: max(0, limit)]


def analyze_coverage_matrix(
    located: list[LocatedSpot],
    sector_width_deg: int = 30,
) -> list[CoverageMatrixCell]:
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    sector_count = 360 // sector_width_deg
    buckets: dict[tuple[int, str, str], list[LocatedSpot]] = {}
    for item in located:
        sector_index = min(int(item.bearing_deg // sector_width_deg), sector_count - 1)
        distance_code = _distance_code(item.distance_km)
        solar_period = _solar_period(item)
        buckets.setdefault(
            (sector_index, distance_code, solar_period),
            [],
        ).append(item)

    cells: list[CoverageMatrixCell] = []
    for solar_period in ("day", "night"):
        for distance_code, _minimum, _maximum in DISTANCE_BANDS:
            for sector_index in range(sector_count):
                items = buckets.get(
                    (sector_index, distance_code, solar_period),
                    [],
                )
                receivers = len({item.spot.rx_call for item in items})
                blocks = len(
                    {
                        int(item.spot.observed_at.timestamp()) // (30 * 60)
                        for item in items
                    }
                )
                completeness = 100.0 * (
                    0.45 * min(1.0, len(items) / 5.0)
                    + 0.35 * min(1.0, receivers / 3.0)
                    + 0.20 * min(1.0, blocks / 2.0)
                )
                cells.append(
                    CoverageMatrixCell(
                        bearing_center_deg=(
                            sector_index * sector_width_deg + sector_width_deg / 2
                        ),
                        distance_code=distance_code,
                        solar_period=solar_period,
                        report_count=len(items),
                        unique_receivers=receivers,
                        time_block_count=blocks,
                        completeness_percent=completeness,
                    )
                )
    return cells


def priority_matrix_cells(
    cells: list[CoverageMatrixCell],
    limit: int = 5,
) -> list[CoverageMatrixCell]:
    return sorted(
        cells,
        key=lambda cell: (
            cell.completeness_percent,
            cell.report_count,
            cell.unique_receivers,
            cell.solar_period,
            cell.distance_code,
            cell.bearing_center_deg,
        ),
    )[: max(0, limit)]


def _distance_code(distance_km: float) -> str:
    for code, minimum, maximum in DISTANCE_BANDS:
        if distance_km >= minimum and (maximum is None or distance_km < maximum):
            return code
    return "ultra"


def _solar_period(item: LocatedSpot) -> str:
    try:
        _latitude, longitude = maidenhead_to_latlon(item.spot.tx_grid)
    except ValueError:
        longitude = 0.0
    observed_at = item.spot.observed_at
    utc_hour = (
        observed_at.hour
        + observed_at.minute / 60.0
        + observed_at.second / 3600.0
    )
    solar_hour = (utc_hour + longitude / 15.0) % 24.0
    return "day" if 6.0 <= solar_hour < 18.0 else "night"
