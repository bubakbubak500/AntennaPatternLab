from __future__ import annotations

from math import pi

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .analysis import LocatedSpot
from .campaigns import MeasurementCampaign
from .coverage import (
    DISTANCE_BANDS,
    analyze_angular_coverage,
    analyze_coverage_matrix,
    priority_matrix_cells,
    priority_sectors,
)
from .measurement_planner import recommend_measurement_window
from .theme import TOKENS, apply_figure_theme, semantic_style


TEXT = {
    "CZE": {
        "title": "Pokrytí měření",
        "chart": "Úplnost podkladů podle azimutu",
        "angular_tab": "Úhlové pokrytí",
        "matrix_tab": "Vzdálenost a den/noc",
        "planner_tab": "Další měřicí okno",
        "planner_title": "Vhodnost půlhodin podle místního slunečního času TX",
        "planner_summary": (
            "Doporučení: {solar} místního slunečního času · nejbližší začátek "
            "{utc} UTC · délka {duration} min · jistota {confidence}"
        ),
        "planner_targets": "Cíle sběru: {bearings} · vzdálenosti {distances}.",
        "planner_rate": (
            "Dosavadní rychlost: {rate} spotů/h · odhad k číselným cílům "
            "(spoty a čas): {hours}."
        ),
        "planner_no_rate": (
            "Dosavadní rychlost zatím nelze odhadnout; doporučení času má "
            "omezenou datovou oporu."
        ),
        "planner_note": (
            "Skóre kombinuje chybějící směry a vzdálenosti s historickou "
            "dostupností RX. Nejde o předpověď aktuální propagace."
        ),
        "planner_headers": [
            "Sluneční čas",
            "Skóre",
            "Spoty",
            "RX",
            "Chybějící priority",
            "Mezera vzdáleností",
        ],
        "confidence": {"low": "nízká", "medium": "střední", "high": "vysoká"},
        "hours_value": "{value:.1f} h",
        "hours_done": "číselné cíle splněny",
        "matrix_chart": "Pokrytí podle azimutu a vzdálenosti — {period}",
        "day": "den",
        "night": "noc",
        "distance": {
            "near": "0–1 000 km",
            "mid": "1 000–3 000 km",
            "dx": "3 000–8 000 km",
            "ultra": "8 000+ km",
        },
        "matrix_priority": "Nejslabší kombinace pro další sběr: {targets}.",
        "matrix_target": "{bearing:.0f}° · {distance} · {period}",
        "matrix_cell_tip": "{percent:.0f}% · {reports} spotů · {receivers} RX · {blocks} bloků",
        "summary": (
            "{good}/{total} sektorů má dobrou datovou oporu · "
            "{empty} sektorů je bez spotu · {context}"
        ),
        "priority": "Nejbližší měření doplňte směrem: {targets}.",
        "target": "{bearing:.0f}° ({time})",
        "all_times": "všechny UTC časy zastoupeny",
        "missing_times": "chybí {windows} UTC",
        "headers": [
            "Sektor",
            "Úplnost",
            "Spoty",
            "RX",
            "30min okna",
            "95% CI",
            "Chybějící 6h okna UTC",
            "Kvalita",
        ],
        "quality": {
            "none": "bez dat",
            "low": "nízká",
            "medium": "střední",
            "high": "dobrá",
        },
        "close": "Zavřít",
        "note": (
            "Úplnost je provozní skóre pokrytí vzorky, přijímači, časovými okny "
            "a šířkou intervalu; není to odhad zisku antény."
        ),
    },
    "ENG": {
        "title": "Measurement coverage",
        "chart": "Evidence completeness by bearing",
        "angular_tab": "Angular coverage",
        "matrix_tab": "Distance and day/night",
        "planner_tab": "Next measurement window",
        "planner_title": "Half-hour suitability by TX local solar time",
        "planner_summary": (
            "Recommendation: {solar} local solar time · nearest start "
            "{utc} UTC · duration {duration} min · {confidence} confidence"
        ),
        "planner_targets": "Collection targets: {bearings} · distances {distances}.",
        "planner_rate": (
            "Observed rate: {rate} spots/h · estimate to numeric goals "
            "(spots and time): {hours}."
        ),
        "planner_no_rate": (
            "The collection rate cannot be estimated yet; the time recommendation "
            "has limited data support."
        ),
        "planner_note": (
            "The score combines missing bearings and distances with historical "
            "RX availability. It is not a current propagation forecast."
        ),
        "planner_headers": [
            "Solar time",
            "Score",
            "Spots",
            "RX",
            "Missing priorities",
            "Distance gap",
        ],
        "confidence": {"low": "low", "medium": "medium", "high": "high"},
        "hours_value": "{value:.1f} h",
        "hours_done": "numeric goals met",
        "matrix_chart": "Coverage by bearing and distance — {period}",
        "day": "day",
        "night": "night",
        "distance": {
            "near": "0–1,000 km",
            "mid": "1,000–3,000 km",
            "dx": "3,000–8,000 km",
            "ultra": "8,000+ km",
        },
        "matrix_priority": "Weakest combinations for the next collection: {targets}.",
        "matrix_target": "{bearing:.0f}° · {distance} · {period}",
        "matrix_cell_tip": "{percent:.0f}% · {reports} spots · {receivers} RX · {blocks} blocks",
        "summary": (
            "{good}/{total} sectors have good data support · "
            "{empty} sectors have no spots · {context}"
        ),
        "priority": "Prioritize the next measurement toward: {targets}.",
        "target": "{bearing:.0f}° ({time})",
        "all_times": "all UTC periods represented",
        "missing_times": "missing {windows} UTC",
        "headers": [
            "Sector",
            "Completeness",
            "Spots",
            "RX",
            "30-min windows",
            "95% CI",
            "Missing 6h UTC windows",
            "Quality",
        ],
        "quality": {
            "none": "no data",
            "low": "low",
            "medium": "medium",
            "high": "good",
        },
        "close": "Close",
        "note": (
            "Completeness is an operational score based on samples, receivers, "
            "time windows and interval width; it is not an antenna-gain estimate."
        ),
    },
}


class CoverageDialog(QDialog):
    def __init__(
        self,
        located: list[LocatedSpot],
        language: str,
        context: str,
        parent=None,
        campaign: MeasurementCampaign | None = None,
    ):
        super().__init__(parent)
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.sectors = analyze_angular_coverage(located, 30)
        self.matrix_cells = analyze_coverage_matrix(located, 30)
        self.setWindowTitle(self.text["title"])
        self.resize(1100, 760)
        layout = QVBoxLayout(self)

        good = sum(sector.quality_label == "high" for sector in self.sectors)
        empty = sum(sector.report_count == 0 for sector in self.sectors)
        self.summary = QLabel(
            self.text["summary"].format(
                good=good,
                total=len(self.sectors),
                empty=empty,
                context=context,
            )
        )
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        priorities = priority_sectors(self.sectors)
        targets = []
        for sector in priorities:
            time_text = (
                self.text["missing_times"].format(
                    windows=", ".join(sector.missing_utc_windows)
                )
                if sector.missing_utc_windows
                else self.text["all_times"]
            )
            targets.append(
                self.text["target"].format(
                    bearing=sector.center_deg,
                    time=time_text,
                )
            )
        self.priority = QLabel(
            self.text["priority"].format(targets=" · ".join(targets))
        )
        self.priority.setWordWrap(True)
        self.priority.setStyleSheet(semantic_style("info", bold=True))
        layout.addWidget(self.priority)

        self.tabs = QTabWidget()
        self.angular_tab = QWidget()
        angular_layout = QVBoxLayout(self.angular_tab)
        self.figure = Figure(figsize=(7, 5), facecolor=TOKENS.panel_background)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.table = QTableWidget(0, len(self.text["headers"]))
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.table)
        splitter.setSizes([560, 520])
        angular_layout.addWidget(splitter)
        self.tabs.addTab(self.angular_tab, self.text["angular_tab"])

        self.matrix_tab = QWidget()
        matrix_layout = QVBoxLayout(self.matrix_tab)
        matrix_priorities = priority_matrix_cells(self.matrix_cells)
        matrix_targets = [
            self.text["matrix_target"].format(
                bearing=cell.bearing_center_deg,
                distance=self.text["distance"][cell.distance_code],
                period=self.text[cell.solar_period],
            )
            for cell in matrix_priorities
        ]
        self.matrix_priority = QLabel(
            self.text["matrix_priority"].format(
                targets=" · ".join(matrix_targets)
            )
        )
        self.matrix_priority.setWordWrap(True)
        self.matrix_priority.setStyleSheet(semantic_style("info", bold=True))
        matrix_layout.addWidget(self.matrix_priority)
        matrix_splitter = QSplitter(Qt.Orientation.Vertical)
        self.matrix_figure = Figure(figsize=(9, 5), facecolor=TOKENS.panel_background)
        self.matrix_canvas = FigureCanvasQTAgg(self.matrix_figure)
        self.matrix_table = QTableWidget(0, 13)
        self.matrix_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.matrix_table.setHorizontalHeaderLabels(
            [""] + [f"{center}°" for center in range(15, 360, 30)]
        )
        matrix_splitter.addWidget(self.matrix_canvas)
        matrix_splitter.addWidget(self.matrix_table)
        matrix_splitter.setSizes([430, 230])
        matrix_layout.addWidget(matrix_splitter, 1)
        self.tabs.addTab(self.matrix_tab, self.text["matrix_tab"])

        self.planner_recommendation = None
        self.planner_tab = None
        self.planner_figure = None
        self.planner_table = None
        if campaign is not None:
            self._build_planner_tab(located, campaign)
        layout.addWidget(self.tabs, 1)

        note = QLabel(self.text["note"])
        note.setWordWrap(True)
        note.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(note)
        close_button = QPushButton(self.text["close"])
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self._draw()
        self._fill_table()
        self._draw_matrix()
        self._fill_matrix_table()

    def _build_planner_tab(
        self,
        located: list[LocatedSpot],
        campaign: MeasurementCampaign,
    ) -> None:
        result = recommend_measurement_window(campaign, located)
        self.planner_recommendation = result
        self.planner_tab = QWidget()
        planner_layout = QVBoxLayout(self.planner_tab)

        summary = QLabel(
            self.text["planner_summary"].format(
                solar=result.recommended.solar_label,
                utc=result.next_start_utc.strftime("%Y-%m-%d %H:%M"),
                duration=result.suggested_duration_minutes,
                confidence=self.text["confidence"][result.confidence],
            )
        )
        summary.setWordWrap(True)
        summary.setStyleSheet(semantic_style("info", bold=True))
        planner_layout.addWidget(summary)

        bearings = ", ".join(
            f"{bearing:.0f}°" for bearing in result.target_bearings
        ) or "—"
        distances = ", ".join(
            self.text["distance"][code] for code in result.target_distance_codes
        ) or "—"
        targets = QLabel(
            self.text["planner_targets"].format(
                bearings=bearings,
                distances=distances,
            )
        )
        targets.setWordWrap(True)
        planner_layout.addWidget(targets)

        if result.spot_rate_per_hour is None:
            rate_text = self.text["planner_no_rate"]
        else:
            hours = (
                self.text["hours_done"]
                if result.estimated_hours_to_numeric_goal == 0
                else self.text["hours_value"].format(
                    value=result.estimated_hours_to_numeric_goal or 0
                )
            )
            rate_text = self.text["planner_rate"].format(
                rate=f"{result.spot_rate_per_hour:.1f}",
                hours=hours,
            )
        rate = QLabel(rate_text)
        rate.setWordWrap(True)
        planner_layout.addWidget(rate)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.planner_figure = Figure(figsize=(9, 4), facecolor=TOKENS.panel_background)
        planner_canvas = FigureCanvasQTAgg(self.planner_figure)
        self.planner_table = QTableWidget(
            0, len(self.text["planner_headers"])
        )
        self.planner_table.setHorizontalHeaderLabels(
            self.text["planner_headers"]
        )
        self.planner_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.planner_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        splitter.addWidget(planner_canvas)
        splitter.addWidget(self.planner_table)
        splitter.setSizes([360, 250])
        planner_layout.addWidget(splitter, 1)

        candidates = sorted(result.candidates, key=lambda item: item.solar_slot)
        axis = self.planner_figure.add_subplot(111)
        colors = [
            TOKENS.success
            if item.solar_slot == result.recommended.solar_slot
            else TOKENS.info
            for item in candidates
        ]
        axis.bar(
            [item.solar_slot / 2 for item in candidates],
            [item.score_percent for item in candidates],
            width=0.43,
            color=colors,
        )
        axis.set_xlim(-0.5, 24)
        axis.set_ylim(0, 100)
        axis.set_xticks(range(0, 25, 3))
        axis.set_ylabel("%")
        axis.set_xlabel("Local solar time" if self.text is TEXT["ENG"] else "Místní sluneční čas")
        axis.set_title(self.text["planner_title"], fontsize=11)
        axis.grid(axis="y", alpha=0.25)
        apply_figure_theme(self.planner_figure)
        self.planner_figure.tight_layout()
        planner_canvas.draw_idle()

        self.planner_table.setRowCount(len(candidates))
        for row, item in enumerate(candidates):
            values = (
                item.solar_label,
                f"{item.score_percent:.0f}%",
                str(item.report_count),
                str(item.unique_receivers),
                str(item.missing_priority_sectors),
                f"{item.distance_gap_percent:.0f}%",
            )
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if column:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.planner_table.setItem(row, column, cell)
        self.planner_table.resizeColumnsToContents()
        self.planner_table.horizontalHeader().setStretchLastSection(True)

        note = QLabel(self.text["planner_note"])
        note.setWordWrap(True)
        note.setStyleSheet(semantic_style("text_secondary"))
        planner_layout.addWidget(note)
        self.tabs.addTab(self.planner_tab, self.text["planner_tab"])

    def _draw(self) -> None:
        axis = self.figure.add_subplot(111, projection="polar")
        axis.set_facecolor(TOKENS.panel_background)
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        theta = [sector.center_deg * pi / 180 for sector in self.sectors]
        width = 28 * pi / 180
        axis.bar(
            theta,
            [100] * len(self.sectors),
            width=width,
            color=TOKENS.surface_3,
            edgecolor=TOKENS.chart_grid,
            linewidth=0.6,
            zorder=1,
        )
        colors = {
            "none": TOKENS.text_muted,
            "low": TOKENS.danger,
            "medium": TOKENS.warning,
            "high": TOKENS.success,
        }
        axis.bar(
            theta,
            [sector.completeness_percent for sector in self.sectors],
            width=width,
            color=[colors[sector.quality_label] for sector in self.sectors],
            alpha=0.88,
            zorder=2,
        )
        axis.set_rlim(0, 100)
        axis.set_yticks((25, 50, 75, 100), labels=("25%", "50%", "75%", "100%"))
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(color=TOKENS.chart_grid, alpha=0.75)
        axis.set_title(self.text["chart"], color=TOKENS.text_primary, pad=18)
        apply_figure_theme(self.figure)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self.sectors))
        for row, sector in enumerate(self.sectors):
            confidence = (
                "—"
                if sector.confidence_low_db is None
                else f"{sector.confidence_low_db:+.1f}…"
                f"{sector.confidence_high_db:+.1f} dB"
            )
            values = (
                f"{sector.start_deg:.0f}–{sector.end_deg:.0f}°",
                f"{sector.completeness_percent:.0f}%",
                str(sector.report_count),
                str(sector.unique_receivers),
                str(sector.time_block_count),
                confidence,
                ", ".join(sector.missing_utc_windows) or "—",
                self.text["quality"][sector.quality_label],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2, 3, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()

    def _draw_matrix(self) -> None:
        self.matrix_figure.clear()
        images = []
        for index, period in enumerate(("day", "night"), start=1):
            axis = self.matrix_figure.add_subplot(2, 1, index)
            values = []
            for distance_code, _minimum, _maximum in DISTANCE_BANDS:
                values.append(
                    [
                        next(
                            cell.completeness_percent
                            for cell in self.matrix_cells
                            if cell.solar_period == period
                            and cell.distance_code == distance_code
                            and cell.bearing_center_deg == center
                        )
                        for center in range(15, 360, 30)
                    ]
                )
            image = axis.imshow(
                values,
                vmin=0,
                vmax=100,
                cmap="RdYlGn",
                aspect="auto",
                interpolation="nearest",
            )
            images.append(image)
            axis.set_title(
                self.text["matrix_chart"].format(period=self.text[period]),
                fontsize=10,
            )
            axis.set_xticks(
                range(12),
                labels=[f"{center}°" for center in range(15, 360, 30)],
            )
            axis.set_yticks(
                range(4),
                labels=[
                    self.text["distance"][code]
                    for code, _minimum, _maximum in DISTANCE_BANDS
                ],
            )
            axis.tick_params(labelsize=8)
            for row in range(4):
                for column in range(12):
                    value = values[row][column]
                    axis.text(
                        column,
                        row,
                        f"{value:.0f}",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color=TOKENS.text_inverse if value < 35 else TOKENS.text_primary,
                    )
        colorbar_axis = self.matrix_figure.add_axes((0.90, 0.18, 0.018, 0.64))
        self.matrix_figure.colorbar(
            images[-1],
            cax=colorbar_axis,
            label="%",
        )
        self.matrix_figure.subplots_adjust(
            left=0.13,
            right=0.87,
            bottom=0.10,
            top=0.92,
            hspace=0.55,
        )
        apply_figure_theme(self.matrix_figure)
        self.matrix_canvas.draw_idle()

    def _fill_matrix_table(self) -> None:
        rows = [
            (period, distance_code)
            for period in ("day", "night")
            for distance_code, _minimum, _maximum in DISTANCE_BANDS
        ]
        self.matrix_table.setRowCount(len(rows))
        for row, (period, distance_code) in enumerate(rows):
            label = (
                f"{self.text[period]} · "
                f"{self.text['distance'][distance_code]}"
            )
            self.matrix_table.setItem(row, 0, QTableWidgetItem(label))
            for column, center in enumerate(range(15, 360, 30), start=1):
                cell = next(
                    item
                    for item in self.matrix_cells
                    if item.solar_period == period
                    and item.distance_code == distance_code
                    and item.bearing_center_deg == center
                )
                item = QTableWidgetItem(f"{cell.completeness_percent:.0f}%")
                item.setToolTip(
                    self.text["matrix_cell_tip"].format(
                        percent=cell.completeness_percent,
                        reports=cell.report_count,
                        receivers=cell.unique_receivers,
                        blocks=cell.time_block_count,
                    )
                )
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.matrix_table.setItem(row, column, item)
        self.matrix_table.resizeColumnsToContents()
