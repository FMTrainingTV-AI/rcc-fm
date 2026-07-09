---
description: Adopt a FileMaker file — ensures project structure, doctor checks, config, baseline Save-as-XML export, change log
argument-hint: "[path/to/file.fmp12]"
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

Initialize the current project for fm-dc-managed FileMaker development. Mirrors the shape of Claris's `/filemaker-init`, using the DataCraft pipeline. Because init means "I'm about to patch this file," it also makes sure the project structure exists — no separate scaffold step required.

1. **Doctor first.** Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/doctor.py` and show the table. If FMDeveloperTool or FMUpgradeTool is missing, stop and tell the user what to install — nothing below works without them.

2. **Find the file(s).** Use $ARGUMENTS if given; otherwise glob `*.fmp12` in the project (excluding `fm/backups/`). Confirm with the user: file path(s), account name, and password env var. Defaults: account `Admin`, empty password (FileMaker defaults) via `FM_DEV_USER`/`FM_DEV_PASS` from `.env` if present.
   - **No `.fmp12` anywhere?** Stop. This is a greenfield project — there's nothing to adopt yet. Point the user at `/fm-scaffold` to lay down structure, then add their file and re-run `/fm-init`.

3. **Ensure project structure (silent, idempotent).** Patching needs somewhere to live, so lay down the minimized DataCraft structure — don't ask, just do it. It never overwrites, so this is safe whether the folder is empty, half-set-up, or complete:

   ```bash
   rsync -a --ignore-existing ${CLAUDE_PLUGIN_ROOT}/templates/scaffold/ ./
   mv -n gitignore.template .gitignore 2>/dev/null || rm -f gitignore.template
   ```

   Note which files were newly created (vs already present) so the report can show it. Minimized only — `--full` / `--client-kit` stay opt-in via `/fm-scaffold`.

4. **Write `fm/fm-dc.json`** (create the `fm/` tree: `fm/baseline/`, `fm/patches/`, `fm/backups/`):

   ```json
   {
     "project": "<folder name>",
     "files": [
       { "path": "<relative path to .fmp12>", "account_env": "FM_DEV_USER", "password_env": "FM_DEV_PASS" }
     ]
   }
   ```

   If `fm/fm-dc.json` already exists, show it and ask whether to add files or reconfigure — never silently overwrite.

5. **Baseline export** for each managed file:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/fm_export.py <file>.fmp12 -o fm/baseline/<name>-$(date +%Y%m%d).xml --stamp-guids
   ```

   The exporter closes/reopens an open local file safely; if it reports a lock it can't clear, ask the user to close the file in FileMaker Pro.

6. **Seed `fm/changelog.md`** with a header and an `init` entry (date, files adopted, baseline paths). Every future patch/rollback appends here — it's the project's audit proxy.

7. **Report:** doctor summary, **project structure created** (list newly-scaffolded files, or note "structure already present"), managed files, baseline location, and what's now possible (fm-patch skill, `/fm-status`, `/fm-rollback`).
