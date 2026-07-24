"""Render deterministic Propagation Intelligence states for visual validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mpl-temp")
)

from matplotlib import get_data_path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.ionosphere import (
    IonosondeMeasurement,
    IonosondeSeries,
    IonosondeStation,
    IonosphereBundle,
)
from antenna_pattern_lab.propagation import (
    PropagationBundle,
    attach_ionosphere,
    parse_noaa_payloads,
)
from antenna_pattern_lab.propagation_intelligence_dialog import (
    PropagationIntelligenceDialog,
)
from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemeController, ThemePreference


OUTPUT = Path(
    os.environ.get(
        "APL_UI_CAPTURE_DIR",
        Path(__file__).resolve().parents[1] / "docs" / "ui" / "after",
    )
)
REFERENCE = datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc)


def snapshot():
    base = parse_noaa_payloads(
        {
            "kp": [{"time_tag": REFERENCE.isoformat(), "Kp": 3.3}],
            "xray": [
                {
                    "time_tag": REFERENCE.isoformat(),
                    "energy": "0.1-0.8nm",
                    "flux": 2.1e-6,
                    "satellite": "GOES-19",
                }
            ],
            "protons": [
                {
                    "time_tag": REFERENCE.isoformat(),
                    "energy": ">=10 MeV",
                    "flux": 12,
                    "satellite": "GOES-19",
                }
            ],
            "dst": [{"time_tag": REFERENCE.isoformat(), "dst": -22}],
            "glotec_geojson": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [longitude, latitude],
                        },
                        "properties": {"tec": 20 + (latitude + 60) / 12, "quality": 0.9},
                    }
                    for latitude in range(-60, 61, 20)
                    for longitude in range(-180, 181, 30)
                ],
            },
        },
        fetched_at=REFERENCE,
    )
    station = IonosondeStation("PQ052", "PRUHONICE", 50.0, 14.6)
    measurement = IonosondeMeasurement(
        REFERENCE,
        92,
        6.4,
        18.7,
        257,
        ("Q", "Q", "Q"),
        False,
    )
    return attach_ionosphere(
        PropagationBundle(base, {}),
        IonosphereBundle(
            (station,),
            (IonosondeSeries(station, (measurement,), REFERENCE, "visual"),),
        ),
    ).snapshot


def populate(repository: SpotRepository) -> int:
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Long summer 20 m route-normalization campaign",
            objective="Visual validation of route context and analytical layers",
            tx_call="OK7PS",
            tx_grid="JN79",
            band="20m",
            mode="FT8",
            antenna_profile_id=None,
            antenna_profile_name="Reference dipole",
            notes="Constant power; documented station setup",
            started_at=REFERENCE - timedelta(hours=6),
        )
    )
    demo = generate_demo_spots(count=72, seed=42)
    repository.add_many(
        replace(
            spot,
            observed_at=REFERENCE - timedelta(minutes=index * 5),
        )
        for index, spot in enumerate(demo)
    )
    repository.save_propagation_snapshot(campaign.id, snapshot())
    return int(campaign.id)


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    fonts = Path(get_data_path()) / "fonts" / "ttf"
    for filename in ("DejaVuSans.ttf", "DejaVuSansMono.ttf"):
        QFontDatabase.addApplicationFont(str(fonts / filename))
    QFont.insertSubstitution("Sans Serif", "DejaVu Sans")
    QFont.insertSubstitution("monospace", "DejaVu Sans Mono")
    application.setFont(QFont("DejaVu Sans"))
    native_palette = application.palette()
    native_font = application.font()
    native_stylesheet = application.styleSheet()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    states = (
        ("eng-light-route-1180x720", "ENG", DesignStyle.MONITOR, ThemePreference.LIGHT, (1180, 720), 0, True),
        ("eng-dark-layers-1366x850", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1366, 850), 1, True),
        ("cze-light-provenance-1366x850", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1366, 850), 2, True),
        ("eng-classic-route-1180x720", "ENG", DesignStyle.CLASSIC, ThemePreference.SYSTEM, (1180, 720), 0, True),
        ("eng-dark-layers-1920x1080", "ENG", DesignStyle.MONITOR, ThemePreference.DARK, (1920, 1080), 1, True),
        ("cze-light-empty-1000x680", "CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, (1000, 680), 0, False),
    )
    with tempfile.TemporaryDirectory(
        prefix="antenna-propagation-intelligence-",
        ignore_cleanup_errors=True,
    ) as directory:
        root = Path(directory)
        for name, language, design, theme, size, tab, populated in states:
            application.setPalette(native_palette)
            application.setFont(native_font)
            application.setStyleSheet(native_stylesheet)
            settings = QSettings(str(root / f"{name}.ini"), QSettings.Format.IniFormat)
            settings.setValue("ui/design_style", design.value)
            settings.setValue("ui/theme", theme.value)
            controller = ThemeController(settings)
            repository = SpotRepository(root / f"{name}.sqlite3")
            if populated:
                populate(repository)
            dialog = PropagationIntelligenceDialog(repository, language)
            dialog.resize(*size)
            dialog.tabs.setCurrentIndex(tab)
            dialog.show()
            application.processEvents()
            destination = OUTPUT / f"dialog-propagation-intelligence-{name}.png"
            if not dialog.grab().save(str(destination)):
                raise RuntimeError(f"Could not save {destination}")
            print(destination)
            dialog.close()
            controller.deleteLater()
            application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
