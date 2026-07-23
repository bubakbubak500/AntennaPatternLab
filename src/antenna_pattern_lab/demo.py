from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

from .domain import Spot

_RECEIVERS = (
    ("DL1DEMO", "JO62QM"),
    ("G4DEMO", "IO91WM"),
    ("EA3DEMO", "JN11BJ"),
    ("OH2DEMO", "KP20LF"),
    ("W1DEMO", "FN42HM"),
    ("JA1DEMO", "PM95VR"),
    ("ZS6DEMO", "KG44EE"),
    ("VK3DEMO", "QF22NE"),
    ("PY2DEMO", "GG66RL"),
    ("4X1DEMO", "KM72JB"),
)

_BAND_FREQUENCIES = {
    "80m": 3_573_000,
    "40m": 7_074_000,
    "30m": 10_136_000,
    "20m": 14_074_000,
    "17m": 18_100_000,
    "15m": 21_074_000,
    "12m": 24_915_000,
    "10m": 28_074_000,
}

_WSPR_FREQUENCIES = {
    "80m": 3_568_600,
    "40m": 7_038_600,
    "30m": 10_138_700,
    "20m": 14_095_600,
    "17m": 18_104_600,
    "15m": 21_094_600,
    "12m": 24_924_600,
    "10m": 28_124_600,
}


def generate_demo_spots(
    callsign: str = "OK7PS",
    tx_grid: str = "JN79",
    band: str = "20m",
    count: int = 100,
    seed: int = 7,
    mode: str = "FT8",
) -> list[Spot]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    selected_band = band if band in _BAND_FREQUENCIES else "20m"
    selected_mode = mode.strip().upper() if mode.strip().upper() in ("FT8", "WSPR") else "FT8"
    center_frequency = (
        _WSPR_FREQUENCIES[selected_band]
        if selected_mode == "WSPR"
        else _BAND_FREQUENCIES[selected_band]
    )
    spots = []
    for index in range(count):
        rx_call, rx_grid = rng.choice(_RECEIVERS)
        spots.append(
            Spot(
                sequence=None,
                frequency_hz=center_frequency + rng.randint(-1200, 1200),
                mode=selected_mode,
                snr_db=rng.randint(-22, 5),
                observed_at=now - timedelta(minutes=index * 3),
                tx_call=callsign.strip().upper(),
                tx_grid=tx_grid.strip().upper(),
                rx_call=rx_call,
                rx_grid=rx_grid,
                band=selected_band,
            )
        )
    return spots
