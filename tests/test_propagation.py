from datetime import datetime, timedelta, timezone
import json
from urllib.error import URLError

import pytest

from antenna_pattern_lab.propagation import (
    DATA_SOURCES,
    IMAGE_SOURCES,
    NOAA_PROVIDER,
    NoaaSwpcClient,
    PropagationDataError,
    PropagationSnapshot,
    condition_summary,
    freshness_text,
    parse_noaa_payloads,
)


NOW = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)


def _payloads():
    return {
        "kp": [
            {
                "time_tag": "2026-07-24T06:00:00",
                "Kp": 5.33,
                "station_count": 8,
            }
        ],
        "f107": [{"flux": 148, "time_tag": "2026-07-23T20:00:00"}],
        "solar_wind_speed": [
            {"proton_speed": 586, "time_tag": "2026-07-24T07:58:00Z"}
        ],
        "solar_wind_field": [
            {"bt": 7, "bz_gsm": -6, "time_tag": "2026-07-24T07:58:00Z"}
        ],
        "scales": {
            "-1": {
                "DateStamp": "2026-07-24",
                "TimeStamp": "08:00:00",
                "R": {"Scale": "1"},
                "S": {"Scale": "0"},
                "G": {"Scale": "1"},
            }
        },
        "sunspots": [
            {"time-tag": "2026-06", "ssn": 122.4},
            {"time-tag": "2026-07", "ssn": None},
        ],
    }


def test_noaa_payloads_are_normalized_and_reproducibly_hashed():
    snapshot = parse_noaa_payloads(_payloads(), fetched_at=NOW)

    assert snapshot.provider == NOAA_PROVIDER
    assert snapshot.kp_index == 5.33
    assert snapshot.f107_sfu == 148
    assert snapshot.sunspot_number == 122.4
    assert snapshot.solar_wind_speed_kms == 586
    assert snapshot.imf_bt_nt == 7
    assert snapshot.imf_bz_nt == -6
    assert (
        snapshot.radio_blackout_scale,
        snapshot.solar_radiation_scale,
        snapshot.geomagnetic_scale,
    ) == (1, 0, 1)
    assert snapshot.observed_at == datetime(
        2026, 7, 24, 8, 0, tzinfo=timezone.utc
    )
    assert len(snapshot.payload_sha256) == 64
    assert json.loads(snapshot.raw_payload_json)["f107"]["flux"] == 148


def test_snapshot_validation_rejects_checksum_or_unphysical_value():
    base = parse_noaa_payloads(_payloads(), fetched_at=NOW)
    with pytest.raises(ValueError, match="checksum"):
        PropagationSnapshot(
            **{
                field: getattr(base, field)
                for field in base.__dataclass_fields__
                if field != "payload_sha256"
            },
            payload_sha256="0" * 64,
        ).validated()
    with pytest.raises(ValueError, match="Kp"):
        PropagationSnapshot(
            **{
                field: getattr(base, field)
                for field in base.__dataclass_fields__
                if field != "kp_index"
            },
            kp_index=12,
        ).validated()


class _Response:
    def __init__(self, content, content_type):
        self._content = content
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self._content


def test_client_fetches_to_cache_then_survives_network_failure(tmp_path):
    resources = {
        url: _Response(b"[]", "application/json")
        for url in DATA_SOURCES.values()
    }
    resources.update({
        DATA_SOURCES[key]: _Response(
            json.dumps(value).encode("utf-8"), "application/json"
        )
        for key, value in _payloads().items()
    })
    resources.update(
        {
            url: _Response(b"image-bytes", "image/png")
            for url in IMAGE_SOURCES.values()
        }
    )

    def opener(request, timeout):
        assert timeout == 4
        return resources[request.full_url]

    client = NoaaSwpcClient(
        tmp_path / "cache",
        opener=opener,
        timeout_seconds=4,
        now=lambda: NOW,
    )
    fetched = client.fetch_current()
    assert fetched.snapshot.kp_index == 5.33
    assert fetched.images["drap"] == b"image-bytes"
    assert not fetched.errors

    cached = client.load_cached()
    assert cached is not None
    assert cached.snapshot.payload_sha256 == fetched.snapshot.payload_sha256

    offline = NoaaSwpcClient(
        tmp_path / "cache",
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            URLError("offline")
        ),
        now=lambda: NOW + timedelta(hours=1),
    ).fetch_current()
    assert offline.snapshot.stale
    assert set(offline.stale_keys) == set(DATA_SOURCES) | set(IMAGE_SOURCES)
    assert len(offline.errors) == len(DATA_SOURCES) + len(IMAGE_SOURCES)


def test_client_rejects_total_failure_without_cache(tmp_path):
    client = NoaaSwpcClient(
        tmp_path / "empty",
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            URLError("offline")
        ),
        now=lambda: NOW,
    )
    with pytest.raises(PropagationDataError, match="no usable cache"):
        client.fetch_current()


def test_client_does_not_cache_oversized_responses(tmp_path):
    client = NoaaSwpcClient(
        tmp_path / "oversized",
        opener=lambda *_args, **_kwargs: _Response(
            b"[" + b"0" * (NoaaSwpcClient.MAX_JSON_BYTES + 1),
            "application/json",
        ),
        now=lambda: NOW,
    )
    with pytest.raises(PropagationDataError, match="no usable cache"):
        client.fetch_current()
    assert list((tmp_path / "oversized").glob("*")) == []


def test_condition_and_freshness_text_are_explicitly_advisory():
    disturbed = parse_noaa_payloads(_payloads(), fetched_at=NOW)
    role, summary = condition_summary(disturbed, "ENG")
    assert role == "warning"
    assert "HF" in summary
    assert "polar" in summary

    role, status = freshness_text(
        disturbed,
        "ENG",
        now=NOW + timedelta(hours=3),
    )
    assert role == "warning"
    assert "stale" in status
