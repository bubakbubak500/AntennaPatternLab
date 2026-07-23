import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.theme import (
    DARK_TOKENS,
    LIGHT_TOKENS,
    DesignStyle,
    ThemeController,
    ThemePreference,
    current_tokens,
)


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
