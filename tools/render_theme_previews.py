"""Render deterministic off-screen screenshots of the Monitor themes."""

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
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import DesignStyle, ThemePreference
from antenna_pattern_lab.ui import MainWindow


def render(
    output_directory: Path,
    design_style: DesignStyle,
    preference: ThemePreference,
) -> Path:
    with tempfile.TemporaryDirectory(
        prefix=f"antenna-{preference.value}-", ignore_cleanup_errors=True
    ) as temporary:
        temporary_path = Path(temporary)
        settings = QSettings(
            str(temporary_path / "settings.ini"), QSettings.Format.IniFormat
        )
        settings.setValue("ui/design_style", design_style.value)
        settings.setValue("ui/theme", preference.value)
        settings.setValue("language", "ENG")
        repository = SpotRepository(temporary_path / "preview.sqlite3")
        window = MainWindow(repository, settings=settings)
        window.resize(1440, 900)
        window.show()
        window.add_demo_data()
        application.processEvents()
        name = (
            "classic"
            if design_style == DesignStyle.CLASSIC
            else f"monitor-{preference.value}"
        )
        destination = output_directory / f"{name}.png"
        if not window.grab().save(str(destination)):
            raise RuntimeError(f"Could not save {destination}")
        window.close()
        application.processEvents()
        return destination


if __name__ == "__main__":
    application = QApplication.instance() or QApplication(sys.argv)
    output = Path(__file__).resolve().parents[1] / ".ui-preview"
    output.mkdir(exist_ok=True)
    selections = (
        (DesignStyle.CLASSIC, ThemePreference.SYSTEM),
        (DesignStyle.MONITOR, ThemePreference.DARK),
        (DesignStyle.MONITOR, ThemePreference.LIGHT),
    )
    for design, selected in selections:
        print(render(output, design, selected))
