from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from math import asin, atan2, cos, degrees, floor, radians, sin
from statistics import median
from typing import Callable, Iterable, Mapping, Sequence

from .analysis import LocatedSpot, bootstrap_median_interval, sector_quality
from .campaigns import MeasurementCampaign
from .geo import (
    distance_and_bearing,
    great_circle_segments,
    maidenhead_to_latlon,
)
from .ionosphere import GIRO_LICENSE, GIRO_PROVIDER, IonosondeMeasurement
from .nec import NecPattern
from .propagation import (
    NOAA_PROVIDER,
    PropagationSnapshot,
    ionosphere_from_snapshot,
    operational_context,
)


FEATURE_SCHEMA = "apl-propagation-features/1"
EXPECTED_MODEL_VERSION = "apl-statistical-path-baseline/1"
IONOSONDE_CATALOG_VERSION = "GIRO stations.csv retrieved with snapshot"
DEFAULT_ASSIGNMENT_TOLERANCE = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    source: str
    provider: str
    observed_at: datetime | None
    age_seconds: float | None
    stale: bool
    quality: str
    identity: str = ""
    license: str = ""
    attribution: str = ""
    catalog_version: str = ""


@dataclass(frozen=True, slots=True)
class SourceClock:
    source: str
    observed_at: datetime | None
    tolerance_seconds: int
    assigned: bool


@dataclass(frozen=True, slots=True)
class SpatialGrid:
    """Regular global grid used for route-wide model sampling.

    Values are indexed north-to-south and west-to-east. Missing cells remain
    ``None``. Bilinear interpolation uses the surrounding cells; a single
    nearest pixel is never treated as evidence for the complete route.
    """

    values: tuple[tuple[float | None, ...], ...]
    north_deg: float = 90.0
    south_deg: float = -90.0
    west_deg: float = -180.0
    east_deg: float = 180.0
    quality: tuple[tuple[float | None, ...], ...] | None = None
    source: str = ""
    observed_at: datetime | None = None

    def validated(self) -> "SpatialGrid":
        if len(self.values) < 2 or len(self.values[0]) < 2:
            raise ValueError("A spatial grid needs at least two rows and columns.")
        width = len(self.values[0])
        if any(len(row) != width for row in self.values):
            raise ValueError("Spatial-grid rows must have equal width.")
        if self.quality is not None and (
            len(self.quality) != len(self.values)
            or any(len(row) != width for row in self.quality)
        ):
            raise ValueError("Spatial-grid quality must match its values.")
        if not self.north_deg > self.south_deg or not self.east_deg > self.west_deg:
            raise ValueError("Spatial-grid bounds are invalid.")
        return self


@dataclass(frozen=True, slots=True)
class RouteGridAssessment:
    mean: float | None
    maximum: float | None
    covered_fraction: float
    elevated_fraction: float
    minimum_quality: float | None
    samples_used: int
    sample_count: int


@dataclass(frozen=True, slots=True)
class PropagationFeatures:
    schema: str
    campaign_id: int | None
    computed_at: datetime
    target_at: datetime
    tx_grid: str
    rx_grid: str
    band: str
    frequency_hz: int
    distance_km: float
    initial_bearing_deg: float
    route_points: tuple[tuple[float, float], ...]
    local_solar_time_hours: float
    day_fraction: float
    night_fraction: float
    grayline_fraction: float
    drap_absorption_db: float | None
    drap_elevated_fraction: float | None
    polar_fraction: float
    polar_absorption_risk: bool
    glotec_tec: float | None
    glotec_coverage_fraction: float | None
    fof2_mhz: float | None
    muf3000_mhz: float | None
    giro_station: str
    giro_distance_to_route_km: float | None
    kp_index: float | None
    dst_nt: float | None
    xray_state: str
    proton_scale: int | None
    source_availability: tuple[str, ...]
    missing_sources: tuple[str, ...]
    limitations: tuple[str, ...]
    provenance: tuple[SourceProvenance, ...]
    clocks: tuple[SourceClock, ...]
    assignment_tolerance_seconds: int
    snapshot_sha256: str
    receiver_network_sha256: str
    input_sha256: str

    @property
    def conclusion_allowed(self) -> bool:
        return (
            not self.missing_sources
            and "stale NOAA snapshot" not in self.limitations
            and self.drap_absorption_db is not None
            and self.muf3000_mhz is not None
        )

    @property
    def confidence_label(self) -> str:
        if not self.conclusion_allowed:
            return "insufficient"
        if self.limitations:
            return "limited"
        return "supported"

    def canonical_dict(self, *, include_hash: bool = True) -> dict[str, object]:
        result = _json_ready(asdict(self))
        if not include_hash:
            result.pop("input_sha256", None)
            result.pop("computed_at", None)
        return result

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def from_json(cls, payload: str) -> "PropagationFeatures":
        raw = json.loads(payload)
        provenance = tuple(
            SourceProvenance(
                **{
                    **item,
                    "observed_at": _optional_datetime(item.get("observed_at")),
                }
            )
            for item in raw.pop("provenance")
        )
        clocks = tuple(
            SourceClock(
                **{
                    **item,
                    "observed_at": _optional_datetime(item.get("observed_at")),
                }
            )
            for item in raw.pop("clocks")
        )
        raw["computed_at"] = _datetime(raw["computed_at"])
        raw["target_at"] = _datetime(raw["target_at"])
        raw["route_points"] = tuple(tuple(point) for point in raw["route_points"])
        for key in (
            "source_availability",
            "missing_sources",
            "limitations",
        ):
            raw[key] = tuple(raw[key])
        return cls(**raw, provenance=provenance, clocks=clocks)


@dataclass(frozen=True, slots=True)
class ExpectedSnrEstimate:
    expected_snr_db: float
    model_version: str
    terms: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class LayerSector:
    center_deg: float
    report_count: int
    unique_receivers: int
    best_snr_db: int | None
    median_snr_db: float | None
    max_distance_km: float | None
    report_density_per_1000km2: float | None
    quality_label: str
    confidence_low_db: float | None
    confidence_high_db: float | None
    normalized_db: float | None
    normalized_low_db: float | None
    normalized_high_db: float | None
    nec_gain_db: float | None
    difference_db: float | None


@dataclass(frozen=True, slots=True)
class CrossValidationResult:
    folds: int
    train_median_absolute_error_db: float | None
    test_median_absolute_error_db: float | None
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayerComparison:
    sectors: tuple[LayerSector, ...]
    model_version: str
    active_filters: tuple[tuple[str, str], ...]
    cross_validation: CrossValidationResult
    warnings: tuple[str, ...]


def spatial_grid_from_geojson(
    payload: object,
    *,
    value_keys: Sequence[str] = ("tec", "value", "anomaly", "muf"),
    quality_keys: Sequence[str] = ("quality", "confidence"),
    source: str = "NOAA GloTEC GeoJSON",
    observed_at: datetime | None = None,
) -> SpatialGrid | None:
    """Create a regular grid from a point FeatureCollection.

    An incomplete product retains missing cells so route coverage remains
    visible. Products that are not an actual two-dimensional grid are refused.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        return None
    points: list[tuple[float, float, float, float | None]] = []
    for feature in payload["features"]:
        if not isinstance(feature, dict):
            continue
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if (
            not isinstance(geometry, dict)
            or str(geometry.get("type")).lower() != "point"
            or not isinstance(geometry.get("coordinates"), (list, tuple))
            or len(geometry["coordinates"]) < 2
            or not isinstance(properties, dict)
        ):
            continue
        value = next(
            (_number(properties.get(key)) for key in value_keys if key in properties),
            None,
        )
        if value is None:
            continue
        quality = next(
            (_number(properties.get(key)) for key in quality_keys if key in properties),
            None,
        )
        try:
            longitude = float(geometry["coordinates"][0])
            latitude = float(geometry["coordinates"][1])
        except (TypeError, ValueError):
            continue
        if -90 <= latitude <= 90 and -180 <= longitude <= 180:
            points.append((latitude, longitude, value, quality))
    latitudes = sorted({point[0] for point in points}, reverse=True)
    longitudes = sorted({point[1] for point in points})
    if len(latitudes) < 2 or len(longitudes) < 2:
        return None
    latitude_index = {value: index for index, value in enumerate(latitudes)}
    longitude_index = {value: index for index, value in enumerate(longitudes)}
    values: list[list[float | None]] = [
        [None] * len(longitudes) for _latitude in latitudes
    ]
    quality_values: list[list[float | None]] = [
        [None] * len(longitudes) for _latitude in latitudes
    ]
    for latitude, longitude, value, quality in points:
        row, column = latitude_index[latitude], longitude_index[longitude]
        values[row][column] = value
        quality_values[row][column] = quality
    return SpatialGrid(
        tuple(tuple(row) for row in values),
        latitudes[0],
        latitudes[-1],
        longitudes[0],
        longitudes[-1],
        tuple(tuple(row) for row in quality_values),
        source,
        observed_at,
    ).validated()


def solar_subpoint(when: datetime) -> tuple[float, float]:
    """Approximate subsolar latitude/longitude using local UTC inputs only."""
    instant = _aware(when).astimezone(timezone.utc)
    day = instant.timetuple().tm_yday
    hour = (
        instant.hour
        + instant.minute / 60.0
        + instant.second / 3600.0
        + instant.microsecond / 3_600_000_000.0
    )
    gamma = 2.0 * 3.141592653589793 / 365.0 * (day - 1 + (hour - 12) / 24)
    declination = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2 * gamma)
        + 0.000907 * sin(2 * gamma)
        - 0.002697 * cos(3 * gamma)
        + 0.00148 * sin(3 * gamma)
    )
    equation_minutes = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )
    longitude = 180.0 - 15.0 * hour - equation_minutes / 4.0
    longitude = (longitude + 180.0) % 360.0 - 180.0
    return degrees(declination), longitude


def solar_elevation(point: tuple[float, float], when: datetime) -> float:
    sub_lat, sub_lon = solar_subpoint(when)
    latitude, longitude = map(radians, point)
    declination = radians(sub_lat)
    hour_angle = radians((point[1] - sub_lon + 180.0) % 360.0 - 180.0)
    altitude = asin(
        max(
            -1.0,
            min(
                1.0,
                sin(latitude) * sin(declination)
                + cos(latitude) * cos(declination) * cos(hour_angle),
            ),
        )
    )
    return degrees(altitude)


def route_points(
    origin: tuple[float, float],
    destination: tuple[float, float],
    point_count: int = 121,
) -> tuple[tuple[float, float], ...]:
    segments = great_circle_segments(origin, destination, point_count)
    return tuple(point for segment in segments for point in segment)


def assess_route_grid(
    grid: SpatialGrid | None,
    points: Sequence[tuple[float, float]],
    *,
    elevated_threshold: float,
) -> RouteGridAssessment:
    if grid is None or not points:
        return RouteGridAssessment(None, None, 0.0, 0.0, None, 0, len(points))
    checked = grid.validated()
    samples: list[float] = []
    quality: list[float] = []
    elevated = 0
    for point in points:
        value, item_quality = _bilinear_sample(checked, point)
        if value is None:
            continue
        samples.append(value)
        elevated += value >= elevated_threshold
        if item_quality is not None:
            quality.append(item_quality)
    return RouteGridAssessment(
        mean=(sum(samples) / len(samples) if samples else None),
        maximum=(max(samples) if samples else None),
        covered_fraction=len(samples) / len(points),
        elevated_fraction=(elevated / len(samples) if samples else 0.0),
        minimum_quality=(min(quality) if quality else None),
        samples_used=len(samples),
        sample_count=len(points),
    )


def derive_features(
    campaign: MeasurementCampaign,
    rx_grid: str,
    target_at: datetime,
    frequency_hz: int,
    snapshot: PropagationSnapshot | None,
    *,
    drap_grid: SpatialGrid | None = None,
    glotec_grid: SpatialGrid | None = None,
    receiver_calls: Iterable[str] = (),
    tx_session_times: Iterable[datetime] = (),
    computed_at: datetime | None = None,
    assignment_tolerance: timedelta = DEFAULT_ASSIGNMENT_TOLERANCE,
) -> PropagationFeatures:
    target = _aware(target_at)
    tx_grid = campaign.tx_grid.strip().upper()
    target_grid = rx_grid.strip().upper()
    origin = maidenhead_to_latlon(tx_grid)
    destination = maidenhead_to_latlon(target_grid)
    distance_km, bearing = distance_and_bearing(origin, destination)
    points = route_points(origin, destination)
    elevations = [solar_elevation(point, target) for point in points]
    day = sum(value > 6.0 for value in elevations) / len(elevations)
    night = sum(value < -6.0 for value in elevations) / len(elevations)
    grayline = max(0.0, 1.0 - day - night)
    midpoint_longitude = points[len(points) // 2][1]
    utc_hours = (
        target.astimezone(timezone.utc).hour
        + target.minute / 60.0
        + target.second / 3600.0
    )
    solar_time = (utc_hours + midpoint_longitude / 15.0) % 24.0
    polar_fraction = sum(abs(latitude) >= 60 for latitude, _longitude in points) / len(
        points
    )
    drap = assess_route_grid(drap_grid, points, elevated_threshold=1.0)
    glotec = assess_route_grid(glotec_grid, points, elevated_threshold=80.0)

    provenance: list[SourceProvenance] = []
    clocks: list[SourceClock] = []
    limitations: list[str] = []
    missing: list[str] = []
    available: list[str] = []
    kp = dst = None
    xray_state = "unavailable"
    proton = None
    fof2 = muf = giro_distance = None
    giro_station = ""
    snapshot_hash = ""
    giro_measurement: IonosondeMeasurement | None = None
    now = computed_at or datetime.now(timezone.utc)
    tolerance_seconds = round(assignment_tolerance.total_seconds())
    clocks.append(SourceClock("reports", target, 0, True))
    tx_times = tuple(_aware(value) for value in tx_session_times)
    nearest_tx = min(
        tx_times,
        key=lambda value: abs((value - target).total_seconds()),
        default=None,
    )
    tx_assigned = (
        nearest_tx is not None
        and abs((nearest_tx - target).total_seconds()) <= tolerance_seconds
    )
    clocks.append(
        SourceClock("TX sessions", nearest_tx, tolerance_seconds, tx_assigned)
    )

    if snapshot is None:
        missing.extend(("NOAA", "GIRO"))
        clocks.append(SourceClock("NOAA", None, tolerance_seconds, False))
        clocks.append(SourceClock("GIRO", None, tolerance_seconds, False))
    else:
        snap = snapshot.validated()
        snapshot_hash = snap.payload_sha256
        delta = abs((target - snap.observed_at).total_seconds())
        assigned = delta <= tolerance_seconds
        clocks.append(SourceClock("NOAA", snap.observed_at, tolerance_seconds, assigned))
        if assigned:
            available.append("NOAA")
            kp = snap.kp_index
            context = operational_context(snap)
            proton = context.proton_scale
            closest_dst = _nearest_series(context.dst, target, assignment_tolerance)
            dst = closest_dst.value if closest_dst else None
            closest_xray = _nearest_series(
                context.xray_flux, target, assignment_tolerance
            )
            xray_state = _xray_class(closest_xray.value if closest_xray else None)
            satellite = (
                context.flare.satellite
                if context.flare is not None
                else closest_xray.source if closest_xray else ""
            )
            provenance.append(
                SourceProvenance(
                    "space-weather",
                    NOAA_PROVIDER,
                    snap.observed_at,
                    delta,
                    snap.stale,
                    "snapshot checksum verified",
                    satellite,
                    attribution="NOAA Space Weather Prediction Center",
                )
            )
            if snap.stale:
                limitations.append("stale NOAA snapshot")
            ionosphere = ionosphere_from_snapshot(snap)
            if ionosphere is not None:
                giro_measurement, giro_distance, giro_station = _nearest_giro_to_route(
                    ionosphere.series, points, target, assignment_tolerance
                )
            if giro_measurement is not None:
                available.append("GIRO")
                fof2 = giro_measurement.fof2_mhz
                muf = giro_measurement.muf3000_mhz
                giro_age = abs((target - giro_measurement.observed_at).total_seconds())
                clocks.append(
                    SourceClock(
                        "GIRO",
                        giro_measurement.observed_at,
                        tolerance_seconds,
                        True,
                    )
                )
                provenance.append(
                    SourceProvenance(
                        "ionosonde",
                        GIRO_PROVIDER,
                        giro_measurement.observed_at,
                        giro_age,
                        False,
                        (
                            f"CS {giro_measurement.confidence_score}; "
                            + (
                                "manual scaling"
                                if giro_measurement.manually_validated
                                else "automatic scaling"
                            )
                        ),
                        giro_station,
                        GIRO_LICENSE,
                        (
                            "Lowell GIRO/DIDBase and the operator of "
                            f"ionosonde {giro_station}"
                        ),
                        IONOSONDE_CATALOG_VERSION,
                    )
                )
            else:
                missing.append("GIRO")
                clocks.append(SourceClock("GIRO", None, tolerance_seconds, False))
        else:
            missing.extend(("NOAA", "GIRO"))
            limitations.append("NOAA outside assignment tolerance")
            clocks.append(SourceClock("GIRO", None, tolerance_seconds, False))

    if drap.mean is None:
        missing.append("D-RAP")
        clocks.append(SourceClock("D-RAP", None, tolerance_seconds, False))
    else:
        available.append("D-RAP")
        clocks.append(
            SourceClock(
                "D-RAP",
                drap_grid.observed_at if drap_grid else None,
                tolerance_seconds,
                drap_grid is not None and drap_grid.observed_at is not None,
            )
        )
        if drap.covered_fraction < 0.8:
            limitations.append("partial D-RAP route coverage")
        provenance.append(
            SourceProvenance(
                "D-RAP",
                NOAA_PROVIDER,
                drap_grid.observed_at if drap_grid else None,
                _age_seconds(target, drap_grid.observed_at if drap_grid else None),
                False,
                f"route coverage {drap.covered_fraction:.0%}",
                drap_grid.source if drap_grid else "",
                attribution="NOAA SWPC D-Region Absorption Predictions",
            )
        )
    if glotec.mean is None:
        missing.append("GloTEC")
        clocks.append(SourceClock("GloTEC", None, tolerance_seconds, False))
    else:
        available.append("GloTEC")
        clocks.append(
            SourceClock(
                "GloTEC",
                glotec_grid.observed_at if glotec_grid else None,
                tolerance_seconds,
                glotec_grid is not None and glotec_grid.observed_at is not None,
            )
        )
        if glotec.covered_fraction < 0.8:
            limitations.append("partial GloTEC route coverage")
        provenance.append(
            SourceProvenance(
                "GloTEC",
                NOAA_PROVIDER,
                glotec_grid.observed_at if glotec_grid else None,
                _age_seconds(target, glotec_grid.observed_at if glotec_grid else None),
                False,
                (
                    f"route coverage {glotec.covered_fraction:.0%}; "
                    "TEC is not an HF-link quality or antenna-gain correction"
                ),
                glotec_grid.source if glotec_grid else "",
                attribution="NOAA SWPC GloTEC",
            )
        )
    polar_risk = polar_fraction > 0 and (proton or 0) >= 1
    if polar_risk:
        limitations.append("polar-cap absorption risk")
    if muf is None:
        limitations.append("MUF unavailable")
    elif frequency_hz / 1_000_000 > muf:
        limitations.append("operating frequency above observed MUF(3000)")
    if glotec.mean is not None:
        limitations.append("GloTEC is qualitative context only")

    receiver_hash = _hash_strings(receiver_calls)
    base = PropagationFeatures(
        FEATURE_SCHEMA,
        campaign.id,
        now,
        target,
        tx_grid,
        target_grid,
        campaign.band,
        int(frequency_hz),
        distance_km,
        bearing,
        points,
        solar_time,
        day,
        night,
        grayline,
        drap.mean,
        drap.elevated_fraction if drap.mean is not None else None,
        polar_fraction,
        polar_risk,
        glotec.mean,
        glotec.covered_fraction if glotec.mean is not None else None,
        fof2,
        muf,
        giro_station,
        giro_distance,
        kp,
        dst,
        xray_state,
        proton,
        tuple(sorted(set(available))),
        tuple(sorted(set(missing))),
        tuple(dict.fromkeys(limitations)),
        tuple(provenance),
        tuple(clocks),
        tolerance_seconds,
        snapshot_hash,
        receiver_hash,
        "",
    )
    digest = hashlib.sha256(
        json.dumps(
            base.canonical_dict(include_hash=False),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return replace(base, input_sha256=digest)


def expected_snr(features: PropagationFeatures) -> ExpectedSnrEstimate:
    """Return a transparent relative path baseline, never a link guarantee."""
    distance_term = -20.0 * _safe_log10(max(100.0, features.distance_km) / 1000.0)
    frequency_mhz = max(1.0, features.frequency_hz / 1_000_000.0)
    frequency_term = -3.0 * _safe_log10(frequency_mhz / 14.074)
    illumination_term = 1.5 * features.grayline_fraction - 1.5 * features.night_fraction
    absorption_term = -float(features.drap_absorption_db or 0.0)
    geomagnetic_term = -max(0.0, float(features.kp_index or 0.0) - 3.0) * 0.7
    muf_term = 0.0
    if features.muf3000_mhz is not None:
        margin = features.muf3000_mhz - frequency_mhz
        muf_term = max(-12.0, min(3.0, margin * 1.5))
    terms = (
        ("distance", distance_term),
        ("frequency", frequency_term),
        ("illumination", illumination_term),
        ("D-RAP", absorption_term),
        ("geomagnetic", geomagnetic_term),
        ("MUF margin", muf_term),
    )
    return ExpectedSnrEstimate(sum(value for _name, value in terms), EXPECTED_MODEL_VERSION, terms)


def compare_layers(
    located_spots: Iterable[LocatedSpot],
    feature_for_spot: Callable[[LocatedSpot], PropagationFeatures],
    *,
    nec_pattern: NecPattern | None = None,
    sector_width_deg: int = 10,
    active_filters: Mapping[str, str] | None = None,
) -> LayerComparison:
    if sector_width_deg <= 0 or 360 % sector_width_deg:
        raise ValueError("Sector width must be a positive divisor of 360.")
    spots = list(located_spots)
    sector_count = 360 // sector_width_deg
    buckets: list[list[tuple[LocatedSpot, float]]] = [
        [] for _index in range(sector_count)
    ]
    expected_by_item: dict[int, float] = {}
    warnings: list[str] = []
    for item in spots:
        features = feature_for_spot(item)
        if not features.conclusion_allowed:
            warnings.append("some propagation features are insufficient")
        estimate = expected_snr(features)
        expected_by_item[id(item)] = estimate.expected_snr_db
        index = min(int(item.bearing_deg // sector_width_deg), sector_count - 1)
        buckets[index].append((item, item.spot.snr_db - estimate.expected_snr_db))

    raw_normalized = [
        float(median(residual for _item, residual in bucket)) if bucket else None
        for bucket in buckets
    ]
    reference = median(value for value in raw_normalized if value is not None) if any(
        value is not None for value in raw_normalized
    ) else 0.0
    nec_reference = _nec_reference(nec_pattern)
    sectors: list[LayerSector] = []
    for index, bucket in enumerate(buckets):
        items = [item for item, _residual in bucket]
        snr = [item.spot.snr_db for item in items]
        residuals = [residual - reference for _item, residual in bucket]
        receivers = len({item.spot.rx_call for item in items})
        _score, quality = sector_quality(len(items), receivers)
        raw_low, raw_high = bootstrap_median_interval(snr, samples=500)
        normalized_low, normalized_high = bootstrap_median_interval(
            residuals, samples=500
        )
        center = index * sector_width_deg + sector_width_deg / 2
        nec_gain = _nearest_nec_gain(nec_pattern, center)
        if nec_gain is not None:
            nec_gain -= nec_reference
        normalized = float(median(residuals)) if residuals else None
        distances = [item.distance_km for item in items]
        radial_area = (
            3.141592653589793
            * max(distances, default=0.0) ** 2
            * sector_width_deg
            / 360.0
        )
        sectors.append(
            LayerSector(
                center,
                len(items),
                receivers,
                max(snr) if snr else None,
                float(median(snr)) if snr else None,
                max(distances) if distances else None,
                (
                    len(items) / radial_area * 1000.0
                    if radial_area > 0
                    else None
                ),
                quality,
                raw_low,
                raw_high,
                normalized,
                normalized_low,
                normalized_high,
                nec_gain,
                (
                    normalized - nec_gain
                    if normalized is not None and nec_gain is not None
                    else None
                ),
            )
        )
    validation = cross_validate_baseline(spots, feature_for_spot)
    if nec_pattern is None:
        warnings.append("NEC baseline not loaded")
    if validation.folds < 2:
        warnings.append("cross-validation needs at least two time blocks")
    return LayerComparison(
        tuple(sectors),
        EXPECTED_MODEL_VERSION,
        tuple(sorted((active_filters or {}).items())),
        validation,
        tuple(dict.fromkeys(warnings)),
    )


def cross_validate_baseline(
    spots: Sequence[LocatedSpot],
    feature_for_spot: Callable[[LocatedSpot], PropagationFeatures],
    *,
    block_minutes: int = 30,
) -> CrossValidationResult:
    blocks: dict[int, list[tuple[float, float]]] = {}
    for item in spots:
        estimate = expected_snr(feature_for_spot(item)).expected_snr_db
        block = int(item.spot.observed_at.timestamp()) // (block_minutes * 60)
        blocks.setdefault(block, []).append((item.spot.snr_db, estimate))
    if len(blocks) < 2:
        return CrossValidationResult(0, None, None, ("insufficient_time_blocks",))
    train_errors: list[float] = []
    test_errors: list[float] = []
    for held_out, test_rows in blocks.items():
        train_rows = [
            row
            for block, rows in blocks.items()
            if block != held_out
            for row in rows
        ]
        intercept = median(observed - estimate for observed, estimate in train_rows)
        train_errors.extend(
            abs(observed - (estimate + intercept))
            for observed, estimate in train_rows
        )
        test_errors.extend(
            abs(observed - (estimate + intercept))
            for observed, estimate in test_rows
        )
    return CrossValidationResult(
        len(blocks),
        float(median(train_errors)) if train_errors else None,
        float(median(test_errors)) if test_errors else None,
        (),
    )


def _nearest_giro_to_route(
    series,
    points: Sequence[tuple[float, float]],
    target: datetime,
    tolerance: timedelta,
) -> tuple[IonosondeMeasurement | None, float | None, str]:
    candidates: list[tuple[float, float, str, IonosondeMeasurement]] = []
    for item in series:
        for measurement in item.measurements:
            age = abs((target - measurement.observed_at).total_seconds())
            if age > tolerance.total_seconds():
                continue
            route_distance = min(
                distance_and_bearing(
                    (item.station.latitude, item.station.longitude), point
                )[0]
                for point in points
            )
            candidates.append((route_distance, age, item.station.code, measurement))
    if not candidates:
        return None, None, ""
    distance, _age, station, measurement = min(
        candidates, key=lambda value: (value[0], value[1])
    )
    return measurement, distance, station


def _nearest_series(points, target: datetime, tolerance: timedelta):
    usable = [
        point
        for point in points
        if abs((point.observed_at - target).total_seconds()) <= tolerance.total_seconds()
    ]
    return min(
        usable,
        key=lambda point: abs((point.observed_at - target).total_seconds()),
        default=None,
    )


def _bilinear_sample(
    grid: SpatialGrid, point: tuple[float, float]
) -> tuple[float | None, float | None]:
    latitude, longitude = point
    if not (
        grid.south_deg <= latitude <= grid.north_deg
        and grid.west_deg <= longitude <= grid.east_deg
    ):
        return None, None
    rows, columns = len(grid.values), len(grid.values[0])
    y = (grid.north_deg - latitude) / (grid.north_deg - grid.south_deg) * (rows - 1)
    x = (longitude - grid.west_deg) / (grid.east_deg - grid.west_deg) * (
        columns - 1
    )
    top, left = min(rows - 2, floor(y)), min(columns - 2, floor(x))
    dy, dx = y - top, x - left
    weights = (
        (top, left, (1 - dy) * (1 - dx)),
        (top, left + 1, (1 - dy) * dx),
        (top + 1, left, dy * (1 - dx)),
        (top + 1, left + 1, dy * dx),
    )
    values = [
        (grid.values[row][column], weight)
        for row, column, weight in weights
        if grid.values[row][column] is not None and weight > 0
    ]
    if len(values) < 2:
        return None, None
    total = sum(weight for _value, weight in values)
    value = sum(float(item) * weight for item, weight in values) / total
    quality = None
    if grid.quality is not None:
        quality_values = [
            grid.quality[row][column]
            for row, column, _weight in weights
            if grid.quality[row][column] is not None
        ]
        quality = min(quality_values) if quality_values else None
    return value, quality


def _nearest_nec_gain(pattern: NecPattern | None, bearing: float) -> float | None:
    if pattern is None or not pattern.points:
        return None
    return min(
        pattern.points,
        key=lambda point: abs((point.bearing_deg - bearing + 180) % 360 - 180),
    ).relative_gain_db


def _nec_reference(pattern: NecPattern | None) -> float:
    values = [point.relative_gain_db for point in pattern.points] if pattern else []
    return float(median(values)) if values else 0.0


def _xray_class(flux: float | None) -> str:
    if flux is None or flux <= 0:
        return "unavailable"
    for threshold, letter in (
        (1e-4, "X"),
        (1e-5, "M"),
        (1e-6, "C"),
        (1e-7, "B"),
    ):
        if flux >= threshold:
            return letter
    return "A"


def _safe_log10(value: float) -> float:
    from math import log10

    return log10(max(value, 1e-12))


def _hash_strings(values: Iterable[str]) -> str:
    canonical = "\n".join(sorted({value.strip().upper() for value in values if value.strip()}))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Propagation Intelligence timestamps must be timezone-aware.")
    return value


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _aware(parsed)


def _optional_datetime(value: str | None) -> datetime | None:
    return None if not value else _datetime(value)


def _age_seconds(target: datetime, observed: datetime | None) -> float | None:
    return None if observed is None else abs((target - observed).total_seconds())


def _json_ready(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None
