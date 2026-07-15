# CLAUDE.md — developing fm-rcc

This repo IS the fm-rcc Claude Code plugin (see [README.md](README.md) for install/use). This file is for working ON the plugin.

## Layout

```
.claude-plugin/plugin.json   manifest (bump version on every shipped change)
commands/                    /* slash commands (prompt markdown, drive tools via ${CLAUDE_PLUGIN_ROOT})
agents/                      fm-patch-builder (transaction owner), fm-xml-validator (independent falsifier)
skills/                      fm-core, fm-connections, fm-xml, fm-patch, fm-proofkit, fm-docs, ddr, fm-scripts
tools/patch/                 vendored FM-Patch-Agent engine — see VENDOR.md; logic changes go upstream-style: edit + test here, note in VENDOR.md
tools/ddr/  tools/fmlint/    vendored analysis + lint engines (VENDOR.md in each)
tools/docs/  tools/doctor.py fm-rcc-native utilities (TDD'd in tests/)
tools/genobj/                Phase 3 stub — deterministic shape compiler
templates/scaffold/          what /fm-scaffold copies (gitignore ships as gitignore.template)
tests/                       patch suite (131, incl. E2E vs real Claris tools) + native tool tests + prompt-battery.md
resources/fmbase.fmp12       scaffold seed file (BASE + ProofKit) for E2E tests
```

## Rules

- **Run tests before claiming anything works:** `.venv/bin/python -m pytest tests -q` (venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`). The E2E tests need the Claris CLI tools and the sandbox: `bash tests/patch/setup_sandbox.sh`.
- **Vendored code (`tools/patch`, `tools/ddr`, `tools/fmlint`, Kear references in `skills/fm-xml`)**: don't drift casually. Real fixes are fine — with tests, and a line in the relevant `VENDOR.md`.
- **Skills reference tools via `${CLAUDE_PLUGIN_ROOT}`** — never relative paths; skills run from arbitrary project cwds.
- **The operator selection gate is sacred** (see `skills/fm-patch/references/workflows/diff-review.md` step 5): no code or prompt in this plugin may synthesize `selection.json`.
- **Clean-room rule:** nothing in this repo may be copied from Claris's beta toolkit plugin. Original code + public docs only.

## Local install for testing

This plugin ships from the `FMTrainingTV-AI/rcc-fm` marketplace (plugin folder `fm-rcc/`). To test local edits without publishing, point `--plugin-dir` at this folder:

```bash
claude --plugin-dir "$(pwd)"   # run from the fm-rcc plugin directory
```
