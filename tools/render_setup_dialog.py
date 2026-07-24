"""Render the external-tools dialog for visual validation."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication
from matplotlib import get_data_path

from antenna_pattern_lab.setup_dialog import SetupDialog
from antenna_pattern_lab.theme import DesignStyle, ThemeController, ThemePreference


OUTPUT = Path(
    os.environ.get(
        "APL_UI_CAPTURE_DIR",
        Path(__file__).resolve().parents[1] / "docs" / "ui" / "after",
    )
)


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
        prefix="antenna-setup-dialog-",
        ignore_cleanup_errors=True,
    ) as directory:
        for language, design_style, theme, suffix in (
            ("CZE", DesignStyle.MONITOR, ThemePreference.LIGHT, "cze-light"),
            ("ENG", DesignStyle.MONITOR, ThemePreference.DARK, "eng-dark"),
            ("ENG", DesignStyle.CLASSIC, ThemePreference.SYSTEM, "eng-classic"),
        ):
            settings = QSettings(
                str(Path(directory) / f"{language}-{design_style.value}-{theme.value}.ini"),
                QSettings.Format.IniFormat,
            )
            settings.setValue("ui/design_style", design_style.value)
            settings.setValue("ui/theme", theme.value)
            settings.setValue("rig_model_id", 3073)
            controller = ThemeController(settings)
            dialog = SetupDialog(settings, language)
            dialog.show()
            application.processEvents()
            destination = OUTPUT / f"dialog-external-tools-{suffix}.png"
            if not dialog.grab().save(str(destination)):
                raise RuntimeError(f"Could not save {destination}")
            print(destination)
            dialog.close()
            controller.deleteLater()
            application.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
