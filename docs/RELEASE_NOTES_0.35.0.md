# Antenna Pattern Lab 0.35.0

This release establishes the public GitHub update channel and improves Windows
shell integration.

## What changed

- The application now checks the official GitHub Releases channel in the
  background on every startup. Offline or temporary GitHub failures are silent.
- The Updates dialog now explains the download, SHA-256 verification, and
  installation flow instead of exposing an editable manifest URL.
- The application process, Start menu shortcut, and desktop shortcut now share
  the stable Windows AppUserModelID `OK7PS.AntennaPatternLab`.
- The installer deploys the application icon explicitly for Windows shortcuts.
- Release assets include `SHA256SUMS.txt`, an update manifest, and a GitHub
  build-provenance attestation.

## Windows signing notice

The application and installer in this release are **not Authenticode-signed**.
Windows can display an **Unknown publisher** or Microsoft Defender SmartScreen
warning. Download only from the official AntennaPatternLab GitHub Releases page
and verify the SHA-256 checksum supplied with the release.
