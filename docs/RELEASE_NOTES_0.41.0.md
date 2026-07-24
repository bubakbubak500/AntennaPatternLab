# Antenna Pattern Lab 0.41.0

## Milestone 10 complete

- Adds the separate **Propagation Intelligence** workspace for a selected
  campaign, target receiver, time, band, and operating frequency.
- Replays great-circle route geometry, day/night and grayline state, local solar
  time, source clocks, assignment tolerance, and route-specific limitations
  without an automatic network request.
- Evaluates spatial D-RAP and GloTEC grids across the route when available. A
  global maximum or one nearest pixel is never substituted for the path.

## Reproducible analytical features

- Adds schema `apl-propagation-features/1` with SHA-256-addressed inputs,
  snapshot and receiver-network hashes, independent NOAA/GIRO/GloTEC clocks,
  source availability, and explicit missing/stale states.
- Carries GIRO confidence score, automatic/manual scaling, ionosonde distance,
  catalog version, license and operator attribution, plus GOES/RTSW identity.
- Stores derived feature files separately from raw reports and canonical
  propagation snapshots in database schema 4. Missing required evidence yields
  an insufficient conclusion instead of an assumed normal value.

## Three separate antenna views

- Extends NEC import with aligned azimuth/elevation cuts, absolute and relative
  gain, front-to-back ratio, frequency, polarization, height, ground-model,
  orientation, and source provenance. Multiple documented baselines can be
  loaded.
- Keeps **Coverage / observed shape** separate and exposes reports, unique
  receivers, best/median SNR, maximum distance, density, quality, and bootstrap
  intervals without filling unsupported sectors.
- Adds the transparent versioned statistical path baseline and computes
  `median(SNR observed − SNR expected)` per sector, with synchronized
  median-aligned NEC/raw/normalized comparison and residuals.
- Uses leave-one-time-block-out validation. Residuals are labelled only as
  suspicions for a controlled A/B follow-up, never as automatic cause findings.

## Validation and compatibility

- Adds backend, storage, migration, NEC, Qt dialog, provenance, missing-data,
  spatial-grid, and blocked-validation tests.
- Visually validates Monitor Light, Monitor Dark, Classic, Czech, English,
  empty/populated, 1180×720, 1366×850, 1920×1080, and 200% scaling states.
- Preserves raw data, campaign snapshots, collection workflows, existing
  QSettings keys, offline operation, and Czech/English behavior.
- Windows packages remain unsigned. Verify the installer against
  `SHA256SUMS.txt` before running it.
