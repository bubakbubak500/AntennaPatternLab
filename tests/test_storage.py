from dataclasses import replace
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from antenna_pattern_lab.campaigns import CampaignLogEntry, MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.profiles import AntennaProfile
from antenna_pattern_lab.storage import SpotRepository


def test_repository_deduplicates_and_filters(tmp_path):
    repository = SpotRepository(tmp_path / "spots.sqlite3")
    spot = generate_demo_spots(count=1)[0]
    assert repository.add(spot) is True
    assert repository.add(spot) is False
    assert repository.count() == 1
    assert repository.list_spots(tx_call="OK7PS", band="20m", mode="FT8") == [spot]
    assert repository.list_spots(tx_call="N0BODY") == []
    assert repository.clear() == 1
    assert repository.count() == 0
    assert repository.clear() == 0


def test_repository_persists_and_filters_spot_source(tmp_path):
    repository = SpotRepository(tmp_path / "sources.sqlite3")
    pskr = generate_demo_spots(count=1)[0]
    adif = replace(
        pskr,
        observed_at=pskr.observed_at + timedelta(minutes=1),
        rx_call="ADIFRX",
        source="adif",
    )
    assert repository.add_many([pskr, adif]) == 2

    assert repository.list_spots(source="pskreporter") == [pskr]
    assert repository.list_spots(source="adif") == [adif]
    assert {spot.source for spot in repository.list_spots(source="all")} == {
        "pskreporter",
        "adif",
    }


def test_spot_is_matched_to_wsjtx_tx_session(tmp_path):
    repository = SpotRepository(tmp_path / "sessions.sqlite3")
    spot = generate_demo_spots(count=1)[0]
    session_id = repository.start_tx_session(
        instance_id="WSJT-X",
        de_call=spot.tx_call,
        de_grid=spot.tx_grid,
        mode=spot.mode,
        dial_frequency_hz=14_074_000,
        tx_frequency_hz=spot.frequency_hz,
        tx_message="CQ OK7PS JN79",
        configuration_name="Default",
        antenna_profile_id=None,
        rig_frequency_hz=None,
        rig_mode=None,
        rig_ptt=None,
        started_at=spot.observed_at - timedelta(seconds=5),
        rotator_azimuth_deg=350.0,
        rotator_elevation_deg=2.0,
    )
    repository.finish_tx_session(
        session_id,
        spot.observed_at + timedelta(seconds=5),
        rotator_azimuth_deg=10.0,
        rotator_elevation_deg=3.0,
        rotator_max_deviation_deg=20.0,
    )
    assert repository.add(spot) is True
    assert repository.spot_tx_session_id(spot) == session_id
    assert repository.tx_session_count() == 1
    summary = repository.list_tx_sessions()[0]
    assert summary.spot_count == 1
    assert summary.unique_receivers == 1
    assert summary.average_snr_db == spot.snr_db
    assert summary.duration_seconds == 10
    assert summary.rotator_start_azimuth_deg == 350.0
    assert summary.rotator_end_azimuth_deg == 10.0
    assert summary.rotator_max_deviation_deg == 20.0
    assert "rotator_moved" in summary.quality_flags
    assert "no_profile" in summary.quality_flags


def test_antenna_profiles_are_reusable_and_archived_not_deleted(tmp_path):
    repository = SpotRepository(tmp_path / "profiles.sqlite3")
    saved = repository.save_antenna_profile(
        AntennaProfile(
            id=None,
            name="EFHW 40",
            antenna_type="EFHW",
            apex_height_m=9.5,
            end_height_m=3.0,
            orientation_deg=35,
            power_w=20,
            tuner_enabled=False,
            notes="Inverted-V",
        )
    )
    assert saved.id is not None
    assert repository.list_antenna_profiles() == [saved]
    updated = repository.save_antenna_profile(replace(saved, power_w=25))
    assert updated.power_w == 25
    assert updated.id != saved.id
    assert updated.revision == 2
    assert updated.predecessor_id == saved.id
    historical = repository.get_antenna_profile(saved.id)
    assert historical.power_w == 20
    assert historical.archived is True
    assert "[v1]" in historical.name
    assert repository.list_antenna_profiles() == [updated]
    repository.archive_antenna_profile(updated.id)
    assert repository.list_antenna_profiles() == []
    assert all(
        profile.archived
        for profile in repository.list_antenna_profiles(include_archived=True)
    )


def test_existing_profile_schema_is_migrated_to_revision_one(tmp_path):
    database_path = tmp_path / "legacy-profiles.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE antenna_profiles (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                antenna_type TEXT NOT NULL DEFAULT '',
                apex_height_m REAL,
                end_height_m REAL,
                orientation_deg REAL,
                power_w REAL,
                tuner_enabled INTEGER NOT NULL DEFAULT 0,
                wire_length_m REAL,
                radial_count INTEGER,
                radial_length_m REAL,
                element_count INTEGER,
                boom_length_m REAL,
                transformer_ratio TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                archived INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO antenna_profiles (
                name, antenna_type, archived, created_at, updated_at
            ) VALUES ('Legacy dipole', 'dipole', 0, '2026-01-01', '2026-01-01')
            """
        )
    repository = SpotRepository(database_path)
    profile = repository.list_antenna_profiles()[0]
    assert profile.revision == 1
    assert profile.predecessor_id is None


def test_existing_campaign_schema_receives_default_targets(tmp_path):
    database_path = tmp_path / "legacy-campaign.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE measurement_campaigns (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                tx_call TEXT NOT NULL,
                tx_grid TEXT NOT NULL,
                band TEXT NOT NULL,
                mode TEXT NOT NULL,
                antenna_profile_id INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO measurement_campaigns (
                name, objective, tx_call, tx_grid, band, mode, notes,
                started_at, created_at
            ) VALUES (
                'Legacy', 'Baseline', 'OK7PS', 'JN79', '20m', 'FT8', '',
                '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'
            )
            """
        )
    repository = SpotRepository(database_path)
    campaign = repository.list_campaigns()[0]
    assert (
        campaign.target_spots,
        campaign.target_receivers,
        campaign.target_sectors,
        campaign.target_time_blocks,
    ) == (100, 10, 8, 6)


def test_existing_tx_session_schema_receives_rotator_columns(tmp_path):
    database_path = tmp_path / "legacy-sessions.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE tx_sessions (
                id INTEGER PRIMARY KEY,
                instance_id TEXT NOT NULL,
                de_call TEXT NOT NULL,
                de_grid TEXT NOT NULL,
                mode TEXT NOT NULL,
                dial_frequency_hz INTEGER NOT NULL,
                tx_frequency_hz INTEGER NOT NULL,
                tx_message TEXT NOT NULL,
                configuration_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
            """
        )

    SpotRepository(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(tx_sessions)")
        }
    assert {
        "rotator_start_azimuth_deg",
        "rotator_start_elevation_deg",
        "rotator_end_azimuth_deg",
        "rotator_end_elevation_deg",
        "rotator_max_deviation_deg",
    } <= columns


def test_measurement_campaign_persists_and_assigns_spots_and_tx_sessions(tmp_path):
    repository = SpotRepository(tmp_path / "campaign.sqlite3")
    now = datetime.now(timezone.utc)
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Vertical baseline",
            objective="Baseline before radial change",
            tx_call="OK7PS",
            tx_grid="JN79",
            band="20m",
            mode="FT8",
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="20 W",
            started_at=now - timedelta(minutes=1),
        )
    )
    assert campaign.id is not None
    assert repository.active_campaign() == campaign
    with pytest.raises(ValueError):
        repository.start_campaign(replace(campaign, id=None))

    spot = replace(generate_demo_spots(count=1)[0], observed_at=now)
    session_id = repository.start_tx_session(
        instance_id="WSJT-X",
        de_call=spot.tx_call,
        de_grid=spot.tx_grid,
        mode=spot.mode,
        dial_frequency_hz=14_074_000,
        tx_frequency_hz=spot.frequency_hz,
        tx_message="CQ",
        configuration_name="Vertical",
        antenna_profile_id=None,
        rig_frequency_hz=None,
        rig_mode=None,
        rig_ptt=None,
        started_at=now - timedelta(seconds=5),
    )
    repository.finish_tx_session(session_id, now + timedelta(seconds=5))
    assert repository.add(spot)
    assert repository.campaign_id_for_spot(spot) == campaign.id
    summary = repository.get_campaign(campaign.id)
    assert summary.spot_count == 1
    assert summary.unique_receivers == 1
    assert summary.tx_session_count == 1

    finished = repository.finish_campaign(campaign.id, now + timedelta(minutes=1))
    assert not finished.active
    assert repository.active_campaign() is None
    later = replace(
        generate_demo_spots(count=1, seed=99)[0],
        observed_at=now + timedelta(minutes=2),
    )
    assert repository.add(later)
    assert repository.campaign_id_for_spot(later) is None

    log_entry = repository.add_campaign_log_entry(
        CampaignLogEntry(
            id=None,
            campaign_id=campaign.id,
            recorded_at=now,
            category="antenna_change",
            text="Added two radials.",
        )
    )
    assert log_entry.id is not None
    assert repository.list_campaign_log_entries(campaign.id) == [log_entry]
    repository.clear()
    assert repository.list_campaign_log_entries(campaign.id) == [log_entry]


def test_receiver_activity_creates_only_verified_tx_exposure(tmp_path):
    repository = SpotRepository(tmp_path / "exposure.sqlite3")
    own_spot = generate_demo_spots(count=1)[0]
    session_id = repository.start_tx_session(
        instance_id="WSJT-X",
        de_call=own_spot.tx_call,
        de_grid=own_spot.tx_grid,
        mode="FT8",
        dial_frequency_hz=14_074_000,
        tx_frequency_hz=own_spot.frequency_hz,
        tx_message="CQ",
        configuration_name="Default",
        antenna_profile_id=None,
        rig_frequency_hz=None,
        rig_mode=None,
        rig_ptt=None,
        started_at=own_spot.observed_at - timedelta(seconds=5),
    )
    repository.finish_tx_session(session_id, own_spot.observed_at + timedelta(seconds=5))
    repository.add(own_spot)
    repository.record_receiver_activity(replace(own_spot, tx_call="OTHER"))
    repository.record_receiver_activity(
        replace(own_spot, tx_call="OTHER2", rx_call="RX-NO-DETECT", rx_grid="IO91")
    )
    observations = repository.list_exposure_observations(band="20m")
    assert {(item.receiver_call, item.detected) for item in observations} == {
        (own_spot.rx_call, True),
        ("RX-NO-DETECT", False),
    }
    assert own_spot.rx_grid[:2] in repository.known_receiver_fields("20m")
