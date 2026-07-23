# Antenna Pattern Lab interface design

## Direction

Design a calm, compact, trustworthy technical measurement workstation. The
screen should be information-dense but ordered: context and collection first,
analysis second, evidence and quality third, integrations last.

Use native Qt controls, restrained surfaces, clear alignment, and desktop form
patterns. Visual character comes from hierarchy, typography, spacing, and
semantic states rather than decoration.

## Main information architecture

```text
Native menu bar
┌──────────────────────────────────────────────────────────────────────────┐
│ CONTEXT                                    COLLECTION                    │
│ OK7PS · JN79 · 20m · FT8 · Vertical 20m  ● Stopped    [ Start collection ]│
│ Campaign: Summer 20m comparison           Concise detail or safety alert │
├──────────────────────────────────────────────────────────────────────────┤
│ Reports 100  Receivers 10  Good sectors 0/9  TX 0  Max range 10,133 km  │
├──────────────────────────────────────────────────────────────────────────┤
│ View [Directional SNR] Sector [10°] Time [All] Distance [All] ...        │
├───────────────────────────────────────┬──────────────────────────────────┤
│ ANALYSIS                              │ REPORTS                    100    │
│                                       │ UTC · RX · Grid · SNR · km ...  │
│ Primary polar chart                   │                                  │
│ Default ≈65% width                    │ Default ≈35% width               │
│                                       │ Selected report details          │
├───────────────────────────────────────┴──────────────────────────────────┤
│ SECTOR QUALITY  [00][01][02]...[35]  Selected 20–30° · Low · 18 / 1 RX │
├──────────────────────────────────────────────────────────────────────────┤
│ ● PSK Reporter: Disconnected  ◐ WSJT-X: Waiting  ○ Hamlib: Off ...      │
└──────────────────────────────────────────────────────────────────────────┘
```

Language moves to Settings/Appearance scope and remains available from the menu.
Communication and maintenance controls remain in their dialogs.

## Semantic tokens

Monitor Light and Dark use the same roles. Classic restores the exact native
application state and does not consume Monitor-specific styling.

### Surfaces

- `application_background`: window surround.
- `workspace_background`: analysis workspace behind panels.
- `panel_surface`: primary chart/report/quality surfaces.
- `raised_surface`: toolbar/header or emphasized region.
- `input_surface`: editable/selectable control fill.
- `selected_surface`: selected row, sector, or segment.
- `hover_surface`: pointer hover.

### Borders

- `border_subtle`: ordinary panel and table dividers.
- `border_strong`: structural separation.
- `border_focus`: keyboard focus.
- `divider`: internal section separation.

### Text

- `text_primary`: values and primary labels.
- `text_secondary`: metadata and normal inactive status.
- `text_muted`: hints and de-emphasized empty values.
- `text_disabled`: unavailable controls.
- `text_inverse`: text on accent/danger fills.
- `text_technical`: callsigns, locators, frequencies, identifiers.

### Semantic state

- `accent`, `accent_hover`, `accent_pressed`
- `success`, `info`, `warning`, `danger`, `inactive`
- `selection`, `focus`

Warning is reserved for attention-worthy conditions. Disabled or waiting does
not automatically use warning yellow.

### Charts

- `chart_background`, `chart_grid`, `chart_axis`, `chart_text`
- `chart_empirical_line`, `chart_empirical_fill`
- `chart_theoretical_reference`, `chart_missing`
- `chart_selected_sector`
- `confidence_none`, `confidence_low`, `confidence_medium`,
  `confidence_high`

Chart tokens must retain sufficient light/dark contrast and scientific
distinction without relying solely on hue.

## Typography

Use the native Windows UI font captured by Qt. Do not package a decorative font.

- Body/control: compact native UI size.
- Metadata: one step smaller, secondary color.
- Section label: compact uppercase or semibold, not a page-size heading.
- Panel title: semibold and modest.
- Metric value: semibold/tabular, never an oversized card number.
- Technical identifier: fixed-width only when scanning benefits.
- Measurements: tabular numerals when the platform font supports them.
- Chart text: sized independently for legibility at minimum and high DPI.

The product name stays in the native title. The main surface presents current
measurement context rather than repeating the brand.

## Spacing and sizing

Use a 4 px base:

- 4 px: tight internal relation.
- 8 px: ordinary control or label gap.
- 12 px: grouped controls.
- 16 px: panel padding.
- 24 px: major separation.

Ordinary controls target 28–32 px logical height. The Start/Stop action targets
32–36 px. Tables target 26–30 px rows. Splitter handles target 4–6 px. Avoid
fixed dimensions unless needed for a technical value; prefer minimums and
stretch policies.

## Surfaces, borders, and radii

Use one application background, a small number of panel surfaces, and subtle
one-pixel borders. Major areas may have a small 2–4 px radius in Monitor. Do not
nest visible cards inside visible cards. Avoid drop shadows except for transient
overlays where native Qt styling is insufficient.

## Icons and status indicators

Prefer standard Qt icons or simple Unicode shapes already supported by the
native font. Icon-only controls require accessible names and tooltips.

Status indicators combine:

- filled dot: active/connected;
- half/outlined dot: waiting/connecting;
- open dot: disabled/inactive;
- warning/error shape plus text: attention condition.

Never encode a state only with color.

## Operational header

Present callsign, locator, band, mode, antenna, and campaign as one measurement
context. Editable controls remain compact and directly reachable. Secondary
profile management belongs in a menu or adjacent understated button.

Collection state includes:

- Stopped: Start enabled.
- Connecting: action disabled, progress text visible.
- Running: Stop becomes the primary action.
- Stopping: action disabled.
- Failed: concise error, useful tooltip/detail, and retry path.

Duplicate starts must be prevented. Safety warnings can occupy the header detail
area and override routine status.

## Metric strip

Use aligned inline metric items, not decorative cards. Candidate values:

- usable reports;
- unique receivers;
- high-quality/covered sectors;
- TX sessions;
- maximum distance;
- active time selection.

Metric labels use secondary text; values use tabular numerals. Metrics are
analytical, not integration state.

## Analysis toolbar

Place graph mode, sector width, time, distance, solar-time, and source in one
coherent row immediately above the workspace. Keep labels consistent and use
stretch to absorb extra width. At the minimum width, allow a compact second row
or an intentional overflow for secondary filters; never clip the primary view
selector.

## Main workspace and chart

Use a persisted horizontal `QSplitter`, defaulting to approximately 65% chart
and 35% reports. Restore `QSplitter.saveState()` through a new namespaced
QSettings key. Invalid state falls back safely. Provide Reset layout in the
View or Settings menu.

The chart:

- maximizes actual axes area;
- uses explicit figure margins instead of mode-dependent accidental clipping;
- preserves unsupported gaps and confidence intervals;
- places legends where they do not consume excessive axes space;
- maintains readable labels in both themes;
- avoids redraw flicker;
- provides deliberate no-data/filter-empty/model-unavailable states.

## Report explorer

Provide a panel title and visible count. Retain `QTableWidget` initially to
minimize behavior risk; enable useful sorting only after numeric sort behavior
is correct.

- Timestamp: consistent UTC format.
- Callsign and locator: easy to scan, tooltip if truncated.
- SNR: always signed and right-aligned.
- Distance: right-aligned, consistent `km`.
- Bearing: right-aligned with degree symbol.
- Frequency: intentional MHz precision and right-aligned.
- Source: compact display with full tooltip.
- Selection: restrained surface, never saturated full-row color.
- Empty: explain no reports versus filters excluding reports.

Do not hide essential values in hover-only details.

## Sector quality

Use a 36-cell ribbon or wrapped matrix at 10° resolution, adapting to other
sector widths. Each cell communicates quality through label/abbreviation,
border/shape, and semantic color. A selected-sector inspector exposes:

- angular range;
- sample count;
- unique receivers;
- existing quality classification;
- confidence interval or unavailable state;
- maximum distance.

Retain an accessible table representation, but it need not permanently consume
the primary chart height.

## Integration status bar

Restrict the bottom row to PSK Reporter/MQTT, WSJT-X, Hamlib, rotator, and
serious warnings. Use concise text and detailed tooltips. Campaign and analytical
counts do not belong here.

## Dialogs

Use ordinary desktop forms:

- 16 px outer margins and 8–12 px rhythm;
- associated labels and growing fields;
- explanatory text above forms;
- standard `QDialogButtonBox` where appropriate;
- one primary/default action;
- destructive actions visually distinct but not dominant;
- Escape cancels, Enter activates the safe default;
- scrolling rather than clipping at high DPI.

Do not redesign forms as dashboards or wrap each group in a card.

## Empty, loading, and error states

Every deliberate state explains:

1. what happened;
2. whether it is expected;
3. what the user can do next.

Required states include no reports, filters exclude all data, history loading,
collection connecting, missing profile/configuration, unavailable chart/map,
integration failure, and demo data.

Do not show raw exception text as the only message.

## Accessibility and keyboard

- Associate labels with controls through buddies.
- Set accessible names/descriptions for primary action, statuses, chart, tables,
  icon-only controls, and quality cells.
- Preserve logical tab order from context through analysis and reports.
- Show a visible focus border in both Monitor themes.
- Ensure status and quality are not color-only.
- Keep native table navigation and dialog acceptance/cancellation.
- Provide tooltips for truncated or technical values.

## Minimum size and high DPI

At 1180×720, the primary action, context, chart, report title/count, quality
summary, and integration states remain available without overlap. Secondary
details may scroll or collapse intentionally.

At 1366×768, the chart is the visual center. At 1920×1080, extra space expands
the chart and report rows rather than inflating headings or metrics.

Validate 125%, 150%, and 200% Windows scaling. Layout decisions use logical Qt
units and size policies; no screenshot-specific fixed positioning is allowed.

## Visual validation references

- Baseline findings: `docs/ui-audit.md`
- Architecture and migration: `docs/ui-architecture.md`
- Before captures: `docs/ui/before/`
- After captures: `docs/ui/after/`

Passing tests is necessary but never sufficient for visual completion.
