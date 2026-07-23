import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.update_dialog import UpdateDialog
from antenna_pattern_lab.updates import DEFAULT_RELEASE_MANIFEST_URL


def test_update_dialog_is_opt_in_and_persists_channel(tmp_path):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "updates.ini"), QSettings.Format.IniFormat)
    dialog = UpdateDialog(settings, "ENG")
    assert not dialog.automatic.isChecked()
    assert dialog.channel_url.text() == DEFAULT_RELEASE_MANIFEST_URL
    dialog.channel_url.setText("https://releases.example/manifest.json")
    dialog.automatic.setChecked(True)
    dialog.accept()
    assert settings.value("release_manifest_url") == "https://releases.example/manifest.json"
    assert int(settings.value("automatic_update_checks")) == 1
    application.processEvents()
