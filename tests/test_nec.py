import pytest

from antenna_pattern_lab.nec import parse_nec_baseline, parse_nec_output


NEC_OUTPUT = """
                              RADIATION PATTERNS
 THETA  PHI   VERT.  HORIZ.  TOTAL  AXIAL  TILT
 90.00  0.00  -20.0  -30.0   -20.0  0.0  0.0
 90.00 90.00    2.0  -30.0     2.0  0.0  0.0
 90.00 180.00 -20.0  -30.0   -20.0  0.0  0.0
 90.00 270.00   2.0  -30.0     2.0  0.0  0.0
"""


def test_parses_and_normalizes_nec_azimuth_cut():
    pattern = parse_nec_output(NEC_OUTPUT)
    assert len(pattern.points) == 4
    assert pattern.points[1].bearing_deg == 90
    assert pattern.points[1].relative_gain_db == 0
    assert pattern.points[0].relative_gain_db == -22
    assert pattern.points[1].absolute_gain_db == 2


def test_rejects_output_without_pattern():
    with pytest.raises(ValueError):
        parse_nec_output("no pattern here")


def test_parse_nec_baseline_preserves_parameters_and_both_cuts():
    text = """
    FREQUENCY = 14.074 MHZ
    RADIATION PATTERNS
      90.0    0.0  0 0   6.0
      90.0   90.0  0 0   2.0
      90.0  180.0  0 0  -4.0
      90.0  270.0  0 0   2.0
       0.0    0.0  0 0 -20.0
      30.0    0.0  0 0   3.0
      60.0    0.0  0 0   5.0
    """
    baseline = parse_nec_baseline(
        text,
        antenna_height_m=12.5,
        ground_model="Sommerfeld-Norton medium",
        polarization="horizontal",
        orientation_deg=30,
        source="dipole.nec.out",
    )
    assert baseline.parameters.frequency_hz == 14_074_000
    assert baseline.parameters.antenna_height_m == 12.5
    assert baseline.parameters.ground_model.startswith("Sommerfeld")
    assert baseline.parameters.orientation_deg == 30
    assert len(baseline.azimuth.points) == 4
    assert len(baseline.elevation.points) == 4
    assert baseline.front_to_back_db == 10
