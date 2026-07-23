from __future__ import annotations

from PySide6.QtCore import QSettings, QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from . import __version__
from .updates import (
    DEFAULT_RELEASE_MANIFEST_URL,
    UpdateCheck,
    check_for_update,
    download_verified_installer,
)


TEXT = {
    "CZE": {
        "title": "Aktualizace aplikace",
        "heading": "Oficiální aktualizace přes GitHub Releases",
        "channel_help": (
            "Antenna Pattern Lab při každém spuštění na pozadí zkontroluje "
            "oficiální GitHub release kanál. Když není internet dostupný, "
            "aplikace pokračuje bez upozornění."
        ),
        "process": (
            "Aktuální verze: {version}\n\n"
            "Instalátor se stáhne do složky Stažené soubory a aplikace před "
            "jeho nabídnutím ověří publikovaný kontrolní součet SHA-256. "
            "Instalátor se nikdy nespustí bez vašeho potvrzení.\n\n"
            "Toto vydání zatím není podepsané Authenticode certifikátem. "
            "Windows proto může zobrazit varování „Neznámý vydavatel“. "
            "Stahujte pouze z oficiálního GitHub repozitáře."
        ),
        "releases": (
            '<a href="https://github.com/bubakbubak500/AntennaPatternLab/'
            'releases/latest">Otevřít GitHub Releases</a>'
        ),
        "check": "Zkontrolovat nyní",
        "download": "Stáhnout ověřený instalátor…",
        "close": "Zavřít",
        "current": "Používáte aktuální verzi {version}.",
        "available": "Je dostupná verze {version}.",
        "failed": "Kontrola aktualizace selhala: {error}",
        "confirm_title": "Stáhnout aktualizaci?",
        "confirm": (
            "Stáhnout instalátor verze {version} a ověřit jeho SHA-256? "
            "Nic se nespustí automaticky."
        ),
        "downloaded": (
            "Ověřený instalátor byl uložen:\n{path}\n\nOtevřít jej nyní?"
        ),
    },
    "ENG": {
        "title": "Application updates",
        "heading": "Official updates through GitHub Releases",
        "channel_help": (
            "Antenna Pattern Lab checks the official GitHub release channel "
            "in the background on every startup. If the internet is unavailable, "
            "the application continues silently."
        ),
        "process": (
            "Current version: {version}\n\n"
            "The installer is downloaded to your Downloads folder. Before it "
            "is offered, the application verifies its published SHA-256 checksum. "
            "The installer is never launched without your confirmation.\n\n"
            "This release is not yet signed with an Authenticode certificate, "
            "so Windows may display an “Unknown publisher” warning. Download "
            "only from the official GitHub repository."
        ),
        "releases": (
            '<a href="https://github.com/bubakbubak500/AntennaPatternLab/'
            'releases/latest">Open GitHub Releases</a>'
        ),
        "check": "Check now",
        "download": "Download verified installer…",
        "close": "Close",
        "current": "You are using the current version {version}.",
        "available": "Version {version} is available.",
        "failed": "Update check failed: {error}",
        "confirm_title": "Download update?",
        "confirm": (
            "Download installer version {version} and verify its SHA-256? "
            "Nothing will run automatically."
        ),
        "downloaded": (
            "The verified installer was saved to:\n{path}\n\nOpen it now?"
        ),
    },
}


class UpdateDialog(QDialog):
    def __init__(self, settings: QSettings, language: str = "CZE", parent=None):
        super().__init__(parent)
        self.settings = settings
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.update_check: UpdateCheck | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(680, 390)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h2>{self.text['heading']}</h2>"))

        help_label = QLabel(self.text["channel_help"])
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        process_label = QLabel(self.text["process"].format(version=__version__))
        process_label.setWordWrap(True)
        layout.addWidget(process_label)

        releases_label = QLabel(self.text["releases"])
        releases_label.setOpenExternalLinks(True)
        layout.addWidget(releases_label)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

        buttons = QHBoxLayout()
        self.check_button = QPushButton(self.text["check"])
        self.download_button = QPushButton(self.text["download"])
        close_button = QPushButton(self.text["close"])
        self.download_button.setEnabled(False)
        buttons.addWidget(self.check_button)
        buttons.addWidget(self.download_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.check_button.clicked.connect(self.check_now)
        self.download_button.clicked.connect(self.download_update)
        close_button.clicked.connect(self.accept)

    def save_settings(self) -> None:
        # Migrate settings from releases before 0.35.0. The official channel is
        # fixed and the lightweight startup check is now always enabled.
        self.settings.remove("release_manifest_url")
        self.settings.remove("automatic_update_checks")
        self.settings.sync()

    def check_now(self) -> None:
        self.save_settings()
        try:
            self.update_check = check_for_update(
                DEFAULT_RELEASE_MANIFEST_URL, __version__
            )
        except Exception as exc:
            self.update_check = None
            self.download_button.setEnabled(False)
            self.status.setText(self.text["failed"].format(error=exc))
            return
        self.download_button.setEnabled(self.update_check.update_available)
        key = "available" if self.update_check.update_available else "current"
        version = (
            self.update_check.manifest.version
            if self.update_check.update_available
            else __version__
        )
        self.status.setText(self.text[key].format(version=version))

    def download_update(self) -> None:
        if self.update_check is None or not self.update_check.update_available:
            return
        manifest = self.update_check.manifest
        answer = QMessageBox.question(
            self,
            self.text["confirm_title"],
            self.text["confirm"].format(version=manifest.version),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        downloads = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        try:
            path = download_verified_installer(manifest, downloads)
        except Exception as exc:
            self.status.setText(self.text["failed"].format(error=exc))
            return
        open_answer = QMessageBox.question(
            self,
            self.text["confirm_title"],
            self.text["downloaded"].format(path=path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if open_answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def accept(self) -> None:
        self.save_settings()
        super().accept()
