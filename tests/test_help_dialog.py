import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.help_dialog import HelpDialog


def test_structured_help_covers_all_major_workflows_in_both_languages():
    application = QApplication.instance() or QApplication([])
    for language in ("CZE", "ENG"):
        dialog = HelpDialog(language)
        assert dialog.sections.count() >= 12
        titles = [
            dialog.sections.item(index).text()
            for index in range(dialog.sections.count())
        ]
        assert len(set(titles)) == len(titles)
        for index in range(dialog.sections.count()):
            dialog.sections.setCurrentRow(index)
            application.processEvents()
            assert len(dialog.content.toPlainText()) > 40
        dialog.close()
