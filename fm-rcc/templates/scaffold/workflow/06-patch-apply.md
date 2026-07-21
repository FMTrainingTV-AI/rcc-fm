# 06 — Patch apply (gen → apply → verify, never trust the banner)

> Pulled from FM-Patch-Agent 2026-07-16. Tool paths: see runbook 04's `$PT`
> convention. After every run: append to [`../logs/patch-apply.log.md`](../logs/).
> Heavy transactions: delegate to the `fm-rcc:fm-patch-builder` agent once the
> operator has produced selection.json.

## Overview

Generate an FMUpgradeTool patch from the dev export + operator selection,
apply it safely to the prod file, verify every selected item resolved. The
file MUST be closed for apply and verify. A timestamped backup is automatic.
If verify fails: restore from backup and investigate — never leave a
partially patched file in production.

Mandatory sequence: **gen → resolve DependencyError → apply → verify → reopen.**

## Steps

### 1. Prerequisites

`dev.xml` (GUID-stamped), `prod.xml`, `diff.json`, operator `selection.json`,
and the target .fmp12 all present; target closed (lsof-checked by the tool).

### 2. Generate

```bash
python3 "$PT/gen_patch.py" \
    --dev-export <work>/dev.xml --prod-export <work>/prod.xml \
    --diff <work>/diff.json --selection <work>/selection.json \
    -o <work>/patch.xml            # add --allow-caution ONLY with explicit operator ack
```

**Exit 2 = DependencyError:** the message lists missing dependencies. Expand
the selection (back through runbook 05) to include them. MUST NOT hand-edit
patch XML — the format is brittle; edits produce silent no-ops or corruption.

Baked-in learnings:
- Generator REJECTS ignored / duplicate-named / manual-tier selections — fix
  the selection or the file, don't work around.
- Auto-enter and validation calcs get ModifyAction re-apply stubs, same as
  top-level calcs — without them, field-referencing formulas land silently
  commented out as `/* … */`.
- Field ReplaceAction preserves PROD's serial `nextvalue` — shipping dev's
  stale counter would mint duplicate serials invisibly to the verify oracle.
- Stale diff.json (from different exports) triggers a loud warning —
  regenerate, don't ignore.
- Catalog order is non-negotiable: BaseTable → FieldsForTables → TO →
  Relationship → ValueList → CustomFunction → Script → Layout, with
  StepsForScripts LAST. FMUpgradeTool processes top-to-bottom.
- Script ReplaceAction rejects step divergence (format can't carry step
  bodies in a Replace) — step changes go delete+re-add, currently manual.
- Custom function changes are manual (official Replace limitation).
- Added scripts land at ScriptCatalog top level — folder placement is lost.
- Relationship and external-data-source deletes are manual.

### 3. Close the target

The tool REFUSES locked files and never closes anything itself. **Operator
prompt (MUST): ask by name — "please CLOSE <file>.fmp12"** — then verify via
lsof before applying.

### 4. Apply

```bash
python3 "$PT/apply_patch.py" apply /path/to/prod.fmp12 <work>/patch.xml \
    --account Admin --pwd "" --backups-dir <work>/backups
```

Internally: lsof check → `--validatePatch` on a temp copy → smoke `--update`
on another temp copy → timestamped size-verified backup → re-check lock →
real in-place apply → auto-restore from backup on failure/hang.

**CRITICAL: "Patch File Applied" prints even on silent no-ops.** The tool's
banner and exit code prove nothing. Verify is the only oracle.

### 5. Verify — mandatory, immediately

```bash
python3 "$PT/apply_patch.py" verify \
    --dev-export <work>/dev.xml --patched /path/to/prod.fmp12 \
    --selection <work>/selection.json --workdir <work>/verify \
    --account Admin --pwd ""
```

Re-exports the patched file (mirroring the dev export's `Has_DDR_INFO` —
asymmetry re-diffs DDR-only annotations as spurious modifications), re-diffs
against dev, and requires every selected key gone. Exit 0 = verified.

**If verify fails:** restore the backup immediately, investigate before any
retry. Known causes: silent no-op (catalog order, forward-reference calcs),
locked object, missing dependency. Diagnosis lever: re-run the failing apply
against a scratch copy with FMUpgradeTool's `-v` (verbose) — the pipeline
doesn't pass it by default (see runbook 00). Deletes verify differently — a deleted
object legitimately re-appears as "added" in dev-vs-patched diffs; assert
key absence in the re-parsed snapshot instead.

### 6. Reopen

**Operator prompt (MUST): "please OPEN <file>.fmp12"** if it was open before.

## Validation

- [ ] gen exit 0 · apply exit 0 · **verify exit 0** (`verified: true`)
- [ ] Backup exists · target opens in FileMaker afterward
- [ ] Run log entry appended

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| gen exit 2 | Missing deps | Expand selection; re-gen |
| Locked on apply | File open / hosted | Close; fatal until resolved |
| validatePatch fails | Malformed patch | Re-gen (never hand-edit); escalate |
| Smoke fails | Tool/version issue | Escalate before touching target |
| verify exit 1 | Silent no-op / partial apply | **Restore backup**; investigate |
| Banner says applied, verify fails | Expected tool behavior | Restore; the banner lies |
