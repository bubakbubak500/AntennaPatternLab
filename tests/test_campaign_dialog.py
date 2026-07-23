import os
from dataclasses import replace
from datetime import timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaign_dialog import CampaignDialog
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.storage import SpotRepository


def test_campaign_dialog_starts_tracks_and_finishes_campaign(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "campaign-dialog.sqlite3")
    dialog = CampaignDialog(
        repository,
        "ENG",
        "OK7PS",
        "JN79",
        "20m",
        "FT8",
        None,
    )
    dialog.name.setText("20m baseline")
    dialog.objective.setText("Measure initial antenna")
    dialog.notes.setPlainText("Dry ground")
    assert "missing" in dialog.readiness.text()
    dialog.target_spots.setValue(5)
    dialog.target_receivers.setValue(2)
    dialog.target_sectors.setValue(1)
    dialog.target_blocks.setValue(1)
    dialog.start_campaign()
    active = repository.active_campaign()
    assert active is not None
    assert active.name == "20m baseline"
    assert not dialog.start_button.isEnabled()
    assert dialog.stop_button.isEnabled()
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 9).text() == "0/4 conditions"

    spots = [
        replace(spot, observed_at=active.started_at + timedelta(seconds=index + 1))
        for index, spot in enumerate(generate_demo_spots(count=5))
    ]
    repository.add_many(spots)
    dialog.refresh()
    assert dialog.table.item(0, 6).text() == "5"
    assert "conditions" in dialog.table.item(0, 9).text()
    dialog.table.selectRow(0)
    application.processEvents()
    assert dialog.coverage_button.isEnabled()
    assert dialog.diary_button.isEnabled()
    assert dialog.attachments_button.isEnabled()
    dialog.open_selected_coverage()
    assert dialog.coverage_campaign_id == active.id
    dialog.stop_campaign()
    assert repository.active_campaign() is None
    assert dialog.start_button.isEnabled()
    dialog.name.setText("20m follow-up")
    dialog.start_campaign()
    assert dialog.table.rowCount() == 2
    selection = dialog.table.selectionModel()
    selection.clearSelection()
    flags = (
        QItemSelectionModel.SelectionFlag.Select
        | QItemSelectionModel.SelectionFlag.Rows
    )
    selection.select(dialog.table.model().index(0, 0), flags)
    selection.select(dialog.table.model().index(1, 0), flags)
    application.processEvents()
    assert dialog.compare_button.isEnabled()
    assert not dialog.coverage_button.isEnabled()
    dialog.close()
    application.processEvents()
