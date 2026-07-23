import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaign_attachments_dialog import (
    CampaignAttachmentsDialog,
)
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.storage import SpotRepository


def _repository_with_campaign(tmp_path):
    repository = SpotRepository(tmp_path / "attachments.sqlite3")
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Attachment test",
            objective="Preserve evidence",
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
    return repository, campaign


def test_campaign_attachment_is_copied_deduplicated_and_verified(tmp_path):
    repository, campaign = _repository_with_campaign(tmp_path)
    source = tmp_path / "analyzer.csv"
    source.write_bytes(b"frequency,swr\n14074000,1.2\n")

    attachment = repository.import_campaign_attachment(
        campaign.id, source, "NanoVNA before test"
    )
    stored = repository.campaign_attachment_path(attachment)
    assert stored != source
    assert stored.read_bytes() == source.read_bytes()
    assert repository.verify_campaign_attachment(attachment) == "ok"
    assert attachment.notes == "NanoVNA before test"

    duplicate = repository.import_campaign_attachment(campaign.id, source)
    assert duplicate.id == attachment.id
    assert len(repository.list_campaign_attachments(campaign.id)) == 1

    stored.write_bytes(b"changed")
    assert repository.verify_campaign_attachment(attachment) == "size_mismatch"
    repository.import_campaign_attachment(campaign.id, source)
    assert repository.verify_campaign_attachment(attachment) == "ok"


def test_campaign_attachment_dialog_lists_integrity_state(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository, campaign = _repository_with_campaign(tmp_path)
    source = tmp_path / "photo.jpg"
    source.write_bytes(b"fake-jpeg")
    repository.import_campaign_attachment(campaign.id, source, "Feed point")

    dialog = CampaignAttachmentsDialog(repository, campaign.id, "ENG")
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 1).text() == "photo.jpg"
    assert dialog.table.item(0, 6).text() == "verified"
    dialog.table.selectRow(0)
    application.processEvents()
    assert dialog.open_button.isEnabled()
    dialog.close()
    application.processEvents()
