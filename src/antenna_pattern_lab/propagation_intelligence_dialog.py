from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .analysis import locate_spot
from .nec import NecBaseline, NecPattern, parse_nec_baseline
from .propagation import PropagationSnapshot
from .propagation_intelligence import (
    LayerComparison,
    PropagationFeatures,
    compare_layers,
    derive_features,
    solar_elevation,
    spatial_grid_from_geojson,
)
from .storage import SpotRepository
from .theme import TOKENS, apply_figure_theme
from .ui_formatting import TechnicalTableItem


TEXT = {
    "CZE": {
        "title": "Propagation Intelligence",
        "intro": (
            "Trasa a tři oddělené vrstvy: teoretická reference NEC, skutečně "
            "pozorované pokrytí a experimentální propagation-normalized odhad. "
            "Žádná vrstva není zárukou spojení ani automatickým určením příčiny."
        ),
        "campaign": "Kampaň:",
        "target": "Cílový RX:",
        "time": "Čas kampaně:",
        "play": "Přehrát",
        "pause": "Pozastavit",
        "route": "Trasa a podmínky",
        "layers": "Tři vrstvy",
        "provenance": "Provenance",
        "import_nec": "Přidat NEC baseline…",
        "save": "Uložit analytický podklad",
        "empty": "Vyberte kampaň s reporty.",
        "no_snapshot": "Pro tento čas není uložený snapshot podmínek.",
        "effect": "Co právě trasu ovlivňuje",
        "missing": "Která data chybějí",
        "caution": (
            "Reziduum je pouze podezření k ověření. Neurčuje automaticky terén, "
            "budovu, common-mode proud, orientaci ani model půdy; ověřte je "
            "kontrolovaným A/B experimentem."
        ),
        "saved": "Analytický podklad uložen · {hash}",
        "cv": "Bloková validace: {folds} bloků · test MAE {mae}",
        "close": "Zavřít",
    },
    "ENG": {
        "title": "Propagation Intelligence",
        "intro": (
            "Route context and three separate layers: a theoretical NEC reference, "
            "observed coverage, and an experimental propagation-normalized estimate. "
            "No layer is a link guarantee or an automatic cause finding."
        ),
        "campaign": "Campaign:",
        "target": "Target RX:",
        "time": "Campaign time:",
        "play": "Play",
        "pause": "Pause",
        "route": "Route and conditions",
        "layers": "Three layers",
        "provenance": "Provenance",
        "import_nec": "Add NEC baseline…",
        "save": "Save analytical basis",
        "empty": "Select a campaign containing reports.",
        "no_snapshot": "No stored conditions snapshot covers this time.",
        "effect": "What affects the route now",
        "missing": "Which data are missing",
        "caution": (
            "A residual is only a suspicion to verify. It does not automatically "
            "identify terrain, a building, common-mode current, orientation, or a "
            "ground-model error; verify it with a controlled A/B experiment."
        ),
        "saved": "Analytical basis saved · {hash}",
        "cv": "Blocked validation: {folds} blocks · test MAE {mae}",
        "close": "Close",
    },
}


class PropagationIntelligenceDialog(QDialog):
    def __init__(
        self,
        repository: SpotRepository,
        language: str = "CZE",
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.language = language if language in TEXT else "ENG"
        self.text = TEXT[self.language]
        self.features: PropagationFeatures | None = None
        self.comparison: LayerComparison | None = None
        self.nec_patterns: list[tuple[str, NecBaseline]] = []
        self._spots = []
        self._located = []
        self._timeline: list[datetime] = []
        self._snapshots: list[PropagationSnapshot] = []
        self._tx_times: list[datetime] = []
        self._timer = QTimer(self)
        self._timer.setInterval(700)
        self._timer.timeout.connect(self._advance_time)

        self.setWindowTitle(self.text["title"])
        self.resize(1280, 820)
        self.setMinimumSize(1000, 680)

        root = QVBoxLayout(self)
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        root.addWidget(intro)

        controls = QHBoxLayout()
        self.campaign = QComboBox()
        self.campaign.setAccessibleName(self.text["campaign"])
        self.campaign.currentIndexChanged.connect(self._campaign_changed)
        self.target = QComboBox()
        self.target.setAccessibleName(self.text["target"])
        self.target.currentIndexChanged.connect(self.refresh)
        self.time_label = QLabel("—")
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimumWidth(220)
        self.time_slider.valueChanged.connect(self._time_changed)
        self.play_button = QPushButton(self.text["play"])
        self.play_button.clicked.connect(self._toggle_playback)
        for label, widget in (
            (self.text["campaign"], self.campaign),
            (self.text["target"], self.target),
        ):
            controls.addWidget(QLabel(label))
            controls.addWidget(widget)
        controls.addWidget(QLabel(self.text["time"]))
        controls.addWidget(self.time_slider, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(self.play_button)
        root.addLayout(controls)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_route_tab(), self.text["route"])
        self.tabs.addTab(self._build_layers_tab(), self.text["layers"])
        self.tabs.addTab(self._build_provenance_tab(), self.text["provenance"])
        root.addWidget(self.tabs, 1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(
            self.text["close"]
        )
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._load_campaigns()

    def _build_route_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.route_figure = Figure(figsize=(7.5, 4.5))
        self.route_canvas = FigureCanvasQTAgg(self.route_figure)
        self.route_canvas.setAccessibleName("Great-circle route, daylight and grayline")
        splitter.addWidget(self.route_canvas)
        facts = QWidget()
        fact_layout = QVBoxLayout(facts)
        self.route_summary = QLabel("")
        self.route_summary.setWordWrap(True)
        self.route_summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.effect_label = QLabel("")
        self.effect_label.setWordWrap(True)
        self.missing_label = QLabel("")
        self.missing_label.setWordWrap(True)
        fact_layout.addWidget(self.route_summary)
        fact_layout.addWidget(self.effect_label)
        fact_layout.addWidget(self.missing_label)
        fact_layout.addStretch(1)
        splitter.addWidget(facts)
        splitter.setSizes([780, 360])
        layout.addWidget(splitter)
        return page

    def _build_layers_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        row = QHBoxLayout()
        self.import_nec_button = QPushButton(self.text["import_nec"])
        self.import_nec_button.clicked.connect(self._import_nec)
        self.nec_choice = QComboBox()
        self.nec_choice.addItem("— NEC —", None)
        self.nec_choice.currentIndexChanged.connect(self.refresh)
        row.addWidget(self.import_nec_button)
        row.addWidget(self.nec_choice)
        row.addStretch(1)
        layout.addLayout(row)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.layer_figure = Figure(figsize=(8, 4.5))
        self.layer_canvas = FigureCanvasQTAgg(self.layer_figure)
        self.layer_canvas.setAccessibleName(
            "Separate NEC, observed coverage and propagation-normalized layers"
        )
        splitter.addWidget(self.layer_canvas)
        self.layer_table = QTableWidget(0, 12)
        self.layer_table.setHorizontalHeaderLabels(
            [
                "Az",
                "Reports",
                "RX",
                "Best SNR",
                "Median SNR",
                "Max km",
                "Density",
                "Quality",
                "Raw CI",
                "Normalized",
                "NEC",
                "Difference",
            ]
        )
        self.layer_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.layer_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.layer_table.setSortingEnabled(True)
        splitter.addWidget(self.layer_table)
        splitter.setSizes([430, 230])
        layout.addWidget(splitter, 1)
        self.cv_label = QLabel("")
        self.caution = QLabel(self.text["caution"])
        self.caution.setWordWrap(True)
        layout.addWidget(self.cv_label)
        layout.addWidget(self.caution)
        return page

    def _build_provenance_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.provenance_text = QTextEdit()
        self.provenance_text.setReadOnly(True)
        self.provenance_text.setAccessibleName("Versioned analytical provenance")
        layout.addWidget(self.provenance_text, 1)
        self.save_button = QPushButton(self.text["save"])
        self.save_button.clicked.connect(self._save_features)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)
        return page

    def _load_campaigns(self) -> None:
        self.campaign.blockSignals(True)
        self.campaign.clear()
        for campaign in self.repository.list_campaigns():
            self.campaign.addItem(
                f"{campaign.name} · {campaign.band} {campaign.mode}",
                campaign.id,
            )
        self.campaign.blockSignals(False)
        self._campaign_changed()

    def _campaign_changed(self) -> None:
        campaign_id = self.campaign.currentData()
        self._spots = (
            self.repository.list_spots(campaign_id=int(campaign_id), limit=20_000)
            if campaign_id is not None
            else []
        )
        campaign = (
            self.repository.get_campaign(int(campaign_id))
            if campaign_id is not None
            else None
        )
        self._located = [
            item
            for spot in self._spots
            if (item := locate_spot(spot, campaign.tx_grid if campaign else ""))
            is not None
        ]
        self._tx_times = [
            session.started_at
            for session in self.repository.list_tx_sessions(limit=10_000)
            if campaign is not None
            and session.started_at >= campaign.started_at
            and (
                campaign.ended_at is None
                or session.started_at <= campaign.ended_at
            )
        ]
        targets = {}
        for spot in self._spots:
            if spot.rx_grid:
                targets[(spot.rx_call, spot.rx_grid)] = spot.observed_at
        self.target.blockSignals(True)
        self.target.clear()
        for (call, grid), observed in sorted(
            targets.items(), key=lambda item: item[1], reverse=True
        ):
            self.target.addItem(f"{call} · {grid}", (call, grid))
        self.target.blockSignals(False)
        self._snapshots = (
            self.repository.list_propagation_snapshots(int(campaign_id))
            if campaign_id is not None
            else []
        )
        times = {spot.observed_at for spot in self._spots}
        times.update(snapshot.observed_at for snapshot in self._snapshots)
        self._timeline = sorted(times)
        self.time_slider.blockSignals(True)
        self.time_slider.setRange(0, max(0, len(self._timeline) - 1))
        self.time_slider.setValue(max(0, len(self._timeline) - 1))
        self.time_slider.blockSignals(False)
        has_data = bool(self._timeline and self.target.count())
        self.target.setEnabled(has_data)
        self.time_slider.setEnabled(has_data)
        self.play_button.setEnabled(has_data and len(self._timeline) > 1)
        self.refresh()

    def _time_changed(self) -> None:
        self.refresh()

    def _toggle_playback(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
            self.play_button.setText(self.text["play"])
        else:
            if self.time_slider.value() >= self.time_slider.maximum():
                self.time_slider.setValue(0)
            self._timer.start()
            self.play_button.setText(self.text["pause"])

    def _advance_time(self) -> None:
        if self.time_slider.value() >= self.time_slider.maximum():
            self._toggle_playback()
            return
        self.time_slider.setValue(self.time_slider.value() + 1)

    def refresh(self) -> None:
        campaign_id = self.campaign.currentData()
        target_data = self.target.currentData()
        if (
            campaign_id is None
            or target_data is None
            or not self._timeline
            or not self._located
        ):
            self.time_label.setText("—")
            self.route_summary.setText(self.text["empty"])
            self.effect_label.clear()
            self.missing_label.clear()
            self.features = None
            self.comparison = None
            self.save_button.setEnabled(False)
            self._clear_figures()
            return
        campaign = self.repository.get_campaign(int(campaign_id))
        _rx_call, rx_grid = target_data
        target_at = self._timeline[self.time_slider.value()]
        self.time_label.setText(
            target_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        )
        snapshot = self._nearest_snapshot(target_at)
        frequency = self._representative_frequency()
        glotec = self._glotec_grid(snapshot)
        receiver_calls = [item.spot.rx_call for item in self._located]
        self.features = derive_features(
            campaign,
            rx_grid,
            target_at,
            frequency,
            snapshot,
            glotec_grid=glotec,
            receiver_calls=receiver_calls,
            tx_session_times=self._tx_times,
        )
        self.save_button.setEnabled(campaign.id is not None)
        self._render_route()
        self._render_layers()
        self.provenance_text.setPlainText(
            json.dumps(
                self.features.canonical_dict(),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )

    def _nearest_snapshot(self, target: datetime) -> PropagationSnapshot | None:
        return min(
            self._snapshots,
            key=lambda snapshot: abs((snapshot.observed_at - target).total_seconds()),
            default=None,
        )

    def _representative_frequency(self) -> int:
        values = sorted(spot.frequency_hz for spot in self._spots)
        return values[len(values) // 2] if values else 14_074_000

    def _glotec_grid(
        self, snapshot: PropagationSnapshot | None
    ):
        if snapshot is None:
            return None
        try:
            payload = json.loads(snapshot.raw_payload_json).get("glotec_geojson")
        except (AttributeError, json.JSONDecodeError):
            return None
        return spatial_grid_from_geojson(
            payload,
            observed_at=snapshot.observed_at,
        )

    def _render_route(self) -> None:
        features = self.features
        if features is None:
            return
        self.route_figure.clear()
        axis = self.route_figure.add_subplot(111)
        axis.set_xlim(-180, 180)
        axis.set_ylim(-90, 90)
        axis.set_xlabel("Longitude")
        axis.set_ylabel("Latitude")
        axis.set_title(
            f"{features.tx_grid} → {features.rx_grid} · "
            f"{features.distance_km:.0f} km · {features.frequency_hz / 1e6:.3f} MHz"
        )
        background_lons = list(range(-180, 181, 10))
        background_lats = list(range(-90, 91, 10))
        background = [
            [
                solar_elevation((latitude, longitude), features.target_at)
                for longitude in background_lons
            ]
            for latitude in background_lats
        ]
        axis.contourf(
            background_lons,
            background_lats,
            background,
            levels=(-90, -6, 6, 90),
            colors=("#203450", "#8b7355", "#f1ca72"),
            alpha=0.18,
        )
        axis.contour(
            background_lons,
            background_lats,
            background,
            levels=(0,),
            colors=(TOKENS.warning_chart,),
            linewidths=0.8,
            linestyles="--",
        )
        lons = [point[1] for point in features.route_points]
        lats = [point[0] for point in features.route_points]
        daylight = [
            solar_elevation(point, features.target_at)
            for point in features.route_points
        ]
        axis.scatter(
            lons,
            lats,
            c=daylight,
            cmap="coolwarm",
            vmin=-30,
            vmax=30,
            s=12,
            zorder=3,
            label="Great circle · solar elevation",
        )
        segment_lons: list[float] = []
        segment_lats: list[float] = []
        for longitude, latitude in zip(lons, lats):
            if segment_lons and abs(longitude - segment_lons[-1]) > 180:
                axis.plot(
                    segment_lons,
                    segment_lats,
                    color=TOKENS.map_route,
                    linewidth=1.1,
                    alpha=0.8,
                )
                segment_lons, segment_lats = [], []
            segment_lons.append(longitude)
            segment_lats.append(latitude)
        if segment_lons:
            axis.plot(
                segment_lons,
                segment_lats,
                color=TOKENS.map_route,
                linewidth=1.1,
                alpha=0.8,
            )
        axis.scatter(
            [lons[0], lons[-1]],
            [lats[0], lats[-1]],
            color=[TOKENS.success, TOKENS.accent],
            s=45,
            zorder=4,
        )
        axis.grid(True, alpha=0.3)
        axis.legend(loc="lower left", fontsize="small")
        apply_figure_theme(self.route_figure)
        self.route_figure.tight_layout(pad=1.1)
        self.route_canvas.draw_idle()
        operating_mhz = features.frequency_hz / 1e6
        muf = "—" if features.muf3000_mhz is None else f"{features.muf3000_mhz:.2f} MHz"
        absorption = (
            "—"
            if features.drap_absorption_db is None
            else f"{features.drap_absorption_db:.1f} dB route mean"
        )
        self.route_summary.setText(
            f"<b>{features.confidence_label.upper()}</b><br>"
            f"Day / grayline / night: {features.day_fraction:.0%} / "
            f"{features.grayline_fraction:.0%} / {features.night_fraction:.0%}<br>"
            f"Route local solar time: {features.local_solar_time_hours:04.1f} h<br>"
            f"Operating frequency / MUF(3000): {operating_mhz:.3f} / {muf}<br>"
            f"D-RAP: {absorption}<br>"
            f"GIRO route distance: "
            f"{'—' if features.giro_distance_to_route_km is None else f'{features.giro_distance_to_route_km:.0f} km'}"
        )
        effects = []
        if features.grayline_fraction:
            effects.append(f"grayline {features.grayline_fraction:.0%}")
        if features.polar_absorption_risk:
            effects.append("polar-cap absorption risk")
        if features.kp_index is not None:
            effects.append(f"Kp {features.kp_index:.1f}")
        if features.muf3000_mhz is not None:
            effects.append(f"MUF margin {features.muf3000_mhz - operating_mhz:+.2f} MHz")
        self.effect_label.setText(
            f"<b>{self.text['effect']}</b><br>"
            + (" · ".join(effects) if effects else "—")
        )
        self.missing_label.setText(
            f"<b>{self.text['missing']}</b><br>"
            + (", ".join(features.missing_sources) or "—")
            + (
                "<br><br>" + "<br>".join(features.limitations)
                if features.limitations
                else ""
            )
        )

    def _feature_for_spot(self, item) -> PropagationFeatures:
        campaign = self.repository.get_campaign(int(self.campaign.currentData()))
        snapshot = self._nearest_snapshot(item.spot.observed_at)
        return derive_features(
            campaign,
            item.spot.rx_grid,
            item.spot.observed_at,
            item.spot.frequency_hz,
            snapshot,
            glotec_grid=self._glotec_grid(snapshot),
            receiver_calls=(spot.spot.rx_call for spot in self._located),
            tx_session_times=self._tx_times,
            computed_at=self.features.computed_at if self.features else None,
        )

    def _selected_nec(self) -> NecPattern | None:
        index = self.nec_choice.currentData()
        return (
            self.nec_patterns[int(index)][1].azimuth
            if index is not None and int(index) < len(self.nec_patterns)
            else None
        )

    def _render_layers(self) -> None:
        campaign = self.repository.get_campaign(int(self.campaign.currentData()))
        self.comparison = compare_layers(
            self._located,
            self._feature_for_spot,
            nec_pattern=self._selected_nec(),
            active_filters={
                "campaign": campaign.name,
                "band": campaign.band,
                "mode": campaign.mode,
                "source": "all campaign reports",
                "time": "campaign timeline",
                "distance": "all",
            },
        )
        self.layer_figure.clear()
        axis = self.layer_figure.add_subplot(111, projection="polar")
        axis.set_theta_zero_location("N")
        axis.set_theta_direction(-1)
        raw_values = [
            sector.median_snr_db
            for sector in self.comparison.sectors
            if sector.median_snr_db is not None
        ]
        raw_reference = float(median(raw_values)) if raw_values else 0.0
        observed = [
            (
                sector.center_deg,
                (
                    None
                    if sector.median_snr_db is None
                    else sector.median_snr_db - raw_reference
                ),
            )
            for sector in self.comparison.sectors
        ]
        normalized = [
            (sector.center_deg, sector.normalized_db)
            for sector in self.comparison.sectors
        ]
        nec = [
            (sector.center_deg, sector.nec_gain_db)
            for sector in self.comparison.sectors
        ]
        for values, label, color, style in (
            (
                observed,
                "Coverage / observed shape · median-aligned",
                TOKENS.chart_series[0],
                "-",
            ),
            (
                normalized,
                f"Propagation-normalized · {self.comparison.model_version}",
                TOKENS.chart_series[2],
                "-",
            ),
            (nec, "NEC theoretical reference", TOKENS.chart_series[3], "--"),
        ):
            if any(value is not None for _bearing, value in values):
                axis.plot(
                    [value[0] * 3.141592653589793 / 180 for value in values],
                    [
                        float("nan") if value[1] is None else value[1]
                        for value in values
                    ],
                    label=label,
                    color=color,
                    linestyle=style,
                    marker="o",
                    markersize=3,
                )
        axis.set_title(
            "Separate median-aligned shapes · unsupported sectors remain empty"
        )
        axis.legend(loc="upper right", bbox_to_anchor=(1.32, 1.12), fontsize="small")
        axis.grid(True, alpha=0.35)
        apply_figure_theme(self.layer_figure)
        self.layer_figure.tight_layout(pad=1.3)
        self.layer_canvas.draw_idle()
        self._fill_layer_table()
        validation = self.comparison.cross_validation
        mae = (
            "—"
            if validation.test_median_absolute_error_db is None
            else f"{validation.test_median_absolute_error_db:.1f} dB"
        )
        filters = " · ".join(
            f"{key}={value}" for key, value in self.comparison.active_filters
        )
        self.cv_label.setText(
            self.text["cv"].format(folds=validation.folds, mae=mae)
            + "<br>"
            + filters
        )

    def _fill_layer_table(self) -> None:
        if self.comparison is None:
            self.layer_table.setRowCount(0)
            return
        self.layer_table.setSortingEnabled(False)
        self.layer_table.setRowCount(len(self.comparison.sectors))
        for row, sector in enumerate(self.comparison.sectors):
            values = (
                f"{sector.center_deg:.0f}°",
                str(sector.report_count),
                str(sector.unique_receivers),
                _signed(sector.best_snr_db),
                _signed(sector.median_snr_db),
                _plain(sector.max_distance_km, 0),
                _plain(sector.report_density_per_1000km2, 3),
                sector.quality_label,
                (
                    "—"
                    if sector.confidence_low_db is None
                    else f"{sector.confidence_low_db:+.1f}…{sector.confidence_high_db:+.1f}"
                ),
                _signed(sector.normalized_db),
                _signed(sector.nec_gain_db),
                _signed(sector.difference_db),
            )
            sort_values = (
                sector.center_deg,
                sector.report_count,
                sector.unique_receivers,
                sector.best_snr_db,
                sector.median_snr_db,
                sector.max_distance_km,
                sector.report_density_per_1000km2,
                sector.quality_label,
                sector.confidence_low_db,
                sector.normalized_db,
                sector.nec_gain_db,
                sector.difference_db,
            )
            for column, value in enumerate(values):
                item = TechnicalTableItem(
                    value,
                    sort_value=(
                        sort_values[column]
                        if sort_values[column] is not None
                        else float("-inf")
                    ),
                    numeric=column not in (7,),
                )
                if column == 7:
                    item.setToolTip(
                        f"{sector.report_count} reports · "
                        f"{sector.unique_receivers} unique receivers"
                    )
                self.layer_table.setItem(row, column, item)
        self.layer_table.setSortingEnabled(True)
        self.layer_table.sortItems(0, Qt.SortOrder.AscendingOrder)

    def _import_nec(self) -> None:
        paths, _filter = QFileDialog.getOpenFileNames(
            self,
            self.text["import_nec"],
            "",
            "NEC output (*.out *.txt);;All files (*)",
        )
        for raw_path in paths:
            path = Path(raw_path)
            try:
                baseline = parse_nec_baseline(
                    path.read_text(encoding="utf-8", errors="replace"),
                    frequency_hz=self._representative_frequency(),
                    source=str(path),
                )
            except (OSError, ValueError) as exc:
                self.status.setText(str(exc))
                continue
            self.nec_patterns.append((path.name, baseline))
            self.nec_choice.addItem(
                f"{path.name} · az+el · "
                f"{baseline.parameters.frequency_hz / 1e6:.3f} MHz · "
                f"{baseline.parameters.ground_model} · "
                f"F/B {_plain(baseline.front_to_back_db, 1)} dB",
                len(self.nec_patterns) - 1,
            )
        if self.nec_patterns:
            self.nec_choice.setCurrentIndex(self.nec_choice.count() - 1)

    def _save_features(self) -> None:
        if self.features is None:
            return
        saved = self.repository.save_propagation_features(self.features)
        self.status.setText(
            self.text["saved"].format(hash=saved.input_sha256[:16])
        )

    def _clear_figures(self) -> None:
        for figure, canvas in (
            (self.route_figure, self.route_canvas),
            (self.layer_figure, self.layer_canvas),
        ):
            figure.clear()
            apply_figure_theme(figure)
            canvas.draw_idle()
        self.layer_table.setRowCount(0)
        self.provenance_text.clear()


def _signed(value) -> str:
    return "—" if value is None else f"{float(value):+.1f}"


def _plain(value, decimals: int) -> str:
    return "—" if value is None else f"{float(value):.{decimals}f}"
