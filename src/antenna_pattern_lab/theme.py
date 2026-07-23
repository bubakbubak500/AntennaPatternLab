from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication


class DesignStyle(StrEnum):
    CLASSIC = "classic"
    MONITOR = "monitor"


class ThemePreference(StrEnum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    application_background: str
    surface_1: str
    surface_2: str
    surface_3: str
    panel_background: str
    panel_border: str
    divider: str
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str
    accent: str
    accent_hover: str
    accent_secondary: str
    success: str
    warning: str
    warning_strong: str
    warning_chart: str
    danger: str
    danger_strong: str
    info: str
    info_soft: str
    selected: str
    hovered: str
    disabled: str
    focused: str
    chart_grid: str
    chart_labels: str
    chart_series: tuple[str, ...]
    map_water: str
    map_land: str
    map_route: str
    spacing_1: int = 4
    spacing_2: int = 8
    spacing_3: int = 12
    spacing_4: int = 16
    spacing_5: int = 24
    radius_small: int = 2
    radius_medium: int = 4
    ui_font_px: int = 12
    heading_font_px: int = 14
    metadata_font_px: int = 10
    transition_ms: int = 140

    @property
    def workspace_background(self) -> str:
        return self.surface_2

    @property
    def panel_surface(self) -> str:
        return self.panel_background

    @property
    def raised_surface(self) -> str:
        return self.surface_1

    @property
    def input_surface(self) -> str:
        return self.surface_2

    @property
    def selected_surface(self) -> str:
        return self.selected

    @property
    def hover_surface(self) -> str:
        return self.hovered

    @property
    def border_subtle(self) -> str:
        return self.panel_border

    @property
    def border_strong(self) -> str:
        return self.divider

    @property
    def border_focus(self) -> str:
        return self.focused

    @property
    def text_disabled(self) -> str:
        return self.disabled

    @property
    def text_technical(self) -> str:
        return self.text_primary

    @property
    def accent_pressed(self) -> str:
        return self.accent_secondary

    @property
    def inactive(self) -> str:
        return self.text_secondary

    @property
    def selection(self) -> str:
        return self.selected

    @property
    def focus(self) -> str:
        return self.focused

    @property
    def chart_background(self) -> str:
        return self.panel_background

    @property
    def chart_axis(self) -> str:
        return self.panel_border

    @property
    def chart_text(self) -> str:
        return self.chart_labels

    @property
    def chart_empirical_line(self) -> str:
        return self.chart_series[0]

    @property
    def chart_empirical_fill(self) -> str:
        return self.chart_series[5]

    @property
    def chart_theoretical_reference(self) -> str:
        return self.warning

    @property
    def chart_missing(self) -> str:
        return self.divider

    @property
    def chart_selected_sector(self) -> str:
        return self.accent

    @property
    def confidence_levels(self) -> dict[str, str]:
        return {
            "none": self.divider,
            "low": self.text_muted,
            "medium": self.accent_secondary,
            "high": self.success,
        }

    @property
    def control_height(self) -> int:
        return 30

    @property
    def primary_control_height(self) -> int:
        return 34

    @property
    def panel_padding(self) -> int:
        return 16

    @property
    def table_row_height(self) -> int:
        return 28

    @property
    def header_height(self) -> int:
        return 28

    @property
    def splitter_width(self) -> int:
        return 5


CLASSIC_TOKENS = ThemeTokens(
    application_background="#f6f8fa",
    surface_1="#ffffff",
    surface_2="#f6f8fa",
    surface_3="#eaeef2",
    panel_background="#ffffff",
    panel_border="#d0d7de",
    divider="#d8dee4",
    text_primary="#1f2328",
    text_secondary="#57606a",
    text_muted="#8c959f",
    text_inverse="#ffffff",
    accent="#0969da",
    accent_hover="#0e7490",
    accent_secondary="#0e7490",
    success="#1a7f37",
    warning="#9a6700",
    warning_strong="#bc4c00",
    warning_chart="#bf8700",
    danger="#b42318",
    danger_strong="#cf222e",
    info="#0969da",
    info_soft="#54aeff",
    selected="#dff1fb",
    hovered="#eaeef2",
    disabled="#8c959f",
    focused="#0969da",
    chart_grid="#d0d7de",
    chart_labels="#57606a",
    chart_series=("#0f766e", "#0969da", "#9a6700", "#b388ff", "#cf222e", "#19b7a5"),
    map_water="#dff1fb",
    map_land="#edf2e8",
    map_route="#f0883e",
)

DARK_TOKENS = ThemeTokens(
    application_background="#0b1118",
    surface_1="#111922",
    surface_2="#16212c",
    surface_3="#1c2a36",
    panel_background="#111922",
    panel_border="#2b3b49",
    divider="#243441",
    text_primary="#edf3f7",
    text_secondary="#aebdca",
    text_muted="#8193a3",
    text_inverse="#edf3f7",
    accent="#2cc7c9",
    accent_hover="#56d9d8",
    accent_secondary="#45b9c8",
    success="#55b77a",
    warning="#d1a44b",
    warning_strong="#d18d4b",
    warning_chart="#c9953f",
    danger="#df6b72",
    danger_strong="#e35d67",
    info="#65a8e8",
    info_soft="#7bb9ed",
    selected="#183e49",
    hovered="#1c303b",
    disabled="#61717e",
    focused="#63dce0",
    chart_grid="#2b3b49",
    chart_labels="#aebdca",
    chart_series=("#2cc7c9", "#65a8e8", "#d1a44b", "#a78bda", "#df6b72", "#55b77a"),
    map_water="#101f2b",
    map_land="#192a28",
    map_route="#d9984f",
)

LIGHT_TOKENS = ThemeTokens(
    application_background="#e9edf1",
    surface_1="#ffffff",
    surface_2="#f5f7f9",
    surface_3="#e6ebef",
    panel_background="#ffffff",
    panel_border="#b8c3cc",
    divider="#cbd3da",
    text_primary="#17232e",
    text_secondary="#3f5363",
    text_muted="#607483",
    text_inverse="#ffffff",
    accent="#007f82",
    accent_hover="#00696c",
    accent_secondary="#176f88",
    success="#23733d",
    warning="#8a5a00",
    warning_strong="#984400",
    warning_chart="#815400",
    danger="#a72c36",
    danger_strong="#9e2532",
    info="#1769a6",
    info_soft="#347fb5",
    selected="#ccebee",
    hovered="#e4f1f2",
    disabled="#7b8994",
    focused="#007f82",
    chart_grid="#c3cdd5",
    chart_labels="#3f5363",
    chart_series=("#007f82", "#1769a6", "#8a5a00", "#7254a3", "#a72c36", "#23733d"),
    map_water="#dcecf3",
    map_land="#e6ece2",
    map_route="#9a561e",
)

_active_tokens = CLASSIC_TOKENS


def current_tokens() -> ThemeTokens:
    return _active_tokens


class _TokenProxy:
    def __getattr__(self, name: str):
        return getattr(current_tokens(), name)


TOKENS = _TokenProxy()


def semantic_style(role: str, *, bold: bool = False, size_px: int | None = None) -> str:
    color = getattr(current_tokens(), role)
    parts = [f"color: {color}"]
    if bold:
        parts.append(
            f"font-weight: {700 if current_tokens() is CLASSIC_TOKENS else 600}"
        )
    if size_px is not None:
        parts.append(f"font-size: {size_px}px")
    return "; ".join(parts) + ";"


def apply_figure_theme(figure) -> ThemeTokens:
    tokens = current_tokens()
    figure.set_facecolor(tokens.panel_background)
    for axis in figure.axes:
        axis.set_facecolor(tokens.panel_background)
        axis.tick_params(colors=tokens.chart_labels)
        axis.xaxis.label.set_color(tokens.text_primary)
        axis.yaxis.label.set_color(tokens.text_primary)
        axis.title.set_color(tokens.text_primary)
        for line in (*axis.get_xgridlines(), *axis.get_ygridlines()):
            line.set_color(tokens.chart_grid)
        legend = axis.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor(tokens.surface_1)
            legend.get_frame().set_edgecolor(tokens.panel_border)
            for text in legend.get_texts():
                text.set_color(tokens.text_primary)
        for spine in axis.spines.values():
            spine.set_color(tokens.panel_border)
    return tokens


def _system_is_dark(application: QApplication) -> bool:
    style_hints = application.styleHints()
    color_scheme = getattr(style_hints, "colorScheme", None)
    if color_scheme is not None:
        return color_scheme() == Qt.ColorScheme.Dark
    window = application.palette().color(QPalette.ColorRole.Window)
    return window.lightness() < 128


def _palette(tokens: ThemeTokens) -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: tokens.application_background,
        QPalette.ColorRole.WindowText: tokens.text_primary,
        QPalette.ColorRole.Base: tokens.surface_1,
        QPalette.ColorRole.AlternateBase: tokens.surface_2,
        QPalette.ColorRole.ToolTipBase: tokens.surface_3,
        QPalette.ColorRole.ToolTipText: tokens.text_primary,
        QPalette.ColorRole.Text: tokens.text_primary,
        QPalette.ColorRole.Button: tokens.surface_2,
        QPalette.ColorRole.ButtonText: tokens.text_primary,
        QPalette.ColorRole.BrightText: tokens.danger,
        QPalette.ColorRole.Highlight: tokens.selected,
        QPalette.ColorRole.HighlightedText: tokens.text_primary,
        QPalette.ColorRole.Link: tokens.accent,
        QPalette.ColorRole.PlaceholderText: tokens.text_muted,
    }
    for role, value in roles.items():
        palette.setColor(role, QColor(value))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(tokens.disabled))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(tokens.disabled))
    return palette


def monitor_stylesheet(tokens: ThemeTokens) -> str:
    return f"""
* {{
    font-size: {tokens.ui_font_px}px;
}}
QWidget {{
    color: {tokens.text_primary};
    background-color: {tokens.application_background};
}}
QMainWindow, QDialog {{
    background-color: {tokens.application_background};
}}
QMenuBar {{
    background: {tokens.surface_1};
    border-bottom: 1px solid {tokens.panel_border};
    padding: {tokens.spacing_1}px;
}}
QMenuBar::item, QMenu::item {{
    padding: {tokens.spacing_2}px {tokens.spacing_4}px;
}}
QMenuBar::item:selected, QMenu::item:selected {{
    background: {tokens.hovered};
}}
QMenu {{
    background: {tokens.surface_1};
    border: 1px solid {tokens.panel_border};
}}
QWidget#AppShell, QWidget#TopToolbar, QWidget#SideNavigation,
QWidget#DataPanel, QWidget#MetricCard, QWidget#PropertyGrid,
QWidget#LogViewer, QWidget#EmptyState, QWidget#primaryControls,
QWidget#OperationalHeader, QWidget#MetricStrip, QWidget#AnalysisToolbar,
QWidget#ReportExplorer, QWidget#SectorQualityPanel,
QWidget#IntegrationStatusBar {{
    background: {tokens.panel_background};
    border: 1px solid {tokens.panel_border};
    border-radius: {tokens.radius_medium}px;
}}
QFrame#TopToolbar {{
    background: {tokens.surface_1};
}}
QFrame#SideNavigation {{
    background: {tokens.surface_2};
}}
QLabel#PanelHeader {{
    color: {tokens.text_primary};
    font-size: {tokens.heading_font_px}px;
    font-weight: 600;
}}
QLabel#Metadata {{
    color: {tokens.text_secondary};
    font-size: {tokens.metadata_font_px}px;
}}
QLabel#ContextValue, QLabel#MetricValue {{
    color: {tokens.text_primary};
    font-weight: 600;
}}
QLabel#MetricLabel {{
    color: {tokens.text_secondary};
    font-size: {tokens.metadata_font_px}px;
}}
QLabel[statusRole="success"] {{ color: {tokens.success}; font-weight: 600; }}
QLabel[statusRole="warning"] {{ color: {tokens.warning}; font-weight: 600; }}
QLabel[statusRole="danger"] {{ color: {tokens.danger}; font-weight: 600; }}
QLabel[statusRole="info"] {{ color: {tokens.info}; font-weight: 600; }}
QLabel[statusRole="muted"] {{ color: {tokens.text_muted}; }}
QLabel[statusRole="inactive"], QLabel[statusRole="waiting"] {{
    color: {tokens.inactive};
}}
QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
QDateTimeEdit, QDateEdit, QTimeEdit {{
    min-height: 22px;
    padding: {tokens.spacing_1}px {tokens.spacing_3}px;
    background: {tokens.surface_2};
    color: {tokens.text_primary};
    border: 1px solid {tokens.panel_border};
    border-radius: {tokens.radius_small}px;
}}
QPushButton:hover, QToolButton:hover, QComboBox:hover, QLineEdit:hover,
QSpinBox:hover, QDoubleSpinBox:hover {{
    background: {tokens.hovered};
    border-color: {tokens.accent};
}}
QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QTableView:focus, QListView:focus {{
    border: 1px solid {tokens.focused};
}}
QPushButton:disabled, QToolButton:disabled, QComboBox:disabled,
QLineEdit:disabled, QSpinBox:disabled {{
    color: {tokens.disabled};
    background: {tokens.surface_1};
}}
QPushButton#primaryAction {{
    background: {tokens.accent};
    color: {tokens.application_background};
    border-color: {tokens.accent};
    font-weight: 600;
}}
QPushButton#primaryAction:hover {{
    background: {tokens.accent_hover};
}}
QPushButton#primaryAction:pressed {{
    background: {tokens.accent_pressed};
}}
QPushButton#primaryAction[collectionState="running"] {{
    background: {tokens.danger};
    border-color: {tokens.danger};
    color: {tokens.text_inverse};
}}
QPushButton[segment="true"] {{
    border-radius: 0;
    border-right-width: 0;
}}
QPushButton[segment="true"]:first {{
    border-top-left-radius: {tokens.radius_small}px;
    border-bottom-left-radius: {tokens.radius_small}px;
}}
QPushButton[segment="true"]:last {{
    border-right-width: 1px;
    border-top-right-radius: {tokens.radius_small}px;
    border-bottom-right-radius: {tokens.radius_small}px;
}}
QPushButton[segment="true"]:checked {{
    background: {tokens.selected};
    color: {tokens.text_primary};
    border-color: {tokens.accent};
}}
QPushButton[buttonRole="danger"] {{
    color: {tokens.danger};
    border-color: {tokens.danger};
}}
QTableView, QTableWidget, QTreeView, QListView {{
    background: {tokens.surface_1};
    alternate-background-color: {tokens.surface_2};
    color: {tokens.text_primary};
    border: 1px solid {tokens.panel_border};
    gridline-color: {tokens.divider};
    selection-background-color: {tokens.selected};
    selection-color: {tokens.text_primary};
}}
QTextEdit, QPlainTextEdit {{
    background: {tokens.surface_1};
    color: {tokens.text_primary};
    border: 1px solid {tokens.panel_border};
    border-radius: {tokens.radius_small}px;
    selection-background-color: {tokens.selected};
}}
QHeaderView::section {{
    background: {tokens.surface_3};
    color: {tokens.text_secondary};
    border: 0;
    border-right: 1px solid {tokens.divider};
    border-bottom: 1px solid {tokens.panel_border};
    padding: {tokens.spacing_2}px {tokens.spacing_3}px;
    font-weight: 600;
}}
QToolButton[qualityRole] {{
    min-height: 24px;
    padding: 1px 3px;
    border-radius: {tokens.radius_small}px;
}}
QToolButton[qualityRole="none"] {{
    color: {tokens.text_muted};
    background: {tokens.surface_2};
    border-color: {tokens.divider};
}}
QToolButton[qualityRole="low"] {{
    color: {tokens.text_primary};
    background: {tokens.surface_2};
    border-color: {tokens.text_muted};
    border-style: dashed;
}}
QToolButton[qualityRole="medium"] {{
    color: {tokens.text_primary};
    background: {tokens.selected};
    border-color: {tokens.accent_secondary};
}}
QToolButton[qualityRole="high"] {{
    color: {tokens.text_primary};
    background: {tokens.selected};
    border: 2px solid {tokens.success};
}}
QToolButton[qualityRole]:checked {{
    border: 2px solid {tokens.focused};
}}
QTabWidget::pane {{
    border: 1px solid {tokens.panel_border};
    background: {tokens.panel_background};
}}
QTabBar::tab {{
    background: {tokens.surface_2};
    border: 1px solid {tokens.panel_border};
    padding: {tokens.spacing_2}px {tokens.spacing_4}px;
}}
QTabBar::tab:selected {{
    background: {tokens.selected};
    color: {tokens.text_primary};
}}
QGroupBox {{
    border: 1px solid {tokens.panel_border};
    border-radius: {tokens.radius_medium}px;
    margin-top: {tokens.spacing_4}px;
    padding-top: {tokens.spacing_4}px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {tokens.spacing_3}px;
    padding: 0 {tokens.spacing_2}px;
}}
QSplitter::handle {{
    background: {tokens.divider};
    width: {tokens.splitter_width}px;
    height: {tokens.splitter_width}px;
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {tokens.surface_1};
    border: 0;
}}
QScrollBar::handle {{
    background: {tokens.disabled};
    border-radius: {tokens.radius_small}px;
    min-width: 20px;
    min-height: 20px;
}}
QStatusBar {{
    background: {tokens.surface_1};
    border-top: 1px solid {tokens.panel_border};
}}
QToolTip {{
    color: {tokens.text_primary};
    background: {tokens.surface_3};
    border: 1px solid {tokens.focused};
    padding: {tokens.spacing_2}px;
}}
"""


class ThemeController(QObject):
    theme_changed = Signal(object)

    def __init__(self, settings: QSettings, parent: QObject | None = None):
        super().__init__(parent)
        self.settings = settings
        self.application = QApplication.instance()
        if self.application is None:
            raise RuntimeError("ThemeController requires a QApplication")
        # Capture the exact application state before Monitor touches it. Using
        # style().standardPalette() here changes the native Windows palette
        # (notably to a beige window background on some systems).
        self._native_palette = QPalette(self.application.palette())
        self._native_font = QFont(self.application.font())
        self._native_stylesheet = self.application.styleSheet()
        style_hints = self.application.styleHints()
        signal = getattr(style_hints, "colorSchemeChanged", None)
        if signal is not None:
            signal.connect(self._system_theme_changed)
        self.apply()

    @property
    def design_style(self) -> DesignStyle:
        value = str(self.settings.value("ui/design_style", DesignStyle.CLASSIC.value))
        try:
            return DesignStyle(value)
        except ValueError:
            return DesignStyle.CLASSIC

    @property
    def preference(self) -> ThemePreference:
        value = str(self.settings.value("ui/theme", ThemePreference.SYSTEM.value))
        try:
            return ThemePreference(value)
        except ValueError:
            return ThemePreference.SYSTEM

    @property
    def effective_theme(self) -> ThemePreference:
        if self.preference != ThemePreference.SYSTEM:
            return self.preference
        return ThemePreference.DARK if _system_is_dark(self.application) else ThemePreference.LIGHT

    @property
    def tokens(self) -> ThemeTokens:
        if self.design_style == DesignStyle.CLASSIC:
            return CLASSIC_TOKENS
        return DARK_TOKENS if self.effective_theme == ThemePreference.DARK else LIGHT_TOKENS

    def set_selection(
        self,
        design_style: DesignStyle | str,
        preference: ThemePreference | str,
    ) -> None:
        design_style = DesignStyle(design_style)
        preference = ThemePreference(preference)
        self.settings.setValue("ui/design_style", design_style.value)
        self.settings.setValue("ui/theme", preference.value)
        self.settings.sync()
        self.apply()

    def apply(self) -> None:
        global _active_tokens
        _active_tokens = self.tokens
        if self.design_style == DesignStyle.CLASSIC:
            self.application.setStyleSheet(self._native_stylesheet)
            self.application.setPalette(self._native_palette)
            self.application.setFont(self._native_font)
        else:
            self.application.setPalette(_palette(_active_tokens))
            self.application.setStyleSheet(monitor_stylesheet(_active_tokens))
            font = QFont(self._native_font)
            font.setPixelSize(_active_tokens.ui_font_px)
            self.application.setFont(font)
        self.theme_changed.emit(_active_tokens)

    def _system_theme_changed(self, _scheme) -> None:
        if self.preference == ThemePreference.SYSTEM:
            self.apply()


def monospace_font(pixel_size: int | None = None) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPixelSize(pixel_size or current_tokens().ui_font_px)
    return font
