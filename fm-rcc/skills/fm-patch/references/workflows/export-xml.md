# Export XML

## Overview

Export a FileMaker file (.fmp12) to SaXML format using FMDeveloperTool, producing an XML snapshot suitable for parsing, diffing, and patch generation. Run once for dev, once for prod. Both exports MUST use the same tool (FMDeveloperTool) for consistency — mixing tool versions produces version-mismatched output that will cause silent failures downstream.

## Scripts Used

- `fm_export.py` — headless Save-as-XML via FMDeveloperTool; handles AppleScript close/reopen for files open in FileMaker Pro; lsof-based open-file detection.

## Inputs

- Required: `<file.fmp12>` — path to the FileMaker file to export
- Required: `-o <out.xml>` — destination path for the XML output
- Optional: `--account <name>` — FileMaker account name (default: Admin)
- Optional: `--pwd <password>` — FileMaker password (default: empty string)
- Optional: `--ddr-info` — include DDR metadata
- Optional: `--stamp-guids` — add GUIDs to objects (MUST be used when exporting the dev file for patch generation; see note below)
- Optional: `--keep-closed` — do not reopen the file in FileMaker after export

## Steps

### 1. Confirm the file is accessible

- MUST verify the .fmp12 path exists and is readable before running.
- MUST confirm `.env` is not required for this script (no API keys needed; FileMaker credentials are passed on the command line).
- SHOULD confirm FMDeveloperTool is installed at its standard path. The script will raise a clear error if not found.

### 2. Export the dev file (with GUID stamping)

The dev export MUST use `--stamp-guids` so that objects get stable identity attributes. The patch generator reads GUIDs from the dev export — without them, `gen_patch.py` will fail at harvest time.

```bash
.venv/bin/python scripts/fm_export.py /path/to/dev.fmp12 \
    -o exports/dev.xml \
    --account Admin \
    --pwd "" \
    --ddr-info \
    --stamp-guids
```

**Note on --stamp-guids:** the script stamps into a temp copy (`-dest_path`) and atomically replaces the source on success, so a crash or timeout mid-stamp can never corrupt the file. (Running `FMUpgradeTool --generateGUIDs` by hand without `-inplace`/`-dest_path` writes a separate `"<name> upgraded.fmp12"` and silently leaves the source untouched — always stamp through the script.)

### 3. Export the prod file (no GUID stamping)

The prod export does NOT need `--stamp-guids`. Export with the same account credentials used in production.

```bash
.venv/bin/python scripts/fm_export.py /path/to/prod.fmp12 \
    -o exports/prod.xml \
    --account Admin \
    --pwd ""
```

### 4. Handle open files

- If the target file is open in FileMaker Pro, the script MUST close it via AppleScript before exporting and reopen it after (unless `--keep-closed` is passed).
- AppleScript close requires macOS **Automation permission**: System Settings → Privacy & Security → Automation. The first interactive use prompts the user.
- In unattended contexts (e.g., running from a background agent), AppleScript MAY time out. The exporter raises an actionable error; close the file manually in FileMaker Pro and re-run.
- Files locked by another process (e.g., FMS hosting) are detected via `lsof` and rejected with an error. MUST resolve the lock before proceeding.
- Empty password: pass `--pwd ""` (two double-quotes). Do not omit the flag; the script passes the value positionally to FMDeveloperTool.

### 5. Confirm output

- MUST verify that the output .xml file exists and is non-empty after the run.
- SHOULD spot-check that the XML version attribute matches expectations (FMDeveloperTool 22.0.5.500 emits SaXML version 2.2.3.0; FM Pro in-app export emits 2.3.0.0 — both are acceptable, but both files in a dev/prod pair MUST be exported by the same tool).

## Validation

- [ ] `exports/dev.xml` exists and is non-empty
- [ ] `exports/prod.xml` exists and is non-empty
- [ ] Both files exported by the same tool (check `FMSaveAsXML version` attribute in the XML header)
- [ ] If the export will feed ReplaceAction/DeleteAction patches: re-run with `--stamp-guids` and confirm FMUpgradeTool reports `items updated: 0` (file fully stamped). Stamping is only load-bearing for Replace/Delete, which target objects by their current UUIDs.
- [ ] No stray `"<name> upgraded.fmp12"` or `.<name>.stamping.fmp12` files remain next to the source

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| `FMDeveloperTool not found` | Tool not installed or wrong path | Install FMDeveloperTool; fatal — stop |
| `File is locked by another process` | FMS hosting or another user | Unmount/close hosting; fatal — stop |
| AppleScript timeout | Unattended context, no Automation permission | Grant permission or close file manually |
| AppleScript `privilege violation (-10004)` | TCC Automation permission denied for the calling app | System Settings → Privacy & Security → Automation → enable FileMaker Pro; or close the file manually and re-run with `--keep-closed` |
| stray `.stamping.fmp12` remains | stamping crashed mid-run (source untouched) | Delete the stray temp file and re-run |
| Output XML empty or missing | Export failed silently | Check FMDeveloperTool logs; fatal — stop |
| Wrong SaXML version | Mixed tool versions (Pro in-app vs FMDeveloperTool) | Re-export both with the same tool |
