from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


def format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def format_signed_snr(value: int | float, decimals: int = 0) -> str:
    return f"{value:+.{decimals}f}" if decimals else f"{int(value):+d}"


def format_distance_km(value: float) -> str:
    return f"{value:,.0f}"


def format_bearing(value: float) -> str:
    return f"{value:.0f}°"


def format_frequency_mhz(value_hz: int) -> str:
    return f"{value_hz / 1_000_000:.6f}"


def compact_source(value: str) -> str:
    return {
        "pskreporter": "PSKR",
        "adif": "ADIF",
    }.get(value, value)


class TechnicalTableItem(QTableWidgetItem):
    def __init__(
        self,
        text: str,
        *,
        sort_value=None,
        tooltip: str = "",
        numeric: bool = False,
    ):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, sort_value if sort_value is not None else text)
        if tooltip:
            self.setToolTip(tooltip)
        if numeric:
            self.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

    def __lt__(self, other) -> bool:
        if isinstance(other, QTableWidgetItem):
            left = self.data(Qt.ItemDataRole.UserRole)
            right = other.data(Qt.ItemDataRole.UserRole)
            try:
                return left < right
            except TypeError:
                return str(left) < str(right)
        return super().__lt__(other)
