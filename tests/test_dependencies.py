from pathlib import Path

import pytest

from antenna_pattern_lab.dependencies import detect_external_tools, rigctld_command


def test_detects_tools_from_path_without_executing_them(tmp_path):
    rigctld = tmp_path / "rigctld.exe"
    wsjtx = tmp_path / "wsjtx.exe"
    rigctld.touch()
    wsjtx.touch()

    def which(name, path=None):
        return str(tmp_path / name)

    statuses = detect_external_tools({"PATH": str(tmp_path)}, which=which)
    assert [status.found for status in statuses] == [True, True]
    assert statuses[0].executable == rigctld.resolve()


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
