# Patch Apply

## Overview

Generate an FMUpgradeTool patch XML from the dev export and operator selection, apply it safely to the prod file, and verify that every selected item is resolved. The file MUST be closed for both the apply and verify steps. A timestamped backup is created automatically before any modification. If verify fails, restore from backup and escalate — never leave a partially patched file in production.

The mandatory sequence is: **gen → resolve DependencyError → apply → verify → reopen**.

## Scripts Used

- `gen_patch.py` — generates FMUpgradeTool-compatible patch XML from dev export, full diff, and selection.
- `apply_patch.py apply` — backup → validatePatch (temp copy) → smoke apply (temp copy) → apply inplace; refuses locked files.
- `apply_patch.py verify` — re-exports patched file, re-snapshots, re-diffs against dev; every selected key must be absent from the new diff.

## Inputs

- Required: `exports/dev.xml` — dev SaXML export with GUIDs (from export-xml workflow)
- Required: `exports/prod.xml` — prod SaXML export (from export-xml workflow)
- Required: `diffs/diff.json` — diff output (from diff-review workflow)
- Required: `selections/selection.json` — operator-approved selection (from diff-review workflow; MUST exist)
- Required: `<target.fmp12>` — the production FileMaker file to patch
- Optional: `--account <name>` — FileMaker account (default: Admin)
- Optional: `--pwd <password>` — FileMaker password (default: empty string)
- Optional: `--allow-caution` — permit caution-tier items in the patch (scripts, deletes); MUST be explicitly requested by the operator
- Optional: `--skip-smoke` — skip the throwaway smoke-apply step (not recommended; only for debugging)

## Steps

### 1. Confirm prerequisites

- MUST confirm `exports/dev.xml`, `exports/prod.xml`, `diffs/diff.json`, and `selections/selection.json` all exist.
- MUST confirm the target .fmp12 path exists.
- MUST confirm `.env` is not required (no API keys; FileMaker credentials on command line).
- SHOULD confirm the target file is closed in FileMaker Pro before proceeding (the script will also check via lsof and refuse if locked).

### 2. Generate the patch

```bash
.venv/bin/python scripts/gen_patch.py \
    --dev-export exports/dev.xml \
    --prod-export exports/prod.xml \
    --diff diffs/diff.json \
    --selection selections/selection.json \
    -o patches/patch.xml
```

Add `--allow-caution` only if the operator has explicitly approved caution-tier items (scripts, deletes):

```bash
.venv/bin/python scripts/gen_patch.py \
    --dev-export exports/dev.xml \
    --prod-export exports/prod.xml \
    --diff diffs/diff.json \
    --selection selections/selection.json \
    -o patches/patch.xml \
    --allow-caution
```

**If gen_patch.py exits with code 2 (DependencyError):**
- The error message lists the missing dependencies (e.g., a TO required by a relationship that wasn't selected).
- MUST resolve by expanding `selection.json` to include the listed dependencies — return to the diff-review workflow, add them to the selection, and re-run gen_patch.py.
- MUST NOT hand-edit the generated patch XML. The patch format is brittle; manual edits produce silent no-ops or corrupt patches.

**Key learnings baked into this step:**
- The generator REJECTS selections containing ignored, duplicate-named, or manual-tier items — fix the selection (or the file) rather than working around the error.
- Auto-enter and validation calc formulas get the same ModifyAction re-apply stubs as top-level calcs (without them, field-name-referencing formulas land silently commented out as `/* … */`).
- A field ReplaceAction preserves PROD's serial-number `nextvalue` (per-instance state, not schema) — shipping dev's stale counter would mint duplicate serials invisibly to the verify oracle.
- A stale `diff.json` (generated from different exports than the ones passed to gen_patch.py) triggers a loud warning — regenerate the diff rather than ignoring it.
- Catalog order in the patch is non-negotiable: BaseTable → FieldsForTables → TO → Relationship → ValueList → CustomFunction → Script → Layout, with StepsForScripts LAST in AddAction. FMUpgradeTool processes top-to-bottom.
- Calc formulas referencing fields/TOs in forward-reference context get silently commented out as `/* … */` on first apply. The generator emits a Structure/ModifyAction re-apply pass (the same mechanism FMSaveAsXML uses) to resolve this — do not remove it.
- Script ReplaceAction REJECTS step divergence — the official format cannot carry step bodies in a Replace (no ObjectList allowed). Scripts with step changes go through delete+re-add (currently manual; see Backlog).
- Custom function changes are manual in v1 (delete+re-add not yet automated). If custom functions appear in the diff, handle them in FileMaker directly.
- Added scripts land at ScriptCatalog top level — folder placement is not preserved.
- Relationship and external data source deletes are manual.

### 3. Close the target file

- MUST confirm the target file is closed before applying the patch.
- If the file is open in FileMaker Pro, close it manually (or run an export first — `fm_export.py` closes via AppleScript). `apply_patch.py` itself REFUSES locked files; it never closes anything.
- Hosted/locked-by-another-process files are detected via `lsof` and rejected; resolve hosting before proceeding.

### 4. Apply the patch

```bash
.venv/bin/python scripts/apply_patch.py apply \
    /path/to/prod.fmp12 \
    patches/patch.xml \
    --account Admin \
    --pwd ""
```

What happens internally:
1. lsof check — refuses if the file is locked.
2. `--validatePatch` run against a temp copy — aborts if validation fails (target untouched).
3. Smoke `--update` run against a different temp copy — aborts if the tool errors (target untouched).
4. Timestamped, size-verified backup created at `backups/<name>-<timestamp>.fmp12` (project-root `backups/` by default; override with `--backups-dir`).
5. Lock re-checked, then the real `--update -inplace` is applied to the target.
6. On a failed or hung in-place apply, the target is AUTO-RESTORED from the backup (the result JSON reports `"restored": true/false`); commands echoed to stderr have passwords redacted.

**CRITICAL:** "Patch File Applied" prints even on silent no-ops. Never trust the tool's exit code or banner as proof of success. The verify step (step 5) is the only valid success oracle.

### 5. Verify the patch

- MUST run verify immediately after apply. Do not skip or defer.

```bash
.venv/bin/python scripts/apply_patch.py verify \
    --dev-export exports/dev.xml \
    --patched /path/to/prod.fmp12 \
    --selection selections/selection.json \
    --workdir verify_workdir/ \
    --account Admin \
    --pwd ""
```

What verify does: re-exports the patched file, re-snapshots, re-diffs against the dev export, checks that every selected key is absent from the new diff.

- The internal re-export automatically mirrors the dev export's `Has_DDR_INFO` setting — DDR-asymmetric exports re-diff DDR-only script annotations as spurious `modified (deep structure)` items (found 2026-06-12, first real-file run).
- FMUpgradeTool's layout AddAction regenerates object UUIDs, stamps `SourceUUID` elements, renumbers internal object ids, and sets layout `Options` bit 26. The parser's layout hash normalizes all of this — a layout flagged modified after apply now indicates REAL divergence, not tool noise.

- Exit 0 = verified. The patch resolved all selected items.
- Exit 1 = unverified. One or more selected items are still present in the diff.

**If verify fails (exit 1):**
- MUST restore from backup immediately: `cp backups/<name>-<timestamp>.fmp12 /path/to/prod.fmp12`
- MUST escalate and investigate before retrying. Do not re-apply blindly.
- Common causes: silent no-op (wrong catalog order, forward-reference calc), locked object, schema dependency missing from selection.

**Note on verify and deletes:** `verify_applied` is the correct oracle for adds and replaces, but NOT for deletes. A deleted object legitimately re-appears as "added" in a dev-vs-patched-prod diff. Verify delete success by direct snapshot assertion (confirm the key is absent from `parsed/patched/` after re-parsing).

### 6. Reopen the file (if it was open before patching)

- If the file was open in FileMaker Pro before patching, reopen it now.
- If `--keep-closed` was NOT passed to the exporter, the exporter already reopened it after export — confirm it is open before declaring done.
- MAY reopen via AppleScript or manually in FileMaker Pro.

## Validation

- [ ] `patches/patch.xml` exists and is valid XML
- [ ] gen_patch.py exited 0 (no DependencyError)
- [ ] Backup exists in `backups/` with correct timestamp
- [ ] `apply_patch.py apply` exited 0
- [ ] `apply_patch.py verify` exited 0 (verified=true, unresolved=[])
- [ ] Target file is accessible and opens in FileMaker Pro after patching

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| gen_patch.py exit 2 (DependencyError) | Missing dependency objects | Expand selection to include listed deps; re-run gen |
| `File is locked` on apply | File open in FM or FMS | Close file; fatal until resolved |
| validatePatch fails | Malformed patch XML | Do NOT hand-edit; re-run gen_patch.py; escalate |
| Smoke apply fails | Tool error or version mismatch | Escalate before touching target |
| verify exit 1 (unverified) | Silent no-op or partial apply | Restore backup immediately; investigate; escalate |
| "Patch File Applied" but verify fails | Silent no-op (tool banner is unreliable) | Restore backup; this is expected behavior |
| Apply fails after backup | Any mid-apply error | Restore from `backups/<name>-<timestamp>.fmp12` |
