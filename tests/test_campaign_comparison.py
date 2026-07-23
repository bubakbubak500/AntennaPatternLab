from dataclasses import replace
from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.campaign_comparison import compare_campaign_conditions
from antenna_pattern_lab.demo import generate_demo_spots


def _located(day_offset: int, hours: tuple[int, ...], distance: float, prefix: str):
    base = generate_demo_spots(count=1)[0]
    return [
        LocatedSpot(
            replace(
                base,
                observed_at=datetime(
                    2026, 7, 20 + day_offset, hour, tzinfo=timezone.utc
                ),
                rx_call=f"RX{index}",
                sequence=day_offset * 100 + index,
            ),
            distance,
            15.0,
        )
        for index, hour in enumerate(hours)
    ]


def test_campaign_comparison_recognizes_matching_solar_windows():
    a = _located(0, (5, 11, 17), 1500.0, "A")
    b = _located(1, (5, 11, 17), 1500.0, "B")
    result = compare_campaign_conditions(a, b)
    assert result.quality == "good"
    assert result.time_overlap_percent == 100
    assert result.block_balance_percent == 100
    assert result.distance_overlap_percent == 100
    assert result.receiver_overlap_percent == 100
    assert result.missing_slots_a == ()
    assert result.missing_slots_b == ()


def test_campaign_comparison_warns_about_disjoint_conditions():
    a = _located(0, (11,), 500.0, "A")
    b = _located(1, (23,), 9000.0, "B")
    result = compare_campaign_conditions(a, b)
    assert result.quality == "low"
    assert result.time_overlap_percent == 0
    assert result.distance_overlap_percent == 0
    assert "no_common_slots" in result.warnings
    assert "distance_imbalance" in result.warnings
    assert "receiver_change" not in result.warnings  # same synthetic RX
    assert len(result.missing_slots_a) == 1
    assert len(result.missing_slots_b) == 1
