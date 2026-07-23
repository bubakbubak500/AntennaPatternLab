from datetime import datetime, timezone

from antenna_pattern_lab.campaigns import (
    MeasurementCampaign,
    assess_campaign_metadata,
    assess_campaign_progress,
)
from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.demo import generate_demo_spots
from dataclasses import replace
from datetime import timedelta


def _campaign(**overrides):
    values = {
        "id": None,
        "name": "20m baseline",
        "objective": "Measure radial change",
        "tx_call": "OK7PS",
        "tx_grid": "JN79",
        "band": "20m",
        "mode": "FT8",
        "antenna_profile_id": 3,
        "antenna_profile_name": "Vertical",
        "notes": "Dry ground, 20 W",
        "started_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return MeasurementCampaign(**values)


def test_campaign_metadata_check_distinguishes_missing_documentation():
    complete = assess_campaign_metadata(_campaign(), 20)
    assert complete.complete
    assert complete.percent == 100

    incomplete = assess_campaign_metadata(
        _campaign(
            objective="",
            tx_grid="INVALID",
            antenna_profile_id=None,
            notes="",
        ),
        None,
    )
    assert not incomplete.complete
    assert set(incomplete.missing) == {
        "objective",
        "grid",
        "profile",
        "power",
        "conditions",
    }
    assert 0 < incomplete.percent < 100


def test_campaign_progress_requires_spots_receivers_sectors_and_time_blocks():
    campaign = _campaign(
        target_spots=6,
        target_receivers=2,
        target_sectors=2,
        target_time_blocks=2,
    )
    base = generate_demo_spots(count=1)[0]
    located = []
    for sector_index, bearing in enumerate((10.0, 40.0)):
        for sample in range(3):
            spot = replace(
                base,
                rx_call=f"RX{sample % 2}",
                observed_at=base.observed_at
                + timedelta(minutes=sector_index * 31, seconds=sample),
                sequence=sector_index * 10 + sample,
            )
            located.append(LocatedSpot(spot, 1500.0, bearing))
    progress = assess_campaign_progress(campaign, located)
    assert progress.complete
    assert progress.met_count == 4
    assert progress.supported_sector_count == 2
    assert progress.time_block_count == 2

    incomplete = assess_campaign_progress(campaign, located[:3])
    assert not incomplete.complete
    assert set(incomplete.missing) == {"spots", "sectors", "time_blocks"}
