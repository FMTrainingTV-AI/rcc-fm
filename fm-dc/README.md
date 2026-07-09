# fm-dc — DataCraft Agentic FileMaker Plugin

A Claude Code plugin that turns a session into a competent FileMaker developer: SaXML **patching** with verify/rollback, **DDR/Save-as-XML analysis**, **snippet validation**, **ProofKit** and **server-connection** doctrine, first-party **docs lookup**, and DataCraft **project scaffolding**.

> Why this exists and where it's going: [SCOPE.md](SCOPE.md). Working on the plugin itself: [CLAUDE.md](CLAUDE.md).

## Install

```bash
# install from the dc-plugins marketplace
/plugin marketplace add datacraftdevelopment/dc-plugins
/plugin install fm-dc

# one-time, on each machine: the tools call system python3, so its deps go there
pip3 install lxml requests python-dotenv
```

> Developing the plugin (running the test suite) instead? Use a venv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

Requirements: macOS, Python 3.10+, and for patching the Claris CLI tools (`FMDeveloperTool`, `FMUpgradeTool` — ship with FileMaker Server; expected in `/usr/local/bin`). `/fm-init` runs a doctor that checks all of this.

## Quickstart

```
cd my-client-project/          # a folder with your .fmp12 in it
/fm-init                       # ensures structure, then adopts: doctor, config, baseline export, changelog
cp .env.example .env           # fill in FM credentials (if the defaults don't fit)
```

`/fm-init` scaffolds the project structure on its own (idempotent, never overwrites), so you don't need a separate step. Reach for **`/fm-scaffold`** directly only when you want structure *without* adopting a file yet — a greenfield project, or `--full` / `--client-kit` shapes.

Then just work — the skills trigger on FileMaker topics. Check state anytime with `/fm-status`; undo with `/fm-rollback`; build the offline docs cache once with `/fm-docs-sync`.

## What's inside

| | |
|---|---|
| **Skills** | `fm-core` (calcs, script patterns, FM 2024–2026) · `fm-xml` (snippet/layout/field XML + SaXML grammar; never guesses shapes) · `fm-patch` (pipeline doctrine + patchability tiers) · `fm-connections` (four-mode doctrine: ProofKit MCP / Data API / OData / schema pipeline) · `fm-proofkit` (MCP, web viewers, TS toolchain) · `fm-docs` (local-first Claris docs) · `ddr` + `fm-scripts` (schema analysis + script round-trip) · `baseelements` (free BE plugin: HTTP, SMTP, encryption, zip, jq/XPath) · `mbs` (MonkeyBread plugin: CURL, email, files, and native-gap capabilities) |
| **Agents** | `fm-patch-builder` — owns the patch transaction (gen → backup → validate → smoke → apply → verify), honors the operator selection gate · `fm-xml-validator` — independent falsifier (lint, scoped re-export verify, live probes) |
| **Tools** | `tools/patch/` — export/parse/diff/review/gen_patch/apply/scaffold (vendored FM-Patch-Agent engine, 131 tests incl. E2E against real Claris tools) · `tools/ddr/` — DDR/SaXML analysis CLI · `tools/fmlint/` — snippet linter · `tools/docs/` — Claris docs mirror · `tools/doctor.py` |
| **Commands** | `/fm-init` · `/fm-scaffold` · `/fm-status` · `/fm-rollback` · `/fm-docs-sync` |

## Safety model

Changes to a `.fmp12` only land through the pipeline: timestamped backup → `--validatePatch` on a copy → smoke apply on a copy → in-place apply → **verify by re-export + re-diff** (the tool's own success banner is known to lie). Every action appends to the project's `fm/changelog.md`; every patch keeps before/after states under `fm/patches/<ts>/` for rollback. What gets patched is always a **human-approved selection** from the HTML review artifact — the agent never picks for you.

## Per-client kits (overlay model)

fm-dc is the generic core. Each client engagement gets a thin overlay — schema bible, glossary, recipes, guardrails, connection facts — scaffolded by `/fm-scaffold --client-kit` and shipped to the client as its own plugin. Core updates never touch overlays.

## Status

Phases 0–2 of [SCOPE.md](SCOPE.md) built (tools vendored + tested, skills consolidated, agents + commands live). Phase 3 (deterministic `genobj` shape compiler, full docs cache, prompt battery) and Phase 4 (hosted-file lane, `/fm-client-kit` generator, schema-builder agent) are next — see SCOPE §9.
