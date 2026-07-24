import hashlib
import io
import json
import zipfile

import pytest

from antenna_pattern_lab.external_install import (
    ReleaseAsset,
    download_release_asset,
    fetch_release_asset,
    install_opennec_archive,
    launch_installer,
)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_fetch_release_asset_selects_official_x64_asset_with_digest():
    content = b"vendor installer"
    digest = hashlib.sha256(content).hexdigest()
    metadata = {
        "tag_name": "v3.0.2",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "wsjtx-3.0.2-win64.exe",
                "state": "uploaded",
                "browser_download_url": (
                    "https://github.com/WSJTX/wsjtx/releases/download/"
                    "v3.0.2/wsjtx-3.0.2-win64.exe"
                ),
                "digest": f"sha256:{digest}",
                "size": len(content),
            }
        ],
    }
    asset = fetch_release_asset(
        "wsjtx",
        opener=lambda *_args, **_kwargs: Response(json.dumps(metadata).encode()),
    )
    assert asset.version == "3.0.2"
    assert asset.sha256 == digest


def test_fetch_release_asset_rejects_unverified_or_nonofficial_asset():
    metadata = {
        "tag_name": "4.7.1",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "hamlib-w64-4.7.1.exe",
                "state": "uploaded",
                "browser_download_url": "https://example.test/hamlib.exe",
                "digest": None,
                "size": 20,
            }
        ],
    }
    with pytest.raises(ValueError, match="official host"):
        fetch_release_asset(
            "hamlib",
            opener=lambda *_args, **_kwargs: Response(json.dumps(metadata).encode()),
        )


def test_fetch_release_asset_selects_opennec_windows_portable_package():
    content = b"portable package"
    digest = hashlib.sha256(content).hexdigest()
    metadata = {
        "tag_name": "v.2.2.0",
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": "onec-windows-x86_64-openblas.zip",
                "state": "uploaded",
                "browser_download_url": (
                    "https://github.com/maurymarkowitz/OpenNEC/releases/download/"
                    "v.2.2.0/onec-windows-x86_64-openblas.zip"
                ),
                "digest": f"sha256:{digest}",
                "size": len(content),
            },
            {
                "name": "onec-windows-x86_64.zip",
                "state": "uploaded",
                "browser_download_url": (
                    "https://github.com/maurymarkowitz/OpenNEC/releases/download/"
                    "v.2.2.0/onec-windows-x86_64.zip"
                ),
                "digest": f"sha256:{digest}",
                "size": len(content),
            },
        ],
    }
    asset = fetch_release_asset(
        "opennec",
        opener=lambda *_args, **_kwargs: Response(json.dumps(metadata).encode()),
    )
    assert asset.version == "2.2.0"
    assert asset.filename == "onec-windows-x86_64.zip"


def test_download_release_asset_is_atomic_and_verifies_sha256(tmp_path):
    content = b"verified installer bytes"
    asset = ReleaseAsset(
        key="hamlib",
        version="4.7.1",
        filename="hamlib-w64-4.7.1.exe",
        download_url=(
            "https://github.com/Hamlib/Hamlib/releases/download/"
            "4.7.1/hamlib-w64-4.7.1.exe"
        ),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )
    progress = []
    result = download_release_asset(
        asset,
        tmp_path,
        opener=lambda *_args, **_kwargs: Response(content),
        progress=lambda received, total: progress.append((received, total)),
    )
    assert result.read_bytes() == content
    assert progress[-1] == (len(content), len(content))
    assert not (tmp_path / f"{asset.filename}.part").exists()

    invalid = ReleaseAsset(
        key=asset.key,
        version=asset.version,
        filename="bad.exe",
        download_url=asset.download_url,
        sha256="0" * 64,
        size=asset.size,
    )
    with pytest.raises(ValueError, match="SHA-256"):
        download_release_asset(
            invalid,
            tmp_path,
            opener=lambda *_args, **_kwargs: Response(content),
        )
    assert not (tmp_path / "bad.exe.part").exists()


def test_launch_installer_uses_windows_shell_so_uac_can_be_shown(tmp_path):
    installer = tmp_path / "vendor-setup.exe"
    installer.write_bytes(b"MZ")
    launched = []
    launch_installer(
        installer,
        shell_execute=lambda path: launched.append(path) or 42,
    )
    assert launched == [installer.resolve()]

    with pytest.raises(OSError, match="code 31"):
        launch_installer(installer, shell_execute=lambda _path: 31)


def test_installs_opennec_zip_into_separate_directory(tmp_path):
    archive = tmp_path / "onec-windows-x86_64.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("bin/onec.exe", b"MZ")
        package.writestr("docs/README.md", b"OpenNEC")
    destination = tmp_path / "Programs" / "OpenNEC"

    executable = install_opennec_archive(archive, destination)

    assert executable == destination / "bin" / "onec.exe"
    assert executable.read_bytes() == b"MZ"
    assert (destination / "docs" / "README.md").is_file()


def test_opennec_zip_install_rejects_path_traversal(tmp_path):
    archive = tmp_path / "onec-windows-x86_64.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("../outside.exe", b"MZ")
        package.writestr("bin/onec.exe", b"MZ")

    with pytest.raises(ValueError, match="unsafe path"):
        install_opennec_archive(archive, tmp_path / "Programs" / "OpenNEC")
    assert not (tmp_path / "outside.exe").exists()
