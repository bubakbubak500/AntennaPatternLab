# Antenna Pattern Lab 0.36.0

## Optional Monitor interface

- Adds the compact Monitor design as an explicitly optional appearance.
- Provides Dark, Light, and Follow system Monitor themes.
- Keeps the original native Windows interface as the unchanged default.
- Restores the exact native palette, typography, spacing, and widget structure
  whenever Original (Classic) is selected.
- Applies semantic colors consistently to charts, maps, tables, statuses, and
  dialogs without changing measurement or collection behavior.

## Reliability

- Persists the selected appearance.
- Reacts to Windows color-scheme changes without restarting when Monitor uses
  Follow system.
- Adds regression coverage for native Classic preservation and round-trip
  switching between Monitor and Classic.
