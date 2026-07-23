import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.analysis import LocatedSpot
from antenna_pattern_lab.campaign_comparison_dialog import (
    CampaignComparisonDialog,
)
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots


def test_campaign_comparison_dialog_renders_metrics_and_slots():
    application = QApplication.instance() or QApplication([])
    start = datetime(2026, 7, 20, 10, tzinfo=timezone.utc)
    campaign_a = MeasurementCampaign(
        id=1,
        name="Before",
        objective="A",
        tx_call="OK7PS",
        tx_grid="JN79",
        band="20m",
        mode="FT8",
        antenna_profile_id=None,
        antenna_profile_name="",
        notes="",
        started_at=start,
    )
    campaign_b = replace(
        campaign_a,
        id=2,
        name="After",
        objective="B",
        started_at=start + timedelta(days=1),
    )
    base = generate_demo_spots(count=1)[0]
    located_a, located_b = [], []
    for index, hour in enumerate((5, 11, 17)):
        spot_a = replace(
            base,
            observed_at=start.replace(hour=hour),
            rx_call=f"RX{index}",
            sequence=index,
        )
        spot_b = replace(
            spot_a,
            observed_at=spot_a.observed_at + timedelta(days=1),
            sequence=100 + index,
        )
        located_a.append(LocatedSpot(spot_a, 1500.0, 15.0))
        located_b.append(LocatedSpot(spot_b, 1500.0, 15.0))
    dialog = CampaignComparisonDialog(
        campaign_a,
        located_a,
        campaign_b,
        located_b,
        "ENG",
    )
    assert dialog.result.quality == "good"
    assert dialog.table.rowCount() == 48
    assert len(dialog.figure.axes) == 1
    assert "well comparable" in dialog.quality.text()
    dialog.close()
    application.processEvents()
