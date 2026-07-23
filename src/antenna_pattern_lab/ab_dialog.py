from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .analysis import ab_sector_profile, compare_profile_spots, recommend_ab_measurement
from .storage import SpotRepository

TEXT = {
    "CZE": {
        "title": "A/B porovnání antén",
        "profile_a": "Profil A",
        "profile_b": "Profil B",
        "band": "Pásmo",
        "mode": "Mód",
        "compare": "Porovnat",
        "close": "Zavřít",
        "note": "Párují se nejbližší reporty stejného RX do 30 minut. Každý přijímač má ve výsledku stejnou váhu bez ohledu na počet reportů. 95% bootstrap interval nekoriguje změny propagace ani výkonu.",
        "need_profiles": "Pro A/B porovnání vytvoř alespoň dva profily.",
        "no_pairs": "Nebyly nalezeny použitelné páry stejného přijímače.",
        "summary": "Medián B − A: {delta:+.1f} dB · {pairs} párů · {receivers} RX",
        "summary_ci": " · 95% CI {low:+.1f} až {high:+.1f} dB",
        "headers": ["RX", "Azimut", "Odstup min", "A SNR", "B SNR", "B − A"],
        "direction_tab": "Směry",
        "pairs_tab": "Spárované reporty",
        "sector_headers": ["Sektor", "Párů", "RX", "Medián", "CI dolní", "CI horní"],
        "sector_plot": "A/B rozdíl podle azimutu (B − A)",
        "recommend_ready": "Základní cíl dat splněn: alespoň {pairs} párů a {receivers} různých RX.",
        "recommend_more": "Doporučení: získat ještě {pairs} párů a {receivers} nových RX{time}.",
        "recommend_time": " · při současné rychlosti přibližně {hours:.1f} h",
    },
    "ENG": {
        "title": "A/B antenna comparison",
        "profile_a": "Profile A",
        "profile_b": "Profile B",
        "band": "Band",
        "mode": "Mode",
        "compare": "Compare",
        "close": "Close",
        "note": "Nearest reports from the same RX within 30 minutes are paired. Every receiver has equal result weight regardless of report count. The 95% bootstrap interval does not correct propagation or power changes.",
        "need_profiles": "Create at least two profiles for A/B comparison.",
        "no_pairs": "No usable same-receiver pairs were found.",
        "summary": "Median B − A: {delta:+.1f} dB · {pairs} pairs · {receivers} RX",
        "summary_ci": " · 95% CI {low:+.1f} to {high:+.1f} dB",
        "headers": ["RX", "Bearing", "Gap min", "A SNR", "B SNR", "B − A"],
        "direction_tab": "Directions",
        "pairs_tab": "Paired reports",
        "sector_headers": ["Sector", "Pairs", "RX", "Median", "CI low", "CI high"],
        "sector_plot": "A/B difference by bearing (B − A)",
        "recommend_ready": "Basic data target reached: at least {pairs} pairs and {receivers} different receivers.",
        "recommend_more": "Recommendation: collect {pairs} more pairs and {receivers} new receivers{time}.",
        "recommend_time": " · approximately {hours:.1f} h at the current rate",
    },
}


class AbComparisonDialog(QDialog):
    def __init__(
        self,
        repository: SpotRepository,
        language: str,
        tx_grid: str,
        initial_band: str,
        initial_mode: str = "FT8",
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.tx_grid = tx_grid
        self.setWindowTitle(self.text["title"])
        self.resize(900, 650)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.profile_a = QComboBox()
        self.profile_b = QComboBox()
        profiles = repository.list_antenna_profiles()
        for profile in profiles:
            self.profile_a.addItem(profile.name, profile.id)
            self.profile_b.addItem(profile.name, profile.id)
        if len(profiles) > 1:
            self.profile_b.setCurrentIndex(1)
        self.band = QComboBox()
        self.band.addItems(["20m", "40m", "15m", "10m", "80m", "30m", "17m", "12m", "+"])
        self.band.setCurrentText(initial_band)
        self.mode = QComboBox()
        self.mode.addItems(["FT8", "WSPR"])
        self.mode.setCurrentText(initial_mode)
        form.addRow(self.text["profile_a"], self.profile_a)
        form.addRow(self.text["profile_b"], self.profile_b)
        form.addRow(self.text["band"], self.band)
        form.addRow(self.text["mode"], self.mode)
        layout.addLayout(form)
        note = QLabel(self.text["note"])
        note.setWordWrap(True)
        note.setStyleSheet("color: #9a6700;")
        layout.addWidget(note)
        self.summary = QLabel()
        self.summary.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self.summary)
        self.recommendation = QLabel()
        self.recommendation.setWordWrap(True)
        self.recommendation.setStyleSheet("color: #0969da;")
        layout.addWidget(self.recommendation)
        tabs = QTabWidget()
        direction_page = QWidget()
        direction_layout = QVBoxLayout(direction_page)
        self.figure = Figure(figsize=(7, 3), facecolor="#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figure)
        direction_layout.addWidget(self.canvas, 1)
        self.sector_table = QTableWidget(0, 6)
        self.sector_table.setHorizontalHeaderLabels(self.text["sector_headers"])
        self.sector_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sector_table.horizontalHeader().setStretchLastSection(True)
        direction_layout.addWidget(self.sector_table, 1)
        tabs.addTab(direction_page, self.text["direction_tab"])
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.table, self.text["pairs_tab"])
        layout.addWidget(tabs, 1)
        buttons = QHBoxLayout()
        compare_button = QPushButton(self.text["compare"])
        close_button = QPushButton(self.text["close"])
        buttons.addWidget(compare_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        compare_button.clicked.connect(self.compare)
        close_button.clicked.connect(self.accept)
        if len(profiles) < 2:
            compare_button.setEnabled(False)
            self.summary.setText(self.text["need_profiles"])

    def compare(self) -> None:
        profile_a_id = self.profile_a.currentData()
        profile_b_id = self.profile_b.currentData()
        if profile_a_id is None or profile_b_id is None or profile_a_id == profile_b_id:
            self.summary.setText(self.text["need_profiles"])
            return
        band = self.band.currentText()
        mode = self.mode.currentText()
        result = compare_profile_spots(
            self.repository.list_spots_for_profile(profile_a_id, band=band, mode=mode),
            self.repository.list_spots_for_profile(profile_b_id, band=band, mode=mode),
            self.tx_grid,
        )
        recommendation = recommend_ab_measurement(result)
        if recommendation.ready:
            self.recommendation.setText(
                self.text["recommend_ready"].format(
                    pairs=recommendation.target_pairs,
                    receivers=recommendation.target_receivers,
                )
            )
        else:
            time_text = ""
            if recommendation.estimated_additional_hours is not None:
                time_text = self.text["recommend_time"].format(
                    hours=recommendation.estimated_additional_hours
                )
            self.recommendation.setText(
                self.text["recommend_more"].format(
                    pairs=recommendation.additional_pairs,
                    receivers=recommendation.additional_receivers,
                    time=time_text,
                )
            )
        sectors = ab_sector_profile(result.pairs, 45)
        populated_sectors = [sector for sector in sectors if sector.count]
        self.sector_table.setRowCount(len(populated_sectors))
        for row, sector in enumerate(populated_sectors):
            start = (sector.center_deg - 22.5) % 360
            end = (sector.center_deg + 22.5) % 360
            values = (
                f"{start:.0f}–{end:.0f}°",
                str(sector.count),
                str(sector.unique_receivers),
                f"{sector.median_delta_db:+.1f}" if sector.median_delta_db is not None else "—",
                f"{sector.confidence_low_db:+.1f}" if sector.confidence_low_db is not None else "—",
                f"{sector.confidence_high_db:+.1f}" if sector.confidence_high_db is not None else "—",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.sector_table.setItem(row, column, item)
        self.sector_table.resizeColumnsToContents()
        self._draw_sectors(sectors)
        self.table.setRowCount(len(result.pairs))
        for row, pair in enumerate(result.pairs):
            values = (
                pair.receiver_call,
                f"{pair.bearing_deg:.0f}°",
                f"{pair.time_gap_seconds / 60:.1f}",
                f"{pair.snr_a_db:+d}",
                f"{pair.snr_b_db:+d}",
                f"{pair.delta_db:+d}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        if result.median_delta_db is None:
            self.summary.setText(self.text["no_pairs"])
        else:
            summary = self.text["summary"].format(
                delta=result.median_delta_db,
                pairs=len(result.pairs),
                receivers=result.unique_receivers,
            )
            if result.confidence_low_db is not None:
                summary += self.text["summary_ci"].format(
                    low=result.confidence_low_db,
                    high=result.confidence_high_db,
                )
            self.summary.setText(summary)

    def _draw_sectors(self, sectors) -> None:
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_facecolor("#ffffff")
        used = [sector for sector in sectors if sector.count]
        x = [sector.center_deg for sector in used]
        y = [sector.median_delta_db for sector in used]
        colors = ["#1a7f37" if value >= 0 else "#b42318" for value in y]
        errors = []
        for sector, value in zip(used, y):
            if sector.confidence_low_db is None:
                errors.append((0.0, 0.0))
            else:
                errors.append(
                    (value - sector.confidence_low_db, sector.confidence_high_db - value)
                )
        axis.bar(x, y, width=38, color=colors, alpha=0.85)
        if errors:
            axis.errorbar(
                x,
                y,
                yerr=[[item[0] for item in errors], [item[1] for item in errors]],
                fmt="none",
                ecolor="#57606a",
                capsize=3,
            )
        axis.axhline(0, color="#8c959f", linewidth=1)
        axis.set_xlim(0, 360)
        axis.set_xticks(range(0, 361, 45))
        axis.set_xlabel("Azimut / Bearing (°)", color="#1f2328")
        axis.set_ylabel("B − A (dB)", color="#1f2328")
        axis.set_title(self.text["sector_plot"], color="#1f2328")
        axis.tick_params(colors="#57606a")
        axis.grid(axis="y", color="#d0d7de", alpha=0.8)
        self.figure.tight_layout()
        self.canvas.draw_idle()
