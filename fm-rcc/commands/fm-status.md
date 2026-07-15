---
description: Show fm-rcc project status — managed files, baseline, patch history, backups, changelog
allowed-tools: Bash, Read, Glob
---

Report the state of fm-rcc-managed FileMaker work in this project. Read-only — change nothing.

1. If `fm/fm-rcc.json` doesn't exist: say the project isn't initialized and point at `/fm-rcc:fm-init`. Stop.
2. Read `fm/fm-rcc.json` — list managed files (and whether each exists on disk).
3. Baseline: list `fm/baseline/` exports with dates.
4. Patches: for each `fm/patches/<ts>/`, show timestamp, patch.xml presence, before/after states, and whether verify passed (from the changelog entry).
5. Backups: list `fm/backups/` with sizes and timestamps.
6. Changelog: show the last 5 entries of `fm/changelog.md`.
7. One-line health summary at the top: files managed, last patch date + verdict, last baseline age. Flag anything odd (baseline older than latest patch, backup missing for a patch, managed file missing on disk).
