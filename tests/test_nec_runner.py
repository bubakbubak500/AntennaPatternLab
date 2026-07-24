from datetime import timezone
import threading

import pytest

from antenna_pattern_lab.antenna_model import antenna_template
from antenna_pattern_lab.nec_runner import (
    RUN_SCHEMA,
    NecRunCancelled,
    NecRunResult,
    RadiationSample,
    estimate_ionospheric_hop_distance_km,
    estimate_radio_horizon_km,
    interpret_radiation_pattern,
    parse_opennec_result,
)


OUTPUT = """
                               FREQUENCY = 14.074 MHZ
                         ANTENNA INPUT PARAMETERS
 TAG SEGMENT VOLTAGE CURRENT IMPEDANCE
   1    11    1.0 0.0  0.02 0.0  72.5 -3.0
                         CURRENTS AND LOCATION
 SEG TAG X Y Z LENGTH REAL IMAG MAGNITUDE PHASE
   1   7 0 0 0 1 0.1 0.0 0.100 0.0
   2   7 0 0 0 1 0.2 0.0 0.200 10.0
                         RADIATION PATTERNS
 THETA PHI VERT HORIZ TOTAL AXIAL TILT
 90.0 0.0 0 0 2.1 0 0
 90.0 90.0 0 0 -3.0 0 0
 45.0 0.0 0 0 5.2 0 0
"""


def test_result_parser_reads_impedance_currents_and_full_radiation_grid():
    impedance, radiation, currents = parse_opennec_result(OUTPUT)

    assert impedance[0].frequency_hz == 14_074_000
    assert impedance[0].resistance_ohm == 72.5
    assert impedance[0].reactance_ohm == -3
    assert impedance[0].swr_50 > 1
    assert len(currents) == 2
    assert currents[0].wire_tag == 7
    assert currents[1].segment == 2
    assert radiation[-1].theta_deg == 45
    assert radiation[-1].gain_db == 5.2


def test_run_result_json_is_versioned_and_reproducible():
    impedance, radiation, currents = parse_opennec_result(OUTPUT)
    from antenna_pattern_lab.nec_runner import NecRunResult
    from datetime import datetime

    result = NecRunResult(
        antenna_template("dipole").sha256,
        "onec.exe",
        "OpenNEC 2.2.0",
        ("onec.exe", "model.nec"),
        datetime(2026, 7, 24, tzinfo=timezone.utc),
        0.25,
        "a" * 64,
        "b" * 64,
        impedance,
        radiation,
        currents,
        OUTPUT,
    )

    restored = NecRunResult.from_json(result.canonical_json())
    assert restored == result
    assert restored.schema == RUN_SCHEMA
    assert restored.radiation_at()[0].frequency_hz == 14_074_000


def test_takeoff_interpretation_uses_elevation_above_horizon_and_spherical_hops():
    samples = tuple(
        RadiationSample(
            14_074_000,
            theta,
            phi,
            6.0 - abs(theta - 60.0) / 5.0 - abs(phi - 90.0) / 90.0,
        )
        for theta in range(0, 91, 5)
        for phi in range(0, 360, 5)
    )

    interpretation = interpret_radiation_pattern(samples, antenna_height_m=10.0)

    assert interpretation is not None
    assert interpretation.peak_elevation_deg == 30.0
    assert interpretation.peak_azimuth_deg == 90.0
    assert interpretation.use_case == "medium"
    assert sum(
        (
            interpretation.low_angle_fraction,
            interpretation.medium_angle_fraction,
            interpretation.high_angle_fraction,
        )
    ) == pytest.approx(1.0)
    assert interpretation.e_layer_hop_km == pytest.approx(365.55, abs=0.1)
    assert interpretation.f2_layer_hop_km == pytest.approx(934.06, abs=0.1)
    assert interpretation.radio_horizon_km == pytest.approx(13.03, abs=0.1)


def test_hop_and_horizon_estimates_validate_their_physical_ranges():
    assert estimate_ionospheric_hop_distance_km(90.0, 300.0) == pytest.approx(0.0)
    assert estimate_radio_horizon_km(0.0) == 0.0
    with pytest.raises(ValueError):
        estimate_ionospheric_hop_distance_km(-1.0, 300.0)
    with pytest.raises(ValueError):
        estimate_ionospheric_hop_distance_km(10.0, 0.0)
    with pytest.raises(ValueError):
        estimate_radio_horizon_km(-1.0)
