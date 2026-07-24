from datetime import datetime, timezone

import pytest

from antenna_pattern_lab.antenna_model import antenna_template
from antenna_pattern_lab.nec_runner import (
    ImpedancePoint,
    NecRunResult,
    RadiationSample,
)
from antenna_pattern_lab.storage import SpotRepository


def _result(model):
    return NecRunResult(
        model.sha256,
        "onec.exe",
        "OpenNEC 2.2.0",
        ("onec.exe", "model.nec"),
        datetime(2026, 7, 24, tzinfo=timezone.utc),
        0.3,
        "1" * 64,
        "2" * 64,
        (ImpedancePoint(14_074_000, 50, 0, 1),),
        (
            RadiationSample(14_074_000, 90, 0, 2),
            RadiationSample(14_074_000, 90, 90, 5),
        ),
        (),
        "normal NEC output",
    )


def test_models_are_immutable_revisions_and_identical_save_is_deduplicated(tmp_path):
    repository = SpotRepository(tmp_path / "models.sqlite3")
    first_model = antenna_template("dipole")
    first = repository.save_nec_model(first_model)
    duplicate = repository.save_nec_model(first_model)
    changed = repository.save_nec_model(
        first_model.transformed(height_delta_m=2)
    )

    assert duplicate.id == first.id
    assert changed.revision == 2
    assert changed.predecessor_id == first.id
    assert repository.list_nec_models() == [changed]
    assert len(repository.list_nec_models(latest_only=False)) == 2


def test_baseline_run_retains_exact_model_and_provenance(tmp_path):
    repository = SpotRepository(tmp_path / "runs.sqlite3")
    model = antenna_template("vertical")
    stored = repository.save_nec_model(model)
    result = _result(model)

    run = repository.save_nec_run(
        stored.id,
        result,
        purpose="independent_baseline",
        label="Before measurements",
    )

    assert run.result == result
    assert run.label == "Before measurements"
    assert repository.list_nec_runs(model_id=stored.id)[0] == run


def test_run_must_match_saved_model_revision(tmp_path):
    repository = SpotRepository(tmp_path / "mismatch.sqlite3")
    stored = repository.save_nec_model(antenna_template("dipole"))

    with pytest.raises(ValueError, match="does not match"):
        repository.save_nec_run(stored.id, _result(antenna_template("loop")))
