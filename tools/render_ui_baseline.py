"""Capture deterministic Phase 1 screenshots of the existing Qt interface."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mpl-temp")
)

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from matplotlib import get_data_path

from antenna_pattern_lab.appearance_dialog import AppearanceDialog
from antenna_pattern_lab.profile_dialog import AntennaProfileDialog
from antenna_pattern_lab.settings_dialog import (
    CommunicationSettings,
    CommunicationSettingsDialog,
)
from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemePreference
from antenna_pattern_lab.ui import MainWindow


OUTPUT = (
    Path(os.environ["APL_UI_CAPTURE_DIR"])
    if os.environ.get("APL_UI_CAPTURE_DIR")
    else Path(__file__).resolve().parents[1] / "docs" / "ui" / "before"
)


def _save(widget, name: str) -> Path:
    QApplication.processEvents()
    destination = OUTPUT / f"{name}.png"
    if not widget.grab().save(str(destination)):
        raise RuntimeError(f"Could not save {destination}")
    print(destination)
    return destination


def _window(
    temporary: Path,
    name: str,
    *,
    size: tuple[int, int],
    design: DesignStyle,
    theme: ThemePreference,
    language: str,
    populated: bool,
) -> MainWindow:
    state = temporary / name
    state.mkdir()
    settings = QSettings(
        str(state / "settings.ini"),
        QSettings.Format.IniFormat,
    )
    settings.setValue("ui/design_style", design.value)
    settings.setValue("ui/theme", theme.value)
    settings.setValue("language", language)
    settings.setValue("onboarding_completed", 1)
    window = MainWindow(SpotRepository(state / "preview.sqlite3"), settings=settings)
    window.resize(*size)
    window.show()
    if populated:
        window.add_demo_data()
    QApplication.processEvents()
    return window


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    matplotlib_fonts = Path(get_data_path()) / "fonts" / "ttf"
    for filename in ("DejaVuSans.ttf", "DejaVuSansMono.ttf"):
        QFontDatabase.addApplicationFont(str(matplotlib_fonts / filename))
    QFont.insertSubstitution("Sans Serif", "DejaVu Sans")
    QFont.insertSubstitution("monospace", "DejaVu Sans Mono")
    application.setFont(QFont("DejaVu Sans"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="antenna-ui-baseline-",
        ignore_cleanup_errors=True,
    ) as directory:
        temporary = Path(directory)
        captures = (
            (
                "1366x768-monitor-light-empty-eng",
                (1366, 768),
                DesignStyle.MONITOR,
                ThemePreference.LIGHT,
                "ENG",
                False,
            ),
            (
                "1366x768-monitor-light-populated-eng",
                (1366, 768),
                DesignStyle.MONITOR,
                ThemePreference.LIGHT,
                "ENG",
                True,
            ),
            (
                "1366x768-monitor-dark-populated-eng",
                (1366, 768),
                DesignStyle.MONITOR,
                ThemePreference.DARK,
                "ENG",
                True,
            ),
            (
                "1920x1080-monitor-light-populated-eng",
                (1920, 1080),
                DesignStyle.MONITOR,
                ThemePreference.LIGHT,
                "ENG",
                True,
            ),
            (
                "1920x1080-monitor-dark-populated-eng",
                (1920, 1080),
                DesignStyle.MONITOR,
                ThemePreference.DARK,
                "ENG",
                True,
            ),
            (
                "1180x720-monitor-light-populated-cze",
                (1180, 720),
                DesignStyle.MONITOR,
                ThemePreference.LIGHT,
                "CZE",
                True,
            ),
            (
                "1366x768-classic-populated-eng",
                (1366, 768),
                DesignStyle.CLASSIC,
                ThemePreference.SYSTEM,
                "ENG",
                True,
            ),
        )
        for name, size, design, theme, language, populated in captures:
            window = _window(
                temporary,
                name,
                size=size,
                design=design,
                theme=theme,
                language=language,
                populated=populated,
            )
            _save(window, name)
            window.close()
            application.processEvents()

        window = _window(
            temporary,
            "interaction-states",
            size=(1366, 768),
            design=DesignStyle.MONITOR,
            theme=ThemePreference.LIGHT,
            language="ENG",
            populated=True,
        )
        window._collecting = True
        window._set_connection_state("connected", "Safe simulated state")
        window._apply_language()
        _save(window, "1366x768-monitor-light-collection-running-simulated")

        window.table.selectRow(0)
        _save(window, "1366x768-monitor-light-selected-report")
        window.table.clearSelection()
        if window.sector_quality_panel._buttons:
            window.sector_quality_panel._buttons[0].click()
        _save(window, "1366x768-monitor-light-selected-sector-row")

        window._set_connection_state("error", "Baseline integration failure")
        _save(window, "1366x768-monitor-light-integration-error")

        appearance = AppearanceDialog(
            DesignStyle.MONITOR,
            ThemePreference.LIGHT,
            language="ENG",
            parent=window,
        )
        appearance.show()
        _save(appearance, "dialog-appearance-eng")
        appearance.close()

        communications = CommunicationSettingsDialog(
            CommunicationSettings(
                wsjtx_host="127.0.0.1",
                wsjtx_port=2237,
                wsjtx_forward="",
                hamlib_enabled=False,
                hamlib_port=4532,
                rotator_enabled=False,
                rotator_port=4533,
                rx_activity_enabled=False,
            ),
            language="CZE",
            parent=window,
        )
        communications.show()
        _save(communications, "dialog-communications-cze")
        communications.close()

        profiles = AntennaProfileDialog(window.repository, "ENG", parent=window)
        profiles.name.setText(
            "Portable multiband reference antenna with unusually long profile name"
        )
        profiles.name.setCursorPosition(0)
        profiles.show()
        _save(profiles, "dialog-antenna-profile-eng-long-text")
        profiles.close()

        window.close()
        application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
