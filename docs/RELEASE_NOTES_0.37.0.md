# Antenna Pattern Lab 0.37.0

## Technical-workstation interface

- Reorganizes the main window around measurement context, collection state,
  analytical metrics, filters, the primary chart, incoming reports, sector
  quality, and integration health.
- Makes Start/Stop the clear primary action and presents stopped, connecting,
  running, stopping, and failed collection states explicitly.
- Adds a compact metric strip and moves analytical counters out of the
  integration status bar.
- Combines chart controls into one coherent analysis toolbar.
- Adds a chart-favoring, user-adjustable splitter whose position is persisted,
  together with a Reset layout command.

## Chart, reports, and quality

- Enlarges the usable polar-chart area and improves semantic Light/Dark chart
  colors, margins, labels, and legend placement.
- Adds a titled report explorer with count, sorting, empty state, adaptive
  columns, full-value tooltips, selected-report details, and consistent
  formatting for UTC, signed SNR, distance, bearing, frequency, and source.
- Replaces the lower spreadsheet-like sector table with a compact 36-sector
  quality matrix and selected-sector inspector.
- Preserves existing analysis formulas, quality thresholds, missing-data
  behavior, protocol handling, and database formats.

## Accessibility and consistency

- Adds accessible names and descriptions to important controls and technical
  statuses, label buddies, a focusable chart-information control, and an
  explicit keyboard tab order.
- Distinguishes connected, waiting, inactive, warning, and error states using
  shape and text as well as color.
- Standardizes representative appearance, communication, antenna-profile, and
  setup dialogs.
- Validates Monitor Light, Monitor Dark, Classic, Czech, English, minimum-size,
  empty/populated, collection, selection, error, and 125%–200% scaling states.

## Engineering

- Extends the semantic theme-token system and reusable Qt widget components.
- Isolates technical display formatting into testable helpers.
- Adds UI architecture, product, design, skill, audit, and before/after visual
  documentation.
- Expands the automated suite to 152 tests.

The Windows application and installer remain unsigned. Verify the SHA-256
checksums supplied with the release before installation.
