from __future__ import annotations

from PySide6.QtCore import QSettings, QStandardPaths, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        "channel": "HTTPS adresa release manifestu",
        "channel_help": "Manifest musí obsahovat version, installer_url a sha256. Bez oficiálního kanálu ponechte pole prázdné.",
        "automatic": "Automaticky kontrolovat při spuštění (pouze opt-in)",
        "check": "Zkontrolovat",
        "download": "Stáhnout ověřený instalátor…",
        "close": "Zavřít",
        "missing": "Nejdříve zadejte HTTPS adresu oficiálního manifestu.",
        "current": "Používáte aktuální verzi {version}.",
        "available": "Je dostupná verze {version}.",
        "failed": "Kontrola aktualizace selhala: {error}",
        "confirm_title": "Stáhnout aktualizaci?",
        "confirm": "Stáhnout instalátor verze {version} a ověřit jeho SHA-256? Nic se nespustí automaticky.",
        "downloaded": "Ověřený instalátor byl uložen:\n{path}\n\nOtevřít jej nyní?",
    },
    "ENG": {
        "title": "Application updates",
        "channel": "HTTPS release manifest URL",
        "channel_help": "Official GitHub Releases channel. The manifest must contain version, installer_url and sha256.",
        "automatic": "Check automatically at startup (opt-in only)",
        "check": "Check",
        "download": "Download verified installer…",
        "close": "Close",
        "missing": "Enter the HTTPS URL of the official manifest first.",
        "current": "You are using the current version {version}.",
        "available": "Version {version} is available.",
        "failed": "Update check failed: {error}",
        "confirm_title": "Download update?",
        "confirm": "Download installer version {version} and verify its SHA-256? Nothing will run automatically.",
        "downloaded": "The verified installer was saved to:\n{path}\n\nOpen it now?",
    },
}


class UpdateDialog(QDialog):
    def __init__(self, settings: QSettings, language: str = "CZE", parent=None):
        super().__init__(parent)
        self.settings = settings
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.update_check: UpdateCheck | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(650, 300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.text["channel"]))
        self.channel_url = QLineEdit(
            str(settings.value("release_manifest_url", DEFAULT_RELEASE_MANIFEST_URL))
        )
        layout.addWidget(self.channel_url)
        help_label = QLabel(self.text["channel_help"])
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.automatic = QCheckBox(self.text["automatic"])
        self.automatic.setChecked(bool(int(settings.value("automatic_update_checks", 0))))
        layout.addWidget(self.automatic)
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
        self.settings.setValue("release_manifest_url", self.channel_url.text().strip())
        self.settings.setValue("automatic_update_checks", int(self.automatic.isChecked()))
        self.settings.sync()

    def check_now(self) -> None:
        self.save_settings()
        url = self.channel_url.text().strip()
        if not url:
            self.status.setText(self.text["missing"])
            return
        try:
            self.update_check = check_for_update(url, __version__)
        except Exception as exc:
            self.update_check = None
            self.download_button.setEnabled(False)
            self.status.setText(self.text["failed"].format(error=exc))
            return
        self.download_button.setEnabled(self.update_check.update_available)
        key = "available" if self.update_check.update_available else "current"
        self.status.setText(self.text[key].format(version=self.update_check.manifest.version if self.update_check.update_available else __version__))

    def download_update(self) -> None:
        if self.update_check is None or not self.update_check.update_available:
            return
        manifest = self.update_check.manifest
        answer = QMessageBox.question(
            self, self.text["confirm_title"], self.text["confirm"].format(version=manifest.version),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        try:
            path = download_verified_installer(manifest, downloads)
        except Exception as exc:
            self.status.setText(self.text["failed"].format(error=exc))
            return
        open_answer = QMessageBox.question(
            self, self.text["confirm_title"], self.text["downloaded"].format(path=path),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if open_answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def accept(self) -> None:
        self.save_settings()
        super().accept()
