from __future__ import annotations

from datetime import datetime, timezone

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .experiments import (
    AlternationProtocol,
    ExperimentGoal,
    recommend_next_experiment,
)
from .analysis import locate_spot
from .rotator_alignment import analyze_rotator_alignment
from .storage import SpotRepository
from .theme import TOKENS, apply_figure_theme, semantic_style


TEXT = {
    "CZE": {
        "title": "Řízený A/B experiment",
        "profile_a": "Profil A",
        "profile_b": "Profil B",
        "interval": "Interval",
        "target_band": "Cílové pásmo",
        "target_bearing": "Cílový azimut",
        "target_distance": "Cílová vzdálenost",
        "max_swr": "Maximální SWR",
        "plan": "Navrhnout další experiment",
        "plan_model": "Návrh: porovnat „{a}“ proti „{b}“. Kandidáti maximalizují kontrast zjednodušeného modelu v azimutu {bearing}°; nejde o předpověď skutečného zisku.",
        "plan_fallback": "Návrh: porovnat „{a}“ proti „{b}“. Pro modelové pořadí není dost podporovaných profilů.",
        "plan_missing": "Pro návrh jsou potřeba alespoň dva aktivní profily.",
        "plan_invalid": "Cílové hodnoty nejsou platné; maximum vzdálenosti musí být vyšší než minimum.",
        "plan_safety": "Před TX ověř SWR ≤ {swr:.1f}; drž stejný výkon, střídej profily a vyhodnocuj jen RX ve vzdálenosti {minimum}–{maximum} km.",
        "start": "Zahájit protokol",
        "confirm": "Potvrdit fyzické přepnutí",
        "stop": "Zastavit",
        "refresh": "Obnovit relace",
        "close": "Zavřít",
        "idle": "Protokol není spuštěn.",
        "switch": "Přepni fyzicky anténu na „{profile}“ a teprve potom změnu potvrď.",
        "running": "Aktivní „{profile}“ · zbývá {minutes:02d}:{seconds:02d}",
        "need_profiles": "Vyber dva různé anténní profily.",
        "note": "Profil se k novým WSJT-X TX relacím přiřadí až po potvrzení. Aplikace sama nepřepíná anténní relé.",
        "timeline": "Časová osa TX relací a kvalita přiřazení",
        "alignment": "Směrový soulad profilu, rotátoru a empirických dat",
        "alignment_headers": ["Profil", "Cíl osy", "Skutečnost", "Empirické maximum", "Odchylka cíle", "Odchylka maxima", "Podklady", "Jistota", "Varování"],
        "alignment_evidence": "{sessions} relací · {spots} spotů · {receivers} RX",
        "confidence": {"low": "nízká", "medium": "střední", "high": "vysoká"},
        "alignment_warnings": {
            "target_mismatch": "natočení ≠ profil",
            "variable_position": "proměnlivé natočení",
            "empirical_mismatch": "maximum mimo očekávaný směr",
            "insufficient_empirical_data": "málo dat pro maximum",
        },
        "not_applicable": "nerelevantní",
        "headers": ["Začátek UTC", "Délka", "Profil", "Mód", "MHz", "Spoty", "RX", "Ø SNR", "Rotátor", "Kvalita"],
        "rotator_value": "{start:.0f}° → {end:.0f}° · Δmax {deviation:.1f}°",
        "rotator_start": "{start:.0f}° · probíhá",
        "quality": "{score}% ({flags})",
        "flags": {"open": "otevřená", "no_profile": "bez profilu", "no_spots": "bez spotů", "short": "krátká", "rotator_moved": "pohyb rotátoru", "ok": "OK"},
    },
    "ENG": {
        "title": "Controlled A/B experiment",
        "profile_a": "Profile A",
        "profile_b": "Profile B",
        "interval": "Interval",
        "target_band": "Target band",
        "target_bearing": "Target bearing",
        "target_distance": "Target distance",
        "max_swr": "Maximum SWR",
        "plan": "Suggest next experiment",
        "plan_model": "Plan: compare “{a}” against “{b}”. Candidates maximize simplified-model contrast at {bearing}°; this is not a prediction of real gain.",
        "plan_fallback": "Plan: compare “{a}” against “{b}”. There are not enough supported profiles for model ranking.",
        "plan_missing": "At least two active profiles are required for a suggestion.",
        "plan_invalid": "The target values are invalid; maximum distance must exceed minimum distance.",
        "plan_safety": "Before TX verify SWR ≤ {swr:.1f}; keep power constant, alternate profiles and evaluate only receivers {minimum}–{maximum} km away.",
        "start": "Start protocol",
        "confirm": "Confirm physical switch",
        "stop": "Stop",
        "refresh": "Refresh sessions",
        "close": "Close",
        "idle": "Protocol is not running.",
        "switch": "Physically switch the antenna to “{profile}”, then confirm the change.",
        "running": "Active “{profile}” · {minutes:02d}:{seconds:02d} remaining",
        "need_profiles": "Select two different antenna profiles.",
        "note": "The profile is assigned to new WSJT-X TX sessions only after confirmation. The app does not operate an antenna relay.",
        "timeline": "TX session timeline and assignment quality",
        "alignment": "Profile, rotator and empirical-direction alignment",
        "alignment_headers": ["Profile", "Axis target", "Actual", "Empirical peak", "Target error", "Peak error", "Evidence", "Confidence", "Warnings"],
        "alignment_evidence": "{sessions} sessions · {spots} spots · {receivers} RX",
        "confidence": {"low": "low", "medium": "medium", "high": "high"},
        "alignment_warnings": {
            "target_mismatch": "position ≠ profile",
            "variable_position": "variable position",
            "empirical_mismatch": "peak outside expected direction",
            "insufficient_empirical_data": "insufficient peak data",
        },
        "not_applicable": "not applicable",
        "headers": ["Start UTC", "Duration", "Profile", "Mode", "MHz", "Spots", "RX", "Avg SNR", "Rotator", "Quality"],
        "rotator_value": "{start:.0f}° → {end:.0f}° · max Δ {deviation:.1f}°",
        "rotator_start": "{start:.0f}° · active",
        "quality": "{score}% ({flags})",
        "flags": {"open": "open", "no_profile": "no profile", "no_spots": "no spots", "short": "short", "rotator_moved": "rotator moved", "ok": "OK"},
    },
}


class ExperimentDialog(QDialog):
    def __init__(
        self, repository: SpotRepository, language: str, on_profile_selected,
        parent=None, band: str = "20m", mode: str = "FT8",
    ):
        super().__init__(parent)
        self.repository = repository
        self.text = TEXT[language if language in TEXT else "CZE"]
        self.on_profile_selected = on_profile_selected
        self.mode = mode
        self.protocol: AlternationProtocol | None = None
        self.profile_names: dict[int, str] = {}
        self.setWindowTitle(self.text["title"])
        self.resize(1100, 820)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.profile_a = QComboBox()
        self.profile_b = QComboBox()
        for profile in repository.list_antenna_profiles():
            self.profile_names[profile.id] = profile.name
            self.profile_a.addItem(profile.name, profile.id)
            self.profile_b.addItem(profile.name, profile.id)
        if self.profile_b.count() > 1:
            self.profile_b.setCurrentIndex(1)
        self.interval_minutes = QSpinBox()
        self.interval_minutes.setRange(1, 120)
        self.interval_minutes.setValue(10)
        self.interval_minutes.setSuffix(" min")
        self.target_band = QComboBox()
        for item in ("80m", "40m", "30m", "20m", "17m", "15m", "12m", "10m"):
            self.target_band.addItem(item)
        self.target_band.setCurrentText(band if band in {self.target_band.itemText(i) for i in range(self.target_band.count())} else "20m")
        self.target_bearing = QSpinBox()
        self.target_bearing.setRange(0, 359)
        self.target_bearing.setValue(90)
        self.target_bearing.setSuffix("°")
        distance_row = QHBoxLayout()
        self.min_distance = QSpinBox()
        self.max_distance = QSpinBox()
        for control in (self.min_distance, self.max_distance):
            control.setRange(0, 20_000)
            control.setSuffix(" km")
        self.min_distance.setValue(1000)
        self.max_distance.setValue(3000)
        distance_row.addWidget(self.min_distance)
        distance_row.addWidget(QLabel("–"))
        distance_row.addWidget(self.max_distance)
        self.max_swr = QDoubleSpinBox()
        self.max_swr.setRange(1.0, 10.0)
        self.max_swr.setSingleStep(0.1)
        self.max_swr.setValue(2.0)
        form.addRow(self.text["profile_a"], self.profile_a)
        form.addRow(self.text["profile_b"], self.profile_b)
        form.addRow(self.text["interval"], self.interval_minutes)
        form.addRow(self.text["target_band"], self.target_band)
        form.addRow(self.text["target_bearing"], self.target_bearing)
        form.addRow(self.text["target_distance"], distance_row)
        form.addRow(self.text["max_swr"], self.max_swr)
        layout.addLayout(form)
        planner_row = QHBoxLayout()
        self.plan_button = QPushButton(self.text["plan"])
        self.plan_result = QLabel()
        self.plan_result.setWordWrap(True)
        self.plan_result.setStyleSheet(semantic_style("info"))
        planner_row.addWidget(self.plan_button)
        planner_row.addWidget(self.plan_result, 1)
        layout.addLayout(planner_row)
        alignment_title = QLabel(self.text["alignment"])
        alignment_title.setStyleSheet("font-weight: 700;")
        layout.addWidget(alignment_title)
        self.alignment_table = QTableWidget(
            0, len(self.text["alignment_headers"])
        )
        self.alignment_table.setHorizontalHeaderLabels(
            self.text["alignment_headers"]
        )
        self.alignment_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.alignment_table.setMaximumHeight(115)
        self.alignment_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.alignment_table)
        note = QLabel(self.text["note"])
        note.setWordWrap(True)
        note.setStyleSheet(semantic_style("warning"))
        layout.addWidget(note)
        self.protocol_status = QLabel(self.text["idle"])
        self.protocol_status.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(self.protocol_status)
        buttons = QHBoxLayout()
        self.start_button = QPushButton(self.text["start"])
        self.confirm_button = QPushButton(self.text["confirm"])
        self.stop_button = QPushButton(self.text["stop"])
        refresh_button = QPushButton(self.text["refresh"])
        close_button = QPushButton(self.text["close"])
        self.confirm_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        for button in (self.start_button, self.confirm_button, self.stop_button, refresh_button):
            buttons.addWidget(button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        self.figure = Figure(figsize=(8, 3.6), facecolor=TOKENS.panel_background)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(260)
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.data_splitter = QSplitter(Qt.Orientation.Vertical)
        self.data_splitter.addWidget(self.canvas)
        self.data_splitter.addWidget(self.table)
        self.data_splitter.setStretchFactor(0, 3)
        self.data_splitter.setStretchFactor(1, 2)
        self.data_splitter.setSizes([340, 220])
        layout.addWidget(self.data_splitter, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self.start_button.clicked.connect(self.start_protocol)
        self.plan_button.clicked.connect(self.suggest_experiment)
        self.profile_a.currentIndexChanged.connect(self.refresh_alignment)
        self.profile_b.currentIndexChanged.connect(self.refresh_alignment)
        self.target_band.currentIndexChanged.connect(self.refresh_alignment)
        self.confirm_button.clicked.connect(self.confirm_switch)
        self.stop_button.clicked.connect(self.stop_protocol)
        refresh_button.clicked.connect(self.refresh_sessions)
        close_button.clicked.connect(self.accept)
        self.refresh_sessions()

    def suggest_experiment(self) -> None:
        goal = ExperimentGoal(
            band=self.target_band.currentText(),
            bearing_deg=self.target_bearing.value(),
            min_distance_km=self.min_distance.value(),
            max_distance_km=self.max_distance.value(),
            max_swr=self.max_swr.value(),
        )
        try:
            recommendation = recommend_next_experiment(
                self.repository.list_antenna_profiles(), goal, self.mode
            )
        except ValueError:
            self.plan_result.setText(self.text["plan_invalid"])
            return
        if recommendation is None:
            self.plan_result.setText(self.text["plan_missing"])
            return
        a_index = self.profile_a.findData(recommendation.profile_a_id)
        b_index = self.profile_b.findData(recommendation.profile_b_id)
        self.profile_a.setCurrentIndex(a_index)
        self.profile_b.setCurrentIndex(b_index)
        template = self.text[
            "plan_model" if recommendation.basis == "model_contrast" else "plan_fallback"
        ]
        plan = template.format(
            a=self.profile_a.currentText(),
            b=self.profile_b.currentText(),
            bearing=goal.bearing_deg,
        )
        safety = self.text["plan_safety"].format(
            swr=goal.max_swr,
            minimum=goal.min_distance_km,
            maximum=goal.max_distance_km,
        )
        self.plan_result.setText(f"{plan} {safety}")

    def start_protocol(self) -> None:
        profile_a = self.profile_a.currentData()
        profile_b = self.profile_b.currentData()
        if profile_a is None or profile_b is None or profile_a == profile_b:
            self.protocol_status.setText(self.text["need_profiles"])
            return
        self.protocol = AlternationProtocol(
            profile_a, profile_b, self.interval_minutes.value() * 60
        )
        target = self.protocol.start()
        self.start_button.setEnabled(False)
        self.confirm_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self._show_switch_request(target)

    def confirm_switch(self) -> None:
        if self.protocol is None:
            return
        profile_id = self.protocol.confirm_switch()
        self.on_profile_selected(profile_id)
        self.confirm_button.setEnabled(False)
        self.timer.start()
        self._render_running()

    def _tick(self) -> None:
        if self.protocol is None:
            return
        target = self.protocol.tick()
        if target is not None:
            self.timer.stop()
            self.confirm_button.setEnabled(True)
            self._show_switch_request(target)
        else:
            self._render_running()

    def _show_switch_request(self, profile_id: int) -> None:
        self.protocol_status.setText(
            self.text["switch"].format(profile=self.profile_names[profile_id])
        )

    def _render_running(self) -> None:
        if self.protocol is None or self.protocol.active_profile_id is None:
            return
        minutes, seconds = divmod(self.protocol.remaining_seconds, 60)
        self.protocol_status.setText(
            self.text["running"].format(
                profile=self.profile_names[self.protocol.active_profile_id],
                minutes=minutes,
                seconds=seconds,
            )
        )

    def stop_protocol(self) -> None:
        self.timer.stop()
        if self.protocol is not None:
            self.protocol.stop()
        self.protocol = None
        self.protocol_status.setText(self.text["idle"])
        self.start_button.setEnabled(True)
        self.confirm_button.setEnabled(False)
        self.stop_button.setEnabled(False)

    def refresh_sessions(self) -> None:
        sessions = self.repository.list_tx_sessions()
        self.table.setRowCount(len(sessions))
        for row, session in enumerate(sessions):
            flags = session.quality_flags or ("ok",)
            duration = session.duration_seconds
            if session.rotator_start_azimuth_deg is None:
                rotator = "—"
            elif session.rotator_end_azimuth_deg is None:
                rotator = self.text["rotator_start"].format(
                    start=session.rotator_start_azimuth_deg
                )
            else:
                rotator = self.text["rotator_value"].format(
                    start=session.rotator_start_azimuth_deg,
                    end=session.rotator_end_azimuth_deg,
                    deviation=session.rotator_max_deviation_deg or 0.0,
                )
            values = (
                session.started_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "—" if duration is None else f"{duration:.0f} s",
                session.profile_name or "—",
                session.mode,
                f"{session.frequency_hz / 1_000_000:.6f}",
                str(session.spot_count),
                str(session.unique_receivers),
                "—" if session.average_snr_db is None else f"{session.average_snr_db:+.1f}",
                rotator,
                self.text["quality"].format(
                    score=session.quality_score,
                    flags=", ".join(self.text["flags"][flag] for flag in flags),
                ),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 4, 5, 6, 7, 8, 9):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self._draw_timeline(sessions)
        self.refresh_alignment(sessions=sessions)

    def refresh_alignment(
        self,
        _index: int | None = None,
        *,
        sessions=None,
    ) -> None:
        all_sessions = sessions or self.repository.list_tx_sessions(limit=20_000)
        profile_ids = []
        for selector in (self.profile_a, self.profile_b):
            profile_id = selector.currentData()
            if profile_id is not None and profile_id not in profile_ids:
                profile_ids.append(profile_id)
        self.alignment_table.setRowCount(len(profile_ids))
        for row, profile_id in enumerate(profile_ids):
            profile = self.repository.get_antenna_profile(profile_id)
            profile_sessions = [
                session
                for session in all_sessions
                if session.profile_id == profile_id and session.mode == self.mode
            ]
            located = [
                item
                for spot in self.repository.list_spots_for_profile(
                    profile_id,
                    band=self.target_band.currentText(),
                    mode=self.mode,
                )
                if (item := locate_spot(spot))
            ]
            result = analyze_rotator_alignment(profile, profile_sessions, located)
            if result.applicable:
                target = (
                    "—"
                    if result.target_azimuth_deg is None
                    else f"{result.target_azimuth_deg:.0f}°"
                )
                actual = (
                    "—"
                    if result.actual_azimuth_deg is None
                    else f"{result.actual_azimuth_deg:.0f}°"
                )
            else:
                target = actual = self.text["not_applicable"]
            peak = (
                "—"
                if result.empirical_peak_deg is None
                else f"{result.empirical_peak_deg:.0f}°"
            )
            target_error = (
                "—"
                if result.target_error_deg is None
                else f"{result.target_error_deg:.1f}°"
            )
            peak_error = (
                "—"
                if result.empirical_error_deg is None
                else f"{result.empirical_error_deg:.1f}°"
            )
            warnings = ", ".join(
                self.text["alignment_warnings"][warning]
                for warning in result.warnings
            ) or "—"
            values = (
                profile.name,
                target,
                actual,
                peak,
                target_error,
                peak_error,
                self.text["alignment_evidence"].format(
                    sessions=result.session_count,
                    spots=result.spot_count,
                    receivers=result.unique_receivers,
                ),
                self.text["confidence"][result.confidence],
                warnings,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (1, 2, 3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alignment_table.setItem(row, column, item)
        self.alignment_table.resizeColumnsToContents()

    def _draw_timeline(self, sessions) -> None:
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_facecolor(TOKENS.panel_background)
        now = datetime.now(timezone.utc)
        for index, session in enumerate(reversed(sessions[:50])):
            end = session.ended_at or now
            color = TOKENS.success if session.quality_score >= 80 else TOKENS.warning if session.quality_score >= 50 else TOKENS.danger
            axis.plot(
                [session.started_at, end],
                [index, index],
                color=color,
                linewidth=6,
                solid_capstyle="round",
            )
        axis.set_title(self.text["timeline"], color=TOKENS.text_primary)
        axis.set_yticks([])
        axis.tick_params(colors=TOKENS.chart_labels)
        axis.grid(axis="x", color=TOKENS.chart_grid, alpha=0.8)
        apply_figure_theme(self.figure)
        if sessions:
            self.figure.autofmt_xdate(rotation=20, ha="right")
        self.figure.tight_layout(pad=1.5)
        self.canvas.draw_idle()

    def accept(self) -> None:
        self.stop_protocol()
        super().accept()
