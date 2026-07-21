# 04 — Export local files as XML (the patch pipeline's read step)

> The scripts live in the plugin; resolve them once per session:
>
> ```bash
> PT="${CLAUDE_PLUGIN_ROOT}/tools/patch"     # run with system python3 (deps: lxml, requests)
> ```
>
> (Outside an agent session, `CLAUDE_PLUGIN_ROOT` is the installed plugin's
> folder under `~/.claude/plugins/cache/`.)
>
> After every run: append an entry to [`../logs/export-xml.log.md`](../logs/).

## Overview

Export a **local** FileMaker file (.fmp12) to SaXML using FMDeveloperTool —
the snapshot that feeds parsing, diffing, and patch generation. Run once for
dev, once for prod. Both exports MUST use the same tool — mixing tool
versions (FMDeveloperTool 22.0.5 emits SaXML 2.2.3.0; FM Pro in-app emits
2.3.0.0) causes silent failures downstream. (Hosted files use the OData
path instead — runbook 03.)

Working dir convention: `<work>` = `dev/<job>/` (scratch, not committed).

## Steps

### 1. Confirm the file is accessible

- MUST verify the .fmp12 path exists and is readable.
- SHOULD confirm FMDeveloperTool is installed (`/usr/local/bin/`); the
  script raises a clear error if not.

### 2. Export the dev file (with GUID stamping)

The dev export MUST use `--stamp-guids` so objects get stable identity —
`gen_patch.py` reads GUIDs from the dev export and fails at harvest without
them.

```bash
python3 "$PT/fm_export.py" /path/to/dev.fmp12 \
    -o <work>/dev.xml --account Admin --pwd "" --ddr-info --stamp-guids
```

**Note on --stamp-guids:** the script stamps into a temp copy and atomically
replaces the source on success — a crash mid-stamp can never corrupt the
file. (Running `FMUpgradeTool --generateGUIDs` by hand without
`-inplace`/`-dest_path` writes a separate `"<name> upgraded.fmp12"` and
silently leaves the source untouched — always stamp through the script.)

### 3. Export the prod file (no GUID stamping)

```bash
python3 "$PT/fm_export.py" /path/to/prod.fmp12 -o <work>/prod.xml --account Admin --pwd ""
```

### 4. Handle open files

- If the target is open in FileMaker Pro, the script closes it via
  AppleScript and reopens after (unless `--keep-closed`). First interactive
  use prompts for macOS Automation permission.
- Unattended contexts MAY hit an AppleScript timeout — close the file
  manually and re-run.
- Files locked by another process (FMS hosting) are detected via `lsof` and
  rejected. Resolve the lock first.
- Empty password: pass `--pwd ""` explicitly — don't omit the flag.

### 5. Confirm output

- MUST verify the output .xml exists and is non-empty.
- SHOULD spot-check the `FMSaveAsXML version` attribute — both files in a
  dev/prod pair MUST come from the same tool.

## Validation

- [ ] `<work>/dev.xml` and `<work>/prod.xml` exist, non-empty
- [ ] Same `FMSaveAsXML version` in both headers
- [ ] Feeding Replace/Delete patches? Re-run `--stamp-guids` until
      FMUpgradeTool reports `items updated: 0` (stamping is only
      load-bearing for Replace/Delete, which target current UUIDs)
- [ ] No stray `"<name> upgraded.fmp12"` / `.<name>.stamping.fmp12` files

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `FMDeveloperTool not found` | Not installed | Install FM Server CLI tools; fatal |
| `File is locked by another process` | FMS hosting / another user | Close hosting; fatal until resolved |
| AppleScript timeout | Unattended, no Automation permission | Grant permission or close manually |
| AppleScript `-10004` | TCC Automation denied | System Settings → Privacy & Security → Automation → enable; or `--keep-closed` after closing manually |
| stray `.stamping.fmp12` | stamping crashed (source untouched) | Delete the temp, re-run |
| Output XML empty | Silent export failure | Check tool logs; fatal |
| Wrong SaXML version | Mixed tools | Re-export both with the same tool |
