from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from .domain import Spot

ENDPOINT = "https://retrieve.pskreporter.info/query"
BAND_RANGES = {
    "80m": (3_500_000, 4_000_000),
    "40m": (7_000_000, 7_300_000),
    "30m": (10_100_000, 10_150_000),
    "20m": (14_000_000, 14_350_000),
    "17m": (18_068_000, 18_168_000),
    "15m": (21_000_000, 21_450_000),
    "12m": (24_890_000, 24_990_000),
    "10m": (28_000_000, 29_700_000),
}


@dataclass(frozen=True, slots=True)
class HistoryResult:
    spots: list[Spot]
    report_count: int
    skipped_count: int
    last_sequence: int | None = None


class HistoryClient:
    def __init__(self, opener: Callable = urlopen, timeout_seconds: int = 25):
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def fetch(
        self,
        callsign: str,
        band: str,
        hours: int,
        fallback_tx_grid: str = "",
        mode: str = "FT8",
    ) -> HistoryResult:
        safe_call = callsign.strip().upper()
        if not safe_call:
            raise ValueError("Callsign is required.")
        if hours not in (1, 6, 12, 24):
            raise ValueError("History window must be 1, 6, 12 or 24 hours.")
        parameters: dict[str, str | int] = {
            "senderCallsign": safe_call,
            "flowStartSeconds": -(hours * 3600),
            "mode": mode.strip().upper() or "FT8",
            "rptlimit": 5000,
            "rronly": 1,
            "noactive": 1,
        }
        if band in BAND_RANGES:
            low, high = BAND_RANGES[band]
            parameters["frange"] = f"{low}-{high}"
        request = Request(
            f"{ENDPOINT}?{urlencode(parameters)}",
            headers={
                "Accept": "application/xml,text/xml",
                "Accept-Encoding": "identity",
                "User-Agent": "AntennaPatternLab/0.1 (PSK Reporter history import)",
            },
        )
        with self._opener(request, timeout=self._timeout_seconds) as response:
            payload = response.read()
        return parse_history_xml(payload, band, fallback_tx_grid, mode)


def parse_history_xml(
    payload: bytes | str,
    requested_band: str = "+",
    fallback_tx_grid: str = "",
    requested_mode: str = "FT8",
) -> HistoryResult:
    root = ET.fromstring(payload)
    spots: list[Spot] = []
    reports = root.findall(".//receptionReport")
    skipped = 0
    for element in reports:
        attributes = element.attrib
        try:
            frequency = int(attributes["frequency"])
            snr = int(attributes["sNR"])
            timestamp = int(attributes["flowStartSeconds"])
            tx_call = attributes["senderCallsign"].strip().upper()
            rx_call = attributes["receiverCallsign"].strip().upper()
            rx_grid = attributes["receiverLocator"].strip().upper()
            tx_grid = (attributes.get("senderLocator") or fallback_tx_grid).strip().upper()
            if not tx_call or not rx_call or not rx_grid or not tx_grid:
                raise ValueError("missing identity or locator")
        except (KeyError, TypeError, ValueError):
            skipped += 1
            continue
        band = requested_band if requested_band in BAND_RANGES else band_for_frequency(frequency)
        if not band:
            skipped += 1
            continue
        spots.append(
            Spot(
                sequence=None,
                frequency_hz=frequency,
                mode=(attributes.get("mode") or requested_mode or "FT8").upper(),
                snr_db=snr,
                observed_at=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                tx_call=tx_call,
                tx_grid=tx_grid,
                rx_call=rx_call,
                rx_grid=rx_grid,
                band=band,
            )
        )
    sequence_element = root.find(".//lastSequenceNumber")
    sequence = None
    if sequence_element is not None:
        try:
            sequence = int(sequence_element.attrib["value"])
        except (KeyError, ValueError):
            pass
    return HistoryResult(
        spots=spots,
        report_count=len(reports),
        skipped_count=skipped,
        last_sequence=sequence,
    )


def band_for_frequency(frequency_hz: int) -> str:
    for band, (low, high) in BAND_RANGES.items():
        if low <= frequency_hz <= high:
            return band
    return ""
