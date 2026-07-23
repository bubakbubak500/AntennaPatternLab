from __future__ import annotations

from pathlib import Path
import threading

from PySide6.QtCore import QObject, QSettings, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from .dependencies import DependencyStatus, detect_external_tools, rigctld_command
from .external_install import (
    download_release_asset,
    fetch_release_asset,
    launch_installer,
)


TEXT = {
    "CZE": {
        "title": "První spuštění a externí nástroje",
        "intro": "Ověří nainstalované nástroje. Chybějící může po potvrzení stáhnout a spustit z oficiálního zdroje.",
        "found": "Nalezeno: {path}",
        "missing": "Nenalezeno",
        "official": "Otevřít oficiální zdroj…",
        "install": "Stáhnout a instalovat…",
        "installed": "Nainstalováno",
        "checking_install": "Instalátor spuštěn — čekám na dokončení a průběžně ověřuji…",
        "resolve_failed": "Instalátor nelze bezpečně určit",
        "download_confirm_title": "Stáhnout oficiální instalátor?",
        "download_confirm": "Stáhnout {name} {version} ({size:.1f} MB) z oficiálního GitHub release?\n\nSoubor bude přijat pouze při shodě publikovaného SHA-256.",
        "downloading": "Stahuji {name}…",
        "run_confirm_title": "Spustit ověřený instalátor?",
        "run_confirm": "Soubor byl stažen a jeho SHA-256 souhlasí.\n\nSpustit nyní {filename}? Další kroky řídí instalační program dodavatele.",
        "download_failed": "Stažení nebo ověření selhalo",
        "launch_failed": "Instalátor nelze spustit",
        "confirm_title": "Otevřít externí web?",
        "confirm": "Otevřít v prohlížeči výhradně oficiální stránku projektu {name}? Instalaci budete řídit sami.",
        "recheck": "Znovu ověřit",
        "hamlib_setup": "Volitelná konfigurace rigctld",
        "model": "Hamlib model ID",
        "serial": "COM port",
        "baud": "Rychlost",
        "hamlib_port": "TCP port rigctld",
        "command": "Příkaz rigctld (náhled)",
        "wsjtx_setup": "WSJT-X UDP Reporting",
        "wsjtx_port": "UDP port",
        "wsjtx_note": "Ve WSJT-X nastavte UDP Server 127.0.0.1 a stejný port. Spojení potvrdí až první Heartbeat.",
        "finish": "Uložit a dokončit",
        "later": "Později",
    },
    "ENG": {
        "title": "First run and external tools",
        "intro": "Checks installed tools. Missing tools can be downloaded and launched from their official source after confirmation.",
        "found": "Found: {path}",
        "missing": "Not found",
        "official": "Open official source…",
        "install": "Download and install…",
        "installed": "Installed",
        "checking_install": "Installer launched — waiting for completion and checking automatically…",
        "resolve_failed": "Cannot safely resolve installer",
        "download_confirm_title": "Download official installer?",
        "download_confirm": "Download {name} {version} ({size:.1f} MB) from the official GitHub release?\n\nThe file is accepted only if its published SHA-256 matches.",
        "downloading": "Downloading {name}…",
        "run_confirm_title": "Launch verified installer?",
        "run_confirm": "The file was downloaded and its SHA-256 matches.\n\nLaunch {filename} now? The vendor installer controls all remaining steps.",
        "download_failed": "Download or verification failed",
        "launch_failed": "Cannot launch installer",
        "confirm_title": "Open an external website?",
        "confirm": "Open only the official {name} project page in your browser? You will control the installation yourself.",
        "recheck": "Check again",
        "hamlib_setup": "Optional rigctld configuration",
        "model": "Hamlib model ID",
        "serial": "COM port",
        "baud": "Baud rate",
        "hamlib_port": "rigctld TCP port",
        "command": "rigctld command preview",
        "wsjtx_setup": "WSJT-X UDP Reporting",
        "wsjtx_port": "UDP port",
        "wsjtx_note": "Set UDP Server in WSJT-X to 127.0.0.1 and the same port. The first Heartbeat confirms the connection.",
        "finish": "Save and finish",
        "later": "Later",
    },
}


class InstallBridge(QObject):
    progress = Signal(int, int)
    completed = Signal(str)
    failed = Signal(str)


class SetupDialog(QDialog):
    def __init__(self, settings: QSettings, language: str = "CZE", parent=None):
        super().__init__(parent)
        self.settings = settings
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.statuses: dict[str, DependencyStatus] = {}
        self.status_labels: dict[str, QLabel] = {}
        self.install_buttons: dict[str, QPushButton] = {}
        self._download_key: str | None = None
        self._pending_install_key: str | None = None
        self._detection_attempts = 0
        self._detection_timer = QTimer(self)
        self._detection_timer.setInterval(2000)
        self._detection_timer.timeout.connect(self._poll_detection)
        self._install_bridge = InstallBridge(self)
        self._install_bridge.progress.connect(self._download_progress)
        self._install_bridge.completed.connect(self._download_completed)
        self._install_bridge.failed.connect(self._download_failed)
        self._progress_dialog: QProgressDialog | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(760, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(7)
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #9a6700;")
        layout.addWidget(intro)
        for key in ("hamlib", "wsjtx"):
            row = QHBoxLayout()
            name = QLabel("Hamlib rigctld" if key == "hamlib" else "WSJT-X")
            name.setMinimumWidth(105)
            status = QLabel()
            status.setWordWrap(True)
            install_button = QPushButton(self.text["install"])
            install_button.clicked.connect(
                lambda _checked=False, item=key: self.download_and_install(item)
            )
            official_button = QPushButton(self.text["official"])
            official_button.clicked.connect(
                lambda _checked=False, item=key: self.open_official_source(item)
            )
            self.status_labels[key] = status
            self.install_buttons[key] = install_button
            row.addWidget(name)
            row.addWidget(status, 1)
            row.addWidget(install_button)
            row.addWidget(official_button)
            layout.addLayout(row)
        recheck = QPushButton(self.text["recheck"])
        recheck.clicked.connect(self.refresh_detection)
        layout.addWidget(recheck)

        hamlib_title = QLabel(self.text["hamlib_setup"])
        hamlib_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(hamlib_title)
        hamlib_form = QFormLayout()
        self.rig_model = QSpinBox()
        self.rig_model.setRange(1, 99999)
        self.rig_model.setValue(int(settings.value("rig_model_id", 1)))
        self.serial_port = QLineEdit(str(settings.value("rig_serial_port", "COM3")))
        self.baud_rate = QComboBox()
        for rate in (4800, 9600, 19200, 38400, 57600, 115200):
            self.baud_rate.addItem(str(rate), rate)
        self.baud_rate.setCurrentIndex(max(0, self.baud_rate.findData(int(settings.value("rig_baud", 9600)))))
        self.hamlib_port = QSpinBox()
        self.hamlib_port.setRange(1, 65535)
        self.hamlib_port.setValue(int(settings.value("hamlib_port", 4532)))
        self.command_preview = QLineEdit()
        self.command_preview.setReadOnly(True)
        hamlib_form.addRow(self.text["model"], self.rig_model)
        hamlib_form.addRow(self.text["serial"], self.serial_port)
        hamlib_form.addRow(self.text["baud"], self.baud_rate)
        hamlib_form.addRow(self.text["hamlib_port"], self.hamlib_port)
        hamlib_form.addRow(self.text["command"], self.command_preview)
        layout.addLayout(hamlib_form)

        wsjtx_title = QLabel(self.text["wsjtx_setup"])
        wsjtx_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(wsjtx_title)
        wsjtx_form = QFormLayout()
        self.wsjtx_port = QSpinBox()
        self.wsjtx_port.setRange(1, 65535)
        self.wsjtx_port.setValue(int(settings.value("wsjtx_port", 2237)))
        wsjtx_form.addRow(self.text["wsjtx_port"], self.wsjtx_port)
        layout.addLayout(wsjtx_form)
        note = QLabel(self.text["wsjtx_note"])
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        later = QPushButton(self.text["later"])
        finish = QPushButton(self.text["finish"])
        later.clicked.connect(self.reject)
        finish.clicked.connect(self.save_and_finish)
        buttons.addStretch()
        buttons.addWidget(later)
        buttons.addWidget(finish)
        layout.addLayout(buttons)
        for control in (self.rig_model, self.serial_port, self.baud_rate, self.hamlib_port):
            if isinstance(control, QLineEdit):
                control.textChanged.connect(self.update_command_preview)
            elif isinstance(control, QComboBox):
                control.currentIndexChanged.connect(self.update_command_preview)
            else:
                control.valueChanged.connect(self.update_command_preview)
        self.refresh_detection()

    def refresh_detection(self) -> None:
        self.statuses = {status.key: status for status in detect_external_tools()}
        for key, status in self.statuses.items():
            label = self.status_labels[key]
            if status.found:
                label.setText(self.text["installed"])
                label.setToolTip(str(status.executable))
                label.setStyleSheet("color: #1a7f37;")
                self.install_buttons[key].setText(self.text["installed"])
                self.install_buttons[key].setEnabled(False)
            elif key == self._pending_install_key:
                label.setText(self.text["checking_install"])
                label.setToolTip("")
                label.setStyleSheet("color: #0969da;")
                self.install_buttons[key].setText(self.text["install"])
                self.install_buttons[key].setEnabled(False)
            else:
                label.setText(self.text["missing"])
                label.setToolTip("")
                label.setStyleSheet("color: #b42318;")
                self.install_buttons[key].setText(self.text["install"])
                self.install_buttons[key].setEnabled(True)
        self.update_command_preview()
        if (
            self._pending_install_key
            and self.statuses.get(self._pending_install_key)
            and self.statuses[self._pending_install_key].found
        ):
            self._detection_timer.stop()
            self._pending_install_key = None
            self._detection_attempts = 0

    def _poll_detection(self) -> None:
        self._detection_attempts += 1
        self.refresh_detection()
        if self._pending_install_key is None:
            return
        if self._detection_attempts >= 150:
            self._detection_timer.stop()
            key = self._pending_install_key
            self._pending_install_key = None
            self._detection_attempts = 0
            status = self.statuses.get(key)
            if status and not status.found:
                self.status_labels[key].setText(self.text["missing"])
                self.status_labels[key].setStyleSheet("color: #b42318;")
                self.install_buttons[key].setEnabled(True)

    def update_command_preview(self) -> None:
        hamlib = self.statuses.get("hamlib")
        executable = hamlib.executable if hamlib and hamlib.executable else "rigctld.exe"
        try:
            command = rigctld_command(
                executable,
                self.rig_model.value(),
                self.serial_port.text(),
                int(self.baud_rate.currentData()),
                self.hamlib_port.value(),
            )
            self.command_preview.setText(" ".join(f'"{item}"' if " " in item else item for item in command))
        except ValueError:
            self.command_preview.clear()

    def open_official_source(self, key: str) -> None:
        status = self.statuses[key]
        answer = QMessageBox.question(
            self,
            self.text["confirm_title"],
            self.text["confirm"].format(name=status.display_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl(status.official_url))

    def download_and_install(self, key: str) -> None:
        status = self.statuses[key]
        self._download_key = key
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            asset = fetch_release_asset(key)
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.text["resolve_failed"],
                str(exc),
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        answer = QMessageBox.question(
            self,
            self.text["download_confirm_title"],
            self.text["download_confirm"].format(
                name=status.display_name,
                version=asset.version,
                size=asset.size / (1024 * 1024),
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        for button in self.install_buttons.values():
            button.setEnabled(False)
        self._progress_dialog = QProgressDialog(
            self.text["downloading"].format(name=status.display_name),
            "",
            0,
            1000,
            self,
        )
        self._progress_dialog.setCancelButton(None)
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setValue(0)
        self._progress_dialog.show()
        downloads = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DownloadLocation
        )
        destination = (
            Path(downloads) if downloads else Path.home() / "Downloads"
        ) / "Antenna Pattern Lab"
        bridge = self._install_bridge

        def worker() -> None:
            try:
                path = download_release_asset(
                    asset,
                    destination,
                    progress=lambda received, total: bridge.progress.emit(
                        received, total
                    ),
                )
            except Exception as exc:
                bridge.failed.emit(str(exc))
            else:
                bridge.completed.emit(str(path))

        threading.Thread(
            target=worker,
            daemon=True,
            name=f"{key}-installer-download",
        ).start()

    def _download_progress(self, received: int, total: int) -> None:
        if self._progress_dialog is not None and total > 0:
            self._progress_dialog.setValue(min(1000, int(received * 1000 / total)))

    def _finish_download_ui(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()
            self._progress_dialog = None
        for key, button in self.install_buttons.items():
            button.setEnabled(not self.statuses[key].found)

    def _download_failed(self, detail: str) -> None:
        self._download_key = None
        self._finish_download_ui()
        QMessageBox.warning(self, self.text["download_failed"], detail)

    def _download_completed(self, filename: str) -> None:
        self._finish_download_ui()
        path = Path(filename)
        answer = QMessageBox.question(
            self,
            self.text["run_confirm_title"],
            self.text["run_confirm"].format(filename=path.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            launch_installer(path)
        except Exception as exc:
            QMessageBox.warning(self, self.text["launch_failed"], str(exc))
            self._download_key = None
            return
        if self._download_key:
            self._pending_install_key = self._download_key
            self._detection_attempts = 0
            self.status_labels[self._download_key].setText(
                self.text["checking_install"]
            )
            self.status_labels[self._download_key].setStyleSheet("color: #0969da;")
            self.install_buttons[self._download_key].setEnabled(False)
            self._detection_timer.start()
        self._download_key = None

    def save_and_finish(self) -> None:
        self.settings.setValue("rig_model_id", self.rig_model.value())
        self.settings.setValue("rig_serial_port", self.serial_port.text().strip())
        self.settings.setValue("rig_baud", int(self.baud_rate.currentData()))
        self.settings.setValue("hamlib_port", self.hamlib_port.value())
        self.settings.setValue("wsjtx_port", self.wsjtx_port.value())
        self.settings.setValue("onboarding_completed", 1)
        self.settings.sync()
        self.accept()
