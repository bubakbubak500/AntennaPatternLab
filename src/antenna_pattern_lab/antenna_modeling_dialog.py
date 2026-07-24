from __future__ import annotations

from dataclasses import replace
import json
from math import cos, pi, radians, sin
from pathlib import Path
import threading

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib import colormaps
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
import numpy as np
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .antenna_model import (
    AntennaModel,
    Excitation,
    FrequencySweep,
    Ground,
    Point3D,
    Wire,
    WireLoad,
    antenna_template,
    model_limits,
    parse_nec_deck,
)
from .dependencies import detect_opennec
from .design_system import DataPanel, MetricCard, PanelHeader, StatusIndicator
from .nec_runner import (
    NecRunCancelled,
    NecRunError,
    NecRunResult,
    run_opennec,
    select_azimuth_cut,
)
from .storage import SpotRepository, StoredAntennaModel
from .theme import TOKENS, apply_figure_theme


TEXT = {
    "CZE": {
        "title": "Modelování antény · NEC2 Workbench",
        "intro": "Navrhněte drátovou anténu, zkontrolujte geometrii a spusťte samostatný OpenNEC. Model a výsledky zůstávají reprodukovatelné i bez solveru.",
        "model": "Model a geometrie",
        "results": "Výsledky 2D",
        "radiation3d": "Vyzařování 3D",
        "candidates": "Asistované varianty",
        "new": "Nový z šablony",
        "load": "Uložené revize:",
        "save": "Uložit revizi",
        "import": "Importovat…",
        "export": "Exportovat…",
        "preview": "Aktualizovat náhled",
        "run": "Vypočítat baseline",
        "cancel": "Zrušit výpočet",
        "installed": "Nainstalováno",
        "missing": "Nenalezeno",
        "solver": "OpenNEC",
        "wires": "Dráty",
        "loads": "RLC zátěže",
        "validation": "Validace modelu",
        "parameters": "Parametry výpočtu",
        "add": "Přidat",
        "remove": "Odebrat",
        "start": "Od MHz",
        "stop": "Do MHz",
        "steps": "Kroků",
        "orientation": "Orientace °",
        "ground": "Zem",
        "epsilon": "Rel. permitivita",
        "conductivity": "Vodivost S/m",
        "source_wire": "Napájený drát",
        "source_segment": "Segment zdroje",
        "gain_mode": "Zisk:",
        "relative": "relativní dB",
        "absolute": "absolutní dBi",
        "candidate_intro": "Výšky a zem se řeší samostatnými běhy. Orientace se následně hledá proti trénovací části kampaně; výsledek musí projít dosud nepoužitými časovými bloky.",
        "height_offsets": "Posuny výšky m",
        "grounds": "Varianty země",
        "solve_candidates": "Vypočítat mřížku variant",
        "open_compare": "Porovnat s měřením a validovat…",
        "limits": "Rozsah NEC2 v1",
        "close": "Zavřít",
    },
    "ENG": {
        "title": "Antenna Modeling · NEC2 Workbench",
        "intro": "Design a wire antenna, validate its geometry, and run standalone OpenNEC. The model and results remain reproducible without the solver.",
        "model": "Model and geometry",
        "results": "2D results",
        "radiation3d": "3D radiation",
        "candidates": "Assisted variants",
        "new": "New from template",
        "load": "Saved revisions:",
        "save": "Save revision",
        "import": "Import…",
        "export": "Export…",
        "preview": "Refresh preview",
        "run": "Calculate baseline",
        "cancel": "Cancel calculation",
        "installed": "Installed",
        "missing": "Not found",
        "solver": "OpenNEC",
        "wires": "Wires",
        "loads": "RLC loads",
        "validation": "Model validation",
        "parameters": "Calculation parameters",
        "add": "Add",
        "remove": "Remove",
        "start": "From MHz",
        "stop": "To MHz",
        "steps": "Steps",
        "orientation": "Orientation °",
        "ground": "Ground",
        "epsilon": "Rel. permittivity",
        "conductivity": "Conductivity S/m",
        "source_wire": "Driven wire",
        "source_segment": "Source segment",
        "gain_mode": "Gain:",
        "relative": "relative dB",
        "absolute": "absolute dBi",
        "candidate_intro": "Height and ground use separate solver runs. Orientation is then fitted on the campaign training partition; it must pass previously unused time blocks.",
        "height_offsets": "Height offsets m",
        "grounds": "Ground variants",
        "solve_candidates": "Calculate candidate grid",
        "open_compare": "Compare with measurements and validate…",
        "limits": "NEC2 v1 scope",
        "close": "Close",
    },
}


class _SolverThread(QThread):
    completed = Signal(object, object, str)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, tasks, executable, parent=None):
        super().__init__(parent)
        self.tasks = list(tasks)
        self.executable = executable
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            total = len(self.tasks)
            for index, (model, metadata) in enumerate(self.tasks, 1):
                if self.cancel_event.is_set():
                    raise NecRunCancelled("Calculation cancelled.")
                self.progress.emit(index, total, model.name)
                result = run_opennec(
                    model,
                    executable=self.executable,
                    cancel_event=self.cancel_event,
                )
                self.completed.emit(model, result, metadata)
        except (NecRunError, OSError, ValueError) as exc:
            self.failed.emit(str(exc))


class AntennaModelingDialog(QDialog):
    def __init__(self, repository: SpotRepository, language: str = "CZE", parent=None):
        super().__init__(parent)
        self.repository = repository
        self.language = language if language in TEXT else "ENG"
        self.text = TEXT[self.language]
        self.solver_path = detect_opennec()
        self.model = antenna_template("dipole")
        self.stored_model: StoredAntennaModel | None = None
        self.result: NecRunResult | None = None
        self.worker: _SolverThread | None = None
        self._candidate_runs = []
        self._loading = False

        self.setObjectName("AntennaModelingDialog")
        self.setWindowTitle(self.text["title"])
        self.resize(1320, 850)
        self.setMinimumSize(1040, 700)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        title = PanelHeader(self.text["title"])
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(intro)
        heading.addLayout(title_box, 1)
        self.solver_indicator = StatusIndicator()
        self._render_solver_status()
        heading.addWidget(self.solver_indicator, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(heading)
        root.addLayout(self._build_toolbar())

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_model_tab(), self.text["model"])
        self.tabs.addTab(self._build_results_tab(), self.text["results"])
        self.tabs.addTab(self._build_3d_tab(), self.text["radiation3d"])
        self.tabs.addTab(self._build_candidates_tab(), self.text["candidates"])
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.status = QLabel("")
        self.status.setWordWrap(True)
        footer.addWidget(self.status, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(self.text["close"])
        buttons.rejected.connect(self.reject)
        footer.addWidget(buttons)
        root.addLayout(footer)
        self._load_model(self.model)
        self._reload_saved_models()

    def _build_toolbar(self):
        row = QHBoxLayout()
        row.addWidget(QLabel(self.text["new"]))
        self.template = QComboBox()
        for label, value in (
            ("Dipole", "dipole"),
            ("Inverted-V", "inverted_v"),
            ("Vertical", "vertical"),
            ("Loop", "loop"),
            ("Yagi", "yagi"),
        ):
            self.template.addItem(label, value)
        self.new_button = QPushButton(self.text["new"])
        self.new_button.clicked.connect(self._new_template)
        row.addWidget(self.template)
        row.addWidget(self.new_button)
        row.addSpacing(12)
        row.addWidget(QLabel(self.text["load"]))
        self.saved_models = QComboBox()
        self.saved_models.setMinimumWidth(230)
        self.saved_models.currentIndexChanged.connect(self._saved_model_selected)
        row.addWidget(self.saved_models)
        self.save_button = QPushButton(self.text["save"])
        self.save_button.clicked.connect(self._save_model)
        self.import_button = QPushButton(self.text["import"])
        self.import_button.clicked.connect(self._import_model)
        self.export_button = QPushButton(self.text["export"])
        self.export_button.clicked.connect(self._export_model)
        row.addWidget(self.save_button)
        row.addWidget(self.import_button)
        row.addWidget(self.export_button)
        row.addStretch(1)
        self.run_button = QPushButton(self.text["run"])
        self.run_button.setProperty("buttonRole", "primary")
        self.run_button.setEnabled(self.solver_path is not None)
        self.run_button.clicked.connect(self._run_baseline)
        self.cancel_button = QPushButton(self.text["cancel"])
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_run)
        row.addWidget(self.run_button)
        row.addWidget(self.cancel_button)
        return row

    def _build_model_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 4, 0)

        parameters = DataPanel()
        form = QFormLayout(parameters)
        self.model_name = QLineEdit()
        form.addRow("Name" if self.language == "ENG" else "Název", self.model_name)
        frequency_row = QWidget()
        frequency_layout = QHBoxLayout(frequency_row)
        frequency_layout.setContentsMargins(0, 0, 0, 0)
        self.frequency_start = self._frequency_spin()
        self.frequency_stop = self._frequency_spin()
        self.frequency_steps = QSpinBox()
        self.frequency_steps.setRange(1, 999)
        for label, widget in (
            (self.text["start"], self.frequency_start),
            (self.text["stop"], self.frequency_stop),
            (self.text["steps"], self.frequency_steps),
        ):
            frequency_layout.addWidget(QLabel(label))
            frequency_layout.addWidget(widget)
        form.addRow(self.text["parameters"], frequency_row)
        self.orientation = QDoubleSpinBox()
        self.orientation.setRange(0, 359.999)
        self.orientation.setDecimals(1)
        form.addRow(self.text["orientation"], self.orientation)
        ground_row = QWidget()
        ground_layout = QHBoxLayout(ground_row)
        ground_layout.setContentsMargins(0, 0, 0, 0)
        self.ground = QComboBox()
        self.ground.addItem("Real / Sommerfeld-Norton", "real")
        self.ground.addItem("Perfect", "perfect")
        self.ground.addItem("Free space", "free_space")
        self.epsilon = QDoubleSpinBox()
        self.epsilon.setRange(1, 100)
        self.epsilon.setDecimals(2)
        self.conductivity = QDoubleSpinBox()
        self.conductivity.setRange(0, 10)
        self.conductivity.setDecimals(6)
        ground_layout.addWidget(self.ground, 2)
        ground_layout.addWidget(QLabel("εr"))
        ground_layout.addWidget(self.epsilon)
        ground_layout.addWidget(QLabel("S/m"))
        ground_layout.addWidget(self.conductivity)
        form.addRow(self.text["ground"], ground_row)
        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        self.source_wire = QSpinBox()
        self.source_wire.setRange(1, 9999)
        self.source_segment = QSpinBox()
        self.source_segment.setRange(1, 9999)
        source_layout.addWidget(QLabel(self.text["source_wire"]))
        source_layout.addWidget(self.source_wire)
        source_layout.addWidget(QLabel(self.text["source_segment"]))
        source_layout.addWidget(self.source_segment)
        form.addRow("", source_row)
        editor_layout.addWidget(parameters)

        wire_head = QHBoxLayout()
        wire_head.addWidget(PanelHeader(self.text["wires"]))
        wire_head.addStretch(1)
        add_wire = QPushButton(self.text["add"])
        remove_wire = QPushButton(self.text["remove"])
        add_wire.clicked.connect(self._add_wire)
        remove_wire.clicked.connect(self._remove_wire)
        wire_head.addWidget(add_wire)
        wire_head.addWidget(remove_wire)
        editor_layout.addLayout(wire_head)
        self.wire_table = QTableWidget(0, 10)
        self.wire_table.setHorizontalHeaderLabels(
            ("Tag", "Label", "X1", "Y1", "Z1", "X2", "Y2", "Z2", "Seg", "Radius m")
        )
        self.wire_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.wire_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.wire_table.horizontalHeader().setStretchLastSection(True)
        self.wire_table.setMinimumHeight(125)
        editor_layout.addWidget(self.wire_table, 2)

        load_head = QHBoxLayout()
        load_head.addWidget(PanelHeader(self.text["loads"]))
        load_head.addStretch(1)
        add_load = QPushButton(self.text["add"])
        remove_load = QPushButton(self.text["remove"])
        add_load.clicked.connect(self._add_load)
        remove_load.clicked.connect(self._remove_load)
        load_head.addWidget(add_load)
        load_head.addWidget(remove_load)
        editor_layout.addLayout(load_head)
        self.load_table = QTableWidget(0, 6)
        self.load_table.setHorizontalHeaderLabels(("Tag", "First", "Last", "R Ω", "L H", "C F"))
        self.load_table.setMaximumHeight(105)
        editor_layout.addWidget(self.load_table)
        splitter.addWidget(editor)

        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(4, 0, 0, 0)
        preview_head = QHBoxLayout()
        preview_head.addWidget(
            PanelHeader("3D geometry" if self.language == "ENG" else "3D geometrie")
        )
        preview_head.addStretch(1)
        refresh = QPushButton(self.text["preview"])
        refresh.clicked.connect(self._refresh_model)
        preview_head.addWidget(refresh)
        preview_layout.addLayout(preview_head)
        self.geometry_figure = Figure(figsize=(6, 5))
        self.geometry_canvas = FigureCanvasQTAgg(self.geometry_figure)
        self.geometry_canvas.setAccessibleName("Rotatable three-dimensional wire geometry")
        preview_layout.addWidget(self.geometry_canvas, 1)
        preview_layout.addWidget(PanelHeader(self.text["validation"]))
        self.validation = QTextEdit()
        self.validation.setReadOnly(True)
        self.validation.setMaximumHeight(150)
        preview_layout.addWidget(self.validation)
        splitter.addWidget(preview)
        splitter.setSizes((690, 590))
        layout.addWidget(splitter)
        return page

    def _build_results_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        controls.addWidget(QLabel(self.text["gain_mode"]))
        self.gain_mode = QComboBox()
        self.gain_mode.addItem(self.text["relative"], "relative")
        self.gain_mode.addItem(self.text["absolute"], "absolute")
        self.gain_mode.currentIndexChanged.connect(self._render_result)
        controls.addWidget(self.gain_mode)
        self.frequency_choice = QComboBox()
        self.frequency_choice.currentIndexChanged.connect(self._render_result)
        controls.addWidget(self.frequency_choice)
        controls.addStretch(1)
        self.peak_card = MetricCard("Peak gain", "—")
        self.fb_card = MetricCard("Front / back", "—")
        controls.addWidget(self.peak_card)
        controls.addWidget(self.fb_card)
        layout.addLayout(controls)
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.result_figure = Figure(figsize=(9, 6))
        self.result_canvas = FigureCanvasQTAgg(self.result_figure)
        self.result_canvas.setAccessibleName("Impedance, SWR, azimuth and elevation results")
        splitter.addWidget(self.result_canvas)
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.current_table = QTableWidget(0, 5)
        self.current_table.setHorizontalHeaderLabels(("MHz", "Wire", "Segment", "|I| A", "Phase °"))
        self.current_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.provenance = QTextEdit()
        self.provenance.setReadOnly(True)
        bottom_layout.addWidget(self.current_table, 2)
        bottom_layout.addWidget(self.provenance, 3)
        splitter.addWidget(bottom)
        splitter.setSizes((520, 170))
        layout.addWidget(splitter)
        return page

    def _build_3d_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        hint = QLabel(
            "Drag to rotate · wheel to zoom"
            if self.language == "ENG"
            else "Tažením otáčejte · kolečkem přibližujte"
        )
        layout.addWidget(hint)
        self.radiation_figure = Figure(figsize=(9, 7))
        self.radiation_canvas = FigureCanvasQTAgg(self.radiation_figure)
        self.radiation_canvas.setAccessibleName("Rotatable three-dimensional radiation pattern")
        layout.addWidget(self.radiation_canvas)
        return page

    def _build_candidates_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        intro = QLabel(self.text["candidate_intro"])
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.height_offsets = QLineEdit("-2, 0, 2")
        self.ground_variants = QLineEdit("real, perfect")
        form.addRow(self.text["height_offsets"], self.height_offsets)
        form.addRow(self.text["grounds"], self.ground_variants)
        layout.addLayout(form)
        row = QHBoxLayout()
        self.solve_candidates = QPushButton(self.text["solve_candidates"])
        self.solve_candidates.setEnabled(self.solver_path is not None)
        self.solve_candidates.clicked.connect(self._run_candidates)
        self.open_compare = QPushButton(self.text["open_compare"])
        self.open_compare.clicked.connect(self._open_comparison)
        row.addWidget(self.solve_candidates)
        row.addWidget(self.open_compare)
        row.addStretch(1)
        layout.addLayout(row)
        self.candidate_table = QTableWidget(0, 6)
        self.candidate_table.setHorizontalHeaderLabels(
            (
                ("Run", "Δ height m", "Ground", "Engine", "Input SHA-256", "Output SHA-256")
                if self.language == "ENG"
                else ("Běh", "Δ výška m", "Zem", "Engine", "Vstup SHA-256", "Výstup SHA-256")
            )
        )
        self.candidate_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.candidate_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.candidate_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.candidate_table, 1)
        layout.addWidget(PanelHeader(self.text["limits"]))
        limits_text = (
            model_limits()
            if self.language == "ENG"
            else (
                "Pouze drátová geometrie NEC2 (GW); bez ploch, budov a objemových těles.",
                "Napěťové zdroje (EX 0), sériové RLC zátěže (LD 0) a volný prostor / dokonalá / reálná zem.",
                "Bez reálného koaxu, terénního profilu, optimalizačního enginu a rozšíření NEC4.",
            )
        )
        limits = QLabel(" • " + "\n • ".join(limits_text))
        limits.setWordWrap(True)
        layout.addWidget(limits)
        return page

    @staticmethod
    def _frequency_spin():
        widget = QDoubleSpinBox()
        widget.setRange(0.001, 5000)
        widget.setDecimals(6)
        widget.setSuffix(" MHz")
        return widget

    def _render_solver_status(self):
        if self.solver_path is None:
            self.solver_indicator.set_indicator(
                self.text["solver"], "inactive", self.text["missing"], self.text["missing"]
            )
        else:
            self.solver_indicator.set_indicator(
                self.text["solver"], "connected", str(self.solver_path), self.text["installed"]
            )

    def _new_template(self):
        self._load_model(antenna_template(str(self.template.currentData())))
        self.stored_model = None
        self.result = None
        self._render_result()

    def _load_model(self, model: AntennaModel):
        self._loading = True
        self.model = model
        self.model_name.setText(model.name)
        self.frequency_start.setValue(model.frequency.start_hz / 1e6)
        self.frequency_stop.setValue(model.frequency.stop_hz / 1e6)
        self.frequency_steps.setValue(model.frequency.steps)
        self.orientation.setValue(model.orientation_deg)
        self.ground.setCurrentIndex(max(0, self.ground.findData(model.ground.kind)))
        self.epsilon.setValue(model.ground.relative_permittivity)
        self.conductivity.setValue(model.ground.conductivity_s_m)
        source = model.excitations[0] if model.excitations else Excitation(1, 1)
        self.source_wire.setValue(source.wire_tag)
        self.source_segment.setValue(source.segment)
        self.wire_table.setRowCount(len(model.wires))
        for row, wire in enumerate(model.wires):
            values = (
                wire.tag, wire.label, wire.start.x_m, wire.start.y_m, wire.start.z_m,
                wire.end.x_m, wire.end.y_m, wire.end.z_m, wire.segments, wire.radius_m,
            )
            for column, value in enumerate(values):
                self.wire_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        f"{value:.6g}" if isinstance(value, float) else str(value)
                    ),
                )
        self.load_table.setRowCount(len(model.loads))
        for row, load in enumerate(model.loads):
            for column, value in enumerate(
                (load.wire_tag, load.first_segment, load.last_segment, load.resistance_ohm, load.inductance_h, load.capacitance_f)
            ):
                self.load_table.setItem(row, column, QTableWidgetItem(str(value)))
        self._loading = False
        self._render_geometry()

    def _model_from_editor(self) -> AntennaModel:
        wires = []
        for row in range(self.wire_table.rowCount()):
            values = [self._cell(self.wire_table, row, column) for column in range(10)]
            wires.append(
                Wire(
                    int(values[0]), Point3D(*map(float, values[2:5])),
                    Point3D(*map(float, values[5:8])), int(values[8]), float(values[9]), values[1],
                )
            )
        loads = []
        for row in range(self.load_table.rowCount()):
            values = [self._cell(self.load_table, row, column) for column in range(6)]
            loads.append(WireLoad(int(values[0]), int(values[1]), int(values[2]), *map(float, values[3:])))
        return AntennaModel(
            self.model_name.text().strip(),
            tuple(wires),
            (Excitation(self.source_wire.value(), self.source_segment.value()),),
            tuple(loads),
            Ground(str(self.ground.currentData()), self.epsilon.value(), self.conductivity.value()),
            FrequencySweep(
                round(self.frequency_start.value() * 1e6),
                round(self.frequency_stop.value() * 1e6),
                self.frequency_steps.value(),
            ),
            self.orientation.value(),
            self.model.notes,
        )

    @staticmethod
    def _cell(table, row, column):
        item = table.item(row, column)
        if item is None or not item.text().strip():
            raise ValueError(f"Table cell {row + 1}:{column + 1} is empty.")
        return item.text().strip()

    def _refresh_model(self):
        try:
            self.model = self._model_from_editor()
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        self._render_geometry()
        return not any(issue.severity == "error" for issue in self.model.validate())

    def _render_geometry(self):
        self.geometry_figure.clear()
        axis = self.geometry_figure.add_subplot(111, projection="3d")
        source_tags = {source.wire_tag for source in self.model.excitations}
        for wire in self.model.wires:
            axis.plot(
                (wire.start.x_m, wire.end.x_m),
                (wire.start.y_m, wire.end.y_m),
                (wire.start.z_m, wire.end.z_m),
                color=TOKENS.accent if wire.tag in source_tags else TOKENS.chart_series[0],
                linewidth=2.4 if wire.tag in source_tags else 1.5,
                marker="o",
                markersize=3,
            )
            midpoint = (
                (wire.start.x_m + wire.end.x_m) / 2,
                (wire.start.y_m + wire.end.y_m) / 2,
                (wire.start.z_m + wire.end.z_m) / 2,
            )
            axis.text(*midpoint, str(wire.tag), fontsize=8)
        points = [
            point
            for wire in self.model.wires
            for point in (wire.start, wire.end)
        ]
        if points:
            values = (
                [point.x_m for point in points],
                [point.y_m for point in points],
                [point.z_m for point in points],
            )
            span = max(
                1.0,
                *(max(axis_values) - min(axis_values) for axis_values in values),
            )
            for setter, axis_values in zip(
                (axis.set_xlim, axis.set_ylim, axis.set_zlim),
                values,
            ):
                center = (min(axis_values) + max(axis_values)) / 2
                setter(center - span * 0.55, center + span * 0.55)
        axis.set_xlabel("X [m]")
        axis.set_ylabel("Y [m]")
        axis.set_zlabel("Z [m]")
        axis.set_title(self.model.name)
        axis.set_box_aspect((1, 1, 0.7))
        apply_figure_theme(self.geometry_figure)
        self.geometry_figure.tight_layout(pad=1)
        self.geometry_canvas.draw_idle()
        issues = self.model.validate()
        if not issues:
            self.validation.setPlainText("✓ OK")
        else:
            self.validation.setPlainText(
                "\n".join(
                    f"{'◆' if issue.severity == 'error' else '▲'} "
                    f"{issue.code}{f' · GW {issue.wire_tag}' if issue.wire_tag else ''}: "
                    f"{issue.message}"
                    for issue in issues
                )
            )

    def _add_wire(self):
        row = self.wire_table.rowCount()
        self.wire_table.insertRow(row)
        defaults = (row + 1, "", 0, 0, 1, 1, 0, 1, 11, 0.001)
        for column, value in enumerate(defaults):
            self.wire_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _remove_wire(self):
        rows = sorted({index.row() for index in self.wire_table.selectedIndexes()}, reverse=True)
        for row in rows or ([self.wire_table.rowCount() - 1] if self.wire_table.rowCount() else []):
            self.wire_table.removeRow(row)

    def _add_load(self):
        row = self.load_table.rowCount()
        self.load_table.insertRow(row)
        for column, value in enumerate((1, 1, 1, 50, 0, 0)):
            self.load_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _remove_load(self):
        row = self.load_table.currentRow()
        if row >= 0:
            self.load_table.removeRow(row)

    def _save_model(self):
        if not self._refresh_model():
            self.status.setText("Model contains errors and was not saved.")
            return
        self.stored_model = self.repository.save_nec_model(self.model)
        self.status.setText(
            f"{self.stored_model.name} · revision {self.stored_model.revision} · {self.stored_model.model_sha256[:16]}"
        )
        self._reload_saved_models(self.stored_model.id)

    def _reload_saved_models(self, selected_id=None):
        self.saved_models.blockSignals(True)
        self.saved_models.clear()
        self.saved_models.addItem("—", None)
        for stored in self.repository.list_nec_models(latest_only=False):
            self.saved_models.addItem(
                f"{stored.name} · r{stored.revision} · {stored.model_sha256[:8]}",
                stored.id,
            )
        index = self.saved_models.findData(selected_id)
        self.saved_models.setCurrentIndex(max(0, index))
        self.saved_models.blockSignals(False)

    def _saved_model_selected(self):
        model_id = self.saved_models.currentData()
        if model_id is None:
            return
        self.stored_model = self.repository.get_nec_model(int(model_id))
        self._load_model(self.stored_model.model)
        runs = self.repository.list_nec_runs(model_id=self.stored_model.id)
        if runs:
            self.result = runs[0].result
            self._render_result()

    def _import_model(self):
        path, _filter = QFileDialog.getOpenFileName(
            self, self.text["import"], "", "Antenna model (*.json);;NEC deck (*.nec);;All files (*)"
        )
        if not path:
            return
        try:
            payload = Path(path).read_text(encoding="utf-8", errors="replace")
            model = AntennaModel.from_json(payload) if Path(path).suffix.lower() == ".json" else parse_nec_deck(payload, name=Path(path).stem)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, self.text["import"], str(exc))
            return
        self.stored_model = None
        self._load_model(model)

    def _export_model(self):
        if not self._refresh_model():
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self, self.text["export"], f"{self.model.name}.nec", "NEC deck (*.nec);;Antenna model (*.json)"
        )
        if not path:
            return
        try:
            is_json = "json" in selected_filter.lower() or Path(path).suffix.lower() == ".json"
            Path(path).write_text(
                self.model.canonical_json() + "\n" if is_json else self.model.to_nec(),
                encoding="utf-8" if is_json else "ascii",
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self.text["export"], str(exc))

    def _run_baseline(self):
        if not self._refresh_model():
            return
        self._start_worker(((self.model, "independent_baseline"),))

    def _run_candidates(self):
        if not self._refresh_model():
            return
        try:
            heights = tuple(float(value.strip()) for value in self.height_offsets.text().split(",") if value.strip())
            grounds = tuple(value.strip().lower() for value in self.ground_variants.text().split(",") if value.strip())
        except ValueError:
            self.status.setText("Invalid height-offset list.")
            return
        if not heights or not grounds or any(value not in {"real", "perfect", "free_space"} for value in grounds):
            self.status.setText("Use ground variants: real, perfect, free_space.")
            return
        tasks = []
        for height in heights:
            for kind in grounds:
                ground = replace(self.model.ground, kind=kind)
                variant = self.model.transformed(height_delta_m=height, ground=ground)
                variant = replace(variant, name=f"{self.model.name} · Δh {height:+g} m · {kind}")
                tasks.append((variant, f"assisted_candidate|{height}|{kind}"))
        self._start_worker(tasks)

    def _start_worker(self, tasks):
        if self.worker is not None and self.worker.isRunning():
            return
        self.run_button.setEnabled(False)
        self.solve_candidates.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.worker = _SolverThread(tasks, self.solver_path, self)
        self.worker.progress.connect(
            lambda index, total, name: self.status.setText(f"OpenNEC {index}/{total} · {name}")
        )
        self.worker.completed.connect(self._run_completed)
        self.worker.failed.connect(self._run_failed)
        self.worker.finished.connect(self._run_finished)
        self.worker.start()

    def _cancel_run(self):
        if self.worker is not None:
            self.worker.cancel()
            self.status.setText("Cancelling OpenNEC…")

    def _run_completed(self, model, result, metadata):
        stored = self.repository.save_nec_model(model)
        if metadata == "independent_baseline":
            run = self.repository.save_nec_run(
                stored.id, result, purpose="independent_baseline", label="Theoretical baseline before assisted fitting"
            )
            self.model = model
            self.stored_model = stored
            self.result = result
            self._reload_saved_models(stored.id)
            self._render_result()
            self.tabs.setCurrentIndex(1)
            self.status.setText(f"Baseline #{run.id} saved · {result.engine_version} · {result.duration_seconds:.2f} s")
        else:
            _purpose, height, kind = metadata.split("|")
            run = self.repository.save_nec_run(
                stored.id, result, purpose="assisted_candidate",
                label=f"Δh {float(height):+g} m · {kind}",
            )
            self._candidate_runs.append((run, float(height), kind))
            self._render_candidates()

    def _run_failed(self, message):
        self.status.setText(message)

    def _run_finished(self):
        self.run_button.setEnabled(self.solver_path is not None)
        self.solve_candidates.setEnabled(self.solver_path is not None)
        self.cancel_button.setEnabled(False)

    def _render_result(self):
        self.result_figure.clear()
        self.radiation_figure.clear()
        self.frequency_choice.blockSignals(True)
        self.frequency_choice.clear()
        if self.result is None:
            for figure, canvas in (
                (self.result_figure, self.result_canvas),
                (self.radiation_figure, self.radiation_canvas),
            ):
                apply_figure_theme(figure)
                canvas.draw_idle()
            self.frequency_choice.blockSignals(False)
            self.current_table.setRowCount(0)
            self.provenance.clear()
            return
        radiation_frequencies = tuple(
            dict.fromkeys(item.frequency_hz for item in self.result.radiation)
        )
        frequencies = radiation_frequencies or tuple(
            dict.fromkeys(item.frequency_hz for item in self.result.impedance)
        )
        for frequency in frequencies:
            self.frequency_choice.addItem(f"{frequency / 1e6:.6f} MHz", frequency)
        self.frequency_choice.blockSignals(False)
        frequency = self.frequency_choice.currentData()
        if frequency is None and frequencies:
            frequency = frequencies[0]
        relative = self.gain_mode.currentData() == "relative"
        radiation = [item for item in self.result.radiation if item.frequency_hz == frequency]
        peak = max((item.gain_db for item in radiation), default=0.0)

        impedance_axis = self.result_figure.add_subplot(221)
        swr_axis = self.result_figure.add_subplot(222)
        azimuth_axis = self.result_figure.add_subplot(223, projection="polar")
        elevation_axis = self.result_figure.add_subplot(224, projection="polar")
        frequencies_mhz = [item.frequency_hz / 1e6 for item in self.result.impedance]
        impedance_axis.plot(frequencies_mhz, [item.resistance_ohm for item in self.result.impedance], label="R Ω")
        impedance_axis.plot(frequencies_mhz, [item.reactance_ohm for item in self.result.impedance], label="X Ω")
        impedance_axis.axhline(50, color=TOKENS.chart_grid, linestyle="--", linewidth=0.8)
        impedance_axis.set_title("Feed-point impedance")
        impedance_axis.set_xlabel("MHz")
        impedance_axis.legend()
        swr_axis.plot(frequencies_mhz, [min(10, item.swr_50) for item in self.result.impedance], color=TOKENS.chart_series[2])
        swr_axis.axhline(2, color=TOKENS.warning, linestyle="--", linewidth=0.8)
        swr_axis.set_title("SWR 50 Ω")
        swr_axis.set_xlabel("MHz")
        azimuth_theta, azimuth_samples = select_azimuth_cut(radiation)
        azimuth = [(item.phi_deg, item.gain_db) for item in azimuth_samples]
        elevation = sorted((item.theta_deg, item.gain_db) for item in radiation if abs(item.phi_deg) <= 0.2)
        for axis, rows, title in (
            (
                azimuth_axis,
                azimuth,
                (
                    f"Azimuth θ={azimuth_theta:.0f}°"
                    if azimuth_theta is not None
                    else "Azimuth"
                ),
            ),
            (elevation_axis, elevation, "Elevation φ=0°"),
        ):
            values = [(radians(angle), gain - peak if relative else gain) for angle, gain in rows]
            if values:
                axis.plot([item[0] for item in values], [item[1] for item in values], color=TOKENS.accent)
                if relative:
                    axis.set_ylim(min(-30.0, min(item[1] for item in values)), 0.0)
            axis.set_theta_zero_location("N")
            axis.set_theta_direction(-1)
            axis.set_title(title)
        apply_figure_theme(self.result_figure)
        self.result_figure.tight_layout(pad=1.2)
        self.result_figure.subplots_adjust(hspace=0.62, wspace=0.24)
        self.result_canvas.draw_idle()

        self._render_radiation_3d(radiation, peak, relative)
        front = self._nearest_gain(azimuth, self.model.orientation_deg)
        back = self._nearest_gain(azimuth, self.model.orientation_deg + 180)
        self.peak_card.value.setText(f"{peak:.2f} dBi" if radiation else "—")
        self.fb_card.value.setText(f"{front - back:.1f} dB" if front is not None and back is not None else "—")
        self.current_table.setRowCount(len(self.result.currents))
        for row, item in enumerate(self.result.currents):
            for column, value in enumerate((f"{item.frequency_hz / 1e6:.6f}", item.wire_tag, item.segment, f"{item.magnitude_a:.6g}", f"{item.phase_deg:.1f}")):
                self.current_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.provenance.setPlainText(
            f"Schema: {self.result.schema}\n"
            f"Engine: {self.result.engine_version}\n"
            f"Executable: {self.result.engine_path}\n"
            f"Command: {' '.join(self.result.command)}\n"
            f"UTC: {self.result.started_at.isoformat()}\n"
            f"Duration: {self.result.duration_seconds:.3f} s\n"
            f"Model SHA-256: {self.result.model_sha256}\n"
            f"Input SHA-256: {self.result.input_sha256}\n"
            f"Output SHA-256: {self.result.output_sha256}"
        )

    def _render_radiation_3d(self, radiation, peak, relative):
        axis = self.radiation_figure.add_subplot(111, projection="3d")
        if radiation:
            theta_values = sorted({item.theta_deg for item in radiation})
            phi_values = sorted({item.phi_deg % 360.0 for item in radiation})
            by_angle = {
                (item.theta_deg, item.phi_deg % 360.0): item.gain_db
                for item in radiation
            }
            theta_grid, phi_grid = np.meshgrid(
                np.radians(theta_values),
                np.radians(phi_values),
                indexing="ij",
            )
            gain_grid = np.array(
                [
                    [
                        by_angle.get((theta, phi), peak - 60.0)
                        for phi in phi_values
                    ]
                    for theta in theta_values
                ]
            )
            radius_grid = 10 ** ((gain_grid - peak) / 20)
            x = radius_grid * np.sin(theta_grid) * np.cos(phi_grid)
            y = radius_grid * np.sin(theta_grid) * np.sin(phi_grid)
            z = radius_grid * np.cos(theta_grid)
            shown_gain = gain_grid - peak if relative else gain_grid
            normalizer = Normalize(
                vmin=float(np.nanmin(shown_gain)),
                vmax=float(np.nanmax(shown_gain)) or 1.0,
            )
            axis.plot_surface(
                x,
                y,
                z,
                facecolors=colormaps["viridis"](normalizer(shown_gain)),
                rstride=1,
                cstride=1,
                linewidth=0,
                antialiased=True,
                shade=True,
            )
        axis.set_xlabel("X")
        axis.set_ylabel("Y")
        axis.set_zlabel("Z")
        axis.set_box_aspect((1, 1, 1))
        axis.set_title("Far-field gain · " + ("relative dB" if relative else "absolute dBi"))
        apply_figure_theme(self.radiation_figure)
        self.radiation_figure.tight_layout(pad=1)
        self.radiation_canvas.draw_idle()

    @staticmethod
    def _nearest_gain(rows, target):
        if not rows:
            return None
        angle, gain = min(rows, key=lambda item: abs((item[0] - target + 180) % 360 - 180))
        return gain

    def _render_candidates(self):
        self.candidate_table.setRowCount(len(self._candidate_runs))
        for row, (stored, height, kind) in enumerate(self._candidate_runs):
            values = (
                stored.id, f"{height:+g}", kind, stored.result.engine_version,
                stored.result.input_sha256[:16], stored.result.output_sha256[:16],
            )
            for column, value in enumerate(values):
                self.candidate_table.setItem(row, column, QTableWidgetItem(str(value)))

    def _open_comparison(self):
        from .propagation_intelligence_dialog import PropagationIntelligenceDialog

        PropagationIntelligenceDialog(self.repository, self.language, self).exec()

    def reject(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(4000)
        super().reject()
