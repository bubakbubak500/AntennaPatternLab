# Antenna Pattern Lab 0.43.0

## NEC candidate-grid reliability

- Fixes assisted height/ground grids failing before OpenNEC with an ASCII
  encoding error when the generated candidate name contained `·`, `Δ`, Czech
  text, or another Unicode character.
- Stores the model name in the ASCII NEC deck as an escaped `CM NAME-JSON`
  comment. Import restores the exact Unicode value, so the supported deck
  round trip and model SHA-256 remain lossless.
- Verifies the complete Yagi candidate path against standalone OpenNEC 2.2.0.

## Clear take-off angle and practical interpretation

- Converts NEC `theta` (measured from zenith) to elevation above the horizon
  (`90° − theta`) and presents the vertical cut on an explicit `0–90°` axis.
- Adds a horizon/ground plane, azimuth references, and a marked peak ray to the
  rotatable 3D far-field surface.
- Adds a CZE/ENG practical panel with peak take-off elevation and azimuth,
  sampled upper-hemisphere power shares, radio horizon, and spherical-Earth
  one-hop geometry for representative E (110 km) and F2 (300 km) virtual
  heights.
- Clearly separates antenna-pattern geometry from propagation prediction:
  current MUF/foF2, absorption, refraction, terrain, polarization, link budget,
  and ground-wave coverage are not inferred.

## Interface and verification

- Prevents the workbench toolbar and tabs from clipping at the minimum width,
  including native Classic.
- Validates Monitor Light, Monitor Dark, and Classic in Czech and English at
  1180×720, 1366×850, and 1920×1080, plus 125%, 150%, and 200% scaling.
- Includes focused regression tests for Unicode NEC decks, spherical
  ionospheric-hop geometry, radio horizon, pattern-power integration, the
  corrected elevation axis, and the candidate grid.

OpenNEC remains an optional, separately installed MIT-licensed executable.
Antenna Pattern Lab does not bundle or link the solver.
