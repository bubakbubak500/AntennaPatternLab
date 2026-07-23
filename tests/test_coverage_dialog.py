import os
from datetime import datetime, timezone

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.analysis import locate_spot
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.coverage_dialog import CoverageDialog
from antenna_pattern_lab.demo import generate_demo_spots


def test_coverage_dialog_renders_sector_table_and_priorities():
    application = QApplication.instance() or QApplication([])
    located = [
        item
        for spot in generate_demo_spots(count=100)
        if (item := locate_spot(spot))
    ]
    dialog = CoverageDialog(located, "ENG", "OK7PS · 20m")
    assert len(dialog.sectors) == 12
    assert dialog.table.rowCount() == 12
    assert "Prioritize" in dialog.priority.text()
    assert dialog.figure.axes[0].name == "polar"
    assert len(dialog.matrix_cells) == 96
    assert dialog.matrix_table.rowCount() == 8
    assert dialog.matrix_table.columnCount() == 13
    assert len(dialog.matrix_figure.axes) == 3  # day, night, shared colorbar
    assert "Weakest combinations" in dialog.matrix_priority.text()
    dialog.close()
    application.processEvents()


def test_campaign_coverage_adds_measurement_window_planner():
    application = QApplication.instance() or QApplication([])
    located = [
        item
        for spot in generate_demo_spots(count=80)
        if (item := locate_spot(spot))
    ]
    campaign = MeasurementCampaign(
        id=1,
        name="20m campaign",
        objective="Improve evidence",
        tx_call="OK7PS",
        tx_grid="JN79",
        band="20m",
        mode="FT8",
        antenna_profile_id=1,
        antenna_profile_name="Vertical",
        notes="Stable setup",
        started_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )

    dialog = CoverageDialog(
        located,
        "ENG",
        "20m campaign",
        campaign=campaign,
    )

    assert dialog.tabs.count() == 3
    assert dialog.planner_recommendation is not None
    assert dialog.planner_table.rowCount() == 48
    assert len(dialog.planner_figure.axes) == 1
    dialog.close()
    application.processEvents()
