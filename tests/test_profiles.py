from antenna_pattern_lab.profiles import AntennaProfile, expected_main_bearings


def profile(antenna_type, orientation):
    return AntennaProfile(
        id=None,
        name="Test",
        antenna_type=antenna_type,
        orientation_deg=orientation,
    )


def test_wire_orientation_is_axis_and_expected_reference_is_broadside():
    assert expected_main_bearings(profile("dipole", 35)) == (125, 305)
    assert expected_main_bearings(profile("EFHW", 350)) == (80, 260)


def test_yagi_orientation_is_forward_bearing():
    assert expected_main_bearings(profile("yagi", 285)) == (285,)


def test_vertical_does_not_invent_a_directional_axis():
    assert expected_main_bearings(profile("vertical", 30)) == ()
