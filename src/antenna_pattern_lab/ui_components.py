from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .design_system import EmptyState, MetricItem, PanelHeader, StatusBadge, repolish


class CollectionControlWidget(QWidget):
    start_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("CollectionControl")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.section_label = QLabel()
        self.section_label.setObjectName("MetricLabel")
        self.state_label = StatusBadge(role="inactive")
        self.detail_label = QLabel()
        self.detail_label.setObjectName("Metadata")
        self.detail_label.setWordWrap(True)
        self.button = QPushButton()
        self.button.setObjectName("primaryAction")
        self.button.setMinimumHeight(34)
        self.button.clicked.connect(self.start_requested)

        state_row = QHBoxLayout()
        state_row.setContentsMargins(0, 0, 0, 0)
        state_row.addWidget(self.state_label)
        state_row.addStretch()
        layout.addWidget(self.section_label)
        layout.addLayout(state_row)
        layout.addWidget(self.detail_label)
        layout.addWidget(self.button)

        self.setMinimumWidth(270)

    def set_texts(self, section: str, action: str) -> None:
        self.section_label.setText(section)
        self.button.setText(action)

    def set_collection_state(
        self,
        state: str,
        label: str,
        detail: str,
        action: str,
    ) -> None:
        roles = {
            "stopped": "inactive",
            "connecting": "info",
            "running": "success",
            "stopping": "info",
            "failed": "danger",
        }
        self.state_label.set_status_role(roles.get(state, "danger"))
        self.state_label.setProperty("collectionState", state)
        self.state_label.setText(label)
        self.state_label.setAccessibleName(label)
        self.detail_label.setText(detail)
        self.detail_label.setAccessibleName(detail)
        self.button.setText(action)
        self.button.setProperty("collectionState", state)
        self.button.setEnabled(state not in {"connecting", "stopping"})
        self.button.setAccessibleName(action)
        self.button.setAccessibleDescription(detail)
        repolish(self.state_label)
        repolish(self.button)


class OperationalHeader(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("OperationalHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)

        self.context = QWidget()
        self.context_layout = QGridLayout(self.context)
        self.context_layout.setContentsMargins(0, 0, 0, 0)
        self.context_layout.setHorizontalSpacing(8)
        self.context_layout.setVerticalSpacing(6)
        self.context_layout.setColumnStretch(1, 1)
        self.context_layout.setColumnStretch(3, 1)
        self.context_layout.setColumnStretch(5, 1)
        self.context_layout.setColumnStretch(7, 1)
        layout.addWidget(self.context, 1)

        self.collection = CollectionControlWidget()
        layout.addWidget(self.collection)

    def add_context(
        self,
        label: QLabel,
        widget: QWidget,
        row: int,
        column: int,
        column_span: int = 1,
    ) -> None:
        label.setBuddy(widget)
        self.context_layout.addWidget(label, row, column)
        self.context_layout.addWidget(widget, row, column + 1, 1, column_span)


class MetricStrip(QFrame):
    _KEYS = ("reports", "receivers", "quality", "tx", "range", "period")

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("MetricStrip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(20)
        self.items: dict[str, MetricItem] = {}
        for key in self._KEYS:
            item = MetricItem()
            self.items[key] = item
            layout.addWidget(item)
        layout.addStretch()

    def set_metrics(
        self,
        metrics: dict[str, tuple[str, str, str]],
    ) -> None:
        for key, item in self.items.items():
            label, value, tooltip = metrics.get(key, ("", "—", ""))
            item.set_metric(label, value, tooltip)


class AnalysisToolbar(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("AnalysisToolbar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 6, 12, 6)
        self.layout.setSpacing(6)

    def add_control(self, label: QLabel, widget: QWidget, stretch: int = 0) -> None:
        label.setBuddy(widget)
        self.layout.addWidget(label)
        self.layout.addWidget(widget, stretch)

    def add_gap(self) -> None:
        self.layout.addSpacing(6)

    def finish(self) -> None:
        self.layout.addStretch()


class ReportExplorerPanel(QFrame):
    def __init__(self, table: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("ReportExplorer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        self.title = PanelHeader()
        self.count = QLabel("0")
        self.count.setObjectName("MetricValue")
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.count)
        layout.addLayout(header)

        stack_host = QWidget()
        self.stack = QStackedLayout(stack_host)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.table = table
        self.empty = EmptyState()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)
        layout.addWidget(stack_host, 1)

        self.selection_detail = QLabel()
        self.selection_detail.setObjectName("Metadata")
        self.selection_detail.setWordWrap(True)
        self.selection_detail.hide()
        layout.addWidget(self.selection_detail)
        self.setMinimumWidth(430)

    def set_texts(self, title: str, empty_title: str, empty_detail: str) -> None:
        self.title.setText(title)
        self.empty.heading.setText(empty_title)
        self.empty.description.setText(empty_detail)

    def set_report_count(self, count: int) -> None:
        self.count.setText(str(count))
        self.count.setAccessibleName(f"{self.title.text()}: {count}")
        self.stack.setCurrentWidget(self.table if count else self.empty)

    def set_selected_detail(self, text: str) -> None:
        self.selection_detail.setText(text)
        self.selection_detail.setVisible(bool(text))
        self.selection_detail.setAccessibleName(text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not hasattr(self.table, "setColumnHidden"):
            return
        compact = self.width() < 620
        very_compact = self.width() < 500
        self.table.setColumnHidden(4, very_compact)
        self.table.setColumnHidden(5, very_compact)
        self.table.setColumnHidden(6, compact)
        self.table.setColumnHidden(7, compact)
        if not hasattr(self.table, "horizontalHeader"):
            return
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        if hasattr(self.table, "verticalHeader"):
            self.table.verticalHeader().setFixedWidth(36)
        for column in range(8):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )
        if compact:
            fixed_widths = {
                0: 140,
                1: 70,
                2: 72,
                3: 52,
                4: 60,
            }
            for column, width in fixed_widths.items():
                if not self.table.isColumnHidden(column):
                    header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                    header.resizeSection(column, width)
        fill_column = 3 if very_compact else (5 if compact else 7)
        header.setSectionResizeMode(fill_column, QHeaderView.ResizeMode.Stretch)


class SectorQualityPanel(QFrame):
    sector_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("SectorQualityPanel")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(4)

        header = QHBoxLayout()
        self.title = PanelHeader()
        self.summary = QLabel()
        self.summary.setObjectName("Metadata")
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.summary)
        outer.addLayout(header)

        self.cells = QWidget()
        self.grid = QGridLayout(self.cells)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(3)
        self.grid.setVerticalSpacing(3)
        outer.addWidget(self.cells)

        self.detail = QLabel()
        self.detail.setObjectName("Metadata")
        self.detail.setWordWrap(True)
        outer.addWidget(self.detail)
        self._buttons: list[QToolButton] = []
        self._details: list[str] = []

    def set_title(self, title: str) -> None:
        self.title.setText(title)

    def set_sectors(
        self,
        sectors: Iterable,
        width_deg: int,
        quality_labels: dict[str, str],
        summary: str,
        detail_rows: list[str],
    ) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buttons.clear()
        self._details = detail_rows
        sector_list = list(sectors)
        columns = min(36, max(1, len(sector_list)))
        for index, sector in enumerate(sector_list):
            button = QToolButton()
            button.setCheckable(True)
            button.setAutoExclusive(True)
            start = sector.center_deg - width_deg / 2
            end = sector.center_deg + width_deg / 2
            role = sector.quality_label
            button.setText(f"{index:02d}")
            button.setProperty("qualityRole", role)
            detail = detail_rows[index]
            button.setToolTip(detail)
            button.setAccessibleName(
                f"{start % 360:.0f}–{end % 360:.0f}°, "
                f"{quality_labels.get(role, role)}"
            )
            button.clicked.connect(
                lambda checked=False, selected=index: self._select(selected)
            )
            self.grid.addWidget(button, index // columns, index % columns)
            self.grid.setColumnStretch(index % columns, 1)
            self._buttons.append(button)
        self.summary.setText(summary)
        if self._buttons:
            self._buttons[0].setChecked(True)
            self._select(0)
        else:
            self.detail.clear()

    def _select(self, index: int) -> None:
        if not (0 <= index < len(self._details)):
            return
        self.detail.setText(self._details[index])
        self.detail.setAccessibleName(self._details[index])
        self.sector_selected.emit(index)


class IntegrationStatusBar(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("IntegrationStatusBar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 4, 10, 4)
        self.layout.setSpacing(18)
        self.warning = QLabel()
        self.warning.setProperty("statusRole", "inactive")

    def add_indicator(self, indicator: QWidget) -> None:
        indicator.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.layout.addWidget(indicator)

    def finish(self) -> None:
        self.layout.addWidget(self.warning, 1)
