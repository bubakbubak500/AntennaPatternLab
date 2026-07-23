from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from .domain import Spot
from .models import representative_frequency_hz


_TAG = re.compile(r"<([^<>]+)>", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AdifImportResult:
    spots: tuple[Spot, ...]
    record_count: int
    skipped_count: int


def import_adif(
    path: str | Path,
    *,
    fallback_tx_call: str = "",
    fallback_tx_grid: str = "",
) -> AdifImportResult:
    data = Path(path).read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    records = parse_adif_records(text)
    spots = []
    skipped = 0
    for record in records:
        try:
            spots.append(
                _record_to_spot(
                    record,
                    fallback_tx_call=fallback_tx_call,
                    fallback_tx_grid=fallback_tx_grid,
                )
            )
        except (KeyError, TypeError, ValueError):
            skipped += 1
    return AdifImportResult(tuple(spots), len(records), skipped)


def parse_adif_records(text: str) -> list[dict[str, str]]:
    """Parse length-delimited ADIF fields without treating values as markup."""
    records: list[dict[str, str]] = []
    record: dict[str, str] = {}
    position = 0
    while match := _TAG.search(text, position):
        descriptor = match.group(1).strip()
        parts = [part.strip() for part in descriptor.split(":")]
        name = parts[0].upper()
        position = match.end()
        if name == "EOH":
            record.clear()
            continue
        if name == "EOR":
            if record:
                records.append(record)
            record = {}
            continue
        if len(parts) < 2:
            continue
        try:
            length = int(parts[1])
        except ValueError:
            continue
        if length < 0 or position + length > len(text):
            raise ValueError(f"Invalid ADIF length for {name}.")
        value = text[position : position + length]
        position += length
        record[name] = value.strip()
    return records


def _record_to_spot(
    record: dict[str, str],
    *,
    fallback_tx_call: str,
    fallback_tx_grid: str,
) -> Spot:
    rx_call = record["CALL"].strip().upper()
    rx_grid = record.get("GRIDSQUARE", "").strip().upper()
    tx_call = (
        record.get("STATION_CALLSIGN")
        or record.get("OPERATOR")
        or fallback_tx_call
    ).strip().upper()
    tx_grid = (record.get("MY_GRIDSQUARE") or fallback_tx_grid).strip().upper()
    if not rx_call or not rx_grid or not tx_call or not tx_grid:
        raise ValueError("ADIF record lacks station identity or Maidenhead grid.")

    mode = (record.get("SUBMODE") or record.get("MODE") or "").strip().upper()
    if mode not in {"FT8", "WSPR"}:
        raise ValueError("Only FT8 and WSPR records are usable.")
    snr = int(record["RST_RCVD"].strip())
    if not -60 <= snr <= 60:
        raise ValueError("Signal report is outside the supported range.")

    band = record.get("BAND", "").strip().lower()
    frequency_text = record.get("FREQ", "").strip()
    if frequency_text:
        frequency_hz = round(float(frequency_text) * 1_000_000)
        if not band:
            band = _band_from_frequency(frequency_hz)
    elif band:
        frequency_hz = representative_frequency_hz(band, mode)
    else:
        raise ValueError("ADIF record lacks both FREQ and BAND.")

    date = record.get("QSO_DATE") or record.get("QSO_DATE_OFF")
    time_value = record.get("TIME_ON") or record.get("TIME_OFF")
    if not date or not time_value:
        raise ValueError("ADIF record lacks QSO date or time.")
    digits = time_value.split(".", 1)[0].strip()
    if len(digits) == 4:
        digits += "00"
    if len(date) != 8 or len(digits) != 6:
        raise ValueError("Unsupported ADIF date/time.")
    observed_at = datetime.strptime(date + digits, "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc
    )
    return Spot(
        sequence=None,
        frequency_hz=frequency_hz,
        mode=mode,
        snr_db=snr,
        observed_at=observed_at,
        tx_call=tx_call,
        tx_grid=tx_grid,
        rx_call=rx_call,
        rx_grid=rx_grid,
        band=band,
        source="adif",
    )


def _band_from_frequency(frequency_hz: int) -> str:
    mhz = frequency_hz / 1_000_000
    ranges = (
        (1.8, 2.0, "160m"),
        (3.5, 4.0, "80m"),
        (5.0, 5.5, "60m"),
        (7.0, 7.3, "40m"),
        (10.1, 10.15, "30m"),
        (14.0, 14.35, "20m"),
        (18.068, 18.168, "17m"),
        (21.0, 21.45, "15m"),
        (24.89, 24.99, "12m"),
        (28.0, 29.7, "10m"),
        (50.0, 54.0, "6m"),
    )
    for low, high, band in ranges:
        if low <= mhz <= high:
            return band
    raise ValueError("Frequency is outside supported amateur bands.")
