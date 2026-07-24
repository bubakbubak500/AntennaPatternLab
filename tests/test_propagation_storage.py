from datetime import datetime, timezone

import pytest

from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.propagation import parse_noaa_payloads
from antenna_pattern_lab.storage import SpotRepository


def _campaign(repository):
    return repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="20m propagation baseline",
            objective="Record space-weather context",
            tx_call="OK7PS",
            tx_grid="JN79",
            band="20m",
            mode="FT8",
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="20 W",
            started_at=datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc),
        )
    )


def _snapshot():
    return parse_noaa_payloads(
        {
            "kp": [{"time_tag": "2026-07-24T09:00:00Z", "Kp": 2.33}],
            "f107": [{"time_tag": "2026-07-24T08:00:00Z", "flux": 145}],
        },
        fetched_at=datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc),
    )


def test_snapshot_is_saved_idempotently_with_complete_provenance(tmp_path):
    repository = SpotRepository(tmp_path / "propagation.sqlite3")
    campaign = _campaign(repository)

    first = repository.save_propagation_snapshot(campaign.id, _snapshot())
    second = repository.save_propagation_snapshot(campaign.id, _snapshot())

    assert first.id == second.id
    assert first.campaign_id == campaign.id
    assert first.payload_sha256
    assert repository.list_propagation_snapshots(campaign.id) == [second]


def test_snapshot_requires_an_existing_campaign(tmp_path):
    repository = SpotRepository(tmp_path / "propagation.sqlite3")
    with pytest.raises(ValueError, match="does not exist"):
        repository.save_propagation_snapshot(999, _snapshot())
