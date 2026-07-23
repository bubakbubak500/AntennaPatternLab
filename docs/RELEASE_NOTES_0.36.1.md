# Antenna Pattern Lab 0.36.1

This maintenance release fixes application appearance switching introduced in
0.36.0.

- Selecting Monitor now applies the chosen Monitor theme immediately after Save.
- The Monitor and theme preferences are persisted and restored on the next run.
- Classic remains the default and retains the native Windows appearance.
- Appearance values are normalized at the UI/controller boundary so packaged
  PySide6 builds behave the same as development builds.
