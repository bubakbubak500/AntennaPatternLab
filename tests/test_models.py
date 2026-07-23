from datetime import datetime, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.models import (
    calibrate_azimuth_model,
    representative_frequency_hz,
    theoretical_azimuth_model,
)
from antenna_pattern_lab.profiles import AntennaProfile


def profile(antenna_type: str, **kwargs) -> AntennaProfile:
    return AntennaProfile(id=None, name="Test", antenna_type=antenna_type, **kwargs)


def levels(model):
    return {point.bearing_deg: point.relative_gain_db for point in model.points}


def test_vertical_is_omnidirectional():
    model = theoretical_azimuth_model(profile("vertical"), 14_074_000)
    assert model is not None
    assert {point.relative_gain_db for point in model.points} == {0.0}


def test_half_wave_dipole_is_broadside_to_wire_axis():
    frequency = 14_074_000
    model = theoretical_azimuth_model(
        profile("dipole", orientation_deg=0, wire_length_m=299_792_458 / frequency / 2),
        frequency,
    )
    value = levels(model)
    assert value[90.0] == 0.0
    assert value[270.0] == 0.0
    assert value[0.0] == -30.0
    assert value[180.0] == -30.0


def test_yagi_points_forward_and_element_count_changes_shape():
    small = theoretical_azimuth_model(
        profile("yagi", orientation_deg=40, element_count=3), 14_074_000
    )
    large = theoretical_azimuth_model(
        profile("yagi", orientation_deg=40, element_count=7), 14_074_000
    )
    small_values = levels(small)
    large_values = levels(large)
    assert small_values[40.0] == 0.0
    assert small_values[220.0] < -10.0
    assert large_values[100.0] < small_values[100.0]


def test_wire_length_and_mode_frequency_affect_model():
    short = theoretical_azimuth_model(
        profile("efhw", orientation_deg=15, wire_length_m=10), 7_074_000
    )
    long = theoretical_azimuth_model(
        profile("efhw", orientation_deg=15, wire_length_m=40), 7_074_000
    )
    assert levels(short) != levels(long)
    assert representative_frequency_hz("20m", "FT8") == 14_074_000
    assert representative_frequency_hz("20m", "WSPR") == 14_095_600


def test_other_has_no_claimed_model_and_inputs_are_validated():
    assert theoretical_azimuth_model(profile("other"), 14_074_000) is None


def test_empirical_calibration_uses_relative_shape_only():
    model = theoretical_azimuth_model(profile("vertical"), 14_074_000)
    located = []
    for bearing, snr in ((10, -10), (10, -9), (10, -11), (190, -4), (190, -5), (190, -3)):
        spot = Spot(
            sequence=None,
            frequency_hz=14_074_000,
            mode="FT8",
            snr_db=snr,
            observed_at=datetime.now(timezone.utc),
            tx_call="OK7PS",
            tx_grid="JN79",
            rx_call=f"RX{bearing}{snr}",
            rx_grid="JO62",
            band="20m",
        )
        located.append(LocatedSpot(spot, 1000, bearing))
    calibration = calibrate_azimuth_model(model, located, sector_width_deg=90)
    assert len(calibration) == 2
    assert calibration[0].measured_relative_db == -6
    assert calibration[1].measured_relative_db == 0
    assert calibration[0].model_relative_db == 0
