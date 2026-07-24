from datetime import datetime, timezone
from urllib.error import URLError

import pytest

from antenna_pattern_lab.ionosphere import (
    GiroDidbaseClient,
    IonosphereDataError,
    IonosondeMeasurement,
    band_usability,
    nearest_stations,
    parse_fastchar,
    parse_station_list,
)


STATIONS = """
<table><tr><td>1</td><td><a href="?ursiCode=PQ052">PQ052</a></td>
<td>PRUHONICE</td><td>50.00</td><td>14.60</td><td>1957</td>
<td>Jul 24, 2026</td></tr>
<tr><td>2</td><td><a href="?ursiCode=MZ152">MZ152</a></td>
<td>WARSAW</td><td>52.20</td><td>21.10</td><td>2012</td>
<td>Jul 24, 2026</td></tr></table>
"""

FASTCHAR = """# Global Ionospheric Radio Observatory (GIRO)
# Location: GEO ( 50.0 N    14.6 E ), URSI-Code PQ052, PRUHONICE
# Time                    CS   foF2 QD MUF(D) QD   hmF2 QD
2026-07-24T10:00:00.000Z   0  5.800 // 18.306 //    --- __
2026-07-24T10:05:00.000Z 999  5.900 AA 18.930 BB  260.0 CC
"""


def test_station_list_and_fastchar_are_parsed_with_quality_and_utc():
    stations = parse_station_list(STATIONS)
    assert [station.code for station in stations] == ["MZ152", "PQ052"]
    assert nearest_stations((50.0, 14.6), stations, 1)[0].code == "PQ052"

    station, rows = parse_fastchar(FASTCHAR)
    assert station.code == "PQ052"
    assert rows[0].observed_at == datetime(
        2026, 7, 24, 10, 0, tzinfo=timezone.utc
    )
    assert rows[0].hmf2_km is None
    assert rows[1].manually_validated
    assert rows[1].muf3000_mhz == 18.93


def test_band_usability_is_advisory_and_does_not_invent_missing_values():
    row = IonosondeMeasurement(
        datetime.now(timezone.utc), 80, 6.1, 18.0, 260, ("//", "//", "//"), False
    )
    states = dict(band_usability(row))
    assert states["20m"] == "supported"
    assert states["17m"] == "above_muf"
    assert {state for _, state in band_usability(None)} == {"unknown"}


class _Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.data


def test_client_uses_post_and_reports_each_unavailable_external_source():
    def opener(request, timeout):
        assert timeout == 5
        if request.full_url.endswith("DIDBStationList"):
            return _Response(STATIONS.encode())
        assert request.data
        assert b"chosenchars%5B%5D=17" in request.data
        return _Response(FASTCHAR.encode())

    client = GiroDidbaseClient(
        opener=opener,
        timeout_seconds=5,
        now=lambda: datetime(2026, 7, 24, 11, tzinfo=timezone.utc),
    )
    bundle = client.fetch_for_grids("JN79", station_limit=1)
    assert bundle.series[0].latest.muf3000_mhz == 18.93
    assert not bundle.errors

    failing = GiroDidbaseClient(
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            URLError("offline")
        )
    )
    with pytest.raises(IonosphereDataError, match="offline"):
        failing.fetch_stations()


def test_giro_series_cache_keeps_offline_workflow_usable(tmp_path):
    def online(request, timeout):
        assert request.data
        return _Response(FASTCHAR.encode())

    now = datetime(2026, 7, 24, 11, tzinfo=timezone.utc)
    first = GiroDidbaseClient(
        cache_path=tmp_path,
        opener=online,
        now=lambda: now,
    ).fetch_for_grids("JN79", station_limit=1)
    assert not first.series[0].stale

    offline = GiroDidbaseClient(
        cache_path=tmp_path,
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            URLError("offline")
        ),
        now=lambda: now,
    ).fetch_for_grids("JN79", station_limit=1)
    assert offline.series[0].stale
    assert "stale cache used" in offline.errors[0]
