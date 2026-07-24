# Antenna Pattern Lab 0.40.0

## Milestone 9 complete

- Completes the propagation-conditions and space-weather milestone without
  treating propagation context as antenna gain.
- Adds reproducible 24-hour GOES X-ray and ≥10 MeV proton series, flare timing,
  NOAA S-scale interpretation, solar-wind density/speed/dynamic pressure,
  IMF Bt/Bz, and Kyoto Dst trends.
- Adds NOAA alerts, three-day Kp and flare/proton probabilities, the 45-day
  Ap/F10.7 outlook, and WSA–ENLIL model context. Observations, forecasts, and
  models remain visibly distinct.

## D-RAP and ionosphere

- Adds selectable 5–30 MHz D-RAP products with direct access to NOAA history.
- Integrates nearest-station Lowell GIRO/DIDBase `foF2`, `hmF2`, and
  `MUF(3000)` measurements for the transmitter and an optional target locator.
- Distinguishes automatic GIRO scaling from manually validated values, exposes
  the station ionogram, and preserves the CC BY-NC-SA 4.0 source/license note.
- Adds the official NOAA GloTEC model image and an intentionally qualitative
  band view. TEC and MUF are not presented as antenna-gain measurements or
  automatic SNR corrections.

## Campaign comparability and provenance

- Stores the complete canonical NOAA products and GIRO measurements in the same
  SHA-256-addressed campaign snapshot and can replay a stored snapshot offline.
- Overlays half-hour condition intervals with campaign reports and TX sessions,
  and flags geomagnetic disturbance, radio blackout, polar-cap absorption risk,
  stale/missing context, and material receiver-network change.
- Separates comparability groups by band, mode, profile power, and receiver
  network.
- Adds sensitivity cases that omit the strongest receiver, busiest hour, or
  most populated direction and report the resulting maximum sector-median
  change.

## Reliability and compatibility

- Keeps NOAA and GIRO network access behind the explicit refresh action. Both
  clients use bounded responses, timeouts, local cache fallback, and partial
  failure reporting; collection and historical campaigns remain usable offline.
- Adds characterization tests for provider/satellite changes, time zones,
  units, missing values, stale cache, external-source failures, campaign
  grouping, and sensitivity analysis.
- Preserves existing database schema, collection workflows, profiles,
  campaigns, integrations, QSettings keys, and Czech/English operation.
- Windows packages remain unsigned. Verify the installer against
  `SHA256SUMS.txt` before running it.
