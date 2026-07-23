---
name: qt-desktop-design
description: Design, audit, and refactor the Antenna Pattern Lab PySide6 and Qt Widgets interface. Use for desktop information architecture, layouts, themes, tables, embedded Matplotlib charts, dialogs, accessibility, high-DPI behavior, and UI component extraction in this repository.
---

# Qt Desktop Design

Read `PRODUCT.md`, `DESIGN.md`, `docs/ui-audit.md`, and
`docs/ui-architecture.md` when they exist. Preserve analysis formulas,
protocol behavior, translations, database formats, and QSettings keys.

## Mandatory rules

- Keep the application native PySide6 and Qt Widgets. Do not introduce web UI,
  QML, Qt Quick, or a local server.
- Prefer standard Qt controls, `QLayout`, and user-adjustable `QSplitter`
  workspaces. Persist relevant geometry and splitter state with compatible
  `QSettings` keys.
- Separate layout construction, presentation formatting, and business logic.
  Extract only cohesive `QWidget` subclasses with explicit signals.
- Extend the existing theme and design-system modules. Use semantic tokens,
  `QPalette`, reusable object names, and dynamic properties; repolish after
  changing a styling property.
- Use QSS for appearance only. Avoid absolute positioning, business state in
  QSS, broad per-widget `setStyleSheet`, and custom painting without clear
  benefit.
- Preserve keyboard behavior, visible focus, associated labels, accessible
  names/descriptions, useful tooltips, and non-color status cues.
- Treat the chart as primary content. Preserve scientific meaning and missing
  data, maximize plotting area, use semantic chart tokens, and prevent label
  clipping or redraw flicker.
- Keep tables keyboard-navigable and sortable. Right-align numeric values,
  format signed SNR consistently, use intentional units and precision, and
  expose truncated technical values in tooltips. Migrate to a model only when
  the behavior and maintenance benefit justify it.
- Support Monitor Light, Monitor Dark, and Classic without hybrid styling.
  Verify Czech and English, 1180x720 minimum target, 1366x768, 1920x1080, and
  Windows scaling at 125%, 150%, and 200%.

## Visual system

- Aim for a calm, compact, trustworthy technical measurement workstation.
- Prioritize: safety and collection state; antenna/band/mode/campaign context;
  main visualization; quality and reports; filters; integrations; settings.
- Use a 4 px spacing base: 4 tight, 8 normal, 12 grouped, 16 panel, 24 major.
  Target ordinary controls at 28–32 px and the primary action at 32–36 px.
- Use restrained borders, surfaces, radii, and shadows. Use tabular numerals
  for measurements and monospace only for useful technical identifiers.
- Make one primary action dominate. Keep metrics compact and integration
  states concise with icon/shape, text, and a detail tooltip.

## Anti-patterns

Avoid nested cards, equal visual weight for every control, oversized headings,
gratuitous gradients or glow, excessive cyan, fixed layouts that clip at high
DPI, saturated full-row table colors, and status conveyed by color alone.
Do not rewrite `MainWindow` in one pass or change behavior for visual purity.

## Workflow and validation

1. Inspect current ownership, settings, translations, themes, and tests.
2. Add characterization tests before risky changes.
3. Refactor in reviewable phases and preserve signals and persisted behavior.
4. Run targeted tests, then the complete suite.
5. Use `$qt-visual-validation` on every major visual phase. Passing tests alone
   never establishes visual completion.

Recommendations may yield to repository evidence; mandatory rules may not.
