import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaign_log_dialog import CampaignLogDialog
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.storage import SpotRepository


def test_campaign_log_dialog_adds_structured_entry(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "campaign-log-dialog.sqlite3")
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Baseline",
            objective="Measure antenna",
            tx_call="OK7PS",
            tx_grid="JN79",
            band="20m",
            mode="FT8",
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="Dry",
            started_at=datetime.now(timezone.utc),
        )
    )
    dialog = CampaignLogDialog(repository, campaign.id, "ENG")
    dialog.category.setCurrentIndex(dialog.category.findData("environment"))
    dialog.entry_text.setPlainText("Rain started.")
    dialog.add_entry()
    entries = repository.list_campaign_log_entries(campaign.id)
    assert len(entries) == 1
    assert entries[0].category == "environment"
    assert entries[0].text == "Rain started."
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 1).text() == "Environment"
    dialog.close()
    application.processEvents()
