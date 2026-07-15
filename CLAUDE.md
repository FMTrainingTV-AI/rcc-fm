# CLAUDE.md — rcc-fm marketplace

This repo is a **Claude Code plugin marketplace** (`FMTrainingTV-AI/rcc-fm`). One `.claude-plugin/marketplace.json` lists its single plugin, **`fm-rcc`** (agentic FileMaker development), which lives in its own subfolder with its own `.claude-plugin/plugin.json`. Installed once per machine (`/plugin marketplace add FMTrainingTV-AI/rcc-fm`), then `/plugin install fm-rcc`.

This is an **RCC-branded fork** of an upstream FileMaker plugin: vendor branding is stripped, the namespace and data paths are renamed to `fm-rcc`, and internal design docs are omitted. It is hand-maintained — when pulling a newer upstream version to parity, re-apply that same debrand (strip vendor branding, rename every `fm-rcc` token consistently, drop internal `SCOPE.md`/`docs/`, keep the `fm-rcc.json` / `~/.fm-rcc/` data paths, add the MIT `LICENSE` + credit footer) and re-run the checks below.

## ⚠️ Pre-flight: adding or copying anything INTO this repo

The plugin is **shared across machines via git**. A file that works locally can silently break on another machine. Run every check below before claiming it works — each is a gotcha we have actually hit.

1. **Symlinks — the #1 gotcha.** `cp -R` copies a symlink as a link, not its target, so anything symlinked out (e.g. a skill kept in iCloud/Obsidian) ships as a dangling reference that won't resolve on install.
   ```bash
   git -C <source> ls-files -s | awk '$1=="120000"'      # any output = a committed symlink
   find <source-dir> -type l                              # untracked symlinks
   ```
   Fix: dereference into real files — `cp -RL`, or `rm link && cp -R <resolved-target> <dest>`.

2. **Copy git-tracked files ONLY.** A raw `cp -R` drags in `.venv/`, `sandbox/`, `__pycache__/`, `.pytest_cache/`, `.DS_Store`, and possibly **client data**. Copy the committed set instead:
   ```bash
   git -C <source> archive HEAD | tar -x -C <dest>
   ```
   Then confirm none of those dirs landed in `<dest>`.

3. **No machine-specific absolute paths** in shipped files:
   ```bash
   git grep -n "/Users/" -- '*.md' '*.py' '*.json' '*.txt'
   ```
   Rewrite install/usage docs to the marketplace form (`/plugin install fm-rcc`), not `claude --plugin-dir /Users/...`. (Provenance notes in `VENDOR.md` are fine.)

4. **Tool invocation must be portable.** Scripts must be called via `python3 ${CLAUDE_PLUGIN_ROOT}/…`, never a hardcoded `.venv/bin/python` — the venv does not travel. Runtime deps go into **system `python3`** per machine; document them (`pip3 install lxml requests python-dotenv`).

5. **Validate the manifests are real JSON:**
   ```bash
   python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('**/.claude-plugin/*.json', recursive=True)]; print('OK')"
   ```

6. **Test from THIS location, not the source.** Parity with upstream is only proven by the suite passing here:
   ```bash
   cd fm-rcc && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt \
     && bash tests/patch/setup_sandbox.sh && .venv/bin/python -m pytest tests -q
   ```

7. **Bump the plugin's `version`** in `fm-rcc/.claude-plugin/plugin.json` on any shipped change, so `/plugin marketplace update` actually pulls it.

## Renaming — watch for name-shaped strings that aren't the name

The plugin's name drives its command namespace (`/fm-rcc:<command>`), but the same token also appears as **config filenames and cache paths hardcoded in code** (`fm-rcc.json`, `~/.fm-rcc/`). In this fork those data paths were renamed together with the namespace, so they stay internally consistent — keep them that way. Never split the namespace and the data paths apart.

## Dev workflow

Develop **in place** in `fm-rcc/`. Ship a change: commit + push, then `/plugin marketplace update rcc-fm` on each machine.

## Tracking (`_pm/`, local-only)

Root `_pm/` holds personal dev tracking. It is **gitignored** (`/_pm/`) — never published. Because this repo lives in Dropbox, `_pm/` still syncs across machines outside of git.
