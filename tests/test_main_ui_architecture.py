import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.ui import MainWindow


def _window(tmp_path, name="ui"):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(
        str(tmp_path / "main-ui.ini"),
        QSettings.Format.IniFormat,
    )
    window = MainWindow(
        SpotRepository(tmp_path / f"{name}.sqlite3"),
        settings=settings,
    )
    return application, settings, window


def test_collection_control_presents_running_stopped_and_failed_states(
    tmp_path, monkeypatch
):
    application, _settings, window = _window(tmp_path)
    starts = []
    stops = []
    monkeypatch.setattr(window.collector, "start", lambda *args: starts.append(args))
    monkeypatch.setattr(window.collector, "stop", lambda: stops.append(True))

    window.toggle_collection()
    assert starts
    assert window._collecting
    assert window._collection_ui_state == "running"
    assert window.live_button.property("collectionState") == "running"
    assert window.live_button.isEnabled()

    window.toggle_collection()
    assert stops
    assert not window._collecting
    assert window._collection_ui_state == "stopped"
    assert window.live_button.property("collectionState") == "stopped"

    monkeypatch.setattr(
        window.collector,
        "start",
        lambda *_args: (_ for _ in ()).throw(ValueError("Invalid callsign")),
    )
    monkeypatch.setattr(QMessageBox, "warning", lambda *_args, **_kwargs: None)
    window.toggle_collection()
    assert window._collection_ui_state == "failed"
    assert window.operational_header.collection.state_label.property(
        "statusRole"
    ) == "danger"
    window.close()
    application.processEvents()


def test_splitter_state_persists_and_reset_restores_chart_favoring_default(tmp_path):
    application, settings, window = _window(tmp_path, "first")
    window.resize(1366, 768)
    window.show()
    application.processEvents()
    window.main_splitter.setSizes([820, 440])
    window._save_splitter_state()
    stored = settings.value("ui/main_splitter_state")
    assert stored
    window.close()
    application.processEvents()

    second = MainWindow(
        SpotRepository(tmp_path / "second.sqlite3"),
        settings=settings,
    )
    second.resize(1366, 768)
    second.show()
    application.processEvents()
    left, right = second.main_splitter.sizes()
    assert left > right

    second.main_splitter.setSizes([500, 700])
    second._reset_layout()
    left, right = second.main_splitter.sizes()
    assert left > right
    assert settings.value("ui/main_splitter_state")
    second.close()
    application.processEvents()


def test_language_is_menu_driven_and_empty_states_are_deliberate(tmp_path):
    application, _settings, window = _window(tmp_path)
    window.show()
    application.processEvents()

    assert window.language.isHidden()
    assert window.language_actions["CZE"].isChecked()
    window.language_actions["ENG"].trigger()
    application.processEvents()
    assert window.language_code == "ENG"
    assert window.language_actions["ENG"].isChecked()

    assert window.chart_stack.currentWidget() is window.chart_empty
    assert window.chart_empty.heading.text() == "The pattern is waiting for data"
    assert window.report_panel.stack.currentWidget() is window.report_panel.empty
    assert window.report_panel.empty.heading.text() == "No reports yet"
    window.close()
    application.processEvents()


def test_main_workflow_has_accessible_controls_and_logical_tab_order(tmp_path):
    application, _settings, window = _window(tmp_path)

    def next_focusable(widget):
        candidate = widget.nextInFocusChain()
        while candidate is not widget:
            if (
                candidate.focusPolicy() != Qt.FocusPolicy.NoFocus
                and candidate.isEnabled()
                and not candidate.isHidden()
            ):
                return candidate
            candidate = candidate.nextInFocusChain()
        return None

    assert window.callsign.accessibleName()
    assert window.tx_grid.accessibleName()
    assert window.live_button.accessibleName()
    assert window.live_button.accessibleDescription()
    assert window.graph_info.accessibleName()
    assert window.table.accessibleName()
    assert next_focusable(window.callsign) is window.tx_grid
    assert next_focusable(window.history_button) is window.live_button
    assert next_focusable(window.sector_width) is window.graph_info

    window.close()
    application.processEvents()
