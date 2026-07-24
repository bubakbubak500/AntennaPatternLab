# Antenna Pattern Lab

A Windows desktop application for building an empirical antenna coverage pattern
from your own FT8 and WSPR reception reports.

Antenna Pattern Lab combines PSK Reporter data, WSJT-X activity, optional Hamlib
radio state, antenna profiles, and measurement campaigns. It stores everything in
a local SQLite database and provides polar plots, maps, comparisons, and exports
without requiring a server.

> [!IMPORTANT]
> The plots describe the reports collected under your measurement conditions.
> They are not a calibrated far-field antenna gain measurement. Propagation,
> station activity, transmit power, time, band, and receiver distribution all
> influence the result.

## Download

Download the current Windows installer from
[GitHub Releases](https://github.com/bubakbubak500/AntennaPatternLab/releases/latest).

The application can check the same official GitHub release channel for updates.
It checks in the background on every startup and fails silently when offline.
Every downloaded installer is accepted only after its SHA-256 digest matches the
published release manifest, and it is never launched without an additional
confirmation.

> [!WARNING]
> Current Windows packages are not Authenticode-signed. Windows can therefore
> display **Unknown publisher** or a Microsoft Defender SmartScreen warning.
> Download only from this repository's Releases page. Each release includes
> SHA-256 checksums and GitHub build-provenance attestations.

## Main features

- live FT8 or WSPR collection through PSK Reporter MQTT/TLS;
- historical PSK Reporter import with persistent rate limiting;
- WSJT-X UDP monitoring with confirmed RX/TX state and TX-session records;
- optional Hamlib `rigctld` monitoring for frequency, mode, and PTT;
- reusable antenna configuration profiles and named measurement campaigns;
- polar SNR, distance, count, time-balanced, and coverage views;
- interactive world map with great-circle paths, azimuth, and distance;
- campaign comparison, A/B analysis, and coverage planning;
- NOAA SWPC X-ray/proton, solar-wind, alert, forecast, D-RAP, GloTEC, and
  WSA–ENLIL context with offline campaign snapshots;
- nearby GIRO/DIDBase ionosonde measurements and campaign condition/sensitivity
  analysis;
- route-specific Propagation Intelligence with local great-circle/daylight
  replay, versioned provenance, blocked validation, and separate NEC,
  observed-coverage, and propagation-normalized layers;
- built-in NEC2 wire-modeling workbench with five templates, validation,
  3D geometry, impedance/current/pattern results, reproducible baselines, and
  an optional separately installed OpenNEC calculation process;
- ADIF/ADI and CSV import, plus CSV export;
- local SQLite storage and diagnostic export;
- English and Czech application UI;
- verified, consent-driven setup assistance for WSJT-X and Hamlib;
- reproducible Windows releases with checksums and GitHub build provenance.

### Appearance

The original native **Classic** interface remains available. The optional
**Monitor** design is a compact technical UI for dense tables, charts, maps,
status indicators, logs, and configuration screens. Open
**Settings → Appearance…** and choose **Dark**, **Light**, or
**Follow system**. The selection is persisted, and Follow system reacts to
Windows color-scheme changes while the application is running.

## Quick start

1. Download the latest installer from
   [Releases](https://github.com/bubakbubak500/AntennaPatternLab/releases/latest).
2. Compare the installer's SHA-256 with `SHA256SUMS.txt`; Windows currently
   reports an unknown publisher because the release is unsigned.
3. Start Antenna Pattern Lab and complete the first-run assistant.
4. Use **Help → Add demo data** to explore the application without a radio.
5. For live collection, enter your callsign and locator, select the band and mode,
   then start collection.

For WSJT-X, open **File → Settings → Reporting** and configure:

```text
UDP Server: 127.0.0.1
UDP Server port number: 2237
```

Use the same port in Antenna Pattern Lab. If JTAlert, GridTracker, or another
application already uses that port, configure a different port, multicast, or UDP
forwarding.

The complete operating instructions are in the
[User Guide](docs/USER_GUIDE.md).

## Development

Requirements:

- Windows 10 or later, x86-64;
- Python 3.11 or later;
- Inno Setup 6 for installer builds.

Set up and run the development version:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m antenna_pattern_lab.app
```

Run the test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Build the application:

```powershell
.\.venv\Scripts\pyinstaller.exe --noconfirm AntennaPatternLab.spec
```

Build an unsigned local installer:

```powershell
.\build_installer.ps1
```

Official releases are built by GitHub Actions, accompanied by SHA-256 checksums
and a GitHub artifact attestation. Authenticode signing can be added later
without changing the update channel. See [Release process](docs/RELEASING.md).

## Contributing

Issues, documentation improvements, tests, and pull requests are welcome. Direct
pushes to `main` are not used: all changes are merged through pull requests after
tests pass and the repository owner approves them.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a change.

## Security and privacy

The application stores its data locally. Network access is used only for features
the user enables, such as PSK Reporter collection, an explicit NOAA SWPC refresh,
verified external-tool downloads, and update checks.

Please report security problems privately as described in
[SECURITY.md](SECURITY.md), not in a public issue.

## License

Licensed under the [MIT License](LICENSE).
