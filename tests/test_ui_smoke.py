import os
from dataclasses import replace
from datetime import timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox

from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.hamlib import RotatorState
from antenna_pattern_lab.ui import MainWindow
from antenna_pattern_lab.wsjtx import Header, Status
from antenna_pattern_lab.profiles import AntennaProfile
from antenna_pattern_lab.campaigns import MeasurementCampaign
from antenna_pattern_lab.demo import generate_demo_spots


def test_window_renders_demo_profile(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(SpotRepository(tmp_path / "ui.sqlite3"), settings=settings)
    assert window.styleSheet() == ""
    assert window.figure.get_facecolor()[:3] == (1.0, 1.0, 1.0)
    assert window.file_menu.title() == "Soubor"
    assert window.settings_menu.title() == "Nastavení"
    assert window.live_button.parentWidget().objectName() == "CollectionControl"
    assert window.operational_header.objectName() == "OperationalHeader"
    assert window.metric_strip.objectName() == "MetricStrip"
    assert window.analysis_toolbar.objectName() == "AnalysisToolbar"
    assert window.main_splitter.objectName() == "MainAnalysisSplitter"
    assert window.report_panel.objectName() == "ReportExplorer"
    assert window.sector_quality_panel.objectName() == "SectorQualityPanel"
    assert window.integration_bar.objectName() == "IntegrationStatusBar"
    assert window.live_button.accessibleName()
    window.language.setCurrentText("CZE")
    window.band.setCurrentText("40m")
    window.add_demo_data()
    application.processEvents()
    assert window.figure.axes[0].get_facecolor()[:3] == (1.0, 1.0, 1.0)
    assert window.table.rowCount() == 100
    assert {spot.band for spot in window.repository.list_spots()} == {"40m"}
    assert "100 použitelných" in window.summary.text()
    assert "PSK Reporter: Odpojeno" in window.connection_indicator.text()
    assert window.connection_indicator.property("statusRole") == "inactive"
    assert window.spot_map_action.text() == "Mapa spotů…"
    assert window.campaigns_action.text() == "Měřicí kampaně…"
    assert window.coverage_action.text() == "Pokrytí měření…"
    assert window.demo_action not in window.data_menu.actions()
    assert window.demo_action in window.help_menu.actions()
    assert window.help_contents_action in window.help_menu.actions()
    assert window.source_filter.count() == 3
    assert window.table.columnCount() == 8
    assert window.campaign_indicator.text() == "Kampaň: —"
    window._open_spot_map()
    application.processEvents()
    assert window._spot_map_dialog is not None
    assert len(window._spot_map_dialog.points) == 10
    window._spot_map_dialog.show_receiver(0)
    assert window._spot_map_dialog._route_artists
    window._spot_map_dialog.close()
    application.processEvents()
    window.language.setCurrentText("ENG")
    application.processEvents()
    assert window.live_button.text() == "Start live collection"
    assert window.history_button.text() == "Load history"
    assert window.spot_map_action.text() == "Spot map…"
    assert window.campaigns_action.text() == "Measurement campaigns…"
    assert window.coverage_action.text() == "Measurement coverage…"
    assert window.help_contents_action.text() == "Help contents…"
    assert "100 usable reports" in window.summary.text()
    starts = []
    monkeypatch.setattr(window.collector, "start", lambda *args: starts.append(args))
    window._collecting = True
    window.callsign.setText("OK1TEST")
    window._collection_configuration_changed()
    assert starts == [("OK1TEST", "40m", "FT8", [])]
    window._collecting = False
    window.callsign.setText("OK7PS")
    profile = window.repository.save_antenna_profile(
        AntennaProfile(
            id=None,
            name="Test EFHW",
            antenna_type="EFHW",
            orientation_deg=35,
            wire_length_m=20.5,
            transformer_ratio="1:49",
            power_w=20,
        )
    )
    window._reload_antenna_profiles(profile.id)
    assert window.antenna_profile.currentData() == profile.id
    window.refresh()
    assert len(window.figure.axes[0].lines) == 3
    assert len(window.figure.axes[0].lines[0].get_xdata()) == 181
    outline = [
        value
        for value in window.figure.axes[0].lines[0].get_ydata()
        if value == value
    ]
    assert len(outline) > 100
    assert min(outline) > 0
    assert window.graph_details.rowCount() == 36
    assert window.graph_details.accessibleName() == "Accessible chart data"
    assert "click pins" in window.graph_info.toolTip()
    assert "width='340'" in window.graph_info.toolTip()
    window._show_graph_hit = lambda _event: True
    window._on_graph_click(None)
    assert window._plot_pinned
    window._show_graph_hit = lambda _event: False
    window._on_graph_click(None)
    assert not window._plot_pinned
    window.graph_view.setCurrentIndex(window.graph_view.findData("model"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    assert len(window.figure.axes[0].lines[0].get_xdata()) == 73
    assert window.graph_details.rowCount() == 72
    assert "Parametric" in window.figure.axes[0].get_title()
    assert not window.sector_width.isEnabled()
    window.graph_view.setCurrentIndex(window.graph_view.findData("count"))
    window.sector_width.setCurrentIndex(window.sector_width.findData(45))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    assert len(window.figure.axes[0].patches) == 8
    assert window.graph_details.rowCount() == 8
    assert window.graph_info.toolTip()
    window.graph_view.setCurrentIndex(window.graph_view.findData("detrended"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    assert "common time trend" in window.figure.axes[0].get_title()
    window.graph_view.setCurrentIndex(window.graph_view.findData("receiver"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    assert "one weighted vote per RX" in window.figure.axes[0].get_title()
    assert window.graph_details.rowCount() > 8
    assert "at most one vote" in window.graph_info.toolTip()
    window.graph_view.setCurrentIndex(window.graph_view.findData("control"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    assert "stable-RX common-trend" in window.figure.axes[0].get_title()
    assert window.graph_details.item(0, 0).text() == "Control group"
    assert "No correction is applied" in window.graph_info.toolTip()
    window.graph_view.setCurrentIndex(window.graph_view.findData("distance"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    window.graph_view.setCurrentIndex(window.graph_view.findData("time"))
    application.processEvents()
    assert window.figure.axes[0].name == "rectilinear"
    assert not window.sector_width.isEnabled()
    window.graph_view.setCurrentIndex(window.graph_view.findData("map"))
    application.processEvents()
    assert window.figure.axes[0].name == "rectilinear"
    assert len(window.figure.axes) == 2  # map plus SNR colorbar
    window.callsign.setText("OK7PS")
    window.time_filter.setCurrentIndex(1)
    application.processEvents()
    assert 0 < window.table.rowCount() < 100
    window.time_filter.setCurrentIndex(0)
    window.graph_view.setCurrentIndex(window.graph_view.findData("snr"))
    application.processEvents()
    assert window.sector_width.isEnabled()
    window.graph_view.setCurrentIndex(window.graph_view.findData("exposure"))
    application.processEvents()
    assert window.figure.axes[0].name == "polar"
    tx_status = Status(
        header=Header(3, 1, "WSJT-X"),
        dial_frequency_hz=7_074_000,
        mode="FT8",
        dx_call="",
        report="",
        tx_mode="FT8",
        tx_enabled=True,
        transmitting=True,
        decoding=False,
        rx_df_hz=1000,
        tx_df_hz=1200,
        de_call="OK1TEST",
        de_grid="JN79",
        dx_grid="",
        tx_watchdog=False,
        tx_message="CQ OK1TEST JN79",
    )
    window._set_rotator_state("connected", "127.0.0.1:4533")
    window._handle_rotator_state(RotatorState(35.0, 2.0))
    window._handle_wsjtx_message(tx_status)
    session_id = window._active_tx_sessions["WSJT-X"]
    assert window.repository.tx_session_profile_id(session_id) == profile.id
    window._handle_rotator_state(RotatorState(40.0, 3.0))
    assert "MOVING DURING TX" in window.rotator_indicator.text()
    assert window.rotator_indicator.property("statusRole") == "danger"
    window._handle_wsjtx_message(replace(tx_status, transmitting=False))
    assert window.repository.tx_session_count() == 1
    session = window.repository.list_tx_sessions()[0]
    assert session.rotator_start_azimuth_deg == 35.0
    assert session.rotator_end_azimuth_deg == 40.0
    assert session.rotator_max_deviation_deg == 5.0
    assert "rotator_moved" in session.quality_flags
    assert "Rotator: Connected · 40°" in window.rotator_indicator.text()
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    window.clear_spots()
    assert window.repository.count() == 0
    assert window.repository.tx_session_count() == 0
    assert window.table.rowCount() == 0
    assert "Deleted 100 spots" in window.status.text()
    window._set_rotator_state("connected", "127.0.0.1:4533")
    window._handle_rotator_state(RotatorState(123.4, 5.6))
    assert "PROFILE MISMATCH" in window.rotator_indicator.text()
    assert "Az 123.4° · El 5.6°" in window.rotator_indicator.toolTip()
    window.antenna_profile.setCurrentIndex(0)
    assert "Rotator: Connected · 123°" in window.rotator_indicator.text()
    window.close()


def test_campaign_indicator_reports_reached_target(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "goal-indicator.sqlite3")
    base = generate_demo_spots(count=1)[0]
    campaign = repository.start_campaign(
        MeasurementCampaign(
            id=None,
            name="Short target",
            objective="Indicator test",
            tx_call=base.tx_call,
            tx_grid=base.tx_grid,
            band=base.band,
            mode=base.mode,
            antenna_profile_id=None,
            antenna_profile_name="",
            notes="Test",
            started_at=base.observed_at - timedelta(minutes=1),
            target_spots=3,
            target_receivers=2,
            target_sectors=1,
            target_time_blocks=1,
        )
    )
    for index in range(3):
        repository.add(
            replace(
                base,
                sequence=index,
                rx_call=f"RX{index % 2}",
                observed_at=base.observed_at + timedelta(seconds=index),
            )
        )
    assert repository.get_campaign(campaign.id).spot_count == 3
    settings = QSettings(
        str(tmp_path / "goal-settings.ini"),
        QSettings.Format.IniFormat,
    )
    window = MainWindow(repository, settings=settings)
    application.processEvents()
    assert "✓" in window.campaign_indicator.text()
    assert "Spoty 3/3" in window.campaign_indicator.toolTip()
    window.close()
