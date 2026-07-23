from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class Spot:
    sequence: int | None
    frequency_hz: int
    mode: str
    snr_db: int
    observed_at: datetime
    tx_call: str
    tx_grid: str
    rx_call: str
    rx_grid: str
    band: str
    source: str = "pskreporter"

    @classmethod
    def from_pskr_payload(cls, payload: bytes | str | dict[str, Any]) -> "Spot":
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if isinstance(payload, str):
            payload = json.loads(payload)

        timestamp = int(payload.get("t_tx") or payload["t"])
        return cls(
            sequence=_optional_int(payload.get("sq")),
            frequency_hz=int(payload["f"]),
            mode=str(payload["md"]).upper(),
            snr_db=int(payload["rp"]),
            observed_at=datetime.fromtimestamp(timestamp, tz=timezone.utc),
            tx_call=str(payload["sc"]).strip().upper(),
            tx_grid=str(payload.get("sl") or "").strip().upper(),
            rx_call=str(payload["rc"]).strip().upper(),
            rx_grid=str(payload.get("rl") or "").strip().upper(),
            band=str(payload.get("b") or "").strip().lower(),
        )

    @property
    def source_key(self) -> str:
        # Content identity is shared by MQTT and the history API. The HTTP API
        # has no per-report sequence number, so using the MQTT sequence here
        # would store the same reception twice when live/history windows overlap.
        stable = "|".join(
            (
                self.observed_at.isoformat(),
                self.tx_call,
                self.rx_call,
                str(self.frequency_hz),
                str(self.snr_db),
            )
        )
        return "spot:" + hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _optional_int(value: Any) -> int | None:
    return None if value is None or value == "" else int(value)
