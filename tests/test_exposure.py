from datetime import datetime, timezone

from antenna_pattern_lab.exposure import ExposureObservation, exposure_sector_profile, wilson_interval


def test_wilson_interval_and_exposure_profile():
    low, high = wilson_interval(5, 10)
    assert 0 < low < 0.5 < high < 1
    observations = [
        ExposureObservation(1, 1, "RX1", "JO62", True, datetime.now(timezone.utc)),
        ExposureObservation(1, 1, "RX2", "JO62", False, datetime.now(timezone.utc)),
    ]
    sectors = exposure_sector_profile(observations, "JN79", 30)
    used = [sector for sector in sectors if sector.opportunities]
    assert len(used) == 1
    assert used[0].detection_rate == 0.5
    assert used[0].unique_receivers == 2
