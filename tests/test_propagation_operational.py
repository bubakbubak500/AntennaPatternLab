from datetime import datetime, timezone

from antenna_pattern_lab.propagation import (
    PropagationBundle,
    attach_ionosphere,
    ionosphere_from_snapshot,
    operational_context,
    parse_noaa_payloads,
    proton_scale,
)
from antenna_pattern_lab.ionosphere import (
    IonosphereBundle,
    IonosondeMeasurement,
    IonosondeSeries,
    IonosondeStation,
)


NOW = datetime(2026, 7, 24, 12, tzinfo=timezone.utc)


def test_operational_products_preserve_series_satellite_units_and_forecast():
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": "2026-07-24T09:00:00Z", "Kp": 3}],
            "xray": [
                {
                    "time_tag": "2026-07-24T10:00:00Z",
                    "satellite": 18,
                    "flux": 1.8e-6,
                    "energy": "0.1-0.8nm",
                },
                {
                    "time_tag": "2026-07-24T10:01:00Z",
                    "satellite": 19,
                    "flux": 2.1e-6,
                    "energy": "0.1-0.8nm",
                },
            ],
            "xray_flare": [{
                "current_class": "C2.1",
                "max_class": "M1.0",
                "begin_time": "2026-07-24T09:00:00Z",
                "max_time": "2026-07-24T09:10:00Z",
                "end_time": "2026-07-24T09:30:00Z",
                "satellite": 19,
            }],
            "protons": [{
                "time_tag": "2026-07-24T10:00:00Z",
                "satellite": 18,
                "flux": 120,
                "energy": ">=10 MeV",
            }],
            "solar_wind_plasma": [{
                "time_tag": "2026-07-24T10:00:00Z",
                "active": True,
                "source": "SOLAR1",
                "proton_speed": 500,
                "proton_density": 5,
            }],
            "solar_wind_mag": [{
                "time_tag": "2026-07-24T10:00:10Z",
                "active": True,
                "source": "SOLAR1",
                "bt": 8,
                "bz_gsm": -6,
            }],
            "dst": [{"time_tag": "2026-07-24T10:00:00", "dst": -42}],
            "alerts": [{
                "product_id": "K05W",
                "issue_datetime": "2026-07-24 10:00:00",
                "message": "WARNING: Geomagnetic storm",
            }],
            "kp_forecast": [{
                "time_tag": "2026-07-25T00:00:00",
                "kp": 5,
                "observed": "predicted",
            }],
            "solar_probabilities": [{
                "date": "2026-07-24T00:00:00",
                "m_class_1_day": 55,
                "x_class_1_day": 10,
                "10mev_protons_1_day": 5,
            }],
            "forecast_45_day": [{
                "issued": "2026-07-24T00:00:00Z",
                "data": [
                    {"time": "2026-07-25T00:00:00Z", "metric": "ap", "value": 20},
                    {"time": "2026-07-25T00:00:00Z", "metric": "f107", "value": 150},
                ],
            }],
            "glotec_geojson": {"features": [{"type": "Feature"}]},
        },
        fetched_at=NOW,
    )
    context = operational_context(snapshot)

    assert [point.source for point in context.xray_flux] == ["18", "19"]
    assert context.flare.peak_class == "M1.0"
    assert context.proton_scale == 2
    assert round(context.solar_wind[0].dynamic_pressure_npa, 2) == 2.09
    assert context.solar_wind[0].bz_nt == -6
    assert context.dst[0].value == -42
    assert context.alerts[0].category == "geomagnetic"
    day = next(item for item in context.forecast if item.day.day == 25)
    assert (day.kp_max, day.ap, day.f107_sfu) == (5, 20, 150)
    assert context.glotec_available


def test_proton_scale_uses_noaa_s1_to_s5_thresholds():
    assert [proton_scale(value) for value in (None, 9.9, 10, 100, 1000, 10000, 100000)] == [
        0, 0, 1, 2, 3, 4, 5
    ]


def test_ionosphere_is_embedded_in_and_restored_from_campaign_snapshot():
    snapshot = parse_noaa_payloads(
        {"kp": [{"time_tag": NOW.isoformat(), "Kp": 2}]},
        fetched_at=NOW,
    )
    station = IonosondeStation("PQ052", "PRUHONICE", 50, 14.6)
    measurement = IonosondeMeasurement(
        NOW, 999, 5.8, 18.3, 260, ("AA", "BB", "CC"), True
    )
    ionosphere = IonosphereBundle(
        (station,),
        (IonosondeSeries(station, (measurement,), NOW, "raw"),),
    )
    attached = attach_ionosphere(PropagationBundle(snapshot, {}), ionosphere)
    restored = ionosphere_from_snapshot(attached.snapshot)

    assert restored.series[0].latest.manually_validated
    assert restored.series[0].latest.muf3000_mhz == 18.3
    assert attached.snapshot.payload_sha256 != snapshot.payload_sha256
