# 07 — Scaffold a file from a schema spec

> Pulled from FM-Patch-Agent 2026-07-16. Tool paths: see runbook 04's `$PT`
> convention; the base file is the plugin's `resources/fmbase.fmp12`.
> After every run: append to [`../logs/scaffold-file.log.md`](../logs/).

## Overview

Build (or evolve) a FileMaker file from a schema spec: copy fmbase on first
run, then reconcile the file to match `../specs/<name>.json` via one
FMUpgradeTool patch — tables, TOs, one generator-owned full-field layout per
table (the Data API layout). No relationship graph (wire it in FM Pro when
wanted). Iteration = edit spec, re-run; **additive-only** — drift is
reported, never destroyed.

Proven runs (FM-Patch-Agent, 2026-06): virgin CRM build 57/57 verified in
~1 min; delta run on a file with live records — records preserved, dead
calcs repaired retroactively, layouts regenerated.

> **Operator prompts (MUST):** the file changes hands between FileMaker and
> the CLI during this workflow. At every gate, ask by name: "please CLOSE
> `<File>.fmp12`" before export/generate/apply; "please OPEN `<File>.fmp12`"
> when bridge work (typegen, seeding, deploy) resumes. Verify closed with
> lsof, open with ProofKit `connectedFiles`.

## Steps

`<work>` = `dev/builds/<File>.scaffold/<timestamp>/`; built files land
in `dev/builds/` (fmp12s never committed).

### 1. Design gate
- MUST have the spec approved in chat before generating (see `../specs/README.md`).
- New solution: `cp "${CLAUDE_PLUGIN_ROOT}/resources/fmbase.fmp12" dev/builds/<File>.fmp12`

### 2. Export target
```bash
python3 "$PT/fm_export.py" dev/builds/<File>.fmp12 -o <work>/pre.xml --account Admin --pwd ""
```

### 3. Generate
```bash
python3 "$PT/gen_scaffold.py" gen ../specs/<name>.json <work>/pre.xml -o <work>/run
```
- MUST surface the drift report to the operator — drift is informational,
  never patched.
- Hard-fails on TO/layout name collisions (rename in FileMaker, re-run).
- `noop: true` → stop; the file already matches the spec.

### 4. Apply
```bash
python3 "$PT/apply_patch.py" apply dev/builds/<File>.fmp12 <work>/run/patch.xml --backups-dir <work>/backups
```
MUST NOT hand-edit patch.xml.

### 5. Verify
```bash
python3 "$PT/gen_scaffold.py" verify <work>/run/expected.json dev/builds/<File>.fmp12 --workdir <work>/verify
```
Exit 0 + `verified: true` is the ONLY success signal — includes the
live-calc oracle (catches the silent `/* commented-out */` calc class).

## Validation

- [ ] verify exit 0, `missing: []`, `mismatched: []`
- [ ] Backup exists in `<work>/backups`
- [ ] Run log entry appended

## Error Handling / Gotchas

- verify fails → backup path is in the apply output; investigate before any
  re-run (never re-apply blindly).
- Generator SpecError → fix the spec in conversation, re-approve, re-run.
- Generator-owned layouts are REGENERATED (delete+re-add) when fields
  change — never hand-customize them; custom layouts get different names
  and are never touched.
- Hand-added fields on scaffolded tables survive in the TABLE but not on a
  regenerated generator layout — put custom fields on custom layouts, or in
  the spec.
- Hand-deleted objects: ids reallocate max+1 — fresh export + drift review
  before the next run.
- Data API serializes big UUIDNumber IDs lossily — web apps read/write IDs
  via `GetAsText` calc twins (the spec's `IDText` pattern); ExecuteSQL
  returns full precision.
