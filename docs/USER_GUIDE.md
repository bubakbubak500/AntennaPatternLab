# Antenna Pattern Lab user guide

## 1. What the application measures

Antenna Pattern Lab groups reception reports by azimuth and helps you compare
coverage observed with different antenna configurations. It is designed for
repeatable field measurements, not as a replacement for a calibrated antenna
range.

For useful comparisons:

- keep the transmitter power, band, mode, and antenna profile accurate;
- collect data over comparable UTC periods;
- avoid comparing a short campaign with a much longer one without using the
  time-balanced views;
- collect reports across as many azimuth sectors as possible;
- record changes to the antenna or station in the campaign notes.

## 2. First run

The first-run assistant checks for WSJT-X and Hamlib. If a tool is missing, the
assistant can offer its official stable Windows release. Download and launch are
two separate confirmations. The file is accepted only when its name, host, size,
and published SHA-256 match the release metadata.

You can skip either dependency:

- WSJT-X is needed for live TX/RX session awareness;
- Hamlib is optional and adds radio frequency, mode, and PTT state;
- demo data and file import work without either tool.

## 3. WSJT-X connection

In WSJT-X, open **File → Settings → Reporting** and set the UDP server to
`127.0.0.1` and the port to `2237`. Enter the same port in Antenna Pattern Lab.

A waiting state means the UDP listener is active but no valid WSJT-X packet has
arrived. RX or TX is shown only after a valid Heartbeat or Status packet.

When another application already owns the port, use a different port, multicast,
or configure UDP forwarding.

## 4. PSK Reporter collection

Enter your callsign and Maidenhead locator, choose FT8 or WSPR and the band, then
start live collection. The MQTT connection indicator becomes connected only after
the broker confirms the subscription.

Historical import can retrieve a limited recent interval. Rate limiting is stored
persistently, so restarting the application does not bypass the service limit.

Only reports that can be associated with your configured station and selected
measurement context should be interpreted as part of that campaign.

## 5. Antenna profiles

Create profiles from **Antenna profile → Manage**. A profile can record antenna
type, dimensions, heights, orientation, power, tuner state, and notes.

Orientation depends on antenna type:

- for wire antennas it is the wire axis; the expected broadside directions are
  approximately orientation ± 90 degrees;
- for a Yagi it is the forward boom direction;
- for a vertical, no directional reference axis is assumed.

The reference line is descriptive only; it is not measured gain.

## 6. Measurement campaigns

Campaigns preserve the callsign, locator, band, mode, antenna profile, objective,
time range, and notes used for a measurement. Use separate campaigns when you
change an antenna, height, matching arrangement, power, or other important
condition.

The coverage planner highlights missing azimuth sectors and useful UTC windows.
Campaign comparison and A/B analysis are most meaningful when the underlying
conditions and sampling are comparable.

## 7. Charts and maps

The application includes views for median SNR, time-balanced SNR, distance,
report count, coverage, and campaign comparisons. Sector width controls angular
aggregation; wider sectors reduce noise but hide smaller directional features.

Large uncovered gaps are intentionally not interpolated as measured data.

The map shows report locations and great-circle paths from the transmitting
locator. Azimuth is the initial bearing at the transmitter.

## 8. Import and export

Use **Data → Import data** for CSV, ADI, or ADIF files. In a completed QSO,
`RST_RCVD` is interpreted as the report the remote station sent about your signal.
An ADIF log contains selected completed contacts and is therefore not equivalent
to the wider passive PSK Reporter dataset.

CSV export can be used for independent analysis or archival.

## 9. Updates

Open **Settings → Updates** to check the official GitHub release channel. Automatic
checks run in the background on every startup. If the internet or GitHub is
unavailable, startup continues normally and no error is shown.

The update process:

1. downloads the HTTPS release manifest;
2. validates its version, installer URL, and SHA-256;
3. downloads to a temporary `.part` file;
4. publishes the `.exe` only after the digest matches;
5. asks before launching the verified installer.

Current releases are not Authenticode-signed, so Windows may report an unknown
publisher or show a SmartScreen warning. Download only from the official GitHub
Releases page and compare the installer with the published SHA-256 checksum.

## 10. Diagnostics and data

Application data is stored outside the installation directory and is preserved by
an in-place upgrade. The diagnostics export helps with support requests but should
still be reviewed before sharing because it can contain station configuration.

Use the confirmed delete action only when you intentionally want to start a clean
measurement dataset.
