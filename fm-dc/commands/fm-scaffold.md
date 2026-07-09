---
description: Scaffold a DataCraft FileMaker project folder (minimized by default; --full or --client-kit for more)
argument-hint: "[--full] [--client-kit]"
allowed-tools: Bash, Read, Write, Glob
---

Scaffold the DataCraft project structure into the current directory from the plugin template. **Never overwrite an existing file** — skip it and note the skip in the report.

1. **Minimized default** — copy `${CLAUDE_PLUGIN_ROOT}/templates/scaffold/` into the cwd:

   ```bash
   rsync -a --ignore-existing ${CLAUDE_PLUGIN_ROOT}/templates/scaffold/ ./
   mv -n gitignore.template .gitignore 2>/dev/null || rm -f gitignore.template
   ```

   Result: `CLAUDE.md` (project stub), `_pm/` (skeleton.md, TASKS.md, sessions/), `schema/{ddrs,parsed,readable,reports}/`, `dev/`, `.env.example`, `.gitignore`.

2. **`--full`** (in $ARGUMENTS) — additionally create the wider starter shape: `webviewer/`, `web/`, `docs/guides/`, `docs/reference/`, `docs/notes/`, plus empty `docs/quirks.md` and `docs/learnings.md` with one-line headers explaining their purpose.

3. **`--client-kit`** (in $ARGUMENTS) — additionally create the per-client overlay skeleton at `client-kit/` (the deliverable that ships to the client, per the DataCraft client-kit model):

   ```
   client-kit/
   ├── .claude-plugin/plugin.json        ← stub: name "<client>-filemaker", version 0.1.0
   └── skills/<client>-filemaker/
       ├── SKILL.md                      ← trigger metadata stub
       ├── connection.md  schema.md  glossary.md  recipes.md  guardrails.md   ← per-client stubs
       ├── samples/
       └── scripts/fm_client.py          ← copy from ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm_client.py
   ```

   Ask for the client name first and substitute it throughout. Stub bodies: one heading + a comment saying what to fill in and from where (schema.md ← parsed DDR; glossary.md ← client conversations; recipes.md ← observed workflows; guardrails.md ← read-only defaults, layout whitelist).

4. **Fill what's knowable:** set the folder name into `CLAUDE.md`'s `<Project Name>` and `fm-dc.json`-less defaults; leave client-specific blanks alone.

5. **Report** the tree created, files skipped, and next steps: fill `_pm/skeleton.md`, copy `.env.example` → `.env`, then `/fm-init` to adopt the .fmp12.
