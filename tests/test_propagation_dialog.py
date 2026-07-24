import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.propagation import PropagationBundle, parse_noaa_payloads
from antenna_pattern_lab.propagation_dialog import PropagationConditionsDialog
from antenna_pattern_lab.storage import SpotRepository


class _CachedClient:
    def __init__(self, bundle):
        self.bundle = bundle

    def load_cached(self):
        return self.bundle


def test_dialog_loads_cache_translates_and_saves_campaign_snapshot(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "dialog.sqlite3")
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Live 20m",
            objective="Baseline",
            tx_call="OK7PS",
            tx_grid="JN79",
            band="20m",
            mode="FT8",
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="Stable power",
            started_at=datetime(2026, 7, 24, 8, 0, tzinfo=timezone.utc),
        )
    )
    snapshot = parse_noaa_payloads(
        {
            "kp": [{"time_tag": "2026-07-24T09:00:00Z", "Kp": 2.0}],
            "f107": [{"time_tag": "2026-07-24T08:00:00Z", "flux": 150}],
        },
        fetched_at=datetime.now(timezone.utc),
    )
    dialog = PropagationConditionsDialog(
        repository,
        "ENG",
        client=_CachedClient(PropagationBundle(snapshot, {})),
    )
    dialog.show()
    application.processEvents()

    assert dialog.windowTitle() == "Propagation conditions"
    assert dialog.metrics["kp"].value.text() == "2.0"
    assert dialog.metrics["f107"].value.text() == "150 sfu"
    assert dialog.campaign.currentData() == campaign.id
    assert dialog.save_button.isEnabled()

    dialog.save_snapshot()
    assert len(repository.list_propagation_snapshots(campaign.id)) == 1
    assert "saved" in dialog.status.text()
    assert dialog.timeline_table.rowCount() == 1
    assert dialog.tabs.count() == 7
    assert dialog.trend_canvas.accessibleName() == "24 h trends"
    dialog.close()
    application.processEvents()
