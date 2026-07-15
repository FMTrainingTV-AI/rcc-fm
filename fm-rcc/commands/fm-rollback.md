---
description: Roll a managed FileMaker file back to a pre-patch backup or before-state
argument-hint: "[backup timestamp or patch id]"
allowed-tools: Bash, Read, Glob, AskUserQuestion
---

Restore a managed .fmp12 to a previous state. This is destructive to current file state — proceed deliberately.

1. Read `fm/fm-rcc.json`; list restore points, newest first: `fm/backups/<name>-YYYYMMDD-HHMMSS.fmp12` and each patch's `fm/patches/<ts>/before/` export record. If $ARGUMENTS names one, select it; otherwise ask the user to pick.
2. **Preconditions:** the target file must not be open (check with `lsof <file>` — if locked, ask the user to close it in FileMaker Pro). Confirm the exact restore: "replace `<target>` with `<backup>` (created <ts>)?"
3. **Safety copy of NOW:** before restoring, copy the current file to `fm/backups/<name>-preRollback-$(date +%Y%m%d-%H%M%S).fmp12` — a rollback must itself be rollbackable.
4. Restore: `cp <chosen backup> <target path>`.
5. **Verify:** re-export and confirm the restored state:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/fm_export.py <target> -o fm/patches/rollback-check.xml
   ```
   Parse and diff against the corresponding baseline/before-state snapshot (saxml_parser.py + saxml_diff.py) and report whether the rolled-back changes are gone.
6. Append a changelog entry: timestamp, file, restore point used, safety-copy path, verify result.
