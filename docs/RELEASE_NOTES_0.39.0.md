# Antenna Pattern Lab 0.39.0

## Propagation conditions

- Adds a dedicated **Tools → Propagation conditions** screen in Czech and
  English.
- Displays official NOAA SWPC planetary Kp, F10.7 flux, observed sunspot
  number, solar-wind speed, IMF Bt/Bz, and R/S/G space-weather scales.
- Keeps the interpretation deliberately advisory: the indicators provide
  measurement context, not a point-to-point propagation forecast or an
  antenna-gain correction.

## NOAA image products and offline behavior

- Displays NOAA D-RAP D-region absorption, northern auroral-oval forecast, and
  GOES SUVI 195 Å solar imagery.
- Downloads data only after the operator explicitly presses **Refresh from
  NOAA**.
- Stores a checksum-verified local cache and clearly reports current, stale,
  partial, offline, and unavailable states.
- Keeps the rest of the application fully usable when NOAA or the internet is
  unavailable.

## Campaign provenance

- Adds database schema version 3 and creates a verified pre-migration backup
  before upgrading an existing database.
- Saves a normalized propagation snapshot and the canonical original NOAA JSON
  source rows used for it, with SHA-256 provenance, to a selected measurement
  campaign.
- Shows stored campaign snapshots in a UTC timeline for later comparison with
  observed coverage.

## Compatibility

- Preserves live PSK Reporter collection, WSJT-X, Hamlib, rotator, profiles,
  campaigns, filters, and existing QSettings keys.
- The Windows application and installer remain unsigned. Verify the local
  installer checksum before running it.
