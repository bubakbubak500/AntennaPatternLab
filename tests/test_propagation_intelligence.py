from dataclasses import replace
from datetime import datetime, timedelta, timezone

from antenna_pattern_lab.analysis import locate_spot
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.ionosphere import (
    IonosondeMeasurement,
    IonosondeSeries,
    IonosondeStation,
    IonosphereBundle,
)
from antenna_pattern_lab.nec import NecPattern, NecPoint
from antenna_pattern_lab.propagation import (
    PropagationBundle,
    attach_ionosphere,
    parse_noaa_payloads,
)
from antenna_pattern_lab.propagation_intelligence import (
    FEATURE_SCHEMA,
    SpatialGrid,
    assess_route_grid,
    compare_layers,
    derive_features,
    solar_subpoint,
    spatial_grid_from_geojson,
)
from antenna_pattern_lab.storage import SpotRepository


NOW = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)


def _campaign() -> MeasurementCampaign:
    return MeasurementCampaign(
        id=1,
        name="20 m route study",
        objective="Propagation normalization",
        tx_call="OK7PS",
        tx_grid="JN79",
        band="20m",
        mode="FT8",
        antenna_profile_id=None,
        antenna_profile_name="Dipole",
        notes="Stable setup",
        started_at=NOW - timedelta(hours=2),
    )


def _snapshot():
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": NOW.isoformat(), "Kp": 2.3}],
            "xray": [
                {
                    "time_tag": NOW.isoformat(),
                    "energy": "0.1-0.8nm",
                    "flux": 2e-6,
                    "satellite": "GOES-19",
                }
            ],
            "protons": [
                {
                    "time_tag": NOW.isoformat(),
                    "energy": ">=10 MeV",
                    "flux": 20,
                    "satellite": "GOES-19",
                }
            ],
            "dst": [{"time_tag": NOW.isoformat(), "dst": -12}],
        },
        fetched_at=NOW,
    )
    station = IonosondeStation("PQ052", "PRUHONICE", 50.0, 14.6)
    measurement = IonosondeMeasurement(
        NOW,
        95,
        7.2,
        18.5,
        265,
        ("Q", "Q", "Q"),
        True,
    )
    ionosphere = IonosphereBundle(
        (station,),
        (IonosondeSeries(station, (measurement,), NOW, "raw"),),
    )
    return attach_ionosphere(PropagationBundle(snapshot, {}), ionosphere).snapshot


def _grid(value: float, source: str) -> SpatialGrid:
    return SpatialGrid(
        ((value, value, value), (value, value, value), (value, value, value)),
        90,
        -90,
        -180,
        180,
        ((1.0, 1.0, 1.0),) * 3,
        source,
        NOW,
    )


def test_solar_geometry_and_route_wide_spatial_sampling_are_reproducible():
    latitude, longitude = solar_subpoint(NOW)
    assert abs(latitude) < 1
    assert abs(longitude) < 3

    assessment = assess_route_grid(
        SpatialGrid(((0.0, 2.0), (4.0, 6.0))),
        ((45.0, -90.0), (0.0, 0.0), (-45.0, 90.0)),
        elevated_threshold=2.0,
    )
    assert assessment.samples_used == 3
    assert assessment.covered_fraction == 1.0
    assert 0 < assessment.mean < assessment.maximum
    assert assessment.elevated_fraction > 0


def test_geojson_grid_preserves_missing_cells_and_quality():
    grid = spatial_grid_from_geojson(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {"tec": value, "quality": 0.9},
                }
                for lon, lat, value in (
                    (-10, 10, 20),
                    (10, 10, 22),
                    (-10, -10, 18),
                )
            ],
        }
    )
    assert grid is not None
    assert grid.values[1][1] is None
    assessment = assess_route_grid(
        grid, ((5, -5), (-10, 10)), elevated_threshold=80
    )
    assert assessment.covered_fraction < 1.0


def test_feature_file_carries_hashes_clocks_quality_and_provenance():
    snapshot = _snapshot()
    first = derive_features(
        _campaign(),
        "JO62QM",
        NOW,
        14_074_000,
        snapshot,
        drap_grid=_grid(0.7, "NOAA D-RAP 20 MHz"),
        glotec_grid=_grid(24.0, "NOAA GloTEC"),
        receiver_calls=("DL1ABC", "G4XYZ"),
        computed_at=NOW,
    )
    second = derive_features(
        _campaign(),
        "JO62QM",
        NOW,
        14_074_000,
        snapshot,
        drap_grid=_grid(0.7, "NOAA D-RAP 20 MHz"),
        glotec_grid=_grid(24.0, "NOAA GloTEC"),
        receiver_calls=("G4XYZ", "DL1ABC"),
        computed_at=NOW + timedelta(minutes=1),
    )

    assert first.schema == FEATURE_SCHEMA
    assert first.input_sha256 == second.input_sha256
    assert first.receiver_network_sha256 == second.receiver_network_sha256
    assert first.giro_station == "PQ052"
    assert first.muf3000_mhz == 18.5
    assert first.proton_scale == 1
    assert first.xray_state == "C"
    assert first.conclusion_allowed
    assert any(item.identity == "GOES-19" for item in first.provenance)
    giro = next(item for item in first.provenance if item.source == "ionosonde")
    assert "manual" in giro.quality
    assert "CC BY-NC-SA" in giro.license
    assert first.from_json(first.canonical_json()) == first


def test_missing_or_old_inputs_refuse_a_supported_conclusion():
    features = derive_features(
        _campaign(),
        "JO62QM",
        NOW,
        14_074_000,
        None,
        receiver_calls=("DL1ABC",),
        computed_at=NOW,
    )
    assert not features.conclusion_allowed
    assert features.confidence_label == "insufficient"
    assert {"NOAA", "GIRO", "D-RAP", "GloTEC"} <= set(features.missing_sources)


def test_three_layers_keep_empty_sectors_and_use_blocked_cross_validation():
    base_spots = generate_demo_spots(count=30, seed=10)
    spots = [
        replace(
            spot,
            observed_at=NOW - timedelta(minutes=index * 10),
        )
        for index, spot in enumerate(base_spots)
    ]
    located = [item for spot in spots if (item := locate_spot(spot)) is not None]
    snapshot = _snapshot()

    def features(item):
        return derive_features(
            _campaign(),
            item.spot.rx_grid,
            item.spot.observed_at,
            item.spot.frequency_hz,
            snapshot,
            drap_grid=_grid(0.4, "D-RAP"),
            glotec_grid=_grid(22.0, "GloTEC"),
            receiver_calls=(value.spot.rx_call for value in located),
            computed_at=NOW,
            assignment_tolerance=timedelta(hours=6),
        )

    nec = NecPattern(
        tuple(
            NecPoint(float(bearing), -abs(bearing - 180) / 30, 5.0)
            for bearing in range(0, 360, 10)
        ),
        "test NEC",
    )
    comparison = compare_layers(
        located,
        features,
        nec_pattern=nec,
        active_filters={"band": "20m", "mode": "FT8"},
    )

    assert len(comparison.sectors) == 36
    assert any(sector.report_count == 0 and sector.normalized_db is None for sector in comparison.sectors)
    assert any(sector.report_count > 0 and sector.difference_db is not None for sector in comparison.sectors)
    assert comparison.cross_validation.folds >= 2
    assert dict(comparison.active_filters) == {"band": "20m", "mode": "FT8"}


def test_feature_sets_are_stored_separately_from_raw_spots(tmp_path):
    repository = SpotRepository(tmp_path / "features.sqlite3")
    campaign = repository.start_campaign(replace(_campaign(), id=None))
    features = derive_features(
        campaign,
        "JO62QM",
        NOW,
        14_074_000,
        _snapshot(),
        drap_grid=_grid(0.5, "D-RAP"),
        glotec_grid=_grid(21.0, "GloTEC"),
        receiver_calls=("DL1ABC",),
        computed_at=NOW,
    )
    saved = repository.save_propagation_features(features)
    assert repository.list_propagation_features(campaign.id) == [saved]
    assert repository.count() == 0
