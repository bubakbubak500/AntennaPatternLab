from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Callable, Mapping

HAMLIB_RELEASES_URL = "https://github.com/Hamlib/Hamlib/releases/latest"
WSJTX_DOWNLOADS_URL = "https://wsjtx.github.io/wsjtx/downloads.html"
OPENNEC_RELEASES_URL = "https://github.com/maurymarkowitz/OpenNEC/releases/latest"


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    key: str
    display_name: str
    found: bool
    executable: Path | None
    official_url: str


@dataclass(frozen=True, slots=True)
class HamlibRigModel:
    model_id: int
    manufacturer: str
    model: str
    version: str
    status: str

    @property
    def display_name(self) -> str:
        return f"{self.model_id} — {self.manufacturer} {self.model} [{self.status}]"


def detect_external_tools(
    environment: Mapping[str, str] | None = None,
    which: Callable[..., str | None] = shutil.which,
) -> tuple[DependencyStatus, ...]:
    """Detect tools without executing them or modifying the system."""
    env = {
        key.casefold(): value
        for key, value in (os.environ if environment is None else environment).items()
    }
    if not env.get("systemdrive"):
        program_files = Path(env.get("programfiles", ""))
        if program_files.name.casefold() in {"program files", "program files (x86)"}:
            system_drive = str(program_files.parent)
        else:
            system_drive = program_files.anchor or Path.home().anchor or "C:\\"
        env["systemdrive"] = system_drive
    elif len(env["systemdrive"]) == 2 and env["systemdrive"].endswith(":"):
        env["systemdrive"] += "\\"
    hamlib = _find_executable(
        "rigctld.exe",
        env,
        which,
        relative_candidates=(
            ("ProgramFiles", "Hamlib", "bin", "rigctld.exe"),
            ("ProgramFiles(x86)", "Hamlib", "bin", "rigctld.exe"),
            ("LOCALAPPDATA", "Programs", "Hamlib", "bin", "rigctld.exe"),
        ),
        glob_candidates=(
            ("ProgramFiles", "hamlib-w64-*", "bin", "rigctld.exe"),
            ("ProgramFiles(x86)", "hamlib-w64-*", "bin", "rigctld.exe"),
            ("LOCALAPPDATA", "Programs", "hamlib-w64-*", "bin", "rigctld.exe"),
        ),
    )
    wsjtx = _find_executable(
        "wsjtx.exe",
        env,
        which,
        relative_candidates=(
            ("ProgramFiles", "wsjtx", "bin", "wsjtx.exe"),
            ("ProgramFiles", "WSJT-X", "bin", "wsjtx.exe"),
            ("ProgramFiles(x86)", "wsjtx", "bin", "wsjtx.exe"),
            ("ProgramFiles(x86)", "WSJT-X", "bin", "wsjtx.exe"),
            ("LOCALAPPDATA", "Programs", "wsjtx", "bin", "wsjtx.exe"),
            ("LOCALAPPDATA", "Programs", "WSJT-X", "bin", "wsjtx.exe"),
            ("LOCALAPPDATA", "WSJT-X", "bin", "wsjtx.exe"),
            ("SystemDrive", "WSJT", "wsjtx", "bin", "wsjtx.exe"),
        ),
    )
    opennec = _find_executable(
        "onec.exe",
        env,
        which,
        relative_candidates=(
            ("ProgramFiles", "OpenNEC", "bin", "onec.exe"),
            ("ProgramFiles", "OpenNEC", "onec.exe"),
            ("ProgramFiles(x86)", "OpenNEC", "bin", "onec.exe"),
            ("ProgramFiles(x86)", "OpenNEC", "onec.exe"),
            ("LOCALAPPDATA", "Programs", "OpenNEC", "bin", "onec.exe"),
            ("LOCALAPPDATA", "Programs", "OpenNEC", "onec.exe"),
        ),
    )
    return (
        DependencyStatus("hamlib", "Hamlib rigctld", hamlib is not None, hamlib, HAMLIB_RELEASES_URL),
        DependencyStatus("wsjtx", "WSJT-X", wsjtx is not None, wsjtx, WSJTX_DOWNLOADS_URL),
        DependencyStatus(
            "opennec",
            "OpenNEC (NEC-2 solver)",
            opennec is not None,
            opennec,
            OPENNEC_RELEASES_URL,
        ),
    )


def detect_opennec(
    environment: Mapping[str, str] | None = None,
    which: Callable[..., str | None] = shutil.which,
) -> Path | None:
    """Return the detected standalone OpenNEC executable, without running it."""
    for status in detect_external_tools(environment, which):
        if status.key == "opennec":
            return status.executable
    return None


def _find_executable(
    filename: str,
    env: Mapping[str, str],
    which: Callable[..., str | None],
    *,
    relative_candidates: tuple[tuple[str, ...], ...],
    glob_candidates: tuple[tuple[str, ...], ...] = (),
) -> Path | None:
    found = which(filename, path=env.get("path"))
    if found:
        path = Path(found)
        if path.is_file():
            return path.resolve()
    for parts in relative_candidates:
        root = env.get(parts[0].casefold())
        if not root:
            continue
        candidate = Path(root).joinpath(*parts[1:])
        if candidate.is_file():
            return candidate.resolve()
    for parts in glob_candidates:
        root = env.get(parts[0].casefold())
        if not root:
            continue
        matches = sorted(
            Path(root).glob(str(Path(*parts[1:]))),
            key=lambda path: path.parent.parent.name.casefold(),
            reverse=True,
        )
        for candidate in matches:
            if candidate.is_file():
                return candidate.resolve()
    return None


def rigctld_command(
    executable: str | Path,
    model_id: int,
    serial_port: str,
    baud_rate: int,
    tcp_port: int = 4532,
) -> tuple[str, ...]:
    if model_id < 1:
        raise ValueError("Hamlib model ID must be positive.")
    if not serial_port.strip():
        raise ValueError("Serial port is required.")
    if baud_rate < 300 or tcp_port not in range(1, 65536):
        raise ValueError("Baud rate or TCP port is invalid.")
    return (
        str(executable), "-m", str(model_id), "-r", serial_port.strip(),
        "-s", str(baud_rate), "-t", str(tcp_port),
    )


def list_hamlib_rig_models(
    executable: str | Path,
    *,
    timeout: float = 10.0,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[HamlibRigModel, ...]:
    """Return the radio backends reported by the installed Hamlib version."""
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = runner(
        (str(executable), "-l"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=True,
        creationflags=creationflags,
    )
    lines = result.stdout.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if "Rig #" in line and "Mfg" in line),
        None,
    )
    if header_index is None:
        raise ValueError("Hamlib did not return a recognizable rig model list.")
    header = lines[header_index]
    columns = tuple(header.index(name) for name in ("Rig #", "Mfg", "Model", "Version", "Status"))
    models: list[HamlibRigModel] = []
    for line in lines[header_index + 1 :]:
        if not line.strip():
            continue
        fields = tuple(
            line[columns[index] : columns[index + 1]].strip()
            for index in range(len(columns) - 1)
        ) + (line[columns[-1] :].split(maxsplit=1)[0],)
        try:
            model_id = int(fields[0])
        except (ValueError, IndexError):
            continue
        models.append(HamlibRigModel(model_id, *fields[1:]))
    if not models:
        raise ValueError("Hamlib returned an empty rig model list.")
    return tuple(models)


def tcp_port_is_open(port: int, host: str = "127.0.0.1", timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def launch_rigctld(command: tuple[str, ...]) -> int:
    """Launch rigctld independently and return its process identifier."""
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NO_WINDOW
        )
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    return process.pid
