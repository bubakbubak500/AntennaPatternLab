# UI skill inventory

Audit date: 2026-07-23

## Discovery

The repository had no `AGENTS.md`, project `.codex` files, or project-local
skills before this audit. The user-level Codex installation exposed system
skills for skill creation and installation, review, image generation, OpenAI
documentation, and plugin creation. The desktop runtime also exposed Windows
computer control, browser control, document, PDF, presentation, spreadsheet,
site, and visualization capabilities.

No existing skill was specific enough for PySide6/Qt Widgets desktop design or
rendered Qt visual validation.

## Impeccable

- Official source: <https://github.com/pbakaus/impeccable>
- Requested installer: `npx impeccable skills install`
- Status: not installed
- Version/commit: unavailable

Node.js, npm, and npx are not available on the repository command `PATH`. A
later workspace-dependency check found a bundled Node.js 24.14.0 executable,
but that bundle contains neither npm nor npx. The official installer therefore
still could not be run. No unofficial copy, fork, gist, or approximation was
installed. This is an explicit environment limitation rather than a successful
installation.

The audit applied the relevant Impeccable mindset described in the task—clarify
hierarchy, distill the interface, normalize repeated patterns, harden states,
and validate rendered results—translated into Qt concepts. No HTML/CSS detector
or web-specific generator was used against Python.

## Created project-local skills

### `qt-desktop-design`

- Location: `.agents/skills/qt-desktop-design/`
- Purpose: PySide6/Qt Widgets information architecture, semantic theming,
  layout, tables, embedded Matplotlib, dialogs, accessibility, high DPI, and
  incremental component extraction.
- Contents: `SKILL.md` and `agents/openai.yaml`
- Status: created, structurally reviewed, and discoverable by Codex
- Used: yes, for the audit, specifications, semantic tokens, component
  boundaries, dialog normalization, accessibility, and final hardening

The skill distinguishes mandatory compatibility and validation rules from
recommendations, includes anti-patterns, and references the project product,
design, audit, and architecture documents rather than duplicating them.

### `qt-visual-validation`

- Location: `.agents/skills/qt-visual-validation/`
- Purpose: run the real Qt interface and inspect themes, sizes, languages,
  data/collection states, selection, warnings, charts, tables, dialogs, focus,
  disabled controls, and clipping.
- Contents: `SKILL.md` and `agents/openai.yaml`
- Status: created, structurally reviewed, and discoverable by Codex
- Used: yes, for the before/after capture matrices, iterative screenshot
  critique, theme/language/state checks, and 125%/150%/200% scaling validation

The skill explicitly states that tests alone do not establish visual
completion and forbids fabricated captures or unsafe live/hardware actions.

## Creation and validation

Both skills were initialized with the official user-level `skill-creator`
scripts. The repository protects `.agents` with a restrictive ACL, so explicit
permission was required to create and populate only these two directories.

The official `quick_validate.py` script could not execute because its runtime
dependency `PyYAML` is not installed in the project virtual environment:

```text
ModuleNotFoundError: No module named 'yaml'
```

No unrelated dependency was added merely to run the validator. Manual
validation confirmed:

- folder name and frontmatter `name` match;
- frontmatter contains only `name` and `description`;
- descriptions include activation contexts;
- `agents/openai.yaml` uses quoted interface strings and a `$skill-name`
  default prompt;
- no placeholder or TODO content remains;
- no scripts, references, assets, caches, or package metadata were added.

The folders use the repository-local `.agents/skills/<name>/SKILL.md` discovery
layout. A subsequent Codex turn listed both skills in the active skill catalog,
confirming repository-local discoverability.

## Third-party skill safety

No additional third-party skill was installed. Impeccable was the only
third-party candidate considered, its official repository was identified, and
installation stopped when the official Node-based path was unavailable.
