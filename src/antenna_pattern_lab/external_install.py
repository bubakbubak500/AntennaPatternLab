from __future__ import annotations

from dataclasses import dataclass
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import zipfile


API_URLS = {
    "hamlib": "https://api.github.com/repos/Hamlib/Hamlib/releases/latest",
    "wsjtx": "https://api.github.com/repos/WSJTX/wsjtx/releases/latest",
    "opennec": "https://api.github.com/repos/maurymarkowitz/OpenNEC/releases/latest",
}
ASSET_PATTERNS = {
    "hamlib": re.compile(r"^hamlib-w64-[0-9][A-Za-z0-9._-]*\.exe$", re.IGNORECASE),
    "wsjtx": re.compile(r"^wsjtx-[0-9][A-Za-z0-9._-]*-win64\.exe$", re.IGNORECASE),
    "opennec": re.compile(r"^onec-windows-x86_64\.zip$", re.IGNORECASE),
}
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_INSTALLER_BYTES = 300 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    key: str
    version: str
    filename: str
    download_url: str
    sha256: str
    size: int


def _open(request, *, timeout: int = 30):
    return urlopen(request, timeout=timeout)


def _validate_download_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in DOWNLOAD_HOSTS:
        raise ValueError("Release asset points outside the approved official host.")


def fetch_release_asset(
    key: str,
    opener: Callable[..., object] = _open,
) -> ReleaseAsset:
    """Resolve the latest official x64 Windows asset and its GitHub digest."""

    if key not in API_URLS:
        raise ValueError("Unsupported external tool.")
    request = Request(
        API_URLS[key],
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AntennaPatternLab",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with opener(request, timeout=30) as response:
        payload = response.read(MAX_METADATA_BYTES + 1)
    if len(payload) > MAX_METADATA_BYTES:
        raise ValueError("Release metadata is unexpectedly large.")
    data = json.loads(payload.decode("utf-8"))
    if data.get("draft") or data.get("prerelease"):
        raise ValueError("The latest release is not a stable published release.")
    pattern = ASSET_PATTERNS[key]
    asset = next(
        (
            item
            for item in data.get("assets", [])
            if item.get("state") == "uploaded"
            and pattern.fullmatch(str(item.get("name", "")))
        ),
        None,
    )
    if asset is None:
        raise ValueError("No official x64 Windows package was found.")
    filename = str(asset["name"])
    download_url = str(asset["browser_download_url"])
    _validate_download_url(download_url)
    digest = str(asset.get("digest") or "")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("The official release does not publish a usable SHA-256 digest.")
    size = int(asset.get("size", 0))
    if not 0 < size <= MAX_INSTALLER_BYTES:
        raise ValueError("Installer size is outside the allowed range.")
    return ReleaseAsset(
        key=key,
        version=str(data.get("tag_name") or data.get("name") or "").lstrip("v."),
        filename=filename,
        download_url=download_url,
        sha256=digest.split(":", 1)[1].lower(),
        size=size,
    )


def download_release_asset(
    asset: ReleaseAsset,
    destination: Path,
    *,
    progress: Callable[[int, int], None] | None = None,
    opener: Callable[..., object] = _open,
) -> Path:
    """Download atomically and accept only the release asset's exact digest."""

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    final_path = destination / asset.filename
    partial_path = destination / f"{asset.filename}.part"
    request = Request(
        asset.download_url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "AntennaPatternLab",
        },
    )
    digest = hashlib.sha256()
    received = 0
    try:
        with opener(request, timeout=60) as response, partial_path.open("wb") as target:
            response_url = getattr(response, "geturl", lambda: asset.download_url)()
            _validate_download_url(str(response_url))
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                if received > MAX_INSTALLER_BYTES or received > asset.size:
                    raise ValueError("Downloaded installer is larger than release metadata.")
                target.write(chunk)
                digest.update(chunk)
                if progress:
                    progress(received, asset.size)
        if received != asset.size:
            raise ValueError("Downloaded installer size does not match release metadata.")
        if digest.hexdigest().lower() != asset.sha256.lower():
            raise ValueError("Downloaded installer failed SHA-256 verification.")
        partial_path.replace(final_path)
        return final_path
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise


def _windows_shell_execute(path: Path) -> int:
    """Open an executable through ShellExecute so Windows can show UAC."""

    if os.name != "nt":
        raise OSError("Vendor installers can only be launched on Windows.")
    execute = ctypes.windll.shell32.ShellExecuteW
    execute.restype = ctypes.c_void_p
    result = execute(
        None,
        "open",
        str(path),
        None,
        str(path.parent),
        1,
    )
    return int(result or 0)


def launch_installer(
    path: Path,
    *,
    shell_execute: Callable[[Path], int] = _windows_shell_execute,
) -> None:
    """Launch a verified vendor installer through the Windows shell/UAC."""

    resolved = Path(path).resolve(strict=True)
    if resolved.suffix.lower() != ".exe":
        raise ValueError("Only Windows executable installers can be launched.")
    result = shell_execute(resolved)
    if result <= 32:
        raise OSError(f"Windows ShellExecute failed with code {result}.")


def install_opennec_archive(archive: Path, destination: Path) -> Path:
    """Install a verified OpenNEC ZIP as a separate per-user tool.

    The archive is extracted into a staging directory and becomes visible only
    after its expected executable has been found. Existing installations are
    retained until that atomic replacement succeeds.
    """

    resolved_archive = Path(archive).resolve(strict=True)
    if resolved_archive.suffix.lower() != ".zip":
        raise ValueError("OpenNEC must be installed from its official ZIP package.")
    destination = Path(destination).resolve()
    if destination.parent == destination or not destination.name:
        raise ValueError("OpenNEC installation destination is invalid.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=".opennec-staging-", dir=destination.parent)
    )
    backup: Path | None = None
    try:
        total_size = 0
        with zipfile.ZipFile(resolved_archive) as source:
            for member in source.infolist():
                normalized = member.filename.replace("\\", "/")
                parts = tuple(
                    part
                    for part in normalized.split("/")
                    if part not in ("", ".")
                )
                if not parts or normalized.startswith("/") or ".." in parts:
                    raise ValueError("OpenNEC archive contains an unsafe path.")
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError(
                        "OpenNEC archive contains an unsupported symbolic link."
                    )
                total_size += member.file_size
                if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    raise ValueError("OpenNEC archive is unexpectedly large.")
                target = staging.joinpath(*parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(member) as input_file, target.open(
                    "wb"
                ) as output_file:
                    shutil.copyfileobj(input_file, output_file)

        staged_executable = staging / "bin" / "onec.exe"
        if not staged_executable.is_file():
            raise ValueError("OpenNEC archive does not contain bin/onec.exe.")

        if destination.exists():
            backup = Path(
                tempfile.mkdtemp(prefix=".opennec-backup-", dir=destination.parent)
            )
            backup.rmdir()
            destination.replace(backup)
        try:
            staging.replace(destination)
        except Exception:
            if backup is not None and backup.exists() and not destination.exists():
                backup.replace(destination)
            raise
        if backup is not None:
            shutil.rmtree(backup)
            backup = None
        return destination / "bin" / "onec.exe"
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup is not None and backup.exists() and destination.exists():
            shutil.rmtree(backup)
