---
description: Adopt a FileMaker file/project — doctor checks, config, baseline Save-as-XML export, change log
argument-hint: "[path/to/file.fmp12]"
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

Initialize the current project for fm-dc-managed FileMaker development. Mirrors the shape of Claris's `/filemaker-init`, using the DataCraft pipeline.

1. **Doctor first.** Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/doctor.py` and show the table. If FMDeveloperTool or FMUpgradeTool is missing, stop and tell the user what to install — nothing below works without them.

2. **Find the file(s).** Use $ARGUMENTS if given; otherwise glob `*.fmp12` in the project (excluding `fm/backups/`). Confirm with the user: file path(s), account name, and password env var. Defaults: account `Admin`, empty password (FileMaker defaults) via `FM_DEV_USER`/`FM_DEV_PASS` from `.env` if present.

3. **Write `fm/fm-dc.json`** (create the `fm/` tree: `fm/baseline/`, `fm/patches/`, `fm/backups/`):

   ```json
   {
     "project": "<folder name>",
     "files": [
       { "path": "<relative path to .fmp12>", "account_env": "FM_DEV_USER", "password_env": "FM_DEV_PASS" }
     ]
   }
   ```

   If `fm/fm-dc.json` already exists, show it and ask whether to add files or reconfigure — never silently overwrite.

4. **Baseline export** for each managed file:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/fm_export.py <file>.fmp12 -o fm/baseline/<name>-$(date +%Y%m%d).xml --stamp-guids
   ```

   The exporter closes/reopens an open local file safely; if it reports a lock it can't clear, ask the user to close the file in FileMaker Pro.

5. **Seed `fm/changelog.md`** with a header and an `init` entry (date, files adopted, baseline paths). Every future patch/rollback appends here — it's the project's audit proxy.

6. **Report:** doctor summary, managed files, baseline location, and what's now possible (fm-patch skill, `/fm-status`, `/fm-rollback`). Suggest `/fm-scaffold` if the project folder has no structure yet.
