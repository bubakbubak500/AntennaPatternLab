import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QDialog

from antenna_pattern_lab.appearance_dialog import AppearanceDialog
from antenna_pattern_lab.storage import SpotRepository
from antenna_pattern_lab.theme import (
    DARK_TOKENS,
    LIGHT_TOKENS,
    DesignStyle,
    ThemeController,
    ThemePreference,
    current_tokens,
)
from antenna_pattern_lab.ui import MainWindow


def _palette_colors(palette):
    return tuple(
        palette.color(role).rgba()
        for role in (
            QPalette.ColorRole.Window,
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Base,
            QPalette.ColorRole.Button,
            QPalette.ColorRole.Text,
        )
    )


def test_classic_preserves_exact_native_application_appearance(tmp_path):
    application = QApplication.instance() or QApplication([])
    native_palette = _palette_colors(application.palette())
    native_stylesheet = application.styleSheet()
    native_font = application.font()
    settings = QSettings(str(tmp_path / "classic.ini"), QSettings.Format.IniFormat)
    controller = ThemeController(settings)

    assert controller.design_style == DesignStyle.CLASSIC
    assert _palette_colors(application.palette()) == native_palette
    assert application.styleSheet() == native_stylesheet
    assert application.font() == native_font

    controller.set_selection(DesignStyle.MONITOR, ThemePreference.DARK)
    assert DARK_TOKENS.application_background in application.styleSheet()
    controller.set_selection(DesignStyle.CLASSIC, ThemePreference.SYSTEM)
    assert _palette_colors(application.palette()) == native_palette
    assert application.styleSheet() == native_stylesheet
    assert application.font() == native_font


def test_monitor_theme_is_persisted_and_applied_application_wide(tmp_path):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "appearance.ini"), QSettings.Format.IniFormat)
    controller = ThemeController(settings)
    try:
        controller.set_selection(DesignStyle.MONITOR, ThemePreference.DARK)
        assert settings.value("ui/design_style") == "monitor"
        assert settings.value("ui/theme") == "dark"
        assert current_tokens() == DARK_TOKENS
        assert DARK_TOKENS.application_background in application.styleSheet()
        assert DARK_TOKENS.focused in application.styleSheet()

        controller.set_selection(DesignStyle.MONITOR, ThemePreference.LIGHT)
        assert current_tokens() == LIGHT_TOKENS
        assert LIGHT_TOKENS.application_background in application.styleSheet()
    finally:
        controller.set_selection(DesignStyle.CLASSIC, ThemePreference.SYSTEM)


def test_follow_system_reapplies_without_restart(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "system-theme.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("antenna_pattern_lab.theme._system_is_dark", lambda _app: True)
    controller = ThemeController(settings)
    try:
        controller.set_selection(DesignStyle.MONITOR, ThemePreference.SYSTEM)
        assert controller.effective_theme == ThemePreference.DARK
        assert current_tokens() == DARK_TOKENS

        monkeypatch.setattr("antenna_pattern_lab.theme._system_is_dark", lambda _app: False)
        controller._system_theme_changed(None)
        assert controller.effective_theme == ThemePreference.LIGHT
        assert current_tokens() == LIGHT_TOKENS
    finally:
        controller.set_selection(DesignStyle.CLASSIC, ThemePreference.SYSTEM)


def test_semantic_token_sets_cover_chart_and_interaction_roles():
    for tokens in (DARK_TOKENS, LIGHT_TOKENS):
        assert len(tokens.chart_series) >= 5
        assert tokens.panel_border != tokens.panel_background
        assert tokens.text_primary != tokens.application_background
        assert tokens.accent != tokens.accent_hover
        assert 100 <= tokens.transition_ms <= 160
        assert tokens.spacing_1 < tokens.spacing_5
        assert tokens.radius_small <= tokens.radius_medium
        assert tokens.workspace_background
        assert tokens.panel_surface
        assert tokens.input_surface
        assert tokens.border_focus == tokens.focused
        assert tokens.accent_pressed
        assert tokens.inactive
        assert tokens.chart_empirical_line
        assert tokens.chart_empirical_fill
        assert tokens.chart_theoretical_reference
        assert set(tokens.confidence_levels) == {"none", "low", "medium", "high"}
        assert tokens.control_height in range(28, 33)
        assert tokens.primary_control_height in range(32, 37)
        assert tokens.table_row_height >= 26


def test_appearance_dialog_only_enables_theme_for_monitor():
    application = QApplication.instance() or QApplication([])
    dialog = AppearanceDialog(
        DesignStyle.CLASSIC, ThemePreference.SYSTEM, language="ENG"
    )
    assert not dialog.theme.isEnabled()
    dialog.design_style.setCurrentIndex(
        dialog.design_style.findData(DesignStyle.MONITOR.value)
    )
    assert dialog.theme.isEnabled()
    assert dialog.design_style.currentData() == "monitor"
    assert dialog.theme.currentData() == "system"
    assert dialog.values() == (DesignStyle.MONITOR, ThemePreference.SYSTEM)
    dialog.close()
    application.processEvents()


def test_real_appearance_dialog_selection_persists_and_applies(tmp_path):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "real-dialog.ini"), QSettings.Format.IniFormat)
    window = MainWindow(
        SpotRepository(tmp_path / "real-dialog.sqlite3"), settings=settings
    )
    dialog = AppearanceDialog(
        window.theme_controller.design_style,
        window.theme_controller.preference,
        language="ENG",
        parent=window,
    )
    dialog.design_style.setCurrentIndex(
        dialog.design_style.findData(DesignStyle.MONITOR.value)
    )
    dialog.theme.set_preference(ThemePreference.DARK)

    design_style, preference = dialog.values()
    window.theme_controller.set_selection(design_style, preference)
    application.processEvents()

    assert settings.value("ui/design_style") == "monitor"
    assert settings.value("ui/theme") == "dark"
    assert window.theme_controller.design_style == DesignStyle.MONITOR
    assert DARK_TOKENS.application_background in application.styleSheet()
    window.theme_controller.set_selection(
        DesignStyle.CLASSIC, ThemePreference.SYSTEM
    )
    dialog.close()
    window.close()
    application.processEvents()


def test_main_window_switches_monitor_and_restores_classic(tmp_path):
    application = QApplication.instance() or QApplication([])
    native_palette = _palette_colors(application.palette())
    native_stylesheet = application.styleSheet()
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    window = MainWindow(
        SpotRepository(tmp_path / "window.sqlite3"), settings=settings
    )
    classic_table_font = window.table.font()

    assert window._root_layout.getContentsMargins() == (12, 8, 12, 8)
    assert _palette_colors(application.palette()) == native_palette
    assert application.styleSheet() == native_stylesheet

    window.theme_controller.set_selection(
        DesignStyle.MONITOR, ThemePreference.DARK
    )
    application.processEvents()
    assert window._root_layout.getContentsMargins() == (12, 8, 12, 8)
    assert DARK_TOKENS.application_background in application.styleSheet()
    assert window.table.font() != classic_table_font

    window.theme_controller.set_selection(
        DesignStyle.CLASSIC, ThemePreference.SYSTEM
    )
    application.processEvents()
    assert window._root_layout.getContentsMargins() == (12, 8, 12, 8)
    assert window.table.font() == classic_table_font
    assert _palette_colors(application.palette()) == native_palette
    assert application.styleSheet() == native_stylesheet
    window.close()
    application.processEvents()


def test_appearance_menu_applies_monitor_selection(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "menu.ini"), QSettings.Format.IniFormat)
    window = MainWindow(
        SpotRepository(tmp_path / "menu.sqlite3"), settings=settings
    )

    class AcceptedMonitorDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

        def values(self):
            return DesignStyle.MONITOR, ThemePreference.DARK

    monkeypatch.setattr(
        "antenna_pattern_lab.ui.AppearanceDialog", AcceptedMonitorDialog
    )
    window._open_appearance_settings()
    application.processEvents()

    assert settings.value("ui/design_style") == "monitor"
    assert settings.value("ui/theme") == "dark"
    assert DARK_TOKENS.application_background in application.styleSheet()
    window.theme_controller.set_selection(
        DesignStyle.CLASSIC, ThemePreference.SYSTEM
    )
    window.close()
    application.processEvents()
