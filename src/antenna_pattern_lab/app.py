from __future__ import annotations

import logging
from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .storage import DatabaseMigrationError, SpotRepository
from .ui import MainWindow


def data_directory() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    return Path(location or Path.cwd() / "data")


def application_icon_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "app-icon.png"


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    application = QApplication(sys.argv)
    application.setApplicationName("Antenna Pattern Lab")
    application.setOrganizationName("OK7PS")
    application.setWindowIcon(QIcon(str(application_icon_path())))
    try:
        repository = SpotRepository(data_directory() / "spots.sqlite3")
    except DatabaseMigrationError as exc:
        QMessageBox.critical(
            None,
            "Antenna Pattern Lab – databáze / database",
            "Databázi nebylo možné bezpečně otevřít ani migrovat. "
            "Původní soubor nebyl změněn.\n\n"
            "The database could not be safely opened or migrated. "
            "The original file was left unchanged.\n\n"
            f"{exc}",
        )
        return 2
    window = MainWindow(repository)
    window.show()
    QTimer.singleShot(0, window.show_setup_if_needed)
    QTimer.singleShot(1500, window.check_updates_if_enabled)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
