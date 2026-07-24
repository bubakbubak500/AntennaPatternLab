"""Render propagation-condition states for visual validation."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSettings
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication
from matplotlib import get_data_path

from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.propagation import (
    NoaaSwpcClient,
    PropagationBundle,
    parse_noaa_payloads,
)
from antenna_pattern_lab.propagation_dialog import PropagationConditionsDialog
from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemeController, ThemePreference


OUTPUT = Path(
    os.environ.get(
        "APL_UI_CAPTURE_DIR",
        Path(__file__).resolve().parents[1] / "docs" / "ui" / "after",
    )
)


class CachedClient:
    def __init__(self, bundle):
        self.bundle = bundle

    def load_cached(self):
        return self.bundle


def representative_image(title: str, colors: tuple[str, str]) -> bytes:
    image = QImage(760, 520, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    for y in range(image.height()):
        ratio = y / max(1, image.height() - 1)
        first = QColor(colors[0])
        second = QColor(colors[1])
        color = QColor(
            round(first.red() * (1 - ratio) + second.red() * ratio),
            round(first.green() * (1 - ratio) + second.green() * ratio),
            round(first.blue() * (1 - ratio) + second.blue() * ratio),
        )
        painter.setPen(color)
        painter.drawLine(0, y, image.width(), y)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPixelSize(34)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(image.rect(), 0x84, title)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def bundle() -> PropagationBundle:
    live_cache = os.environ.get("APL_NOAA_CACHE")
    if live_cache:
        cached = NoaaSwpcClient(live_cache).load_cached()
        if cached is not None:
            return cached
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": "2026-07-24T09:00:00Z", "Kp": 3.33}],
            "f107": [{"time_tag": "2026-07-24T08:00:00Z", "flux": 148}],
            "sunspots": [{"time-tag": "2026-06", "ssn": 122.4}],
            "solar_wind_speed": [
                {"time_tag": "2026-07-24T09:35:00Z", "proton_speed": 586}
            ],
            "solar_wind_field": [
                {"time_tag": "2026-07-24T09:35:00Z", "bt": 7, "bz_gsm": -3}
            ],
            "scales": {
                "-1": {
                    "DateStamp": "2026-07-24",
                    "TimeStamp": "09:30:00",
                    "R": {"Scale": "0"},
                    "S": {"Scale": "0"},
                    "G": {"Scale": "0"},
                }
            },
        },
        fetched_at=datetime.now(timezone.utc),
    )
    return PropagationBundle(
        snapshot,
        {
            "drap": representative_image("D-RAP", ("#0d2754", "#cc8b2b")),
            "aurora": representative_image("AURORA", ("#07141f", "#25885d")),
            "sun": representative_image("SUVI 195 Å", ("#200a03", "#b74d12")),
        },
    )


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    matplotlib_fonts = Path(get_data_path()) / "fonts" / "ttf"
    for filename in ("DejaVuSans.ttf", "DejaVuSansMono.ttf"):
        QFontDatabase.addApplicationFont(str(matplotlib_fonts / filename))
    QFont.insertSubstitution("Sans Serif", "DejaVu Sans")
    QFont.insertSubstitution("monospace", "DejaVu Sans Mono")
    application.setFont(QFont("DejaVu Sans"))
    native_palette = application.palette()
    native_font = application.font()
    native_stylesheet = application.styleSheet()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    states = (
        ("cze-light-empty", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (900, 620), None, 0),
        ("cze-light-overview", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 760), bundle(), 0),
        ("eng-dark-images", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), bundle(), 1),
        ("eng-dark-overview-1920x1080", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1920, 1080), bundle(), 0),
        ("eng-classic-timeline", "ENG", DesignStyle.CLASSIC, ThemePreference.LIGHT, (1180, 760), bundle(), 2),
    )
    with tempfile.TemporaryDirectory(
        prefix="antenna-propagation-dialog-",
        ignore_cleanup_errors=True,
    ) as directory:
        root = Path(directory)
        for (
            name,
            language,
            design_style,
            theme,
            size,
            current_bundle,
            tab,
        ) in states:
            application.setPalette(native_palette)
            application.setFont(native_font)
            application.setStyleSheet(native_stylesheet)
            settings = QSettings(
                str(root / f"{name}.ini"),
                QSettings.Format.IniFormat,
            )
            settings.setValue("ui/design_style", design_style.value)
            settings.setValue("ui/theme", theme.value)
            controller = ThemeController(settings)
            repository = SpotRepository(root / f"{name}.sqlite3")
            campaign = repository.start_campaign(
                MeasurementCampaign(
                    id=None,
                    name=(
                        "Dlouhá letní referenční kampaň 20 m"
                        if language == "CZE"
                        else "Long summer reference campaign 20 m"
                    ),
                    objective="Visual validation",
                    tx_call="OK7PS",
                    tx_grid="JN79",
                    band="20m",
                    mode="FT8",
                    antenna_profile_id=None,
                    antenna_profile_name="",
                    notes="Stable power",
                    started_at=datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc),
                )
            )
            if current_bundle is not None:
                repository.save_propagation_snapshot(
                    campaign.id,
                    current_bundle.snapshot,
                )
            dialog = PropagationConditionsDialog(
                repository,
                language,
                client=CachedClient(current_bundle),
            )
            dialog.resize(*size)
            dialog.tabs.setCurrentIndex(tab)
            dialog.show()
            application.processEvents()
            destination = OUTPUT / f"dialog-propagation-{name}.png"
            if not dialog.grab().save(str(destination)):
                raise RuntimeError(f"Could not save {destination}")
            print(destination)
            dialog.close()
            controller.deleteLater()
            application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
