from __future__ import annotations

from pathlib import Path
import threading

from PySide6.QtCore import QObject, QSettings, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
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

from .dependencies import (
    DependencyStatus,
    detect_external_tools,
    launch_rigctld,
    list_hamlib_rig_models,
    rigctld_command,
    tcp_port_is_open,
)
from .external_install import (
    download_release_asset,
    fetch_release_asset,
    launch_installer,
)
from .theme import semantic_style


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
        "model": "Model rádia",
        "serial": "COM port",
        "baud": "Rychlost",
        "hamlib_port": "TCP port rigctld",
        "start_rigctld": "Spustit rigctld",
        "rigctld_ready": "Připraveno ke spuštění",
        "rigctld_missing": "Nejdříve nainstalujte Hamlib",
        "rigctld_starting": "Spouštím…",
        "rigctld_started": "Běží na portu {port} (PID {pid})",
        "rigctld_already_running": "Port {port} už používá běžící služba",
        "rigctld_failed": "rigctld se nepodařilo spustit",
        "models_failed": "Názvy modelů nelze z Hamlibu načíst: {detail}",
        "saved_model": "{model_id} — uložené ID",
        "model_help": "Začněte psát ID, výrobce nebo název rádia.",
        "select_model": "Vyberte rádio ze seznamu modelů podporovaných Hamlibem.",
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
        "model": "Radio model",
        "serial": "COM port",
        "baud": "Baud rate",
        "hamlib_port": "rigctld TCP port",
        "start_rigctld": "Start rigctld",
        "rigctld_ready": "Ready to start",
        "rigctld_missing": "Install Hamlib first",
        "rigctld_starting": "Starting…",
        "rigctld_started": "Running on port {port} (PID {pid})",
        "rigctld_already_running": "Port {port} is already used by a running service",
        "rigctld_failed": "Could not start rigctld",
        "models_failed": "Could not load model names from Hamlib: {detail}",
        "saved_model": "{model_id} — saved ID",
        "model_help": "Type a model ID, manufacturer, or radio name to search.",
        "select_model": "Select a radio from the list of models supported by Hamlib.",
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
        self._loaded_models_for: Path | None = None
        self._rigctld_launch_attempts = 0
        self._rigctld_pid: int | None = None
        self.setWindowTitle(self.text["title"])
        self.resize(760, 410)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet(semantic_style("warning"))
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
        hamlib_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        hamlib_form.setHorizontalSpacing(12)
        hamlib_form.setVerticalSpacing(8)
        self.rig_model = QComboBox()
        self.rig_model.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.rig_model.setMinimumContentsLength(34)
        self.rig_model.setEditable(True)
        self.rig_model.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.rig_model.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion
        )
        self.rig_model.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.rig_model.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )
        self.rig_model.setAccessibleName(self.text["model"])
        self.rig_model.setAccessibleDescription(self.text["model_help"])
        self.rig_model.setToolTip(self.text["model_help"])
        self._set_saved_rig_model(int(settings.value("rig_model_id", 1)))
        self.serial_port = QLineEdit(str(settings.value("rig_serial_port", "COM3")))
        self.baud_rate = QComboBox()
        for rate in (4800, 9600, 19200, 38400, 57600, 115200):
            self.baud_rate.addItem(str(rate), rate)
        self.baud_rate.setCurrentIndex(max(0, self.baud_rate.findData(int(settings.value("rig_baud", 9600)))))
        self.hamlib_port = QSpinBox()
        self.hamlib_port.setRange(1, 65535)
        self.hamlib_port.setValue(int(settings.value("hamlib_port", 4532)))
        rigctld_actions = QHBoxLayout()
        self.start_rigctld_button = QPushButton(self.text["start_rigctld"])
        self.start_rigctld_button.setAccessibleName(self.text["start_rigctld"])
        self.start_rigctld_button.clicked.connect(self.start_rigctld)
        self.rigctld_status = QLabel(self.text["rigctld_missing"])
        self.rigctld_status.setWordWrap(True)
        rigctld_actions.addWidget(self.start_rigctld_button)
        rigctld_actions.addWidget(self.rigctld_status, 1)
        hamlib_form.addRow(self.text["model"], self.rig_model)
        hamlib_form.addRow(self.text["serial"], self.serial_port)
        hamlib_form.addRow(self.text["baud"], self.baud_rate)
        hamlib_form.addRow(self.text["hamlib_port"], self.hamlib_port)
        hamlib_form.addRow("", rigctld_actions)
        layout.addLayout(hamlib_form)

        wsjtx_title = QLabel(self.text["wsjtx_setup"])
        wsjtx_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(wsjtx_title)
        wsjtx_form = QFormLayout()
        wsjtx_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        wsjtx_form.setHorizontalSpacing(12)
        wsjtx_form.setVerticalSpacing(8)
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
        finish.setObjectName("primaryAction")
        finish.setDefault(True)
        finish.setAccessibleName(self.text["finish"])
        later.clicked.connect(self.reject)
        finish.clicked.connect(self.save_and_finish)
        buttons.addStretch()
        buttons.addWidget(later)
        buttons.addWidget(finish)
        layout.addLayout(buttons)
        self.refresh_detection()

    def _set_saved_rig_model(self, model_id: int) -> None:
        self.rig_model.clear()
        self.rig_model.addItem(self.text["saved_model"].format(model_id=model_id), model_id)

    def _load_rig_models(self, executable: Path) -> None:
        if self._loaded_models_for == executable:
            return
        saved_model_id = int(
            self.rig_model.currentData()
            if self.rig_model.currentData() is not None
            else self.settings.value("rig_model_id", 1)
        )
        try:
            models = list_hamlib_rig_models(executable)
        except Exception as exc:
            self._loaded_models_for = None
            self.rig_model.setToolTip(
                self.text["models_failed"].format(detail=str(exc))
            )
            return
        self.rig_model.clear()
        for model in models:
            self.rig_model.addItem(model.display_name, model.model_id)
        selected = self.rig_model.findData(saved_model_id)
        if selected < 0:
            self.rig_model.insertItem(
                0,
                self.text["saved_model"].format(model_id=saved_model_id),
                saved_model_id,
            )
            selected = 0
        self.rig_model.setCurrentIndex(selected)
        self.rig_model.setToolTip(self.text["model_help"])
        self._loaded_models_for = executable

    def refresh_detection(self) -> None:
        self.statuses = {status.key: status for status in detect_external_tools()}
        for key, status in self.statuses.items():
            label = self.status_labels[key]
            if status.found:
                label.setText(self.text["installed"])
                label.setToolTip(str(status.executable))
                label.setStyleSheet(semantic_style("success"))
                self.install_buttons[key].setText(self.text["installed"])
                self.install_buttons[key].setEnabled(False)
                if key == "hamlib" and status.executable is not None:
                    self._load_rig_models(status.executable)
                    self.start_rigctld_button.setEnabled(True)
                    if self._rigctld_pid is None:
                        self.rigctld_status.setText(self.text["rigctld_ready"])
                        self.rigctld_status.setStyleSheet(semantic_style("info"))
            elif key == self._pending_install_key:
                label.setText(self.text["checking_install"])
                label.setToolTip("")
                label.setStyleSheet(semantic_style("info"))
                self.install_buttons[key].setText(self.text["install"])
                self.install_buttons[key].setEnabled(False)
            else:
                label.setText(self.text["missing"])
                label.setToolTip("")
                label.setStyleSheet(semantic_style("danger"))
                self.install_buttons[key].setText(self.text["install"])
                self.install_buttons[key].setEnabled(True)
                if key == "hamlib":
                    self.start_rigctld_button.setEnabled(False)
                    self.rigctld_status.setText(self.text["rigctld_missing"])
                    self.rigctld_status.setStyleSheet(semantic_style("inactive"))
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
                self.status_labels[key].setStyleSheet(semantic_style("danger"))
                self.install_buttons[key].setEnabled(True)

    def _rigctld_command(self) -> tuple[str, ...]:
        hamlib = self.statuses.get("hamlib")
        if not hamlib or not hamlib.executable:
            raise ValueError(self.text["rigctld_missing"])
        return rigctld_command(
            hamlib.executable,
            self._rig_model_id(),
            self.serial_port.text(),
            int(self.baud_rate.currentData()),
            self.hamlib_port.value(),
        )

    def _rig_model_id(self) -> int:
        model_id = self.rig_model.currentData()
        if model_id is None:
            exact = self.rig_model.findText(
                self.rig_model.currentText(),
                Qt.MatchFlag.MatchFixedString,
            )
            if exact >= 0:
                model_id = self.rig_model.itemData(exact)
        if model_id is None:
            raise ValueError(self.text["select_model"])
        return int(model_id)

    def start_rigctld(self) -> None:
        port = self.hamlib_port.value()
        if tcp_port_is_open(port):
            self.rigctld_status.setText(
                self.text["rigctld_already_running"].format(port=port)
            )
            self.rigctld_status.setStyleSheet(semantic_style("success"))
            return
        try:
            command = self._rigctld_command()
            self._save_hamlib_settings()
            self._rigctld_pid = launch_rigctld(command)
        except Exception as exc:
            self.rigctld_status.setText(str(exc))
            self.rigctld_status.setStyleSheet(semantic_style("danger"))
            QMessageBox.warning(self, self.text["rigctld_failed"], str(exc))
            return
        self._rigctld_launch_attempts = 0
        self.start_rigctld_button.setEnabled(False)
        self.rigctld_status.setText(self.text["rigctld_starting"])
        self.rigctld_status.setStyleSheet(semantic_style("info"))
        QTimer.singleShot(250, self._check_rigctld_started)

    def _check_rigctld_started(self) -> None:
        self._rigctld_launch_attempts += 1
        port = self.hamlib_port.value()
        if tcp_port_is_open(port):
            self.rigctld_status.setText(
                self.text["rigctld_started"].format(
                    port=port,
                    pid=self._rigctld_pid,
                )
            )
            self.rigctld_status.setStyleSheet(semantic_style("success"))
            return
        if self._rigctld_launch_attempts < 8:
            QTimer.singleShot(250, self._check_rigctld_started)
            return
        self.start_rigctld_button.setEnabled(True)
        self.rigctld_status.setText(self.text["rigctld_failed"])
        self.rigctld_status.setStyleSheet(semantic_style("danger"))
        self._rigctld_pid = None

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
            self.status_labels[self._download_key].setStyleSheet(semantic_style("info"))
            self.install_buttons[self._download_key].setEnabled(False)
            self._detection_timer.start()
        self._download_key = None

    def _save_hamlib_settings(self) -> None:
        self.settings.setValue("rig_model_id", self._rig_model_id())
        self.settings.setValue("rig_serial_port", self.serial_port.text().strip())
        self.settings.setValue("rig_baud", int(self.baud_rate.currentData()))
        self.settings.setValue("hamlib_port", self.hamlib_port.value())

    def save_and_finish(self) -> None:
        try:
            self._save_hamlib_settings()
        except ValueError as exc:
            QMessageBox.warning(self, self.text["rigctld_failed"], str(exc))
            return
        self.settings.setValue("wsjtx_port", self.wsjtx_port.value())
        self.settings.setValue("onboarding_completed", 1)
        self.settings.sync()
        self.accept()
