import pytest

from antenna_pattern_lab.nec import parse_nec_output


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
