from __future__ import annotations

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .theme import ThemePreference, current_tokens, monospace_font


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class _NamedFrame(QFrame):
    object_name = ""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName(self.object_name)


class AppShell(_NamedFrame):
    object_name = "AppShell"


class TopToolbar(_NamedFrame):
    object_name = "TopToolbar"


class SideNavigation(_NamedFrame):
    object_name = "SideNavigation"


class DataPanel(_NamedFrame):
    object_name = "DataPanel"


class PanelHeader(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("PanelHeader")


class MetricCard(_NamedFrame):
    object_name = "MetricCard"

    def __init__(self, label: str = "", value: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.label = QLabel(label)
        self.label.setObjectName("Metadata")
        self.value = QLabel(value)
        self.value.setFont(monospace_font())
        layout.addWidget(self.label)
        layout.addWidget(self.value)


class MetricItem(QWidget):
    def __init__(self, label: str = "", value: str = "—", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.label = QLabel(label)
        self.label.setObjectName("MetricLabel")
        self.value = QLabel(value)
        self.value.setObjectName("MetricValue")
        self.value.setFont(monospace_font())
        layout.addWidget(self.label)
        layout.addWidget(self.value)

    def set_metric(self, label: str, value: str, tooltip: str = "") -> None:
        self.label.setText(label)
        self.value.setText(value)
        self.setToolTip(tooltip)
        accessible = f"{label}: {value}"
        self.setAccessibleName(accessible)
        self.value.setAccessibleName(accessible)


class StatusBadge(QLabel):
    def __init__(self, text: str = "", role: str = "info", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.set_status_role(role)

    def set_status_role(self, role: str) -> None:
        self.setProperty("statusRole", role)
        repolish(self)


class StatusIndicator(StatusBadge):
    _GLYPHS = {
        "active": "●",
        "connected": "●",
        "success": "●",
        "connecting": "◐",
        "waiting": "◐",
        "inactive": "○",
        "disabled": "○",
        "warning": "▲",
        "error": "◆",
        "danger": "◆",
    }
    _ROLES = {
        "active": "success",
        "connected": "success",
        "success": "success",
        "connecting": "info",
        "waiting": "waiting",
        "inactive": "inactive",
        "disabled": "inactive",
        "warning": "warning",
        "error": "danger",
        "danger": "danger",
    }

    def __init__(
        self,
        name: str = "",
        state: str = "inactive",
        detail: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.set_indicator(name, state, detail)

    def set_indicator(
        self,
        name: str,
        state: str,
        detail: str = "",
        state_label: str | None = None,
    ) -> None:
        normalized = state if state in self._GLYPHS else "error"
        self.set_status_role(self._ROLES[normalized])
        self.setProperty("statusState", normalized)
        glyph = self._GLYPHS[normalized]
        visible_state = state_label or state
        self.setText(f"{glyph} {name}: {visible_state}")
        self.setToolTip(detail)
        self.setAccessibleName(f"{name}: {visible_state}")
        self.setAccessibleDescription(detail)
        repolish(self)


class CompactButton(QPushButton):
    def __init__(self, text: str = "", parent: QWidget | None = None, role: str = ""):
        super().__init__(text, parent)
        if role:
            self.setProperty("buttonRole", role)


class IconButton(QToolButton):
    def __init__(self, tooltip: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)


class SegmentedControl(QWidget):
    selection_changed = Signal(str)

    def __init__(self, options: tuple[tuple[str, str], ...], parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for index, (value, label) in enumerate(options):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("segment", True)
            button.setProperty("segmentValue", value)
            self.group.addButton(button, index)
            layout.addWidget(button)
        self.group.idClicked.connect(
            lambda identifier: self.selection_changed.emit(
                str(self.group.button(identifier).property("segmentValue"))
            )
        )

    def set_value(self, value: str) -> None:
        for button in self.group.buttons():
            if button.property("segmentValue") == value:
                button.setChecked(True)
                return


class SearchField(QLineEdit):
    def __init__(self, placeholder: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)


class DataTable(QTableWidget):
    def __init__(self, rows: int = 0, columns: int = 0, parent: QWidget | None = None):
        super().__init__(rows, columns, parent)
        self.setAlternatingRowColors(True)


class PropertyGrid(_NamedFrame):
    object_name = "PropertyGrid"


class LogViewer(QTextEdit):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("LogViewer")
        self.setReadOnly(True)
        self.setFont(monospace_font())


class EmptyState(_NamedFrame):
    object_name = "EmptyState"

    def __init__(self, title: str = "", detail: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addStretch()
        self.heading = PanelHeader(title)
        self.description = QLabel(detail)
        self.description.setObjectName("Metadata")
        self.description.setWordWrap(True)
        self.description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.heading)
        layout.addWidget(self.description)
        layout.addStretch()


class ModalDialog(QDialog):
    pass


class ToastNotification(StatusBadge):
    def __init__(self, text: str = "", role: str = "info", parent: QWidget | None = None):
        super().__init__(text, role, parent)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._transition = QPropertyAnimation(
            self._opacity, QByteArray(b"opacity"), self
        )
        self._transition.setDuration(current_tokens().transition_ms)
        self._transition.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_message(self, text: str, role: str = "info") -> None:
        self.setText(text)
        self.set_status_role(role)
        self._transition.stop()
        self._transition.setStartValue(0.0)
        self._transition.setEndValue(1.0)
        self.show()
        self._transition.start()


class ThemeToggle(QComboBox):
    preference_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.addItem("Dark", ThemePreference.DARK.value)
        self.addItem("Light", ThemePreference.LIGHT.value)
        self.addItem("Follow system", ThemePreference.SYSTEM.value)
        self.currentIndexChanged.connect(
            lambda index: self.preference_changed.emit(
                ThemePreference(self.itemData(index))
            )
        )

    def set_preference(self, preference: ThemePreference) -> None:
        index = self.findData(preference.value)
        if index >= 0:
            self.setCurrentIndex(index)
