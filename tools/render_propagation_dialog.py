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
from antenna_pattern_lab.domain import Spot
from antenna_pattern_lab.ionosphere import (
    IonosphereBundle,
    IonosondeMeasurement,
    IonosondeSeries,
    IonosondeStation,
)
from antenna_pattern_lab.propagation import (
    NoaaSwpcClient,
    PropagationBundle,
    attach_ionosphere,
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
            "xray": [
                {
                    "time_tag": f"2026-07-24T{hour:02d}:00:00Z",
                    "satellite": 18,
                    "flux": 1e-7 * (1 + hour / 12),
                    "energy": "0.1-0.8nm",
                }
                for hour in range(24)
            ],
            "xray_flare": [{
                "current_class": "C1.2",
                "max_class": "M1.0",
                "begin_time": "2026-07-24T08:10:00Z",
                "max_time": "2026-07-24T08:22:00Z",
                "end_time": "2026-07-24T08:40:00Z",
                "satellite": 18,
            }],
            "protons": [
                {
                    "time_tag": f"2026-07-24T{hour:02d}:00:00Z",
                    "satellite": 18,
                    "flux": 0.5 + hour / 24,
                    "energy": ">=10 MeV",
                }
                for hour in range(24)
            ],
            "solar_wind_plasma": [
                {
                    "time_tag": f"2026-07-24T{hour:02d}:00:00Z",
                    "active": True,
                    "source": "SOLAR1",
                    "proton_speed": 400 + hour * 8,
                    "proton_density": 4 + hour / 8,
                }
                for hour in range(24)
            ],
            "solar_wind_mag": [
                {
                    "time_tag": f"2026-07-24T{hour:02d}:00:00Z",
                    "active": True,
                    "source": "SOLAR1",
                    "bt": 5 + hour / 10,
                    "bz_gsm": -3 + hour / 8,
                }
                for hour in range(24)
            ],
            "dst": [
                {"time_tag": f"2026-07-24T{hour:02d}:00:00Z", "dst": -20 + hour}
                for hour in range(24)
            ],
            "alerts": [{
                "product_id": "K05W",
                "issue_datetime": "2026-07-24 09:00:00",
                "message": "WARNING: Geomagnetic K-index of 5 expected",
            }],
            "kp_forecast": [
                {
                    "time_tag": f"2026-07-{day:02d}T00:00:00",
                    "kp": 3 + day % 3,
                    "observed": "predicted",
                }
                for day in range(25, 28)
            ],
            "solar_probabilities": [{
                "date": "2026-07-24T00:00:00",
                "m_class_1_day": 45,
                "m_class_2_day": 35,
                "m_class_3_day": 25,
                "x_class_1_day": 10,
                "x_class_2_day": 5,
                "x_class_3_day": 5,
                "10mev_protons_1_day": 5,
                "10mev_protons_2_day": 5,
                "10mev_protons_3_day": 1,
            }],
            "forecast_45_day": [{
                "issued": "2026-07-24T00:00:00Z",
                "data": [
                    {"time": "2026-07-25T00:00:00Z", "metric": "ap", "value": 12},
                    {"time": "2026-07-25T00:00:00Z", "metric": "f107", "value": 148},
                ],
            }],
            "enlil": [{
                "time_tag": "2026-07-26T10:00:00Z",
                "v_r": 620,
                "cloud": 0.8,
            }],
            "glotec_geojson": {"features": [{"type": "Feature"}]},
        },
        fetched_at=datetime.now(timezone.utc),
    )
    base = PropagationBundle(
        snapshot,
        {
            "drap": representative_image("D-RAP", ("#0d2754", "#cc8b2b")),
            "drap_05": representative_image("D-RAP 5 MHz", ("#0d2754", "#cc8b2b")),
            "drap_10": representative_image("D-RAP 10 MHz", ("#0d2754", "#cc8b2b")),
            "drap_15": representative_image("D-RAP 15 MHz", ("#0d2754", "#cc8b2b")),
            "drap_20": representative_image("D-RAP 20 MHz", ("#0d2754", "#cc8b2b")),
            "drap_25": representative_image("D-RAP 25 MHz", ("#0d2754", "#cc8b2b")),
            "drap_30": representative_image("D-RAP 30 MHz", ("#0d2754", "#cc8b2b")),
            "aurora": representative_image("AURORA", ("#07141f", "#25885d")),
            "sun": representative_image("SUVI 195 Å", ("#200a03", "#b74d12")),
            "glotec": representative_image("GloTEC", ("#12233c", "#b36a39")),
        },
    )
    station = IonosondeStation("PQ052", "PRUHONICE", 50.0, 14.6)
    measurement = IonosondeMeasurement(
        datetime(2026, 7, 24, 9, 35, tzinfo=timezone.utc),
        92,
        5.7,
        18.7,
        257,
        ("//", "//", "//"),
        False,
    )
    return attach_ionosphere(
        base,
        IonosphereBundle(
            (station,),
            (IonosondeSeries(station, (measurement,), datetime.now(timezone.utc), "visual"),),
        ),
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
        ("eng-dark-trends", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), bundle(), 1),
        ("eng-dark-planning", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), bundle(), 2),
        ("cze-light-ionosphere", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 760), bundle(), 3),
        ("eng-dark-images", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), bundle(), 4),
        ("eng-dark-overview-1920x1080", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1920, 1080), bundle(), 0),
        ("eng-classic-timeline", "ENG", DesignStyle.CLASSIC, ThemePreference.LIGHT, (1180, 760), bundle(), 5),
        ("eng-light-analysis", "ENG", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 760), bundle(), 6),
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
                for index, rx_grid in enumerate(("JO70", "JN58", "IO91", "KO02")):
                    repository.add(
                        Spot(
                            sequence=index,
                            frequency_hz=14_074_000,
                            mode="FT8",
                            snr_db=-5 - index * 3,
                            observed_at=datetime(
                                2026, 7, 24, 8, index * 10, tzinfo=timezone.utc
                            ),
                            tx_call="OK7PS",
                            tx_grid="JN79",
                            rx_call=f"RX{index + 1}",
                            rx_grid=rx_grid,
                            band="20m",
                        )
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
