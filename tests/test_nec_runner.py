from datetime import timezone
import threading

import pytest

from antenna_pattern_lab.antenna_model import antenna_template
from antenna_pattern_lab.nec_runner import (
    RUN_SCHEMA,
    NecRunCancelled,
    NecRunResult,
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
