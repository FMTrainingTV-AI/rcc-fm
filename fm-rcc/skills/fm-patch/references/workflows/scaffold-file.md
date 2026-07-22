# Scaffold File

## Overview
Build (or evolve) a FileMaker file from a schema spec: copy `resources/fmbase.fmp12`
on first run, then reconcile the file to match `specs/<name>.json` via one
FMUpgradeTool patch — tables (BASE-7 + domain fields), TOs, one generator-owned
full-field layout per table (the Data API layout). No relationship graph (developer
wires it in FM Pro when wanted). Iteration = edit spec, re-run; additive-only.

## Scripts Used
- fm_export.py — FMSaveAsXML export of the target (MUST be closed; lsof-checked)
- gen_scaffold.py gen — spec + export → patch.xml + expected.json (+ drift report)
- apply_patch.py apply — backup → validatePatch → smoke → in-place apply
- gen_scaffold.py verify — re-export + spec-coverage oracle

## Inputs
- Required: approved spec at `specs/<name>.json` (Claude-authored, chat-approved)
- Optional: target path (default `builds/<File>.fmp12`); account (default Admin,
  empty password — fmbase convention)
- `<work>` = `builds/<File>.scaffold/<timestamp>/` (gitignored with builds/)

## Steps

> **Operator prompts (MUST):** the target file changes hands between FileMaker and
> the CLI tools during this workflow. At every gate, explicitly ASK the operator,
> naming the file: "please CLOSE builds/<File>.fmp12" before export/generate/apply;
> "please OPEN builds/<File>.fmp12" when bridge work (typegen, seeding, deploy)
> resumes. Never assume; verify closed with lsof, open with connectedFiles.

### 1. Design gate
- MUST have the spec approved in chat before generating anything.
- New solution: `mkdir -p builds && cp resources/fmbase.fmp12 builds/<File>.fmp12`

### 2. Export target
- MUST: `.venv/bin/python scripts/fm_export.py builds/<File>.fmp12 -o <work>/pre.xml --account Admin`

### 3. Generate
- MUST: `.venv/bin/python scripts/gen_scaffold.py gen specs/<name>.json <work>/pre.xml -o <work>/run`
- MUST surface the drift report to the operator; drift is informational, never patched.
- Generator hard-fails on TO/layout name collisions (rename in FileMaker, re-run).
- If `noop: true` — stop; file already matches spec.

### 4. Apply
- MUST: `.venv/bin/python scripts/apply_patch.py apply builds/<File>.fmp12 <work>/run/patch.xml`
- MUST NOT hand-edit patch.xml (silent no-ops / corruption).

### 5. Verify
- MUST: `.venv/bin/python scripts/gen_scaffold.py verify <work>/run/expected.json builds/<File>.fmp12 --workdir <work>/verify`
- Exit 0 + `verified: true` is the ONLY success signal. Never trust "Patch File Applied".

## Validation
- [ ] verify exit code 0, `missing: []`, `mismatched: []`
- [ ] Backup exists in `backups/`
- [ ] Run log entry appended

## Error Handling
- verify fails → backup path is in the apply output; investigate the patch before
  re-running (never re-apply blindly).
- Generator SpecError → fix the spec in conversation, re-approve, re-run.
- Generator-owned layouts: the per-table full-field layouts belong to the
  scaffolder and are REGENERATED (delete+re-add) when fields change — never
  hand-customize them; custom layouts get different names and are never touched.
- Layout regen (delete+re-add) preserves records — exercised 2026-07-22: all 11
  layouts of a populated file regenerated with seeded records present;
  `foundCount` and `totalRecordCount` unchanged after the run.
- **Container fields in a spec will NOT land via patch** — Container-datatype
  field adds silently no-op (matrix footnote 6). Deliver them via clipboard XML
  after the scaffold run, or expect `verify` to flag them missing.
- Hand-deleted objects in the target (deleted in FM after a scaffold run): ids are
  reallocated max+1, so prefer a fresh export + drift review before the next run.
- Hand-added fields on scaffolded tables are reported as drift and survive in the
  TABLE, but the generator-owned layout will not carry them after a regen — put
  custom fields on custom layouts, or add them to the spec instead.
