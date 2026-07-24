from datetime import datetime, timezone
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.antenna_modeling_dialog import AntennaModelingDialog
from antenna_pattern_lab.nec_runner import (
    CurrentSample,
    ImpedancePoint,
    NecRunResult,
    RadiationSample,
)
from antenna_pattern_lab.storage import SpotRepository


def _dialog(tmp_path, monkeypatch, language="ENG"):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "antenna_pattern_lab.antenna_modeling_dialog.detect_opennec",
        lambda: None,
    )
    dialog = AntennaModelingDialog(
        SpotRepository(tmp_path / "modeling.sqlite3"),
        language,
    )
    return application, dialog


def _result(model):
    radiation = tuple(
        RadiationSample(14_074_000, theta, phi, 6 - abs(theta - 60) / 10 - abs(phi - 90) / 90)
        for theta in range(0, 91, 15)
        for phi in range(0, 361, 30)
    )
    return NecRunResult(
        model.sha256,
        "C:/OpenNEC/onec.exe",
        "OpenNEC 2.2.0",
        ("onec.exe", "-f", "original", "-o", "model.out", "model.nec"),
        datetime(2026, 7, 24, tzinfo=timezone.utc),
        0.4,
        "a" * 64,
        "b" * 64,
        (
            ImpedancePoint(14_000_000, 43, -8, 1.25),
            ImpedancePoint(14_074_000, 51, 1, 1.03),
            ImpedancePoint(14_200_000, 68, 12, 1.42),
        ),
        radiation,
        (CurrentSample(14_074_000, 1, 11, 0.12, -5),),
        "normal output",
    )


def test_workbench_exposes_editor_validation_and_solver_gating(tmp_path, monkeypatch):
    _application, dialog = _dialog(tmp_path, monkeypatch)

    assert dialog.tabs.count() == 4
    assert dialog.wire_table.rowCount() == 2
    assert dialog.validation.toPlainText() == "✓ OK"
    assert not dialog.run_button.isEnabled()
    assert "OpenNEC" in dialog.solver_indicator.text()
    assert dialog.geometry_figure.axes[0].name == "3d"
    dialog.close()


def test_workbench_saves_model_revision_and_renders_all_result_views(tmp_path, monkeypatch):
    application, dialog = _dialog(tmp_path, monkeypatch)
    dialog._save_model()
    first = dialog.stored_model
    dialog.model_name.setText(first.name)
    dialog.frequency_stop.setValue(dialog.frequency_stop.value() + 0.1)
    dialog._save_model()

    assert dialog.stored_model.revision == 2
    result = _result(dialog.model)
    dialog._run_completed(dialog.model, result, "independent_baseline")
    application.processEvents()

    assert len(dialog.result_figure.axes) == 4
    assert dialog.radiation_figure.axes[0].name == "3d"
    assert dialog.current_table.rowCount() == 1
    assert result.output_sha256 in dialog.provenance.toPlainText()
    assert dialog.repository.list_nec_runs(purpose="independent_baseline")
    assert dialog.result_figure.axes[3].get_xlabel() == "Elevation above horizon (°)"
    assert "30.0°" in dialog.takeoff_value.text()
    assert "934 km" in dialog.f2_hop_value.text()
    assert "does not calculate ground wave" in dialog.groundwave_value.text()
    dialog.close()


def test_candidate_grid_covers_height_and_ground_parameters(tmp_path, monkeypatch):
    _application, dialog = _dialog(tmp_path, monkeypatch)
    captured = []
    dialog.solver_path = "onec.exe"
    monkeypatch.setattr(dialog, "_start_worker", lambda tasks: captured.extend(tasks))
    dialog.height_offsets.setText("-1, 2")
    dialog.ground_variants.setText("real, perfect, free_space")

    dialog._run_candidates()

    assert len(captured) == 6
    assert {model.ground.kind for model, _metadata in captured} == {
        "real",
        "perfect",
        "free_space",
    }
    assert {metadata.split("|")[1] for _model, metadata in captured} == {"-1.0", "2.0"}
    assert all(model.to_nec().isascii() for model, _metadata in captured)
    dialog.close()
