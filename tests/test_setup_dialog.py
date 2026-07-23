import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QMessageBox

from antenna_pattern_lab.dependencies import DependencyStatus, HamlibRigModel
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
    dialog.rig_model.addItem("3073 — Icom IC-7300 [Stable]", 3073)
    dialog.rig_model.setCurrentIndex(dialog.rig_model.findData(3073))
    dialog.wsjtx_port.setValue(2240)
    dialog.save_and_finish()
    assert int(settings.value("onboarding_completed")) == 1
    assert int(settings.value("wsjtx_port")) == 2240
    assert int(settings.value("rig_model_id")) == 3073
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
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.list_hamlib_rig_models",
        lambda _executable: (
            HamlibRigModel(1, "Hamlib", "Dummy", "1", "Stable"),
            HamlibRigModel(3073, "Icom", "IC-7300", "1", "Stable"),
        ),
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


def test_setup_dialog_maps_model_names_and_starts_rigctld(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "setup.ini"), QSettings.Format.IniFormat)
    settings.setValue("rig_model_id", 3073)
    executable = tmp_path / "rigctld.exe"
    executable.touch()
    statuses = (
        DependencyStatus("hamlib", "Hamlib rigctld", True, executable, "https://example.test"),
        DependencyStatus("wsjtx", "WSJT-X", False, None, "https://example.test"),
    )
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.detect_external_tools", lambda: statuses
    )
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.list_hamlib_rig_models",
        lambda _executable: (
            HamlibRigModel(1, "Hamlib", "Dummy", "1", "Stable"),
            HamlibRigModel(3073, "Icom", "IC-7300", "1", "Stable"),
        ),
    )
    port_checks = iter((False, True))
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.tcp_port_is_open",
        lambda _port: next(port_checks),
    )
    launched = []
    monkeypatch.setattr(
        "antenna_pattern_lab.setup_dialog.launch_rigctld",
        lambda command: launched.append(command) or 1234,
    )

    dialog = SetupDialog(settings, "ENG")
    assert dialog.rig_model.currentData() == 3073
    assert dialog.rig_model.currentText() == "3073 — Icom IC-7300 [Stable]"
    assert not hasattr(dialog, "command_preview")
    dialog.serial_port.setText("COM7")
    dialog.start_rigctld()
    dialog._check_rigctld_started()

    assert launched == [
        (
            str(executable),
            "-m",
            "3073",
            "-r",
            "COM7",
            "-s",
            "9600",
            "-t",
            "4532",
        )
    ]
    assert dialog.rigctld_status.text() == "Running on port 4532 (PID 1234)"
    assert int(settings.value("rig_model_id")) == 3073
    dialog.close()
    application.processEvents()
