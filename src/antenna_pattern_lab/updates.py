from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Callable
from urllib.parse import urlparse
from urllib.request import urlopen


DEFAULT_RELEASE_MANIFEST_URL = (
    "https://github.com/bubakbubak500/AntennaPatternLab/"
    "releases/latest/download/release-manifest.json"
)


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    version: str
    installer_url: str
    sha256: str
    notes_url: str = ""

    def validated(self) -> "ReleaseManifest":
        _version_tuple(self.version)
        if urlparse(self.installer_url).scheme.lower() != "https":
            raise ValueError("Installer URL must use HTTPS.")
        if self.notes_url and urlparse(self.notes_url).scheme.lower() != "https":
            raise ValueError("Release notes URL must use HTTPS.")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256):
            raise ValueError("Release SHA-256 is invalid.")
        return self

    @property
    def filename(self) -> str:
        name = Path(urlparse(self.installer_url).path).name
        if not name.lower().endswith(".exe"):
            raise ValueError("Release asset must be a Windows .exe installer.")
        return name


@dataclass(frozen=True, slots=True)
class UpdateCheck:
    manifest: ReleaseManifest
    update_available: bool


def parse_release_manifest(payload: bytes | str, current_version: str) -> UpdateCheck:
    raw = json.loads(payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload.lstrip("\ufeff"))
    if not isinstance(raw, dict):
        raise ValueError("Release manifest must be a JSON object.")
    manifest = ReleaseManifest(
        version=str(raw.get("version", "")),
        installer_url=str(raw.get("installer_url", "")),
        sha256=str(raw.get("sha256", "")),
        notes_url=str(raw.get("notes_url", "")),
    ).validated()
    manifest.filename
    return UpdateCheck(manifest, _version_tuple(manifest.version) > _version_tuple(current_version))


def check_for_update(
    manifest_url: str,
    current_version: str,
    *,
    opener: Callable = urlopen,
    timeout: float = 10.0,
) -> UpdateCheck:
    if urlparse(manifest_url).scheme.lower() != "https":
        raise ValueError("Release manifest URL must use HTTPS.")
    with opener(manifest_url, timeout=timeout) as response:
        payload = response.read(1_000_001)
    if len(payload) > 1_000_000:
        raise ValueError("Release manifest is too large.")
    return parse_release_manifest(payload, current_version)


def download_verified_installer(
    manifest: ReleaseManifest,
    destination_directory: str | Path,
    *,
    opener: Callable = urlopen,
    timeout: float = 60.0,
) -> Path:
    manifest = manifest.validated()
    destination = Path(destination_directory)
    destination.mkdir(parents=True, exist_ok=True)
    final_path = destination / manifest.filename
    temporary_path = final_path.with_suffix(final_path.suffix + ".part")
    digest = hashlib.sha256()
    try:
        with opener(manifest.installer_url, timeout=timeout) as response, temporary_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest().lower() != manifest.sha256.lower():
            raise ValueError("Downloaded installer failed SHA-256 verification.")
        temporary_path.replace(final_path)
        return final_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        raise ValueError("Version must use major.minor.patch format.")
    return tuple(int(part) for part in match.groups())
