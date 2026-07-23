# Antenna Pattern Lab product definition

## Purpose

Antenna Pattern Lab is a native Windows measurement workstation for
radio-amateur operators who want to collect, inspect, and compare empirical
antenna-coverage evidence from FT8 and WSPR reports.

It combines local observations from PSK Reporter, WSJT-X activity, optional
Hamlib radio and rotator state, antenna profiles, and named measurement
campaigns. Data remains in a local SQLite database.

## Intended users

- Radio amateurs comparing installed or portable antenna configurations.
- Operators monitoring directional coverage over hours, days, or campaigns.
- Technically experienced users who need exact filtering, units, timestamps,
  quality context, exports, and reproducible local records.
- Newer operators who benefit from deliberate empty states, safe setup help,
  demo data, and plain-language explanations of limitations.

The interface assumes desktop mouse and keyboard use but must remain fully
operable by keyboard and at common Windows scaling factors.

## Primary workflows

1. Establish measurement context: callsign, TX locator, band, mode, antenna
   profile, and optional campaign.
2. Start or stop live collection while understanding connecting, running,
   stopping, inactive, warning, and failed states.
3. Load history, import records, or add demo data without confusing these
   secondary paths with live collection.
4. Inspect the primary analysis chart and change view, sector, time, distance,
   solar-time, and source filters.
5. Scan incoming reports, select a report, and inspect exact technical values.
6. Judge directional coverage and confidence without mistaking sparse sectors
   for reliable ones.
7. Understand integration health for PSK Reporter/MQTT, WSJT-X, Hamlib, and the
   rotator without treating normal inactivity as failure.
8. Create and compare campaigns and antenna profiles, inspect maps, and export
   or diagnose results.

## Operational priorities

The UI must communicate information in this order:

1. collection state, serious warnings, and rotator safety;
2. antenna, band, mode, locator, and campaign context;
3. the main analysis visualization;
4. report evidence and sector quality;
5. analysis filters;
6. integration status;
7. settings, maintenance, import, export, and secondary tools.

Only one action should dominate the main screen: Start or Stop live collection.

## Scientific limitations

The plots are empirical coverage evidence under observed conditions. They are
not calibrated far-field antenna gain measurements. Propagation, station
activity, transmit power, time, band, receiver distribution, equipment state,
and missing data affect every result.

The application must:

- preserve unsupported angular gaps;
- distinguish samples, receiver diversity, and confidence;
- avoid interpolation that invents evidence;
- avoid claiming reliability from one or two reports;
- retain existing quality thresholds and analysis formulas unless separately
  reviewed as scientific changes;
- keep theoretical or NEC references visibly distinct from empirical results.

## Desktop context and supported environment

- Windows 10 or later, x86-64.
- Python 3.11+ source environment.
- Native PySide6 and Qt Widgets.
- Matplotlib through `FigureCanvasQTAgg`.
- Local SQLite storage.
- English and Czech UI.
- Monitor Light, Monitor Dark, Follow System, and native Classic appearance.
- Minimum target 1180×720; reference 1366×768; common 1920×1080.
- Windows scaling targets: 125%, 150%, and 200%.

## Integration states

Each integration presents a shape/icon, concise text, and detailed tooltip.

- Active/connected: available and healthy.
- Waiting: enabled but awaiting a peer or data.
- Inactive/disabled: deliberately not enabled; not an error.
- Connecting: temporary progress.
- Warning/stale: attention may be needed, but operation can continue.
- Error: unavailable or failed, with a recovery path.

Rotator movement or profile mismatch during TX is a safety warning and outranks
ordinary integration state.

## Product invariants

- Preserve live collection, history, import/export, demo, profile, campaign,
  WSJT-X, Hamlib, rotator, update, storage, and analysis behavior.
- Preserve database formats and existing QSettings keys.
- Preserve English and Czech translations.
- Preserve native keyboard, focus, accessibility, and dialog semantics.
- Keep Classic functional and prevent partial Monitor styling from leaking into
  it.
- Keep data local unless the user enables a documented network feature.

## What the product must not become

- A website, local web server, Electron/Tauri application, QML/Qt Quick UI, or
  browser dashboard.
- A generic SaaS dashboard, mobile layout enlarged for desktop, gaming HUD,
  retro-radio imitation, or decorative control panel.
- A field of nested rounded cards, oversized headings, gradients, glow, or
  excessive cyan.
- A simplified viewer that removes technical controls or hides important values
  behind hover-only behavior.
- A visual redesign that changes scientific meaning, protocols, hardware
  safety, or persisted user data.
