from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .ionosphere import (
    IonosphereBundle,
    IonosondeMeasurement,
    IonosondeSeries,
    IonosondeStation,
)

NOAA_PROVIDER = "NOAA SWPC"
NOAA_BASE_URL = "https://services.swpc.noaa.gov"

DATA_SOURCES = {
    "kp": f"{NOAA_BASE_URL}/products/noaa-planetary-k-index.json",
    "f107": f"{NOAA_BASE_URL}/products/summary/10cm-flux.json",
    "solar_wind_speed": (
        f"{NOAA_BASE_URL}/products/summary/solar-wind-speed.json"
    ),
    "solar_wind_field": (
        f"{NOAA_BASE_URL}/products/summary/solar-wind-mag-field.json"
    ),
    "scales": f"{NOAA_BASE_URL}/products/noaa-scales.json",
    "sunspots": (
        f"{NOAA_BASE_URL}/json/solar-cycle/observed-solar-cycle-indices.json"
    ),
    "xray": f"{NOAA_BASE_URL}/json/goes/primary/xrays-1-day.json",
    "xray_flare": (
        f"{NOAA_BASE_URL}/json/goes/primary/xray-flares-latest.json"
    ),
    "protons": (
        f"{NOAA_BASE_URL}/json/goes/primary/integral-protons-1-day.json"
    ),
    "solar_wind_plasma": f"{NOAA_BASE_URL}/json/rtsw/rtsw_wind_1m.json",
    "solar_wind_mag": f"{NOAA_BASE_URL}/json/rtsw/rtsw_mag_1m.json",
    "dst": f"{NOAA_BASE_URL}/products/kyoto-dst.json",
    "alerts": f"{NOAA_BASE_URL}/products/alerts.json",
    "kp_forecast": (
        f"{NOAA_BASE_URL}/products/noaa-planetary-k-index-forecast.json"
    ),
    "solar_probabilities": f"{NOAA_BASE_URL}/json/solar_probabilities.json",
    "forecast_45_day": f"{NOAA_BASE_URL}/json/45-day-forecast.json",
    "enlil": f"{NOAA_BASE_URL}/json/enlil_time_series.json",
    "glotec_geojson": f"{NOAA_BASE_URL}/products/glotec/geojson_2d_urt.json",
}

IMAGE_SOURCES = {
    "drap": f"{NOAA_BASE_URL}/images/d-rap/global.png",
    "aurora": (
        f"{NOAA_BASE_URL}/images/aurora-forecast-northern-hemisphere.jpg"
    ),
    "sun": (
        f"{NOAA_BASE_URL}/images/animations/suvi/primary/195/latest.png"
    ),
    "drap_05": f"{NOAA_BASE_URL}/images/d-rap/global_f05.png",
    "drap_10": f"{NOAA_BASE_URL}/images/d-rap/global_f10.png",
    "drap_15": f"{NOAA_BASE_URL}/images/d-rap/global_f15.png",
    "drap_20": f"{NOAA_BASE_URL}/images/d-rap/global_f20.png",
    "drap_25": f"{NOAA_BASE_URL}/images/d-rap/global_f25.png",
    "drap_30": f"{NOAA_BASE_URL}/images/d-rap/global_f30.png",
    "glotec": (
        f"{NOAA_BASE_URL}/images/animations/glotec/100asm_urt/latest.png"
    ),
}


class PropagationDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PropagationSnapshot:
    id: int | None
    campaign_id: int | None
    fetched_at: datetime
    observed_at: datetime
    provider: str
    kp_index: float | None = None
    f107_sfu: float | None = None
    sunspot_number: float | None = None
    solar_wind_speed_kms: float | None = None
    imf_bt_nt: float | None = None
    imf_bz_nt: float | None = None
    radio_blackout_scale: int | None = None
    solar_radiation_scale: int | None = None
    geomagnetic_scale: int | None = None
    payload_sha256: str = ""
    raw_payload_json: str = "{}"
    stale: bool = False

    def validated(self) -> "PropagationSnapshot":
        if self.provider.strip() != NOAA_PROVIDER:
            raise ValueError("Unsupported propagation-data provider.")
        if self.fetched_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ValueError("Propagation timestamps must be timezone-aware.")
        for value, label, lower, upper in (
            (self.kp_index, "Kp", 0, 9),
            (self.f107_sfu, "F10.7", 0, 1000),
            (self.sunspot_number, "sunspot number", 0, 1000),
            (self.solar_wind_speed_kms, "solar-wind speed", 0, 5000),
            (self.imf_bt_nt, "IMF Bt", 0, 500),
            (self.imf_bz_nt, "IMF Bz", -500, 500),
        ):
            if value is not None and not lower <= value <= upper:
                raise ValueError(f"Invalid {label} value.")
        for value, label in (
            (self.radio_blackout_scale, "R scale"),
            (self.solar_radiation_scale, "S scale"),
            (self.geomagnetic_scale, "G scale"),
        ):
            if value is not None and not 0 <= value <= 5:
                raise ValueError(f"Invalid NOAA {label}.")
        payload = self.raw_payload_json.strip() or "{}"
        try:
            json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Propagation raw payload is not valid JSON.") from exc
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if self.payload_sha256 and self.payload_sha256.lower() != digest:
            raise ValueError("Propagation payload checksum does not match.")
        return replace(
            self,
            provider=NOAA_PROVIDER,
            payload_sha256=digest,
            raw_payload_json=payload,
        )


@dataclass(frozen=True, slots=True)
class CachedResource:
    key: str
    url: str
    fetched_at: datetime
    content_type: str
    content: bytes
    sha256: str
    stale: bool


@dataclass(frozen=True, slots=True)
class PropagationBundle:
    snapshot: PropagationSnapshot
    images: dict[str, bytes]
    stale_keys: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    ionosphere: IonosphereBundle | None = None


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    observed_at: datetime
    value: float
    source: str = ""


@dataclass(frozen=True, slots=True)
class FlareSummary:
    current_class: str
    peak_class: str
    begin_at: datetime | None
    peak_at: datetime | None
    end_at: datetime | None
    satellite: str


@dataclass(frozen=True, slots=True)
class SolarWindPoint:
    observed_at: datetime
    speed_kms: float | None
    density_cm3: float | None
    dynamic_pressure_npa: float | None
    bt_nt: float | None
    bz_nt: float | None
    source: str


@dataclass(frozen=True, slots=True)
class SpaceWeatherAlert:
    issued_at: datetime
    product_id: str
    category: str
    headline: str
    message: str
    bulletin_url: str


@dataclass(frozen=True, slots=True)
class ForecastDay:
    day: datetime
    kp_max: float | None
    ap: float | None
    f107_sfu: float | None
    m_flare_percent: int | None
    x_flare_percent: int | None
    proton_percent: int | None


@dataclass(frozen=True, slots=True)
class CmeForecast:
    issued_at: datetime | None
    arrival_at: datetime | None
    speed_kms: float | None
    earth_directed: bool | None
    source: str


@dataclass(frozen=True, slots=True)
class OperationalContext:
    xray_flux: tuple[SeriesPoint, ...]
    proton_flux_10mev: tuple[SeriesPoint, ...]
    proton_scale: int
    flare: FlareSummary | None
    solar_wind: tuple[SolarWindPoint, ...]
    dst: tuple[SeriesPoint, ...]
    alerts: tuple[SpaceWeatherAlert, ...]
    forecast: tuple[ForecastDay, ...]
    cme: CmeForecast | None
    glotec_available: bool


class PropagationCache:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _paths(self, key: str) -> tuple[Path, Path]:
        safe_key = "".join(
            character for character in key if character.isalnum() or character in "-_"
        )
        if not safe_key:
            raise ValueError("Cache key is required.")
        return self.root / f"{safe_key}.bin", self.root / f"{safe_key}.json"

    def load(
        self,
        key: str,
        url: str,
        *,
        now: datetime | None = None,
        max_age: timedelta = timedelta(minutes=30),
    ) -> CachedResource | None:
        data_path, metadata_path = self._paths(key)
        if not data_path.is_file() or not metadata_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("url") != url:
                return None
            content = data_path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if digest != metadata.get("sha256"):
                return None
            fetched_at = _parse_time(metadata["fetched_at"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        current = now or datetime.now(timezone.utc)
        return CachedResource(
            key=key,
            url=url,
            fetched_at=fetched_at,
            content_type=str(metadata.get("content_type") or ""),
            content=content,
            sha256=digest,
            stale=current - fetched_at > max_age,
        )

    def store(
        self,
        key: str,
        url: str,
        content: bytes,
        content_type: str,
        *,
        fetched_at: datetime | None = None,
    ) -> CachedResource:
        if not content:
            raise ValueError("Empty NOAA response cannot be cached.")
        self.root.mkdir(parents=True, exist_ok=True)
        data_path, metadata_path = self._paths(key)
        timestamp = fetched_at or datetime.now(timezone.utc)
        digest = hashlib.sha256(content).hexdigest()
        data_temporary = data_path.with_suffix(".bin.part")
        metadata_temporary = metadata_path.with_suffix(".json.part")
        metadata = {
            "url": url,
            "fetched_at": timestamp.isoformat(),
            "content_type": content_type,
            "sha256": digest,
        }
        try:
            data_temporary.write_bytes(content)
            metadata_temporary.write_text(
                json.dumps(metadata, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(data_temporary, data_path)
            os.replace(metadata_temporary, metadata_path)
        finally:
            for temporary in (data_temporary, metadata_temporary):
                if temporary.exists():
                    try:
                        temporary.unlink()
                    except OSError:
                        pass
        return CachedResource(
            key=key,
            url=url,
            fetched_at=timestamp,
            content_type=content_type,
            content=content,
            sha256=digest,
            stale=False,
        )


class NoaaSwpcClient:
    USER_AGENT = "AntennaPatternLab/0.40 (+https://github.com/bubakbubak500/AntennaPatternLab)"
    MAX_JSON_BYTES = 4 * 1024 * 1024
    MAX_IMAGE_BYTES = 8 * 1024 * 1024

    def __init__(
        self,
        cache_path: str | Path,
        *,
        opener: Callable[..., object] = urlopen,
        timeout_seconds: float = 15.0,
        now: Callable[[], datetime] | None = None,
    ):
        self.cache = PropagationCache(cache_path)
        self.opener = opener
        self.timeout_seconds = timeout_seconds
        self.now = now or (lambda: datetime.now(timezone.utc))

    def load_cached(self) -> PropagationBundle | None:
        resources: dict[str, CachedResource] = {}
        for key, url in {**DATA_SOURCES, **IMAGE_SOURCES}.items():
            resource = self.cache.load(key, url, now=self.now())
            if resource is not None:
                resources[key] = resource
        return self._bundle_from_resources(resources) if resources else None

    def fetch_current(self) -> PropagationBundle:
        resources: dict[str, CachedResource] = {}
        errors: list[str] = []
        for key, url in {**DATA_SOURCES, **IMAGE_SOURCES}.items():
            try:
                resources[key] = self._download(key, url)
            except PropagationDataError as exc:
                cached = self.cache.load(key, url, now=self.now())
                if cached is not None:
                    resources[key] = replace(cached, stale=True)
                    errors.append(f"{key}: {exc}")
                else:
                    errors.append(f"{key}: {exc}")
        bundle = self._bundle_from_resources(resources, tuple(errors))
        if bundle is None:
            raise PropagationDataError(
                "NOAA data are unavailable and no usable cache exists."
            )
        return bundle

    def _download(self, key: str, url: str) -> CachedResource:
        request = Request(
            url,
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "application/json,image/png,image/jpeg,*/*;q=0.5",
            },
        )
        try:
            response = self.opener(request, timeout=self.timeout_seconds)
            with response:
                content_type = str(
                    response.headers.get("Content-Type", "")
                ).split(";", 1)[0]
                limit = (
                    self.MAX_IMAGE_BYTES
                    if key in IMAGE_SOURCES
                    else self.MAX_JSON_BYTES
                )
                content = response.read(limit + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise PropagationDataError(str(exc)) from exc
        expected_image = key in IMAGE_SOURCES
        if len(content) > limit:
            raise PropagationDataError("NOAA response exceeds the safety limit.")
        if expected_image and not content_type.startswith("image/"):
            raise PropagationDataError("NOAA image response has an invalid content type.")
        if not expected_image:
            try:
                json.loads(content.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PropagationDataError("NOAA JSON response is invalid.") from exc
        return self.cache.store(
            key,
            url,
            content,
            content_type,
            fetched_at=self.now(),
        )

    def _bundle_from_resources(
        self,
        resources: dict[str, CachedResource],
        errors: tuple[str, ...] = (),
    ) -> PropagationBundle | None:
        payloads: dict[str, object] = {}
        for key in DATA_SOURCES:
            resource = resources.get(key)
            if resource is None:
                continue
            try:
                payloads[key] = json.loads(resource.content.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        if not payloads:
            return None
        snapshot = parse_noaa_payloads(
            payloads,
            fetched_at=max(
                (
                    resource.fetched_at
                    for resource in resources.values()
                    if resource.key in DATA_SOURCES
                ),
                default=self.now(),
            ),
            stale=any(resource.stale for resource in resources.values()),
        )
        return PropagationBundle(
            snapshot=snapshot,
            images={
                key: resource.content
                for key, resource in resources.items()
                if key in IMAGE_SOURCES
            },
            stale_keys=tuple(
                sorted(key for key, resource in resources.items() if resource.stale)
            ),
            errors=errors,
        )


def parse_noaa_payloads(
    payloads: dict[str, object],
    *,
    fetched_at: datetime,
    stale: bool = False,
) -> PropagationSnapshot:
    observed_times: list[datetime] = []

    kp_row = _latest_dict(payloads.get("kp"))
    kp = _number(kp_row, "Kp", "kp")
    _append_time(observed_times, kp_row)

    flux_row = _latest_dict(payloads.get("f107"))
    f107 = _number(flux_row, "flux", "f10.7", "f107")
    _append_time(observed_times, flux_row)

    speed_row = _latest_dict(payloads.get("solar_wind_speed"))
    speed = _number(speed_row, "proton_speed", "speed")
    _append_time(observed_times, speed_row)

    field_row = _latest_dict(payloads.get("solar_wind_field"))
    bt = _number(field_row, "bt", "Bt")
    bz = _number(field_row, "bz_gsm", "bz", "Bz")
    _append_time(observed_times, field_row)

    sunspot_row = _latest_numeric_row(
        payloads.get("sunspots"),
        ("ssn", "observed_swpc_ssn", "observed_ssn", "sunspot_number"),
    )
    sunspots = _number(
        sunspot_row,
        "ssn",
        "observed_swpc_ssn",
        "observed_ssn",
        "sunspot_number",
    )
    _append_time(observed_times, sunspot_row)

    r_scale, s_scale, g_scale, scale_time, scale_row = _parse_noaa_scales(
        payloads.get("scales")
    )
    if scale_time is not None:
        observed_times.append(scale_time)

    # Store every normalized source response, not only the latest display row.
    # The complete canonical payload is required for campaign replay, trends,
    # provider/satellite changes and later feature extraction.
    evidence_payloads = {
        key: value for key, value in sorted(payloads.items()) if value is not None
    }
    evidence_payloads.update(
        {
            key: value
            for key, value in (
                ("kp", kp_row),
                ("f107", flux_row),
                ("solar_wind_speed", speed_row),
                ("solar_wind_field", field_row),
                ("sunspots", sunspot_row),
                ("scales", scale_row),
            )
            if value
        }
    )
    raw_payload = json.dumps(
        evidence_payloads,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    observed_at = max(observed_times, default=fetched_at)
    snapshot = PropagationSnapshot(
        id=None,
        campaign_id=None,
        fetched_at=fetched_at.astimezone(timezone.utc),
        observed_at=observed_at.astimezone(timezone.utc),
        provider=NOAA_PROVIDER,
        kp_index=kp,
        f107_sfu=f107,
        sunspot_number=sunspots,
        solar_wind_speed_kms=speed,
        imf_bt_nt=bt,
        imf_bz_nt=bz,
        radio_blackout_scale=r_scale,
        solar_radiation_scale=s_scale,
        geomagnetic_scale=g_scale,
        raw_payload_json=raw_payload,
        stale=stale,
    )
    return snapshot.validated()


def operational_context(snapshot: PropagationSnapshot) -> OperationalContext:
    try:
        payloads = json.loads(snapshot.raw_payload_json)
    except json.JSONDecodeError:
        payloads = {}
    if not isinstance(payloads, dict):
        payloads = {}

    xray = _series(
        payloads.get("xray"),
        value_keys=("flux",),
        predicate=lambda row: str(row.get("energy", "")) == "0.1-0.8nm",
        source_key="satellite",
    )
    protons = _series(
        payloads.get("protons"),
        value_keys=("flux",),
        predicate=lambda row: "10 MeV" in str(row.get("energy", "")),
        source_key="satellite",
    )
    flare = _flare_summary(payloads.get("xray_flare"))
    wind = _solar_wind_series(
        payloads.get("solar_wind_plasma"),
        payloads.get("solar_wind_mag"),
    )
    dst = _series(payloads.get("dst"), value_keys=("dst",))
    alerts = _alerts(payloads.get("alerts"))
    forecast = _forecast_days(
        payloads.get("kp_forecast"),
        payloads.get("solar_probabilities"),
        payloads.get("forecast_45_day"),
    )
    cme = _enlil_summary(payloads.get("enlil"))
    glotec = payloads.get("glotec_geojson")
    return OperationalContext(
        xray,
        protons,
        proton_scale(protons[-1].value if protons else None),
        flare,
        wind,
        dst,
        alerts,
        forecast,
        cme,
        isinstance(glotec, dict)
        and bool(glotec.get("features"))
        or isinstance(glotec, list)
        and bool(glotec),
    )


def proton_scale(flux_pfu: float | None) -> int:
    if flux_pfu is None or flux_pfu < 10:
        return 0
    if flux_pfu >= 100_000:
        return 5
    if flux_pfu >= 10_000:
        return 4
    if flux_pfu >= 1_000:
        return 3
    if flux_pfu >= 100:
        return 2
    return 1


def attach_ionosphere(
    bundle: PropagationBundle,
    ionosphere: IonosphereBundle,
) -> PropagationBundle:
    payload = json.loads(bundle.snapshot.raw_payload_json)
    payload["ionosphere"] = {
        "provider": "Lowell GIRO / DIDBase",
        "license": "CC BY-NC-SA 4.0",
        "stations": [
            {
                "code": station.code,
                "name": station.name,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "latest_data": station.latest_data,
                "ionogram_url": station.ionogram_url,
            }
            for station in ionosphere.stations
        ],
        "series": [
            {
                "station": series.station.code,
                "fetched_at": series.fetched_at.isoformat(),
                "stale": series.stale,
                "raw_text": series.raw_text,
                "measurements": [
                    {
                        "observed_at": item.observed_at.isoformat(),
                        "confidence_score": item.confidence_score,
                        "fof2_mhz": item.fof2_mhz,
                        "muf3000_mhz": item.muf3000_mhz,
                        "hmf2_km": item.hmf2_km,
                        "quality_codes": item.quality_codes,
                        "manually_validated": item.manually_validated,
                    }
                    for item in series.measurements
                ],
            }
            for series in ionosphere.series
        ],
        "errors": ionosphere.errors,
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    snapshot = replace(
        bundle.snapshot,
        raw_payload_json=raw,
        payload_sha256="",
    ).validated()
    return replace(bundle, snapshot=snapshot, ionosphere=ionosphere)


def ionosphere_from_snapshot(
    snapshot: PropagationSnapshot,
) -> IonosphereBundle | None:
    try:
        payload = json.loads(snapshot.raw_payload_json).get("ionosphere")
    except (AttributeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    stations = {}
    for row in payload.get("stations", []):
        if not isinstance(row, dict):
            continue
        try:
            station = IonosondeStation(
                str(row["code"]),
                str(row.get("name") or row["code"]),
                float(row["latitude"]),
                float(row["longitude"]),
                str(row.get("latest_data") or ""),
            )
        except (KeyError, TypeError, ValueError):
            continue
        stations[station.code] = station
    series_items = []
    for row in payload.get("series", []):
        if not isinstance(row, dict) or str(row.get("station")) not in stations:
            continue
        measurements = []
        for item in row.get("measurements", []):
            if not isinstance(item, dict):
                continue
            observed = _optional_time(item.get("observed_at"))
            if observed is None:
                continue
            quality = item.get("quality_codes")
            quality_codes = (
                tuple(str(value) for value in quality)
                if isinstance(quality, (list, tuple)) and len(quality) == 3
                else ("__", "__", "__")
            )
            measurements.append(
                IonosondeMeasurement(
                    observed,
                    _integer(item.get("confidence_score")),
                    _optional_number(item.get("fof2_mhz")),
                    _optional_number(item.get("muf3000_mhz")),
                    _optional_number(item.get("hmf2_km")),
                    quality_codes,
                    bool(item.get("manually_validated")),
                )
            )
        fetched = _optional_time(row.get("fetched_at")) or snapshot.fetched_at
        series_items.append(
            IonosondeSeries(
                stations[str(row["station"])],
                tuple(sorted(measurements, key=lambda item: item.observed_at)),
                fetched,
                str(row.get("raw_text") or ""),
                bool(row.get("stale")),
            )
        )
    return IonosphereBundle(
        tuple(stations.values()),
        tuple(series_items),
        tuple(str(value) for value in payload.get("errors", [])),
    )


def condition_summary(
    snapshot: PropagationSnapshot,
    language: str,
) -> tuple[str, str]:
    czech = language == "CZE"
    warnings: list[str] = []
    if (snapshot.radio_blackout_scale or 0) >= 1:
        warnings.append(
            "Sluneční erupce může zhoršovat KV na osvětlené straně Země."
            if czech
            else "A solar flare may degrade HF on the sunlit side of Earth."
        )
    if (snapshot.geomagnetic_scale or 0) >= 1 or (snapshot.kp_index or 0) >= 5:
        warnings.append(
            "Geomagnetická aktivita může destabilizovat zejména polární trasy."
            if czech
            else "Geomagnetic activity may destabilize polar paths in particular."
        )
    if (
        snapshot.imf_bz_nt is not None
        and snapshot.imf_bz_nt <= -5
        and (snapshot.solar_wind_speed_kms or 0) >= 500
    ):
        warnings.append(
            "Jižní Bz a rychlý sluneční vítr zvyšují riziko geomagnetické poruchy."
            if czech
            else "Southward Bz and fast solar wind raise the disturbance risk."
        )
    if warnings:
        return "warning", " ".join(warnings)
    return (
        "success",
        (
            "Z dostupných ukazatelů nevyplývá výrazná okamžitá porucha. "
            "Jde o orientační kontext, nikoli předpověď spojení."
            if czech
            else
            "Available indicators show no major immediate disturbance. "
            "This is context, not a path forecast."
        ),
    )


def freshness_text(
    snapshot: PropagationSnapshot,
    language: str,
    *,
    now: datetime | None = None,
) -> tuple[str, str]:
    current = now or datetime.now(timezone.utc)
    age = max(timedelta(), current - snapshot.fetched_at)
    minutes = int(age.total_seconds() // 60)
    stale = snapshot.stale or age > timedelta(hours=2)
    if language == "CZE":
        return (
            ("warning" if stale else "success"),
            (
                f"Cache je zastaralá · staženo před {minutes} min"
                if stale
                else f"Aktuální cache · staženo před {minutes} min"
            ),
        )
    return (
        ("warning" if stale else "success"),
        (
            f"Cached data are stale · fetched {minutes} min ago"
            if stale
            else f"Current cache · fetched {minutes} min ago"
        ),
    )


def _latest_dict(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        for item in reversed(payload):
            if isinstance(item, dict):
                return item
    return {}


def _latest_numeric_row(
    payload: object,
    keys: tuple[str, ...],
) -> dict[str, object]:
    if not isinstance(payload, list):
        return _latest_dict(payload)
    for item in reversed(payload):
        if isinstance(item, dict) and _number(item, *keys) is not None:
            return item
    return {}


def _number(row: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, "", "null"):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _append_time(target: list[datetime], row: dict[str, object]) -> None:
    for key in ("time_tag", "time-tag", "time", "date"):
        value = row.get(key)
        if not value:
            continue
        try:
            target.append(_parse_time(str(value)))
        except ValueError:
            pass
        return


def _parse_noaa_scales(
    payload: object,
) -> tuple[
    int | None,
    int | None,
    int | None,
    datetime | None,
    dict[str, object],
]:
    candidates: list[dict[str, object]] = []
    if isinstance(payload, dict):
        candidates.append(payload)
        candidates.extend(
            value for value in payload.values() if isinstance(value, dict)
        )
    elif isinstance(payload, list):
        candidates.extend(item for item in payload if isinstance(item, dict))
    for candidate in candidates:
        values = []
        for key in ("R", "S", "G"):
            nested = candidate.get(key)
            if isinstance(nested, dict):
                raw = nested.get("Scale", nested.get("scale"))
            else:
                raw = nested
            values.append(_scale_number(raw))
        if any(value is not None for value in values):
            timestamp = None
            stamp = candidate.get("DateStamp") or candidate.get("date")
            clock = candidate.get("TimeStamp") or candidate.get("time")
            if stamp:
                try:
                    timestamp = _parse_time(
                        f"{stamp}T{clock or '00:00:00'}"
                    )
                except ValueError:
                    timestamp = None
            return values[0], values[1], values[2], timestamp, candidate
    return None, None, None, None, {}


def _scale_number(value: object) -> int | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if text and text[0] in "RSG":
        text = text[1:]
    try:
        result = int(float(text))
    except ValueError:
        return None
    return result if 0 <= result <= 5 else None


def _series(
    payload: object,
    *,
    value_keys: tuple[str, ...],
    predicate: Callable[[dict[str, object]], bool] | None = None,
    source_key: str = "",
) -> tuple[SeriesPoint, ...]:
    rows = payload if isinstance(payload, list) else [payload]
    result: list[SeriesPoint] = []
    for row in rows:
        if not isinstance(row, dict) or predicate and not predicate(row):
            continue
        value = _number(row, *value_keys)
        stamp = _row_time(row)
        if value is None or stamp is None:
            continue
        result.append(
            SeriesPoint(stamp, value, str(row.get(source_key, "")) if source_key else "")
        )
    unique = {
        (point.observed_at, point.source): point
        for point in result
    }
    return tuple(sorted(unique.values(), key=lambda point: point.observed_at))


def _flare_summary(payload: object) -> FlareSummary | None:
    row = _latest_dict(payload)
    if not row:
        return None
    return FlareSummary(
        str(row.get("current_class") or "—"),
        str(row.get("max_class") or "—"),
        _optional_time(row.get("begin_time")),
        _optional_time(row.get("max_time")),
        _optional_time(row.get("end_time")),
        str(row.get("satellite") or ""),
    )


def _solar_wind_series(
    plasma_payload: object,
    mag_payload: object,
) -> tuple[SolarWindPoint, ...]:
    plasma_rows = plasma_payload if isinstance(plasma_payload, list) else []
    mag_rows = mag_payload if isinstance(mag_payload, list) else []
    plasma: dict[datetime, dict[str, object]] = {}
    magnetic: dict[datetime, dict[str, object]] = {}
    for row in plasma_rows:
        if not isinstance(row, dict) or row.get("active") is False:
            continue
        stamp = _row_time(row)
        if stamp is not None:
            plasma[stamp.replace(second=0, microsecond=0)] = row
    for row in mag_rows:
        if not isinstance(row, dict) or row.get("active") is False:
            continue
        stamp = _row_time(row)
        if stamp is not None:
            magnetic[stamp.replace(second=0, microsecond=0)] = row
    result = []
    for stamp in sorted(set(plasma) | set(magnetic)):
        wind = plasma.get(stamp, {})
        field = magnetic.get(stamp, {})
        speed = _number(wind, "proton_speed")
        density = _number(wind, "proton_density")
        # P[nPa] ≈ 1.6726e-6 * density[cm^-3] * speed[km/s]^2.
        pressure = (
            1.6726e-6 * density * speed * speed
            if density is not None and speed is not None
            else None
        )
        result.append(
            SolarWindPoint(
                stamp,
                speed,
                density,
                pressure,
                _number(field, "bt"),
                _number(field, "bz_gsm"),
                str(wind.get("source") or field.get("source") or ""),
            )
        )
    return tuple(result)


def _alerts(payload: object) -> tuple[SpaceWeatherAlert, ...]:
    rows = payload if isinstance(payload, list) else []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        issued = _optional_time(row.get("issue_datetime"))
        if issued is None:
            continue
        message = str(row.get("message") or "").strip()
        product_id = str(row.get("product_id") or "")
        upper = message.upper()
        if "RADIO BLACKOUT" in upper or "X-RAY" in upper:
            category = "radio_blackout"
        elif "SOLAR RADIATION" in upper or "PROTON" in upper:
            category = "solar_radiation"
        elif "GEOMAGNETIC" in upper or product_id.startswith("K"):
            category = "geomagnetic"
        else:
            continue
        headline = next(
            (
                line.strip()
                for line in message.splitlines()
                if any(
                    token in line.upper()
                    for token in ("ALERT:", "WARNING:", "WATCH:", "SUMMARY:")
                )
            ),
            message.splitlines()[0] if message else product_id,
        )
        result.append(
            SpaceWeatherAlert(
                issued,
                product_id,
                category,
                headline,
                message,
                (
                    "https://www.swpc.noaa.gov/products/"
                    "alerts-watches-and-warnings"
                ),
            )
        )
    result.sort(key=lambda item: item.issued_at, reverse=True)
    return tuple(result[:100])


def _forecast_days(
    kp_payload: object,
    probability_payload: object,
    long_payload: object,
) -> tuple[ForecastDay, ...]:
    days: dict[datetime, dict[str, object]] = {}
    if isinstance(kp_payload, list):
        for row in kp_payload:
            if not isinstance(row, dict) or str(row.get("observed")) != "predicted":
                continue
            stamp = _row_time(row)
            kp = _number(row, "kp")
            if stamp is None or kp is None:
                continue
            day = stamp.replace(hour=0, minute=0, second=0, microsecond=0)
            days.setdefault(day, {})["kp"] = max(
                kp, float(days.get(day, {}).get("kp", 0))
            )
    probability_rows = (
        [row for row in probability_payload if isinstance(row, dict)]
        if isinstance(probability_payload, list)
        else []
    )
    probability = max(
        probability_rows,
        key=lambda row: _row_time(row)
        or datetime.min.replace(tzinfo=timezone.utc),
        default=_latest_dict(probability_payload),
    )
    probability_day = _row_time(probability)
    if probability_day is not None:
        base = probability_day.replace(hour=0, minute=0, second=0, microsecond=0)
        for offset in range(3):
            values = days.setdefault(base + timedelta(days=offset), {})
            values["m"] = _integer(probability.get(f"m_class_{offset + 1}_day"))
            values["x"] = _integer(probability.get(f"x_class_{offset + 1}_day"))
            values["proton"] = _integer(
                probability.get(f"10mev_protons_{offset + 1}_day")
            )
    long_row = _latest_dict(long_payload)
    if isinstance(long_row.get("data"), list):
        for item in long_row["data"]:
            if not isinstance(item, dict):
                continue
            stamp = _optional_time(item.get("time"))
            value = _number(item, "value")
            metric = str(item.get("metric") or "")
            if stamp is None or value is None or metric not in {"ap", "f107"}:
                continue
            day = stamp.replace(hour=0, minute=0, second=0, microsecond=0)
            days.setdefault(day, {})[metric] = value
    return tuple(
        ForecastDay(
            day,
            _optional_number(values.get("kp")),
            _optional_number(values.get("ap")),
            _optional_number(values.get("f107")),
            _integer(values.get("m")),
            _integer(values.get("x")),
            _integer(values.get("proton")),
        )
        for day, values in sorted(days.items())
    )


def _enlil_summary(payload: object) -> CmeForecast | None:
    rows = payload if isinstance(payload, list) else []
    if not rows:
        return None
    candidates = [row for row in rows if isinstance(row, dict)]
    if not candidates:
        return None
    explicit = [
        row
        for row in candidates
        if any(
            key in row
            for key in ("arrival_time", "earth_arrival_time", "time_at_earth")
        )
    ]
    if explicit:
        row = explicit[-1]
        earth_raw = row.get("earth_directed", row.get("earth_hit"))
        return CmeForecast(
            _row_time(row),
            _optional_time(
                row.get("arrival_time")
                or row.get("earth_arrival_time")
                or row.get("time_at_earth")
            ),
            _number(row, "speed", "earth_speed", "velocity", "v_r"),
            None if earth_raw is None else bool(earth_raw),
            "NOAA WSA–ENLIL",
        )
    cloud_rows = [
        row
        for row in candidates
        if (_number(row, "cloud") or 0) > 0 and _row_time(row) is not None
    ]
    if cloud_rows:
        row = max(cloud_rows, key=lambda item: _number(item, "cloud") or 0)
        return CmeForecast(
            None,
            _row_time(row),
            _number(row, "v_r"),
            True,
            "NOAA WSA–ENLIL model cloud",
        )
    return CmeForecast(None, None, None, False, "NOAA WSA–ENLIL")


def _row_time(row: dict[str, object]) -> datetime | None:
    for key in ("time_tag", "issue_datetime", "date", "time", "issued"):
        if row.get(key):
            return _optional_time(row[key])
    return None


def _optional_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return _parse_time(str(value))
    except ValueError:
        return None


def _optional_number(value: object) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: object) -> int | None:
    try:
        return None if value is None else int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_time(value: str) -> datetime:
    normalized = value.strip()
    if len(normalized) == 7 and normalized[4] == "-":
        normalized += "-01T00:00:00+00:00"
    elif normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    result = datetime.fromisoformat(normalized)
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)
