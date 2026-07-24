import os
from dataclasses import replace
from datetime import timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots
from antenna_pattern_lab.propagation import parse_noaa_payloads
from antenna_pattern_lab.propagation_intelligence_dialog import (
    PropagationIntelligenceDialog,
)
from antenna_pattern_lab.storage import SpotRepository


def test_dialog_exposes_route_layers_playback_and_saved_provenance(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "dialog.sqlite3")
    spots = generate_demo_spots(count=12, seed=4)
    first = min(spot.observed_at for spot in spots)
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="PI campaign",
            objective="Route analysis",
            tx_call=spots[0].tx_call,
            tx_grid=spots[0].tx_grid,
            band=spots[0].band,
            mode=spots[0].mode,
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="Stable",
            started_at=first - timedelta(minutes=1),
        )
    )
    repository.add_many(spots)
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": spots[0].observed_at.isoformat(), "Kp": 2.0}],
        },
        fetched_at=spots[0].observed_at,
    )
    repository.save_propagation_snapshot(campaign.id, snapshot)

    dialog = PropagationIntelligenceDialog(repository, "ENG")
    dialog.show()
    application.processEvents()

    assert dialog.windowTitle() == "Propagation Intelligence"
    assert dialog.tabs.count() == 3
    assert dialog.target.count() > 0
    assert dialog.features is not None
    assert dialog.features.campaign_id == campaign.id
    assert dialog.layer_table.rowCount() == 36
    assert dialog.route_canvas.accessibleName()
    assert dialog.layer_canvas.accessibleName()
    assert "input_sha256" in dialog.provenance_text.toPlainText()
    assert dialog.play_button.isEnabled()

    dialog._save_features()
    assert len(repository.list_propagation_features(campaign.id)) == 1
    assert "saved" in dialog.status.text().lower()
    dialog.close()
    application.processEvents()
