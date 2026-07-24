from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.antenna_model import antenna_template
from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.nec_fitting import FIT_SCHEMA, FitCandidate, assisted_fit
from antenna_pattern_lab.nec_runner import NecRunResult, RadiationSample
from antenna_pattern_lab.propagation_intelligence import (
    FEATURE_SCHEMA,
    PropagationFeatures,
)


def _features() -> PropagationFeatures:
    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    return PropagationFeatures(
        FEATURE_SCHEMA, 1, now, now, "JN79AA", "JO62QM", "20m", 14_074_000,
        300, 0, ((50, 14), (52, 13)), 12, 1, 0, 0, 0, 0, 0, False,
        10, 1, 8, 12, "TEST", 0, 2, -5, "quiet", 0, ("all",), (), (), (),
        (), 1800, "a", "b", "c",
    )


def _candidate(pattern):
    model = antenna_template("dipole")
    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    result = NecRunResult(
        model.sha256, "onec", "2.2", ("onec",), now, 1, "a", "b", (),
        tuple(RadiationSample(14_074_000, 90, angle, gain) for angle, gain in pattern),
        (), "output",
    )
    return FitCandidate(1, 2, 0, "real", model, result)


def test_assisted_fit_selects_orientation_on_train_and_reports_untouched_test():
    start = datetime(2026, 7, 24, 10, tzinfo=timezone.utc)
    spots = []
    # Pattern maximum is at model phi=0, while observations peak at bearing=90.
    for block in range(4):
        for bearing, snr in ((0, -20), (90, -5), (180, -20), (270, -30)):
            spot = Spot(
                sequence=block * 10 + bearing,
                frequency_hz=14_074_000,
                mode="FT8",
                snr_db=snr,
                observed_at=start + timedelta(minutes=30 * block),
                tx_call="OK7PS",
                tx_grid="JN79AA",
                rx_call=f"RX{block}{bearing}",
                rx_grid="JO62QM",
                band="20m",
            )
            spots.append(LocatedSpot(spot, 300, bearing))
    candidate = _candidate(((0, 0), (90, -15), (180, -25), (270, -15)))

    result = assisted_fit(spots, lambda _spot: _features(), (candidate,), orientation_step_deg=10)

    assert result.schema == FIT_SCHEMA
    assert result.orientation_deg == 90
    assert result.train_blocks == 3
    assert result.test_blocks == 1
    assert result.train_reports == 12
    assert result.test_reports == 4
    assert "validation uses only one untouched time block" in result.warnings
