from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.propagation import parse_noaa_payloads
from antenna_pattern_lab.propagation_analysis import (
    PropagationRecord,
    analyze_campaign_conditions,
)


def test_campaign_overlay_separates_dimensions_flags_conditions_and_sensitivity():
    start = datetime(2026, 7, 24, 10, tzinfo=timezone.utc)
    records = [
        PropagationRecord(start, "20m", "FT8", 20, "RX1", 5, -5),
        PropagationRecord(start + timedelta(minutes=2), "20m", "FT8", 20, "RX2", 35, -12),
        PropagationRecord(start + timedelta(minutes=35), "20m", "FT8", 20, "RX3", 65, -8),
        PropagationRecord(start + timedelta(minutes=37), "40m", "FT8", 50, "RX4", 95, -15),
    ]
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": start.isoformat(), "Kp": 6}],
            "scales": {"R": {"Scale": "1"}, "S": {"Scale": "0"}, "G": {"Scale": "1"}},
        },
        fetched_at=start,
    )
    analysis = analyze_campaign_conditions(records, [snapshot])

    assert len(analysis.groups) == 3
    assert "mixed_band_mode_or_power" in analysis.warnings
    assert "receiver_network_changed" in analysis.warnings
    assert "geomagnetic_disturbance" in analysis.intervals[0].flags
    assert "radio_blackout" in analysis.intervals[0].flags
    assert not analysis.intervals[0].direct_comparison_suitable
    assert {case.omitted for case in analysis.sensitivity} == {
        "receiver", "time", "direction"
    }
