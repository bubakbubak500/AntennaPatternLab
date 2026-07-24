# Antenna Pattern Lab 0.42.0

## Antenna Modeling · NEC2 Workbench

- Adds a native CZE/ENG wire-antenna workbench under **Tools**, with Dipole,
  Inverted-V, Vertical, Loop, and 3-element Yagi templates.
- Adds the versioned, solver-independent `apl-nec-model/1` format, immutable
  saved revisions, canonical JSON/SHA-256, and lossless round trips for the
  supported NEC2 deck subset.
- Adds editable wires, feed point, series RLC loads, free/perfect/real ground,
  orientation, and linear frequency sweeps.
- Validates segmentation, connections/crossings, source/load references, wire
  radius, below-ground geometry, frequency ranges, and explicit NEC2 limits
  before calculation.
- Runs separately installed OpenNEC as a cancellable child process through a
  temporary `.nec`/`.out` pair. No OpenNEC library is bundled or linked.
- Records engine version/path, exact command, UTC start, duration, model/input/
  output hashes, normal output, impedance, currents, and radiation samples in
  the versioned `apl-nec-run/1` result.

## Results and measured-data integration

- Adds R/X and 50 Ω SWR sweeps, wire-current tables, peak and front/back
  metrics, absolute/relative azimuth and elevation plots, and mouse-rotatable
  3D far-field visualization.
- Stores every normal calculation as an independent theoretical baseline and
  automatically offers saved baselines in Propagation Intelligence alongside
  the separate raw-coverage and propagation-normalized layers.
- Adds explicit height/ground candidate grids. Assisted orientation selection
  uses earlier campaign time blocks only and reports median absolute error on
  later, previously unused blocks. Candidate results cannot overwrite the
  independent baseline.

## External solver and licensing

- OpenNEC remains optional and separately installed in the per-user Programs
  directory from its official MIT-licensed GitHub release.
- The assistant verifies the GitHub-published SHA-256 before extraction.
  Antenna Pattern Lab remains MIT-licensed and fully usable for collection,
  analysis, import/export, model editing, and saved-result review without the
  solver.
- The first workbench release is deliberately limited to supported NEC2 wire
  cards. Patches, buildings, volumetric solids, real coax, full terrain,
  NEC4-only features, and an unconstrained optimizer are not included.

## Validation and compatibility

- Migrates SQLite storage from schema 4 to schema 5 through the existing
  verified pre-migration backup workflow.
- Executes all five templates successfully with official OpenNEC 2.2.0 on
  Windows; the reference dipole produced nine impedance points, 198 current
  samples, and 11,664 usable far-field samples.
- Adds domain, parser, storage, fitting, Qt integration, menu, and saved-
  baseline tests.
- Visually validates Monitor Light, Monitor Dark, Classic, Czech, English,
  1180×720, 1366×850, 1920×1080, populated model/result/candidate states, and
  200% scaling.
- Preserves measurement rows, campaigns, profiles, propagation snapshots,
  QSettings keys, offline workflows, and existing import behavior.
- Windows packages remain unsigned. Verify the installer against
  `SHA256SUMS.txt` before running it.
