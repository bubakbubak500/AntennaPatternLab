from dataclasses import replace
from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.coverage import (
    analyze_angular_coverage,
    analyze_coverage_matrix,
    priority_matrix_cells,
    priority_sectors,
)
from antenna_pattern_lab.demo import generate_demo_spots


def test_coverage_analysis_prioritizes_empty_bearings():
    sectors = analyze_angular_coverage([], 30)
    assert len(sectors) == 12
    assert all(sector.completeness_percent == 0 for sector in sectors)
    assert [sector.center_deg for sector in priority_sectors(sectors)] == [15, 45, 75]


def test_coverage_analysis_rewards_receiver_and_time_diversity():
    base = generate_demo_spots(count=1)[0]
    start = datetime(2026, 7, 23, tzinfo=timezone.utc)
    located = []
    for index in range(10):
        spot = replace(
            base,
            rx_call=f"RX{index % 5}",
            observed_at=start + timedelta(minutes=index * 31),
            sequence=index,
        )
        located.append(LocatedSpot(spot, 1200.0, 10.0))
    sectors = analyze_angular_coverage(located, 30)
    supported = sectors[0]
    assert supported.report_count == 10
    assert supported.unique_receivers == 5
    assert supported.time_block_count >= 3
    assert supported.quality_label == "high"
    assert supported.completeness_percent > sectors[1].completeness_percent
    assert "06–12" in supported.missing_utc_windows


def test_coverage_matrix_separates_distance_and_solar_period():
    base = generate_demo_spots(count=1)[0]
    day = replace(
        base,
        observed_at=datetime(2026, 7, 23, 12, tzinfo=timezone.utc),
        rx_call="DAYRX",
    )
    night = replace(
        base,
        observed_at=datetime(2026, 7, 23, 0, tzinfo=timezone.utc),
        rx_call="NIGHTRX",
        sequence=2,
    )
    cells = analyze_coverage_matrix(
        [
            LocatedSpot(day, 500.0, 10.0),
            LocatedSpot(night, 4500.0, 10.0),
        ],
        30,
    )
    assert len(cells) == 96
    day_near = next(
        cell
        for cell in cells
        if cell.bearing_center_deg == 15
        and cell.distance_code == "near"
        and cell.solar_period == "day"
    )
    night_dx = next(
        cell
        for cell in cells
        if cell.bearing_center_deg == 15
        and cell.distance_code == "dx"
        and cell.solar_period == "night"
    )
    assert day_near.report_count == 1
    assert night_dx.report_count == 1
    assert day_near.completeness_percent > 0
    assert priority_matrix_cells(cells, 3)[0].report_count == 0
