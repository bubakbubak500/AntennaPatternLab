import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.update_dialog import UpdateDialog
def test_update_dialog_uses_fixed_channel_and_migrates_old_settings(tmp_path):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "updates.ini"), QSettings.Format.IniFormat)
    settings.setValue("release_manifest_url", "https://releases.example/manifest.json")
    settings.setValue("automatic_update_checks", 0)
    dialog = UpdateDialog(settings, "ENG")
    assert not hasattr(dialog, "channel_url")
    assert not hasattr(dialog, "automatic")
    dialog.accept()
    assert not settings.contains("release_manifest_url")
    assert not settings.contains("automatic_update_checks")
    application.processEvents()
