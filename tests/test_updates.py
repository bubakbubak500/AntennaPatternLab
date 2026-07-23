from io import BytesIO
import hashlib
import json

import pytest

from antenna_pattern_lab.updates import (
    DEFAULT_RELEASE_MANIFEST_URL,
    download_verified_installer,
    parse_release_manifest,
)


class Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_default_release_channel_is_official_github_latest_release():
    assert DEFAULT_RELEASE_MANIFEST_URL == (
        "https://github.com/bubakbubak500/AntennaPatternLab/"
        "releases/latest/download/release-manifest.json"
    )


def test_manifest_requires_https_hash_and_newer_semver():
    payload = json.dumps(
        {
            "version": "0.16.0",
            "installer_url": "https://releases.example/AntennaPatternLab-0.16.0.exe",
            "sha256": "a" * 64,
            "notes_url": "https://releases.example/0.16.0.html",
        }
    )
    check = parse_release_manifest(payload, "0.15.0")
    assert check.update_available
    assert check.manifest.filename == "AntennaPatternLab-0.16.0.exe"
    assert parse_release_manifest(b"\xef\xbb\xbf" + payload.encode(), "0.15.0").update_available
    with pytest.raises(ValueError):
        parse_release_manifest(payload.replace("https://", "http://", 1), "0.15.0")


def test_download_is_published_only_after_sha256_matches(tmp_path):
    content = b"signed installer bytes"
    payload = json.dumps(
        {
            "version": "1.0.0",
            "installer_url": "https://releases.example/setup.exe",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    )
    manifest = parse_release_manifest(payload, "0.15.0").manifest
    result = download_verified_installer(
        manifest, tmp_path, opener=lambda *_args, **_kwargs: Response(content)
    )
    assert result.read_bytes() == content
    assert not (tmp_path / "setup.exe.part").exists()


def test_hash_mismatch_removes_partial_download(tmp_path):
    payload = json.dumps(
        {
            "version": "1.0.0",
            "installer_url": "https://releases.example/setup.exe",
            "sha256": "0" * 64,
        }
    )
    manifest = parse_release_manifest(payload, "0.15.0").manifest
    with pytest.raises(ValueError, match="SHA-256"):
        download_verified_installer(
            manifest, tmp_path, opener=lambda *_args, **_kwargs: Response(b"tampered")
        )
    assert list(tmp_path.iterdir()) == []
