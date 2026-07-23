import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.design_system import MetricItem, StatusIndicator
from antenna_pattern_lab.ui_components import (
    CollectionControlWidget,
    MetricStrip,
    ReportExplorerPanel,
)
from PySide6.QtWidgets import QTableWidget


def test_metric_item_exposes_label_value_and_accessible_name():
    application = QApplication.instance() or QApplication([])
    metric = MetricItem()
    metric.set_metric("Reports", "123", "Usable reports")

    assert metric.label.text() == "Reports"
    assert metric.value.text() == "123"
    assert metric.accessibleName() == "Reports: 123"
    assert metric.toolTip() == "Usable reports"
    metric.close()
    application.processEvents()


def test_status_indicator_uses_shape_text_and_semantic_state():
    application = QApplication.instance() or QApplication([])
    indicator = StatusIndicator()
    indicator.set_indicator("WSJT-X", "waiting", "Awaiting heartbeat")

    assert indicator.text().startswith("◐ WSJT-X:")
    assert indicator.property("statusState") == "waiting"
    assert indicator.property("statusRole") == "waiting"
    assert indicator.accessibleName() == "WSJT-X: waiting"
    assert indicator.accessibleDescription() == "Awaiting heartbeat"

    indicator.set_indicator("WSJT-X", "connected", "Heartbeat received")
    assert indicator.text().startswith("● WSJT-X:")
    assert indicator.property("statusRole") == "success"
    indicator.close()
    application.processEvents()


def test_collection_control_exposes_semantic_transition_state():
    application = QApplication.instance() or QApplication([])
    control = CollectionControlWidget()
    control.set_collection_state(
        "connecting",
        "Connecting",
        "Opening PSK Reporter connection",
        "Connecting…",
    )

    assert control.state_label.property("collectionState") == "connecting"
    assert not control.button.isEnabled()
    assert control.button.accessibleDescription() == "Opening PSK Reporter connection"

    control.set_collection_state("running", "Running", "Receiving reports", "Stop")
    assert control.button.isEnabled()
    assert control.button.property("collectionState") == "running"
    control.close()
    application.processEvents()


def test_metric_strip_and_report_empty_state_are_structural():
    application = QApplication.instance() or QApplication([])
    strip = MetricStrip()
    strip.set_metrics({"reports": ("Reports", "12", "Usable reports")})
    assert strip.items["reports"].value.text() == "12"

    table = QTableWidget(0, 8)
    reports = ReportExplorerPanel(table)
    reports.set_texts("Reports", "No reports", "Start collection or load history.")
    reports.set_report_count(0)
    assert reports.stack.currentWidget() is reports.empty
    assert reports.empty.heading.text() == "No reports"
    reports.set_report_count(2)
    assert reports.stack.currentWidget() is table
    reports.resize(480, 300)
    reports.show()
    application.processEvents()
    assert table.isColumnHidden(4)
    assert table.isColumnHidden(5)
    assert table.isColumnHidden(6)
    assert table.isColumnHidden(7)
    reports.resize(700, 300)
    application.processEvents()
    assert not table.isColumnHidden(4)
    assert not table.isColumnHidden(5)
    assert not table.isColumnHidden(6)
    assert not table.isColumnHidden(7)
    reports.close()
    strip.close()
    application.processEvents()
