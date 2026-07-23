from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .domain import Spot

FIELDS = (
    "sequence",
    "frequency_hz",
    "mode",
    "snr_db",
    "observed_at",
    "tx_call",
    "tx_grid",
    "rx_call",
    "rx_grid",
    "band",
    "source",
)


def export_spots(path: str | Path, spots: list[Spot]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for spot in spots:
            writer.writerow({field: getattr(spot, field) for field in FIELDS})


def import_spots(path: str | Path) -> list[Spot]:
    result = []
    with Path(path).open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            observed_at = datetime.fromisoformat(row["observed_at"])
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
            result.append(
                Spot(
                    sequence=int(row["sequence"]) if row.get("sequence") else None,
                    frequency_hz=int(row["frequency_hz"]),
                    mode=row["mode"].upper(),
                    snr_db=int(row["snr_db"]),
                    observed_at=observed_at,
                    tx_call=row["tx_call"].upper(),
                    tx_grid=row.get("tx_grid", "").upper(),
                    rx_call=row["rx_call"].upper(),
                    rx_grid=row.get("rx_grid", "").upper(),
                    band=row.get("band", "").lower(),
                    source=row.get("source", "pskreporter").lower(),
                )
            )
    return result
