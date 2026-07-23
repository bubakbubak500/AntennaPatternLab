# Antenna Pattern Lab 0.38.0

## Hamlib radio setup

- Replaces the numeric-only Hamlib model field with a searchable mapping of
  model IDs to manufacturer and radio names.
- Reads the complete model list from the user's installed `rigctld`, so the
  choices match the exact Hamlib version on that computer.
- Preserves a previously saved model ID even when the current Hamlib version
  does not report it.
- Removes the passive command-line preview.

## Managed rigctld startup

- Adds a **Start rigctld** action to the external-tools dialog.
- Validates the selected model, serial port, baud rate, and local TCP port,
  saves the configuration, and launches `rigctld` as an independent background
  process.
- Detects an already occupied local port and reports launch progress, success,
  or failure with text as well as semantic color.
- Keeps radio access read-only from Antenna Pattern Lab; the application does
  not send tuning, PTT, or other control commands to the rig.

## Compatibility

- Leaves WSJT-X UDP reporting and its settings unchanged.
- Preserves the existing QSettings keys and Hamlib TCP client behavior.
- Adds parser, launch-flow, persistence, and visual-validation coverage.

The Windows application and installer remain unsigned. Verify the SHA-256
checksums supplied with the release before installation.
