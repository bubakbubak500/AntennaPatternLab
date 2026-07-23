import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from antenna_pattern_lab.experiment_dialog import ExperimentDialog
from antenna_pattern_lab.profiles import AntennaProfile
from antenna_pattern_lab.storage import SpotRepository


def test_experiment_dialog_confirms_profile_before_recording(tmp_path):
    application = QApplication.instance() or QApplication([])
    repository = SpotRepository(tmp_path / "experiment.sqlite3")
    profile_a = repository.save_antenna_profile(
        AntennaProfile(id=None, name="A", antenna_type="vertical")
    )
    profile_b = repository.save_antenna_profile(
        AntennaProfile(id=None, name="B", antenna_type="dipole")
    )
    selected = []
    dialog = ExperimentDialog(repository, "ENG", selected.append)
    assert dialog.canvas.minimumHeight() >= 260
    assert dialog.table.columnCount() == 10
    assert dialog.alignment_table.rowCount() == 2
    assert dialog.alignment_table.columnCount() == 9
    assert dialog.data_splitter.orientation().name == "Vertical"
    dialog.target_bearing.setValue(90)
    dialog.max_swr.setValue(1.8)
    dialog.suggest_experiment()
    assert "not a prediction of real gain" in dialog.plan_result.text()
    assert "SWR ≤ 1.8" in dialog.plan_result.text()
    assert dialog.profile_a.currentData() != dialog.profile_b.currentData()
    dialog.start_protocol()
    assert selected == []
    assert dialog.confirm_button.isEnabled()
    dialog.confirm_switch()
    assert selected == [profile_a.id]
    assert dialog.protocol.active_profile_id == profile_a.id
    dialog.stop_protocol()
    assert dialog.protocol is None
    dialog.close()
    application.processEvents()
