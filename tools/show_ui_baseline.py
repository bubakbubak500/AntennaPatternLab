"""Show an isolated populated baseline window for real Windows inspection."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemePreference
from antenna_pattern_lab.ui import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    with tempfile.TemporaryDirectory(
        prefix="antenna-ui-visible-",
        ignore_cleanup_errors=True,
    ) as directory:
        temporary = Path(directory)
        settings = QSettings(
            str(temporary / "settings.ini"),
            QSettings.Format.IniFormat,
        )
        settings.setValue("ui/design_style", DesignStyle.MONITOR.value)
        settings.setValue("ui/theme", ThemePreference.LIGHT.value)
        settings.setValue("language", "ENG")
        settings.setValue("onboarding_completed", 1)
        window = MainWindow(
            SpotRepository(temporary / "baseline.sqlite3"),
            settings=settings,
        )
        window.resize(1366, 768)
        window.add_demo_data()
        window.show()
        return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
