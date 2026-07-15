---
description: Adopt a FileMaker file (local .fmp12 or hosted) — ensures project structure, doctor checks, config, baseline export, change log
argument-hint: "[path/to/file.fmp12 | host/File.fmp12]"
allowed-tools: Bash, Read, Write, Glob, AskUserQuestion
---

Initialize the current project for fm-rcc-managed FileMaker development. Because init means "I'm about to patch this file," it also makes sure the project structure exists — no separate scaffold step required.

**Two adoption modes.** A **local** `.fmp12` on disk gets the full pipeline (baseline via FMDeveloperTool, patching). A **hosted** file (there is no local copy — only a server) gets the same project structure plus a remote connection config; its baseline comes over the wire. Detect hosted mode when: $ARGUMENTS looks like `host/File.fmp12`, an `fmnet:/` path, or a URL; or no `.fmp12` exists locally and the user says the file is hosted.

1. **Doctor first.** Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/doctor.py` and show the table.
   - *Local mode:* if FMDeveloperTool or FMUpgradeTool is missing, stop and tell the user what to install — nothing below works without them.
   - *Hosted mode:* the Claris CLI tools are NOT required — only `python3` and network reach to the server. Note missing CLI tools as "needed later if you patch locally," don't stop.

2. **Find the file(s).** Use $ARGUMENTS if given; otherwise glob `*.fmp12` in the project (excluding `fm/backups/`). Confirm with the user: file path(s), account name, and password env var. Defaults: account `Admin`, empty password (FileMaker defaults) via `FM_DEV_USER`/`FM_DEV_PASS` from `.env` if present.
   - **No `.fmp12` anywhere?** Ask whether the file is **hosted**. If yes → hosted mode: collect server host, file name, and an OData-enabled account, then continue below (structure, config, remote baseline). If the project truly has no file yet, point the user at `/fm-rcc:fm-scaffold` to lay down structure and re-run `/fm-rcc:fm-init` later.

2a. **Hosted mode specifics.**
   - Write credentials to `fm/hostedFile.md` (`server - host` / `file - X.fmp12` / `account - user` / `pass - secret`, the fm-odata config shape). Ensure `.gitignore` covers it — credentials never commit.
   - Verify the connection: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-odata/scripts/fm_odata.py connect --config fm/hostedFile.md`.
   - **Remote baseline** requires the `Agent_SaXML_Export` script installed in the hosted file (a one-time, per-file setup). Probe with a trigger call; if it 404s, **offer the setup interview** from `${CLAUDE_PLUGIN_ROOT}/docs/guides/remote-file-agent-workflow.md` §3 — ask before acting, choose/create the drop table (every file is different; nothing is hardcoded), walk the human layout step if needed, generate the script from `${CLAUDE_PLUGIN_ROOT}/templates/agent-saxml-export.template.xml` with that file's names, print it on screen for the paste, record the chosen names in `fm/fm-rcc.json`, then smoke-test. Once installed, trigger the export over OData and land the XML in `schema/ddrs/YYYY-MM-DD/` (this replaces step 5's local export; parse it per the fm-saxml skill).
   - In `fm/fm-rcc.json`, record the file with `"hosted": true` and `"config": "fm/hostedFile.md"` instead of a local path. Patching a hosted file still requires downloading a closed copy later — say so in the report.

3. **Ensure project structure (silent, idempotent).** Patching needs somewhere to live, so lay down the minimized project structure — don't ask, just do it. It never overwrites, so this is safe whether the folder is empty, half-set-up, or complete:

   ```bash
   rsync -a --ignore-existing ${CLAUDE_PLUGIN_ROOT}/templates/scaffold/ ./
   mv -n gitignore.template .gitignore 2>/dev/null || rm -f gitignore.template
   ```

   Note which files were newly created (vs already present) so the report can show it. Minimized only — `--full` / `--client-kit` stay opt-in via `/fm-rcc:fm-scaffold`.

4. **Write `fm/fm-rcc.json`** (create the `fm/` tree: `fm/baseline/`, `fm/patches/`, `fm/backups/`):

   ```json
   {
     "project": "<folder name>",
     "files": [
       { "path": "<relative path to .fmp12>", "account_env": "FM_DEV_USER", "password_env": "FM_DEV_PASS" }
     ]
   }
   ```

   If `fm/fm-rcc.json` already exists, show it and ask whether to add files or reconfigure — never silently overwrite.

5. **Baseline export** for each managed file:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/fm_export.py <file>.fmp12 -o fm/baseline/<name>-$(date +%Y%m%d).xml --stamp-guids
   ```

   The exporter closes/reopens an open local file safely; if it reports a lock it can't clear, ask the user to close the file in FileMaker Pro.

6. **Seed `fm/changelog.md`** with a header and an `init` entry (date, files adopted, baseline paths). Every future patch/rollback appends here — it's the project's audit proxy.

7. **Report:** doctor summary, **project structure created** (list newly-scaffolded files, or note "structure already present"), managed files, baseline location, and what's now possible (fm-patch skill, `/fm-rcc:fm-status`, `/fm-rcc:fm-rollback`).
