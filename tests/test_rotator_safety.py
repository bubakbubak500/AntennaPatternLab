from antenna_pattern_lab.profiles import AntennaProfile
from antenna_pattern_lab.rotator_safety import (
    evaluate_rotator_safety,
    mechanical_target,
)


def test_directional_profile_target_and_live_tx_alerts_wrap_north():
    profile = AntennaProfile(
        id=1,
        name="Yagi",
        antenna_type="yagi",
        orientation_deg=350,
    )
    target = mechanical_target(profile)
    result = evaluate_rotator_safety(
        current_azimuth_deg=10,
        target_azimuth_deg=target,
        movement_deg=4,
        transmitting=True,
    )

    assert target == 350
    assert result.target_error_deg == 20
    assert result.severity == "error"
    assert result.warnings == ("moving_during_tx", "profile_mismatch")


def test_preflight_mismatch_is_warning_and_vertical_has_no_target():
    result = evaluate_rotator_safety(
        current_azimuth_deg=100,
        target_azimuth_deg=90,
        transmitting=False,
    )
    assert result.severity == "warning"
    assert result.warnings == ("profile_mismatch",)
    assert mechanical_target(
        AntennaProfile(
            id=2,
            name="Vertical",
            antenna_type="vertical",
            orientation_deg=90,
        )
    ) is None


def test_tolerances_do_not_warn_at_boundary():
    result = evaluate_rotator_safety(
        current_azimuth_deg=95,
        target_azimuth_deg=90,
        movement_deg=3,
        transmitting=True,
    )
    assert result.severity == "none"
    assert result.warnings == ()
