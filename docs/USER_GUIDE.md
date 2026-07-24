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

The first-run assistant checks for WSJT-X, Hamlib, and the optional OpenNEC
NEC-2 solver. If a tool is missing, the assistant can offer its official stable
Windows release. Download and installation or launch require separate
confirmations. The file is accepted only when its name, host, size, and
published SHA-256 match the release metadata.

You can skip any dependency:

- WSJT-X is needed for live TX/RX session awareness;
- Hamlib is optional and adds radio frequency, mode, and PTT state;
- OpenNEC is optional and will provide calculations for the antenna-modeling
  workbench; imported NEC output remains usable without it;
- demo data, measurement analysis, and file import work without these tools.

OpenNEC is downloaded from its official GitHub release and unpacked into the
separate per-user `Programs/OpenNEC` directory. It remains an independent MIT
licensed command-line tool. Antenna Pattern Lab does not import or link its
solver library; it only detects `onec.exe` and will exchange standard `.nec`
input and `.out` result files when the modeling workbench is available.

When Hamlib is installed, **Settings → External tools** reads the model IDs,
manufacturers, radio names, and backend status directly from that installed
Hamlib version. Search the radio list by ID, manufacturer, or model, set the COM
port and baud rate, then choose **Start rigctld**. The application validates the
configuration, saves it, starts the daemon, and reports whether its local TCP
port became available. It does not send tuning, PTT, or other control commands
to the radio. The WSJT-X UDP setup is independent and unchanged.

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

## 8. Propagation conditions

Open **Tools → Propagation conditions** to add current space-weather context to
a measurement. The screen does not make any network request when opened. Press
**Refresh from NOAA** to explicitly download official NOAA SWPC observations
and images.

The overview includes planetary Kp, F10.7 flux, the latest available observed
sunspot number, solar-wind speed, IMF Bt/Bz, and NOAA R/S/G scales. The
**24 h trends** tab adds GOES X-ray and ≥10 MeV proton flux, flare timing,
solar-wind speed, density and dynamic pressure, Bt/Bz, and Kyoto Dst. The
planning tab separates NOAA observations, alerts, forecasts, and the WSA–ENLIL
model; it includes three-day probabilities and the longer Ap/F10.7 outlook.

The image tab shows the northern auroral-oval forecast and GOES SUVI 195 Å
imagery. D-RAP can be selected at 5, 10, 15, 20, 25, or 30 MHz, and the NOAA
history can be opened from the same tab.

When a campaign has a valid transmitter locator, the explicit refresh also
queries nearby Lowell GIRO/DIDBase ionosondes for `foF2`, `hmF2`, and
`MUF(3000)`. Enter an optional target locator on the **Ionosphere** tab to add
stations near a target area. Automatic scaling and manually validated values
remain distinct. GIRO data are published under CC BY-NC-SA 4.0 and retain their
station provenance. The official NOAA GloTEC image is labelled as a model.

Downloaded products are cached locally. Current, stale, partial, offline, and
unavailable states remain visible. Select a campaign and use **Save snapshot to
campaign** to preserve normalized values, UTC timestamps, the canonical NOAA
JSON source products and GIRO rows used, and their SHA-256. Stored snapshots
appear in the campaign timeline and can be loaded again without a network
connection.

**Campaign comparability** overlays half-hour condition intervals with reports
and TX sessions. It separates band, mode, profile power, and receiver-network
changes, marks intervals unsuitable for direct A/B comparison, and shows how
sector medians change after omitting the strongest receiver, busiest hour, or
most populated direction.

Treat this information as measurement context. It is not a point-to-point
propagation forecast and does not turn coverage reports into calibrated antenna
gain. `foF2`, MUF, and TEC are situational evidence, not a guarantee that a
specific path will open and not an automatic correction of SNR.

## 9. Propagation Intelligence

Open **Tools → Propagation Intelligence** after reports and at least one
propagation snapshot have been saved to a campaign. Select a target receiver and
move the campaign-time slider to replay the route. The map calculates the great
circle, day/night side, grayline, and local solar time locally; it does not make
an automatic network request.

The route summary assigns only time-valid NOAA and GIRO evidence. It shows the
assignment tolerance, source clocks, distance of the selected ionosonde from
the complete route, scaling quality, satellite identity, and missing or stale
sources. D-RAP and GloTEC are evaluated across the route when spatial products
are available. A global maximum or one nearest pixel is not substituted for the
route, and TEC remains qualitative context rather than an SNR correction.

The **Three layers** tab keeps these results distinct:

- **NEC theoretical reference**: imported azimuth and elevation cuts with
  frequency, polarization, height/ground-model metadata, orientation, source,
  absolute/relative gain, and front-to-back ratio;
- **Coverage / observed shape**: report and receiver counts, best and median
  SNR, maximum distance, report density, quality, and confidence intervals;
- **Propagation-normalized estimate**: median observed-minus-expected residual
  from the displayed versioned statistical path model.

The chart median-aligns shapes to a common reference and leaves unsupported
sectors empty. The table retains the underlying absolute observed SNR. The
normalization is cross-validated by campaign time blocks. If required inputs are
missing or stale, the result is explicitly marked insufficient rather than
filled with typical values.

Use **Save analytical basis** to store the feature schema, input and snapshot
SHA-256 values, receiver-network hash, source clocks, individual uncertainties,
GIRO license/attribution, and model inputs in a separate database table. Raw
reports and snapshots are never modified. A residual is only a suspicion for a
controlled A/B experiment; the application does not automatically claim a
building, terrain, common-mode current, orientation, or ground model as its
cause.

## 10. Antenna Modeling · NEC2 Workbench

Open **Tools → Antenna modeling (NEC2)**. The workbench owns a versioned,
solver-independent wire model; OpenNEC is only an optional standalone
calculation process. Without OpenNEC you can still create, validate, save, and
import/export models and inspect previously saved results.

Start with **Dipole**, **Inverted-V**, **Vertical**, **Loop**, or **Yagi**.
Edit wire endpoints, odd segment counts, radii, source segment, series RLC
loads, ground parameters, orientation, and the frequency sweep in the table.
**Refresh preview** validates missing/duplicate tags, zero-length or overly
thick wires, coarse segmentation, invalid sources/loads, below-ground geometry,
and approximate crossings before a solver is started.

**Calculate baseline** writes a temporary `.nec` deck, runs the detected
`onec.exe` as a cancellable child process, reads its `.out`, and then removes
the temporary directory. The stored result contains the exact model revision,
engine path/version, UTC time, command parameters, input/output SHA-256, and
normal NEC output. The result tabs show R/X and 50 Ω SWR over frequency, wire
currents, peak and front/back values, selectable absolute/relative azimuth and
elevation cuts, and a mouse-rotatable 3D far-field surface. NEC reports
`theta` from the zenith; the workbench converts it to the operational take-off
elevation `90° − theta`, where `0°` is the horizon and `90°` is straight up.
The 3D view draws the horizon plane, azimuth references, and the peak ray so a
low or high lobe is not inferred from the viewing perspective.

**Practical interpretation** reports the peak elevation/azimuth, approximate
relative power shares in the `0–10°`, `10–30°`, and `30–90°` upper-hemisphere
bands, and the radio horizon from the highest modeled point. It also gives
spherical-Earth one-hop geometry for assumed virtual heights of 110 km
(representative E region) and 300 km (representative F2 peak). The layer ranges
are consistent with the [NOAA ionospheric-region
definitions](https://www.ngdc.noaa.gov/stp/IONO/ionostru.html); this simple
geometry is deliberately not an [ITU-R P.533 HF propagation
prediction](https://www.itu.int/rec/R-REC-P.533/en).

The displayed hop distance does **not** establish that the selected frequency
will be supported. It excludes current foF2/MUF, D-region absorption, refraction
details, terrain, receiver height, polarization mismatch, and link budget.
The NEC far-field surface also does not calculate ground-wave coverage, which
depends on polarization, frequency, ground conductivity, terrain, and loss.

Saved independent baselines automatically appear in **Propagation
Intelligence → Three layers**, next to raw observed coverage and the separate
propagation-normalized estimate. **Assisted variants** solve explicit
height/ground combinations separately. Orientation selection uses only the
training time blocks and always reports error on later, previously unused
campaign blocks; it never replaces the original independent baseline.

Version 0.43.0 intentionally supports a documented NEC2 subset: `GW`, `GE`,
`GN`, voltage `EX 0`, series-RLC `LD 0`, linear `FR`, and the generated `RP`.
Unsupported cards are refused instead of silently discarded. Patches,
buildings, volumetric solids, a real coax/feed-line model, full terrain,
NEC4 extensions, and an unconstrained optimizer are outside this release.

## 11. Import and export

Use **Data → Import data** for CSV, ADI, or ADIF files. In a completed QSO,
`RST_RCVD` is interpreted as the report the remote station sent about your signal.
An ADIF log contains selected completed contacts and is therefore not equivalent
to the wider passive PSK Reporter dataset.

CSV export can be used for independent analysis or archival.

## 12. Appearance

Open **Settings → Appearance…** to retain the native **Classic** interface or
enable the compact **Monitor** design. Monitor provides **Dark**, **Light**, and
**Follow system** themes. The preference is saved automatically. Follow system
tracks Windows color-scheme changes while the application remains open.

## 13. Updates

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

## 13. Diagnostics and data

Application data is stored outside the installation directory and is preserved by
an in-place upgrade. The diagnostics export helps with support requests but should
still be reviewed before sharing because it can contain station configuration.

Use the confirmed delete action only when you intentionally want to start a clean
measurement dataset.
