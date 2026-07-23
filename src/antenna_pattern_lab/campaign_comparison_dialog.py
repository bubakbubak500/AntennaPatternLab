from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .analysis import LocatedSpot
from .campaign_comparison import compare_campaign_conditions
from .campaigns import MeasurementCampaign
from .theme import TOKENS, apply_figure_theme, semantic_style


TEXT = {
    "CZE": {
        "title": "Srovnatelnost kampaní",
        "heading": "{a}  ×  {b}",
        "quality": {
            "good": "Podmínky jsou dobře srovnatelné",
            "medium": "Podmínky jsou použitelné s výhradami",
            "low": "Podmínky jsou výrazně nevyvážené",
        },
        "warnings": {
            "no_common_slots": "kampaně nemají společné půlhodinové období",
            "low_time_overlap": "malý překryv slunečních časových oken",
            "block_imbalance": "výrazně rozdílný počet měřicích bloků",
            "day_night_imbalance": "odlišný poměr denních a nočních dat",
            "distance_imbalance": "odlišné zastoupení vzdálenostních vrstev",
            "receiver_change": "malý překryv sítě přijímačů",
            "sparse_a": "kampaň A má méně než tři časové bloky",
            "sparse_b": "kampaň B má méně než tři časové bloky",
        },
        "no_warnings": "Bez zásadního varování podle zvolených pravidel.",
        "missing_a": "Do kampaně A doplňte místní sluneční čas: {slots}",
        "missing_b": "Do kampaně B doplňte místní sluneční čas: {slots}",
        "none_missing": "Obě kampaně mají stejné zastoupené časové sloty.",
        "metrics": [
            "Překryv času",
            "Vyváženost bloků",
            "Shoda den/noc",
            "Shoda vzdáleností",
            "Společné RX",
        ],
        "headers": ["Místní sluneční čas", "Bloky A", "Bloky B", "Stav"],
        "both": "obě",
        "a_only": "jen A",
        "b_only": "jen B",
        "empty": "bez dat",
        "note": (
            "Metriky kontrolují srovnatelnost podmínek, ale samy nedokazují, "
            "že rozdíl výsledku způsobila anténa."
        ),
        "close": "Zavřít",
    },
    "ENG": {
        "title": "Campaign comparability",
        "heading": "{a}  ×  {b}",
        "quality": {
            "good": "Conditions are well comparable",
            "medium": "Conditions are usable with caveats",
            "low": "Conditions are substantially imbalanced",
        },
        "warnings": {
            "no_common_slots": "campaigns have no common half-hour period",
            "low_time_overlap": "low overlap of local-solar time windows",
            "block_imbalance": "substantially different measurement-block counts",
            "day_night_imbalance": "different day/night proportions",
            "distance_imbalance": "different distance-layer proportions",
            "receiver_change": "low overlap of receiver networks",
            "sparse_a": "campaign A has fewer than three time blocks",
            "sparse_b": "campaign B has fewer than three time blocks",
        },
        "no_warnings": "No major warning under the selected rules.",
        "missing_a": "Add local-solar time to campaign A: {slots}",
        "missing_b": "Add local-solar time to campaign B: {slots}",
        "none_missing": "Both campaigns contain the same represented time slots.",
        "metrics": [
            "Time overlap",
            "Block balance",
            "Day/night match",
            "Distance match",
            "Common RX",
        ],
        "headers": ["Local solar time", "A blocks", "B blocks", "Status"],
        "both": "both",
        "a_only": "A only",
        "b_only": "B only",
        "empty": "no data",
        "note": (
            "The metrics check condition comparability; they do not by themselves "
            "prove that an observed difference was caused by the antenna."
        ),
        "close": "Close",
    },
}


class CampaignComparisonDialog(QDialog):
    def __init__(
        self,
        campaign_a: MeasurementCampaign,
        located_a: list[LocatedSpot],
        campaign_b: MeasurementCampaign,
        located_b: list[LocatedSpot],
        language: str,
        parent=None,
    ):
        super().__init__(parent)
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.result = compare_campaign_conditions(located_a, located_b)
        self.setWindowTitle(self.text["title"])
        self.resize(1050, 720)
        layout = QVBoxLayout(self)

        heading = QLabel(
            self.text["heading"].format(a=campaign_a.name, b=campaign_b.name)
        )
        heading.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(heading)
        self.quality = QLabel(self.text["quality"][self.result.quality])
        colors = {"good": TOKENS.success, "medium": TOKENS.warning, "low": TOKENS.danger}
        self.quality.setStyleSheet(
            f"color: {colors[self.result.quality]}; font-weight: 700;"
        )
        layout.addWidget(self.quality)

        warning_text = (
            " · ".join(self.text["warnings"][key] for key in self.result.warnings)
            or self.text["no_warnings"]
        )
        self.warning = QLabel(warning_text)
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)

        recommendations = []
        if self.result.missing_slots_a:
            recommendations.append(
                self.text["missing_a"].format(
                    slots=", ".join(self.result.missing_slots_a)
                )
            )
        if self.result.missing_slots_b:
            recommendations.append(
                self.text["missing_b"].format(
                    slots=", ".join(self.result.missing_slots_b)
                )
            )
        self.recommendation = QLabel(
            " · ".join(recommendations) or self.text["none_missing"]
        )
        self.recommendation.setWordWrap(True)
        self.recommendation.setStyleSheet(semantic_style("info", bold=True))
        layout.addWidget(self.recommendation)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.figure = Figure(figsize=(6, 4), facecolor=TOKENS.panel_background)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.table)
        splitter.setSizes([530, 500])
        layout.addWidget(splitter, 1)

        note = QLabel(self.text["note"])
        note.setWordWrap(True)
        note.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(note)
        close_button = QPushButton(self.text["close"])
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self._draw()
        self._fill_table()

    def _draw(self) -> None:
        result = self.result
        day_match = (
            max(0.0, 100.0 - result.day_share_difference_points)
            if result.day_share_difference_points is not None
            else 0.0
        )
        values = (
            result.time_overlap_percent,
            result.block_balance_percent,
            day_match,
            result.distance_overlap_percent,
            result.receiver_overlap_percent,
        )
        axis = self.figure.add_subplot(111)
        positions = list(range(len(values)))
        colors = [
            TOKENS.success if value >= 70 else TOKENS.warning if value >= 50 else TOKENS.danger
            for value in values
        ]
        axis.barh(positions, values, color=colors)
        axis.set_yticks(positions, labels=self.text["metrics"])
        axis.set_xlim(0, 100)
        axis.set_xlabel("%")
        axis.axvline(60, color=TOKENS.text_secondary, linestyle="--", linewidth=1)
        axis.grid(axis="x", color=TOKENS.chart_grid, alpha=0.7)
        axis.invert_yaxis()
        for position, value in zip(positions, values):
            axis.text(min(value + 2, 96), position, f"{value:.0f}%", va="center")
        apply_figure_theme(self.figure)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self.result.slots))
        for row, slot in enumerate(self.result.slots):
            if slot.blocks_a and slot.blocks_b:
                status, color = self.text["both"], TOKENS.success
            elif slot.blocks_a:
                status, color = self.text["a_only"], TOKENS.warning
            elif slot.blocks_b:
                status, color = self.text["b_only"], TOKENS.warning
            else:
                status, color = self.text["empty"], TOKENS.text_secondary
            values = (slot.label, str(slot.blocks_a), str(slot.blocks_b), status)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 3:
                    item.setForeground(QColor(color))
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
