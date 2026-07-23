from dataclasses import replace
from datetime import datetime, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.experiments import TxSessionSummary
from antenna_pattern_lab.profiles import AntennaProfile
from antenna_pattern_lab.rotator_alignment import analyze_rotator_alignment


def _session(azimuth: float) -> TxSessionSummary:
    return TxSessionSummary(
        id=1,
        started_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        ended_at=datetime(2026, 7, 23, 0, 1, tzinfo=timezone.utc),
        profile_id=1,
        profile_name="Yagi",
        mode="FT8",
        frequency_hz=14_074_000,
        rotator_start_azimuth_deg=azimuth,
        rotator_start_elevation_deg=0,
        rotator_end_azimuth_deg=azimuth,
        rotator_end_elevation_deg=0,
        rotator_max_deviation_deg=0,
        power_w=20,
        spot_count=0,
        unique_receivers=0,
        average_snr_db=None,
    )


def _spot(index: int, bearing: float, snr: int) -> LocatedSpot:
    observed = datetime(2026, 7, 23, index // 6, (index % 6) * 5, tzinfo=timezone.utc)
    spot = Spot(
        sequence=index,
        frequency_hz=14_074_000,
        mode="FT8",
        snr_db=snr,
        observed_at=observed,
        tx_call="OK7PS",
        tx_grid="JN79",
        rx_call=f"RX{index % 8}",
        rx_grid="JO62",
        band="20m",
    )
    return LocatedSpot(spot, 1500, bearing)


def test_alignment_compares_target_actual_and_supported_empirical_peak():
    profile = AntennaProfile(
        id=1, name="Yagi", antenna_type="yagi", orientation_deg=350
    )
    located = [
        _spot(index, [330, 350, 10, 90][index % 4], -2 if index % 4 != 3 else -18)
        for index in range(64)
    ]

    result = analyze_rotator_alignment(
        profile, [_session(348), _session(352)], located
    )

    assert result.applicable
    assert result.actual_azimuth_deg == 350
    assert result.target_error_deg == 0
    assert result.empirical_peak_deg is not None
    assert result.empirical_error_deg is not None
    assert result.empirical_error_deg < 30
    assert result.confidence == "high"
    assert "target_mismatch" not in result.warnings


def test_vertical_has_no_directional_target():
    result = analyze_rotator_alignment(
        AntennaProfile(
            id=1, name="Vertical", antenna_type="vertical", orientation_deg=20
        ),
        [_session(20)],
        [],
    )
    assert not result.applicable
    assert result.target_azimuth_deg is None
    assert result.empirical_peak_deg is None
    assert "insufficient_empirical_data" in result.warnings
