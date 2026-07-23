---
name: qt-visual-validation
description: Run and visually validate the real Antenna Pattern Lab PySide6 interface. Use after Qt UI changes or during UI audits to capture and inspect screenshots across themes, sizes, languages, data states, collection states, focus, disabled controls, charts, tables, and representative dialogs.
---

# Qt Visual Validation

Read `DESIGN.md` and `docs/ui-audit.md` when present. Store baseline images in
`docs/ui/before/` and revised images in `docs/ui/after/`, subject to repository
binary-file conventions. Never fabricate a capture or claim inspection when
the application did not run.

## Mandatory workflow

1. Run the repository-supported application in its supported environment.
2. Load demo data where practical; use only safe simulation for collection.
3. Capture and visually inspect the rendered UI, not just widget metadata.
4. Exercise Monitor Light and Dark, Classic when supported, minimum practical
   size, 1366x768, and 1920x1080.
5. Exercise empty and populated data, collection stopped and running or a safe
   equivalent, selected report and sector, a warning or integration failure,
   Czech and English, and representative dialogs.
6. Compare before and after captures. After each major phase, record at least
   three remaining visual problems, fix important ones, and repeat until no
   obvious P0 or P1 issue remains.
7. Run structural and behavioral tests as supporting evidence. Passing tests
   alone is not sufficient for visual completion.

## Inspection checklist

- Check clipping, elision tooltips, baseline alignment, control heights,
  margins, whitespace, crowding, hierarchy, nested-card appearance, borders,
  splitter and scrollbar behavior, and primary-action visibility.
- Check chart plotting area, grid and label legibility, missing-data honesty,
  legend collisions, resize behavior, and dark/light parity.
- Check table scanning, numeric alignment, selection, keyboard navigation,
  empty states, and horizontal scrolling.
- Check visible keyboard focus, logical tab order, associated labels,
  accessible names, disabled states, non-color status cues, and contrast.
- Check long callsigns, profile/campaign names, and long Czech and English
  labels at 125%, 150%, and 200% Windows scaling where the environment permits.

## Evidence and limitations

Name screenshots by state and viewport. Record command, theme, language, data
state, collection state, and observed limitation in `docs/ui-audit.md`. If
automation, display access, integrations, or scaling controls are unavailable,
state exactly what could not be validated and perform the strongest available
manual or offscreen inspection.

Do not use brittle pixel-perfect comparison unless the repository already has
stable infrastructure. Do not start live transmissions or unsafe hardware
actions for validation.

Recommendations may yield to repository evidence; mandatory workflow and
honest evidence requirements may not.
