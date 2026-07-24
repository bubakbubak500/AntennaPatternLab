from pathlib import Path
import subprocess

import pytest

from antenna_pattern_lab.dependencies import (
    detect_external_tools,
    list_hamlib_rig_models,
    rigctld_command,
)


def test_detects_tools_from_path_without_executing_them(tmp_path):
    rigctld = tmp_path / "rigctld.exe"
    wsjtx = tmp_path / "wsjtx.exe"
    onec = tmp_path / "onec.exe"
    rigctld.touch()
    wsjtx.touch()
    onec.touch()

    def which(name, path=None):
        return str(tmp_path / name)

    statuses = detect_external_tools({"PATH": str(tmp_path)}, which=which)
    assert [status.found for status in statuses] == [True, True, True]
    assert statuses[0].executable == rigctld.resolve()
    assert statuses[2].executable == onec.resolve()


def test_detects_common_wsjt_x_location(tmp_path):
    executable = tmp_path / "wsjtx" / "bin" / "wsjtx.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    statuses = detect_external_tools(
        {"ProgramFiles": str(tmp_path), "PATH": ""},
        which=lambda *_args, **_kwargs: None,
    )
    assert not statuses[0].found
    assert statuses[1].executable == executable.resolve()


def test_detects_versioned_hamlib_directory(tmp_path):
    executable = tmp_path / "hamlib-w64-4.7.2" / "bin" / "rigctld.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    statuses = detect_external_tools(
        {"ProgramFiles": str(tmp_path), "PATH": ""},
        which=lambda *_args, **_kwargs: None,
    )
    assert statuses[0].executable == executable.resolve()


def test_detects_separately_installed_opennec(tmp_path):
    executable = tmp_path / "Programs" / "OpenNEC" / "bin" / "onec.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    statuses = detect_external_tools(
        {"LOCALAPPDATA": str(tmp_path), "PATH": ""},
        which=lambda *_args, **_kwargs: None,
    )
    assert statuses[2].key == "opennec"
    assert statuses[2].executable == executable.resolve()


def test_derives_system_drive_for_wsjt_x_when_environment_omits_it(tmp_path):
    drive = tmp_path / "drive"
    executable = drive / "WSJT" / "wsjtx" / "bin" / "wsjtx.exe"
    executable.parent.mkdir(parents=True)
    executable.touch()
    statuses = detect_external_tools(
        {"ProgramFiles": str(drive / "Program Files"), "PATH": ""},
        which=lambda *_args, **_kwargs: None,
    )
    assert statuses[1].executable == executable.resolve()


def test_rigctld_command_is_explicit_and_validated():
    command = rigctld_command("rigctld.exe", 3073, "COM4", 19200)
    assert command == (
        "rigctld.exe", "-m", "3073", "-r", "COM4", "-s", "19200", "-t", "4532"
    )
    with pytest.raises(ValueError):
        rigctld_command("rigctld.exe", 0, "COM4", 19200)


def test_parses_model_ids_and_names_reported_by_installed_hamlib():
    output = """\
 Rig #  Mfg                    Model                   Version         Status      Macro
     1  Hamlib                 Dummy                   20240709.0      Stable      RIG_MODEL_DUMMY
  1001  Yaesu                  FT-847                  20230512.0      Stable      RIG_MODEL_FT847
  3073  Icom                   IC-7300                 20250101.0      Beta        RIG_MODEL_IC7300
"""

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess(("rigctld.exe", "-l"), 0, output, "")

    models = list_hamlib_rig_models("rigctld.exe", runner=runner)
    assert [model.model_id for model in models] == [1, 1001, 3073]
    assert models[2].manufacturer == "Icom"
    assert models[2].model == "IC-7300"
    assert models[2].display_name == "3073 — Icom IC-7300 [Beta]"


def test_rejects_unrecognized_hamlib_model_output():
    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess(("rigctld.exe", "-l"), 0, "unexpected", "")

    with pytest.raises(ValueError, match="recognizable"):
        list_hamlib_rig_models("rigctld.exe", runner=runner)
