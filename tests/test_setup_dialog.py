import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QMessageBox

from antenna_pattern_lab.dependencies import DependencyStatus
from antenna_pattern_lab.setup_dialog import SetupDialog


def test_setup_dialog_saves_ports_and_never_opens_url_without_consent(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "setup.ini"), QSettings.Format.IniFormat)
    statuses = (
        DependencyStatus("hamlib", "Hamlib rigctld", False, None, "https://example.test/hamlib"),
        DependencyStatus("wsjtx", "WSJT-X", False, None, "https://example.test/wsjtx"),
    )
    monkeypatch.setattr("antenna_pattern_lab.setup_dialog.detect_external_tools", lambda: statuses)
    opened = []
    monkeypatch.setattr("antenna_pattern_lab.setup_dialog.QDesktopServices.openUrl", opened.append)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_args, **_kwargs: QMessageBox.StandardButton.No
    )
    dialog = SetupDialog(settings, "ENG")
    assert dialog.height() <= 430
    text_color = dialog.palette().color(QPalette.ColorRole.WindowText)
    background = dialog.palette().color(QPalette.ColorRole.Window)
    assert text_color.lightness() < background.lightness()
    assert dialog.install_buttons["hamlib"].isEnabled()
    assert dialog.install_buttons["wsjtx"].text() == "Download and install…"
    dialog.open_official_source("wsjtx")
    assert opened == []
    dialog.serial_port.setText("COM7")
    dialog.rig_model.setValue(3073)
    assert "COM7" in dialog.command_preview.text()
    dialog.wsjtx_port.setValue(2240)
    dialog.save_and_finish()
    assert int(settings.value("onboarding_completed")) == 1
    assert int(settings.value("wsjtx_port")) == 2240
    dialog.close()
    application.processEvents()


def test_setup_dialog_rechecks_a_launched_installer_until_tool_is_found(
    tmp_path, monkeypatch
):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "setup.ini"), QSettings.Format.IniFormat)
    executable = tmp_path / "rigctld.exe"
    missing = (
        DependencyStatus("hamlib", "Hamlib rigctld", False, None, "https://example.test"),
        DependencyStatus("wsjtx", "WSJT-X", False, None, "https://example.test"),
    )
    found = (
        DependencyStatus("hamlib", "Hamlib rigctld", True, executable, "https://example.test"),
        missing[1],
    )
    detections = iter((missing, found))
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.detect_external_tools",
        lambda: next(detections),
    )
    dialog = SetupDialog(settings, "ENG")
    dialog._pending_install_key = "hamlib"
    dialog._detection_attempts = 0
    dialog._detection_timer.start()
    dialog._poll_detection()
    assert dialog._pending_install_key is None
    assert not dialog._detection_timer.isActive()
    assert dialog.status_labels["hamlib"].text() == "Installed"
    assert dialog.status_labels["hamlib"].toolTip() == str(executable)
    dialog.close()
    application.processEvents()
