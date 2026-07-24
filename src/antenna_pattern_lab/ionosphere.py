from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
import json
from math import isfinite
import os
from pathlib import Path
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .geo import distance_and_bearing, maidenhead_to_latlon


GIRO_PROVIDER = "Lowell GIRO / DIDBase"
GIRO_STATIONS_URL = "https://lgdc.uml.edu/common/DIDBStationList"
GIRO_FASTCHAR_URL = "https://giro.uml.edu/didbase/scaled.php"
GIRO_LICENSE_URL = (
    "https://giro.uml.edu/didbase/RulesOfTheRoad.html"
)
GIRO_LICENSE = "CC BY-NC-SA 4.0"


class IonosphereDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IonosondeStation:
    code: str
    name: str
    latitude: float
    longitude: float
    latest_data: str = ""

    @property
    def ionogram_url(self) -> str:
        return (
            "https://lgdc.uml.edu/common/DIDBYearListForStation?"
            f"ursiCode={self.code}"
        )


@dataclass(frozen=True, slots=True)
class IonosondeMeasurement:
    observed_at: datetime
    confidence_score: int | None
    fof2_mhz: float | None
    muf3000_mhz: float | None
    hmf2_km: float | None
    quality_codes: tuple[str, str, str]
    manually_validated: bool


@dataclass(frozen=True, slots=True)
class IonosondeSeries:
    station: IonosondeStation
    measurements: tuple[IonosondeMeasurement, ...]
    fetched_at: datetime
    raw_text: str
    stale: bool = False

    @property
    def latest(self) -> IonosondeMeasurement | None:
        return self.measurements[-1] if self.measurements else None


@dataclass(frozen=True, slots=True)
class IonosphereBundle:
    stations: tuple[IonosondeStation, ...]
    series: tuple[IonosondeSeries, ...]
    errors: tuple[str, ...] = ()


# Stable operational subset used for immediate nearest-station selection.
# The live DIDBase station list remains available through `fetch_stations`,
# but can take more than a minute to generate. Coordinates are the station
# coordinates published by that list; individual FastChar replies re-assert
# them and are rejected if their URSI code differs from the request.
DEFAULT_STATIONS = (
    IonosondeStation("PQ052", "PRUHONICE", 50.00, 14.60),
    IonosondeStation("DB049", "DOURBES", 50.10, 4.60),
    IonosondeStation("JR055", "JULIUSRUH", 54.60, 13.40),
    IonosondeStation("MZ152", "WARSAW", 52.20, 21.10),
    IonosondeStation("RO041", "ROME", 41.80, 12.50),
    IonosondeStation("AT138", "ATHENS", 38.00, 23.50),
    IonosondeStation("TR169", "TROMSO", 69.60, 19.20),
    IonosondeStation("BC840", "BOULDER", 40.00, -105.30),
    IonosondeStation("MH453", "MILLSTONE HILL", 42.60, -71.50),
    IonosondeStation("WP937", "WALLOPS IS", 37.90, -75.50),
    IonosondeStation("AL945", "ALPENA", 45.07, -83.56),
    IonosondeStation("AS00Q", "ASCENSION ISLAND", -7.95, -14.40),
    IonosondeStation("SMJ67", "SAO LUIS", -2.60, -44.20),
    IonosondeStation("BVJ03", "BOA VISTA", 2.80, -60.70),
    IonosondeStation("GR13L", "GRAHAMSTOWN", -33.30, 26.50),
    IonosondeStation("LL721", "LOUISVALE", -28.50, 21.20),
    IonosondeStation("TR170", "TROMSO-EISCAT", 69.60, 19.20),
    IonosondeStation("TO535", "KOKUBUNJI", 35.70, 139.50),
    IonosondeStation("JI91J", "JICAMARCA", -12.00, -76.80),
    IonosondeStation("BR52P", "BRISBANE", -27.06, 153.06),
    IonosondeStation("CB53N", "CANBERRA", -35.30, 149.00),
    IonosondeStation("LV12P", "LEARMONTH", -22.20, 114.10),
    IonosondeStation("TV51R", "TOWNSVILLE", -19.63, 146.85),
    IonosondeStation("HAJ43", "HANSCOM AFB", 42.50, -71.30),
    IonosondeStation("GU513", "GUAM", 13.60, 144.90),
)


class GiroDidbaseClient:
    USER_AGENT = (
        "AntennaPatternLab/0.40 "
        "(https://github.com/bubakbubak500/AntennaPatternLab)"
    )
    MAX_RESPONSE_BYTES = 4 * 1024 * 1024

    def __init__(
        self,
        *,
        cache_path: str | Path | None = None,
        opener: Callable[..., object] = urlopen,
        timeout_seconds: float = 20.0,
        now: Callable[[], datetime] | None = None,
    ):
        self.opener = opener
        self.cache_path = Path(cache_path) if cache_path is not None else None
        self.timeout_seconds = timeout_seconds
        self.now = now or (lambda: datetime.now(timezone.utc))

    def fetch_for_grids(
        self,
        tx_grid: str,
        target_grid: str = "",
        *,
        hours: int = 24,
        station_limit: int = 2,
    ) -> IonosphereBundle:
        if hours < 1 or hours > 72:
            raise ValueError("GIRO query interval must be between 1 and 72 hours.")
        stations = DEFAULT_STATIONS
        origins = [maidenhead_to_latlon(tx_grid)]
        if target_grid.strip():
            origins.append(maidenhead_to_latlon(target_grid))
        selected: list[IonosondeStation] = []
        for origin in origins:
            for station in nearest_stations(origin, stations, station_limit):
                if station.code not in {item.code for item in selected}:
                    selected.append(station)
        end = self.now().astimezone(timezone.utc)
        start = end - timedelta(hours=hours)
        series: list[IonosondeSeries] = []
        errors: list[str] = []
        for station in selected:
            try:
                fetched = self.fetch_series(station, start, end)
                series.append(fetched)
                self._store_cached_series(fetched)
            except IonosphereDataError as exc:
                cached = self._load_cached_series(station)
                if cached is not None:
                    series.append(cached)
                    errors.append(f"{station.code}: {exc}; stale cache used")
                else:
                    errors.append(f"{station.code}: {exc}")
        return IonosphereBundle(tuple(selected), tuple(series), tuple(errors))

    def fetch_stations(self) -> tuple[IonosondeStation, ...]:
        request = Request(
            GIRO_STATIONS_URL,
            headers={"User-Agent": self.USER_AGENT, "Accept": "text/html"},
        )
        content = self._read(request)
        try:
            text = content.decode("utf-8", errors="replace")
        except UnicodeDecodeError as exc:
            raise IonosphereDataError("GIRO station list encoding is invalid.") from exc
        stations = parse_station_list(text)
        if not stations:
            raise IonosphereDataError("GIRO station list contains no usable stations.")
        return stations

    def fetch_series(
        self,
        station: IonosondeStation,
        start: datetime,
        end: datetime,
    ) -> IonosondeSeries:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("GIRO query timestamps must be timezone-aware.")
        if end <= start or end - start > timedelta(hours=72):
            raise ValueError("GIRO query interval is invalid.")
        fields = [
            ("date_start", start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")),
            ("date_end", end.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")),
            ("location", station.code),
            ("chosenchars[]", "0"),
            ("chosenchars[]", "8"),
            ("chosenchars[]", "17"),
            ("DMUF", "3000"),
            ("query_submit", "Search"),
        ]
        request = Request(
            GIRO_FASTCHAR_URL,
            data=urlencode(fields).encode("ascii"),
            headers={
                "User-Agent": self.USER_AGENT,
                "Accept": "text/plain",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        content = self._read(request)
        text = content.decode("utf-8", errors="replace")
        parsed_station, measurements = parse_fastchar(text)
        if parsed_station.code != station.code:
            raise IonosphereDataError("GIRO response station does not match request.")
        return IonosondeSeries(
            parsed_station,
            measurements,
            self.now().astimezone(timezone.utc),
            text,
        )

    def _read(self, request: Request) -> bytes:
        try:
            response = self.opener(request, timeout=self.timeout_seconds)
            with response:
                content = response.read(self.MAX_RESPONSE_BYTES + 1)
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            raise IonosphereDataError(str(exc)) from exc
        if len(content) > self.MAX_RESPONSE_BYTES:
            raise IonosphereDataError("GIRO response exceeds the safety limit.")
        if not content:
            raise IonosphereDataError("GIRO returned an empty response.")
        return content

    def _store_cached_series(self, series: IonosondeSeries) -> None:
        if self.cache_path is None:
            return
        self.cache_path.mkdir(parents=True, exist_ok=True)
        data_path = self.cache_path / f"{series.station.code}.txt"
        metadata_path = self.cache_path / f"{series.station.code}.json"
        data_part = data_path.with_suffix(".txt.part")
        metadata_part = metadata_path.with_suffix(".json.part")
        try:
            data_part.write_text(series.raw_text, encoding="utf-8")
            metadata_part.write_text(
                json.dumps(
                    {
                        "fetched_at": series.fetched_at.isoformat(),
                        "station": series.station.code,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            os.replace(data_part, data_path)
            os.replace(metadata_part, metadata_path)
        finally:
            for path in (data_part, metadata_part):
                if path.exists():
                    try:
                        path.unlink()
                    except OSError:
                        pass

    def _load_cached_series(
        self,
        station: IonosondeStation,
    ) -> IonosondeSeries | None:
        if self.cache_path is None:
            return None
        data_path = self.cache_path / f"{station.code}.txt"
        metadata_path = self.cache_path / f"{station.code}.json"
        try:
            raw = data_path.read_text(encoding="utf-8")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            parsed_station, measurements = parse_fastchar(raw)
            fetched_at = _utc_time(str(metadata["fetched_at"]))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if parsed_station.code != station.code:
            return None
        return IonosondeSeries(
            parsed_station,
            measurements,
            fetched_at,
            raw,
            stale=True,
        )


def parse_station_list(payload: str) -> tuple[IonosondeStation, ...]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", payload, flags=re.I | re.S)
    stations: list[IonosondeStation] = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 7:
            continue
        code_match = re.search(r"ursiCode=([A-Z0-9_]{5})", cells[1], flags=re.I)
        if not code_match:
            continue
        values = [_plain_text(cell) for cell in cells]
        try:
            latitude = float(values[3])
            longitude = float(values[4])
        except (ValueError, IndexError):
            continue
        if longitude > 180:
            longitude -= 360
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        stations.append(
            IonosondeStation(
                code_match.group(1).upper(),
                values[2].strip(),
                latitude,
                longitude,
                values[6].strip(),
            )
        )
    unique = {station.code: station for station in stations}
    return tuple(sorted(unique.values(), key=lambda station: station.code))


def parse_fastchar(
    payload: str,
) -> tuple[IonosondeStation, tuple[IonosondeMeasurement, ...]]:
    location = re.search(
        r"^# Location:\s*GEO\s*\(\s*([-+]?\d+(?:\.\d+)?)\s+N\s+"
        r"([-+]?\d+(?:\.\d+)?)\s+E\s*\),\s*URSI-Code\s+([A-Z0-9_]{5}),\s*(.+)$",
        payload,
        flags=re.M | re.I,
    )
    if not location:
        raise IonosphereDataError("GIRO response has no valid station header.")
    latitude = float(location.group(1))
    longitude = float(location.group(2))
    if longitude > 180:
        longitude -= 360
    station = IonosondeStation(
        location.group(3).upper(),
        location.group(4).strip(),
        latitude,
        longitude,
    )
    rows: list[IonosondeMeasurement] = []
    pattern = re.compile(
        r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+"
        r"(-?\d+)\s+(\S+)\s+(\S{2})\s+(\S+)\s+(\S{2})\s+(\S+)\s+(\S{2})\s*$"
    )
    for line in payload.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        confidence = int(match.group(2))
        rows.append(
            IonosondeMeasurement(
                observed_at=_utc_time(match.group(1)),
                confidence_score=None if confidence < 0 else confidence,
                fof2_mhz=_optional_float(match.group(3)),
                muf3000_mhz=_optional_float(match.group(5)),
                hmf2_km=_optional_float(match.group(7)),
                quality_codes=(
                    match.group(4),
                    match.group(6),
                    match.group(8),
                ),
                manually_validated=confidence == 999,
            )
        )
    rows.sort(key=lambda item: item.observed_at)
    return station, tuple(rows)


def nearest_stations(
    origin: tuple[float, float],
    stations: tuple[IonosondeStation, ...],
    limit: int = 3,
) -> tuple[IonosondeStation, ...]:
    if limit < 1:
        return ()
    return tuple(
        sorted(
            stations,
            key=lambda station: distance_and_bearing(
                origin, (station.latitude, station.longitude)
            )[0],
        )[:limit]
    )


def band_usability(
    measurement: IonosondeMeasurement | None,
    bands_mhz: tuple[tuple[str, float], ...] = (
        ("160m", 1.84),
        ("80m", 3.57),
        ("60m", 5.36),
        ("40m", 7.07),
        ("30m", 10.14),
        ("20m", 14.07),
        ("17m", 18.10),
        ("15m", 21.07),
        ("12m", 24.92),
        ("10m", 28.07),
    ),
) -> tuple[tuple[str, str], ...]:
    muf = measurement.muf3000_mhz if measurement else None
    result = []
    for band, frequency in bands_mhz:
        if muf is None:
            state = "unknown"
        elif frequency <= 0.85 * muf:
            state = "supported"
        elif frequency <= muf:
            state = "marginal"
        else:
            state = "above_muf"
        result.append((band, state))
    return tuple(result)


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(without_tags).split())


def _optional_float(value: str) -> float | None:
    if value in {"---", "NaN", "null", ""}:
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if isfinite(result) else None


def _utc_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
