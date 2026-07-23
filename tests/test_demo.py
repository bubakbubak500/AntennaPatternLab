from antenna_pattern_lab.demo import generate_demo_spots


def test_wspr_demo_uses_wspr_mode_and_frequency():
    spots = generate_demo_spots(band="20m", count=3, mode="WSPR")
    assert {spot.mode for spot in spots} == {"WSPR"}
    assert all(14_094_000 < spot.frequency_hz < 14_097_000 for spot in spots)
