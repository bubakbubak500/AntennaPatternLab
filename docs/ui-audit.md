# UI audit: baseline, implementation, and final validation

Audit date: 2026-07-23
Baseline application version: 0.36.1
Scope: Phase 1 baseline followed by Phases 2–11 implementation and validation

## Evidence and method

The current source was rendered with an isolated temporary SQLite database and
INI settings through `tools/render_ui_baseline.py`. Demo data came from the
repository's deterministic generator. Collection-running and integration-error
captures are presentation-only simulations; no live collection, transmission,
radio, or rotator action occurred.

Stored captures:

- [1366×768 Monitor Light, empty](ui/before/1366x768-monitor-light-empty-eng.png)
- [1366×768 Monitor Light, populated](ui/before/1366x768-monitor-light-populated-eng.png)
- [1366×768 Monitor Dark, populated](ui/before/1366x768-monitor-dark-populated-eng.png)
- [1920×1080 Monitor Light, populated](ui/before/1920x1080-monitor-light-populated-eng.png)
- [1920×1080 Monitor Dark, populated](ui/before/1920x1080-monitor-dark-populated-eng.png)
- [1180×720 Monitor Light, Czech](ui/before/1180x720-monitor-light-populated-cze.png)
- [1366×768 Classic, populated](ui/before/1366x768-classic-populated-eng.png)
- [collection running, safely simulated](ui/before/1366x768-monitor-light-collection-running-simulated.png)
- [selected report](ui/before/1366x768-monitor-light-selected-report.png)
- [selected sector-detail row](ui/before/1366x768-monitor-light-selected-sector-row.png)
- [integration error](ui/before/1366x768-monitor-light-integration-error.png)
- [Appearance dialog](ui/before/dialog-appearance-eng.png)
- [Communication dialog, Czech](ui/before/dialog-communications-cze.png)
- [Antenna profile dialog, long English value](ui/before/dialog-antenna-profile-eng-long-text.png)

The source-rendering environment exposes no system fonts to offscreen Qt.
The capture tool therefore registers Matplotlib's bundled DejaVu Sans/Mono for
readable evidence; this affects only the audit tool. A native Windows window
was also inspected through Windows Graphics Capture and rendered Czech text
normally, confirming that missing glyphs were an offscreen artifact.

The offscreen WSJT-X listener reports an error because local listener behavior
is constrained in this runtime; native inspection showed the expected Waiting
state. Qt scaling was subsequently exercised in isolated processes with
`QT_SCALE_FACTOR=1.25`, `1.5`, and `2`. The resulting physical-pixel captures
were inspected from `.ui-preview/highdpi-*`; they are validation artifacts,
not source-controlled documentation images.

## Repository measurements

- `ui.py`: 3,021 lines; one `MainWindow`
- `theme.py`: 527 lines
- `design_system.py`: 205 lines
- 14 dialog modules; the largest are Coverage (612), Campaign (550), and
  Experiment (507) lines
- 48 direct `setStyleSheet` calls
- 96 hex-color literals, concentrated mainly in the three token sets
- 10 explicit margin calls and 7 explicit spacing calls
- 1 fixed-size call and 11 minimum-size calls
- 13 `QTableWidget` constructions and no `QTableView` construction
- 7 splitters and 8 embedded Matplotlib canvases
- 40 test files; 142 tests pass

The direct-style count includes legitimate centralized theme application, but
status labels and several dialog headings still construct visual state locally.

## Validated findings

### Information architecture and hierarchy

The preliminary diagnosis is correct. The screen is functional but organized
as a styled input form plus two grids. Callsign, locator, band, mode, language,
profile, history, graph mode, sector width, and every filter have similar
weight. The operational context is not presented as one coherent object.

The internal `ANTENNA PATTERN LAB` heading repeats the native title and consumes
a full row without conveying antenna, campaign, band, mode, or collection
state. Language is permanently visible despite being a settings-level choice.

The primary Start action has an accent fill in Monitor, but it competes with a
large Load history button and is not paired with an explicit state label or
transition feedback. The current state is dispersed between button text,
MQTT label, status message, and the bottom row.

### Layout and spacing

The top context form has a fixed maximum height of 105 px and ten grid columns.
It remains legible in the baseline, but it has no adaptive grouping and leaves
little room for longer translations or high-DPI growth.

The analysis controls are split across two rows with uneven label/control
rhythm. The main horizontal splitter exists but is not stored, named, or
restored; its initial sizes are `[620, 540]`, which gives the report table
nearly equal authority to the chart.

At 1180×720, the chart becomes small, the report panel stays dominant, and the
bottom text has insufficient room. At 1920×1080 the plot grows, but the lower
sector-detail grid still reserves a large band and leaves substantial blank
space in its unused columns.

### Typography

Monitor uses a compact 12 px application font and switches several technical
widgets to the system fixed font. Measurements benefit from tabular glyphs, but
the policy is broad: callsign, locator, both tables, and history hours all
change font together. Panel titles, metadata, metrics, and technical identifiers
do not yet form a deliberate type hierarchy.

The repeated all-caps product heading and letter spacing draw attention without
adding operational meaning. Table timestamps and frequencies are dense at
1366×768.

### Control consistency

The repository has useful named primitives and semantic tokens, yet main-window
construction mostly instantiates raw Qt widgets. Many controls therefore share
the same height and boundary treatment, including primary, secondary, filter,
and settings actions.

Normal disabled and focus states exist in Monitor QSS. Important main controls
do not consistently set accessible names or descriptions; the icon-only graph
information label is a text glyph with a tooltip rather than a focusable
control.

### Chart usability

The chart is the defining output but receives only about half of the workspace.
At 1366×768 its polar axes are approximately 250 px across; at 1180×720 they are
smaller still. The chart title can collide with or be clipped beneath the
filter row in the empty state.

`tight_layout()` is invoked independently by chart modes. The polar legend is
positioned below-left outside the axes and consumes vertical plotting space.
The data representation itself is appropriately conservative: missing sectors
remain gaps, confidence intervals are shown, and theoretical bearings remain
distinct.

Light and Dark chart tokens are coherent and readable. The empirical outline,
confidence fill, grid, reference rays, and labels remain distinguishable in
both themes.

### Report explorer

The report table is a raw eight-column `QTableWidget` with no panel title,
visible count, search, details region, or deliberate empty state. In empty data
it becomes a large blank grid.

Formatting is partly sound: timestamps are consistent, SNR includes a sign,
azimuth includes a degree symbol, and frequency uses six decimals. Numeric
cells are not right-aligned; callsigns and locators receive no distinct
formatting or tooltip; every row repeats the full `PSK Reporter` source.
`resizeColumnsToContents()` runs after every fill, which produces horizontal
scrolling in the minimum-size capture and may add refresh cost.

Sorting is not enabled in construction. Keyboard row selection remains native,
but selection has no associated report inspector or visible semantic purpose.

### Sector quality

The lower five-column chart-detail `QTableWidget` exposes the analytical data
and has a valuable accessible name. Visually it reads as a second spreadsheet,
not a coverage/confidence component. It lists all 36 sectors at 10° width even
when most contain no data, and only four rows are visible at common sizes.

Quality is repeated as text (`no data`, `low`, and so on), which is preferable
to color-only meaning, but the component does not provide a scannable overview,
selected-sector summary, or confidence progression. One receiver and many
reports are correctly classified as low quality by the existing analysis; that
classification must be preserved.

### Status and feedback

The bottom row mixes MQTT, WSJT-X, Hamlib, rotator, campaign progress, transient
status, report count, receiver count, good/covered sectors, and TX count. Five
fixed minimum widths consume at least 760 px before the status and summary.
This is visually dense at 1366×768 and does not fit robustly at the minimum
target.

Normal waiting and inactive states use text and a dot, but Waiting is colored
with warning yellow. This overstates normal inactivity. Integration details are
available in tooltips, while analytical metrics should move to a compact strip
near the context.

History loading disables the action and reports progress only in the bottom
text. Collection has only stopped/running booleans—no explicit connecting or
stopping presentation—and duplicate-start prevention depends on current button
flow rather than a visible state machine.

### Empty, loading, and error states

The empty state is an empty polar grid, an all-`no data` 36-row sector table,
and a blank report table. It does not explain whether no reports exist, filters
removed all results, the profile is missing, or the next action is Start,
History, Import, or Demo.

History and integration errors are concise text in the bottom row. There is no
dedicated recovery surface, and raw network error detail can compete with all
other status content. Model and NEC modes do have explanatory text, showing a
useful precedent for deliberate states.

### Dialog consistency

Representative dialogs use ordinary desktop layouts and avoid dashboard-card
overdesign. Appearance and Communication use `QFormLayout` plus standard
button boxes. Profile and Campaign use hand-built action rows.

Outer margins, status-heading styles, button hierarchy, minimum sizes, and
error presentation vary across modules. Twelve dialog/main modules use local
stylesheet calls. Large dialogs combine forms, tables, and plots without one
shared spacing or title policy. This is a P2 issue until the main workspace and
tokens stabilize.

### Accessibility, keyboard, translation, and high DPI

Positive evidence:

- native Qt controls retain keyboard navigation;
- tables are read-only and select rows;
- graph data has an accessible table name;
- icon buttons in `design_system.py` assign an accessible name;
- statuses contain text in addition to color;
- both English and Czech dictionaries are exercised by tests and captures.

Risks:

- most main controls have no explicit accessible name/description;
- labels are not consistently associated with buddies;
- the graph-info glyph is not a keyboard-focusable button;
- no explicit tab order is defined;
- selected sector/report state has no narrated detail;
- focus appearance is defined in Monitor QSS but was not exhaustively exercised;
- 125–200% scaling remains unverified;
- fixed/minimum widths and the 105 px controls maximum height can clip at high
  DPI or with longer labels.

## Priorities

### P0 — resolve before broad polish

1. Preserve collection, integration, rotator-safety, analysis, translation,
   Classic, and QSettings behavior with characterization tests before
   extraction.
2. Define deliberate empty/filter-empty/loading/failure states so the primary
   workspace never presents unexplained blank grids.
3. Prevent minimum-size and high-DPI clipping of the operational state and
   primary action.

### P1 — main-screen redesign

1. Replace the product heading/form with an operational header: measurement
   context, collection state/action, and compact metrics.
2. Consolidate all analysis controls into one coherent toolbar.
3. Persist a chart-favoring main splitter and provide a safe reset.
4. Give the chart substantially more plotting area and deterministic margins.
5. Turn the report grid into a titled report explorer with count, scan-friendly
   formatting, alignment, tooltips, selection, and empty state.
6. Replace the generic sector-detail grid with a compact semantic
   coverage/quality component using unchanged thresholds.
7. Restrict the bottom bar to integrations and serious warnings; treat Waiting
   and Disabled as inactive rather than warning.
8. Add explicit connecting/running/stopping/failed collection presentation and
   make Start/Stop the single dominant action.

### P2 — consistency and hardening

1. Normalize representative dialogs after main tokens and components stabilize.
2. Reduce local stylesheet construction through semantic properties.
3. Improve labels, buddies, accessible descriptions, focus order, and
   keyboard-only inspection.
4. Validate long English/Czech content and Windows scaling at 125%, 150%, and
   200%.
5. Measure table refresh cost before choosing `QTableView`.

## Proposed information architecture

```text
Menu bar
Operational header
  Context: callsign · locator · band · mode · antenna · campaign
  Collection: state · detail · dominant Start/Stop action
Metric strip
  usable reports · receivers · quality sectors · TX · maximum range
Analysis toolbar
  view · sector · time · distance · solar time · source
Main splitter
  Chart panel (larger default) | Report explorer
Sector quality / selected-sector detail
Integration status bar
  MQTT/PSK Reporter · WSJT-X · Hamlib · rotator · serious warnings
```

Language, communication, appearance, setup, and maintenance actions move to
menus/dialogs. No feature is removed.

## Explicitly rejected ideas

- Web, QML, Qt Quick, Electron, and custom browser UI: violate the native
  desktop product and would discard mature Qt behavior.
- A big-bang `MainWindow` rewrite: too much collection, settings, translation,
  and protocol risk.
- A card for every field or metric: would create nested visual noise and reduce
  information density.
- Decorative gradients, glow, oversized metrics, or gaming-HUD styling:
  undermine a calm measurement-workstation character.
- Interpolating across unsupported sectors: would imply scientific confidence
  that the data does not provide.
- Immediate `QTableView` migration: not justified until formatting,
  performance, sorting, and behavior requirements are characterized.
- Redesigning every dialog first: would spread unstable token and component
  decisions.

## Baseline test result

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Result: `142 passed in 9.24s`.

The suite covers theme persistence and Classic restoration, a broad main-window
smoke flow, collection-adjacent behavior, chart modes, translations, campaigns,
dialogs, storage, integrations, and analysis. It does not replace rendered
visual inspection and currently lacks splitter persistence, explicit collection
transition-state, table-formatting, and comprehensive accessibility tests.

## Phase 1 conclusion

The preliminary observations are substantially validated. The strongest gains
will come from information architecture, resize behavior, operational state
clarity, and chart/report/quality ownership—not additional decoration.

No production UI code changed in this phase. `PRODUCT.md`, `DESIGN.md`, the
wireframe decision, and owner-approved component contract are intentionally
deferred to Phase 2.

## Final implementation and validation

The Phase 1 material above is retained as the historical baseline. The
approved direction was implemented incrementally in Phases 2–11.

Final evidence is stored under [`docs/ui/after`](ui/after/). It covers the same
14-state matrix as the baseline: 1180×720, 1366×768, and 1920×1080; Monitor
Light and Dark; Classic; Czech and English; empty and populated data; stopped
and safely simulated running collection; selected report and sector;
integration failure; and three representative dialogs.

### Resolved P0/P1 findings

- The redundant in-window product heading and permanent language selector were
  removed from the workspace. Language remains available in Settings.
- The operational header now groups measurement context with an explicit
  stopped/connecting/running/stopping/failed collection state. Start/Stop is
  the only dominant action.
- Analytical counters moved into a compact metric strip.
- All chart filters form one toolbar with associated labels.
- A persistent, resettable, chart-favoring `QSplitter` now owns chart/report
  sizing through the existing QSettings store.
- Chart colors use semantic tokens. Plot margins and the legend were adjusted
  after rendered review so angular labels remain clear at minimum size and
  150% scaling.
- The report explorer has a title, count, empty state, sorting, semantic
  formatting, right-aligned measurements, full-value tooltips, selection
  detail, and adaptive columns. At 1180×720 it shows full UTC, RX, locator, and
  signed SNR without a horizontal scrollbar; secondary values remain in the
  selected-report detail.
- Sector quality is a 36-cell keyboard-focusable matrix with text/pattern
  differences, tooltips, and a selected-sector inspector. Existing analytical
  classifications and thresholds are unchanged.
- The bottom bar now contains integration health and serious/transient status,
  not analytical metrics. Connected, waiting, inactive, warning, and error
  states combine shape, text, color, and detailed tooltips.
- Empty chart and report states explain the expected condition and a recovery
  path rather than displaying blank grids.
- Appearance, communication, antenna-profile, and setup forms now share outer
  spacing, field growth, primary/default action behavior, and accessible
  labeling. Long loaded profile names show their beginning and expose the full
  value as a tooltip.
- Important controls have accessible names/descriptions, labels have buddies,
  the chart-info control is keyboard focusable, and the main workflow has an
  explicit tab order.

### Final visual critique

The final review found no remaining P0 or P1 visual issue in the required
capture matrix. Specific polish iterations fixed:

1. compact-table SNR truncation and horizontal scrolling;
2. a clipped Czech locator header at high DPI;
3. polar 180° label/legend collisions at 150%;
4. unnecessary sector-panel height;
5. long profile values opening at the trailing end.

Monitor Light and Dark have equivalent hierarchy and chart meaning. Classic
retains native behavior and the original theme-controller restoration path.
The 1920×1080 layouts use the additional area for the primary visualization
and report rows without inflating controls.

### Intentional compromises

- The report implementation remains `QTableWidget`. A model migration offered
  insufficient benefit for the behavior risk; formatting and numeric sorting
  are isolated in `TechnicalTableItem`.
- `MainWindow` remains the service orchestrator and still owns chart drawing.
  Cohesive visual components and formatting were extracted without moving
  protocol, storage, or scientific ownership.
- At the narrow breakpoint, distance, bearing, frequency, and source are
  removed from the table columns to prevent scrolling. They are not hover-only:
  keyboard/mouse selection exposes them in the report detail region, and cell
  tooltips retain full values at wider breakpoints.
- Offscreen WSJT-X bind failure is an environment limitation, not a product
  state. The visual error capture is useful for the required failure case.
- The official Impeccable skill could not be installed because the available
  Node bundle has no npm/npx. The limitation is recorded in
  `docs/ui-skills.md`; no installation was fabricated.

### Future P2 recommendations

- Extract the Matplotlib chart panel from `MainWindow` when feature work next
  touches chart ownership.
- Extend the normalized dialog contract to campaign, comparison, coverage, and
  map dialogs after their behavior receives targeted characterization tests.
- Add a Windows-native screen-reader pass and real multi-monitor DPI-transition
  test; Qt offscreen scaling verifies layout geometry but not assistive
  technology integration or per-monitor transitions.

### Final verification

- Full suite: `152 passed in 14.04s`
- Rendered startup/capture tool: completed all 14 final states
- Documentation images: 14 baseline and 14 final captures
- Diff hygiene: `git diff --check` reported no whitespace errors

## 0.38 external-tools dialog validation

The Hamlib portion of the real `SetupDialog` was rendered on 2026-07-23 against
the locally installed Hamlib 4.7.2 model list. No daemon, radio command, or
transmission was started during visual validation.

The first implementation render exposed three remaining usability issues:

1. the previous numeric-only model field did not reveal the radio name;
2. a list containing hundreds of Hamlib backends needed search by ID,
   manufacturer, and model rather than scrolling alone;
3. the passive command preview provided no operational feedback and occupied a
   full form row.

The final dialog uses a searchable model-name mapping, replaces the preview with
a **Start rigctld** action and textual status, and retains the unchanged WSJT-X
UDP section. Monitor Light Czech and Monitor Dark English captures are stored as
`dialog-external-tools-cze-light.png` and
`dialog-external-tools-eng-dark.png` under `docs/ui/after/`; the supplied 0.37
dialog capture is stored under `docs/ui/before/`. The dialog was also rendered
at 200% Qt scaling with no clipping or overlap. Offscreen captures use DejaVu
Sans because the rendering environment does not expose native Windows fonts.

## 0.39 propagation-conditions validation

The new real `PropagationConditionsDialog` was rendered on 2026-07-24 with an
isolated SQLite database and the official NOAA SWPC products cached by the
production client. No radio, rotator, collector, transmission, or automatic
network action was started. The capture refresh itself was a separate explicit
test of the NOAA client.

Final evidence under [`docs/ui/after`](ui/after/) covers:

- `dialog-propagation-cze-light-empty.png`: 900×620 logical pixels, Monitor
  Light, Czech, empty cache;
- `dialog-propagation-cze-light-overview.png`: 1180×760, Monitor Light, Czech,
  populated overview and active campaign;
- `dialog-propagation-eng-dark-images.png`: 1366×850, Monitor Dark, English,
  real D-RAP, auroral-oval, and GOES SUVI images;
- `dialog-propagation-eng-dark-overview-1920x1080.png`: 1920×1080, Monitor
  Dark, English;
- `dialog-propagation-eng-classic-timeline.png`: 1180×760, Classic, English,
  stored campaign snapshot.

The same state matrix was rendered in an isolated process at
`QT_SCALE_FACTOR=2`. The 900×620 Czech empty state, long campaign name, tab
labels, primary/disabled actions, metric grid, explanatory copy, source line,
and Close button remained visible without clipping or overlap.

The first visual pass found and corrected:

1. Classic captures inheriting the preceding dark Monitor palette in the
   validation tool rather than restoring a clean native baseline;
2. the recommended-workflow label consuming a stretched blank region instead
   of remaining a compact explanatory footer;
3. an unnecessary numbered vertical header in the campaign timeline.

The final review found no obvious P0 or P1 issue. The overview deliberately uses
available height without inventing additional metrics, image panels preserve
aspect ratios, source URLs remain visible and selectable, numerical timeline
columns are right-aligned and sort by numeric values, and state meaning combines
shape, text, and semantic color. The offscreen font renders Å as A in one panel
title; the NOAA image itself remains correct and this matches the previously
documented offscreen font limitation.

Verification:

- production NOAA fetch: Kp, F10.7, SSN, solar-wind speed, Bt/Bz, R/S/G, and
  all three images loaded successfully;
- full suite: `165 passed in 13.55s`;
- 100%, 200%, Monitor Light, Monitor Dark, Classic, Czech, English, empty,
  populated, and stored-timeline states inspected.

## 0.40 milestone 9 completion validation

The expanded real `PropagationConditionsDialog` was rendered on 2026-07-24
against an isolated database with representative NOAA, GIRO, GloTEC, TX-session,
and campaign-report data. A separate production integration check exercised the
official public endpoints after the operator-authorized refresh boundary. No
collector, radio, rotator, transmission, or hardware command was started.

Final evidence under [`docs/ui/after`](ui/after/) now includes:

- `dialog-propagation-eng-dark-trends.png`: GOES X-ray/proton, solar-wind
  speed/density/dynamic-pressure, Bt/Bz, and Dst series;
- `dialog-propagation-eng-dark-planning.png`: NOAA alerts, WSA–ENLIL model
  context, three-day probabilities, and long-range Ap/F10.7;
- `dialog-propagation-cze-light-ionosphere.png`: nearest GIRO station,
  scaling quality, qualitative band view, and GloTEC model;
- `dialog-propagation-eng-dark-images.png`: selectable-frequency D-RAP,
  auroral oval, and SUVI products;
- `dialog-propagation-eng-classic-timeline.png`: stored-snapshot replay in
  Classic;
- `dialog-propagation-eng-light-analysis.png`: half-hour campaign/TX overlay
  and sensitivity cases;
- the existing empty, Czech overview, and 1920×1080 overview captures,
  regenerated for the seven-tab dialog.

The same nine states were rendered with `QT_SCALE_FACTOR=2`. The long Czech
license explanation, optional target-locator form, technical tables, charts,
GloTEC panel, tab scrolling at the 900×620 minimum, source lines, and Close
button remained reachable without overlap. The ionosphere table intentionally
uses horizontal scrolling at the narrow breakpoint so no technical column is
silently removed.

The first visual pass found and corrected:

1. the ionosphere split gave the band summary too much width and clipped the
   station-distance column;
2. raw internal campaign-analysis flag names were exposed instead of localized
   Czech/English terms;
3. the long-range forecast initially sorted newest-first rather than in planning
   order;
4. the solar-wind chart omitted density/dynamic pressure and the Bt/Bz pair
   even though the current-value overview already exposed them.

The final review found no obvious P0 or P1 visual issue. Observations,
forecasts, and models retain explicit labels; missing values remain visible;
the graphs do not interpolate absent evidence; GIRO automatic/manual quality
and license text remain readable; and stored campaign evidence can be replayed
without network access.

Verification:

- production endpoints: all NOAA JSON/image products loaded with zero errors;
  1,438 X-ray points, 287 ≥10 MeV proton points, 1,426 joined solar-wind
  points, 100 classified alerts, and 45 forecast days parsed;
- GIRO production query: PQ052 (261 rows) and MZ152 (59 rows), zero errors;
- full suite after implementation: `173 passed`;
- 100% and 200% rendered state matrix inspected;
- `git diff --check` clean.
