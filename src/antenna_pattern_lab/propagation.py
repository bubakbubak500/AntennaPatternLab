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
}

IMAGE_SOURCES = {
    "drap": f"{NOAA_BASE_URL}/images/d-rap/global.png",
    "aurora": (
        f"{NOAA_BASE_URL}/images/aurora-forecast-northern-hemisphere.jpg"
    ),
    "sun": (
        f"{NOAA_BASE_URL}/images/animations/suvi/primary/195/latest.png"
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
    USER_AGENT = "AntennaPatternLab/0.39 (+https://github.com/bubakbubak500/AntennaPatternLab)"
    MAX_JSON_BYTES = 2 * 1024 * 1024
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

    evidence_payloads = {
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
