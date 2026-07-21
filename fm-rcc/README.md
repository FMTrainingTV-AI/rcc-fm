# fm-rcc — Agentic FileMaker Plugin

A Claude Code plugin that turns a session into a competent FileMaker developer. It knows the calculation language, generates and validates paste-ready XML, audits a schema from a Save-as-XML or DDR export, and **patches `.fmp12` files with backup → validate → verify → rollback safety** — plus Data API / OData / ProofKit integration, first-party docs lookup, and the BaseElements + MBS plugins.

> Working on the plugin itself: [CLAUDE.md](CLAUDE.md).

## Install

```bash
# from the rcc-fm marketplace
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install fm-rcc

# one-time per machine — the tools run on system python3, so its deps go there
pip3 install lxml requests python-dotenv
```

**Requirements:** macOS, Python 3.10+, and for *patching* the Claris CLI tools (`FMDeveloperTool`, `FMUpgradeTool` — ship with FileMaker Server, expected in `/usr/local/bin`). `/fm-rcc:fm-init` runs a doctor that checks all of it.

> Developing the plugin (running the test suite)? Use a venv instead: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

## Quickstart

```
cd my-client-project/     # a folder with your .fmp12 in it
/fm-rcc:fm-init            # ensures structure, then adopts: doctor, config, baseline export, changelog
cp .env.example .env      # fill in FM credentials if the defaults don't fit
```

`/fm-rcc:fm-init` scaffolds the project structure itself (idempotent, never overwrites), so there's no separate setup step. Then just work — the skills fire on FileMaker topics. Check state with `/fm-rcc:fm-status`, undo with `/fm-rcc:fm-rollback`, build the offline docs cache once with `/fm-rcc:fm-docs-sync`.

Use **`/fm-rcc:fm-scaffold`** on its own only when you want structure *without* a file yet (greenfield), or the wider `--full` / `--client-kit` shapes.

## The 12 skills — one verb each

Skills load automatically when the topic matches. They're organized by what you're doing:

### ✍️ Author — produce FileMaker
| Skill | Owns |
|---|---|
| **`fm-core`** | The calculation **language** — Let/Case/If, JSON functions, ExecuteSQL, text styling, dates, naming. The foundation the others build on. |
| **`fm-scripts`** | **Scripting** — write/modify scripts against *this project's real schema*, script structure, error handling, PSOS, and the FM 2024–2026 AI/script-step catalog. Drives the paste-in → updated-XML round trip. |
| **`fm-xml`** | The XML **wire format** — generate paste-ready `fmxmlsnippet` / `LayoutObjectList` / field-definition XML and review it for silent paste-handler failures. Never guesses shapes. |

### 🔎 Analyze — understand what's there
| Skill | Owns |
|---|---|
| **`fm-saxml`** | **Schema analysis** — parse a Save-as-XML (FM 2026 split-catalog) or classic DDR export into per-object files + an agent-readable knowledge base; trace refs/orphans, diff versions. Reads and analyzes; it never mutates. |
| **`fm-docs`** | **Authoritative lookup** — ground claims in first-party Claris docs (step semantics, function signatures, exact option names). Local-first cache. |

### 🚀 Deploy — change the file
| Skill | Owns |
|---|---|
| **`fm-patch`** | The **mutation pipeline** — export → diff dev/prod → generate an FMUpgradeTool patch → apply safely → verify by re-export → roll back. The only path that touches a `.fmp12`. |

### 🔌 Integrate — connect to a live file *(tool-skills: hand them creds, they run)*
| Skill | Owns |
|---|---|
| **`fm-dataapi`** | **Records** over the Data API — query/create/update/delete/find/count on a hosted file, connecting *directly* with supplied credentials. Ships a ready-to-run zero-dep client. |
| **`fm-odata`** | The **schema side-door** — connect over OData with credentials and create/alter tables & fields on a live file. SQL-DDL validation baked in (no more `8310`). Ships a ready-to-run client. |
| **`fm-admin`** | The **server door** — Admin API v2 with console credentials: hosted-file inventory, server status, and **download a hosted `.fmp12`** (close → download → always reopen). Ships a ready-to-run driver. |
| **`fm-connections`** | The **router** — which method when (MCP vs direct OData vs direct Data API vs Admin API vs offline), and the "arbitrary file → go direct, never the fixed MCP" rule. |
| **`fm-proofkit`** | The **ProofKit bridge** — MCP server (live schema, SQL, CRUD, ERD), React web-viewer apps inside FileMaker, and the ProofGeist TS toolchain for external web apps. |

### 🧩 Extend — third-party plugins *(unprefixed by design — they're separate products)*
| Skill | Owns |
|---|---|
| **`baseelements`** | The free Goya **BaseElements** plugin (`BE_*`): HTTP/cURL, files, SMTP, encryption, hashing, zip, XML/XPath, jq, PDF, shell. |
| **`mbs`** | The **MonkeyBread (MBS)** plugin's ~8,000 functions via `MBS("Component.Function";…)`: email, CURL, PDF (DynaPDF), barcodes, image processing, external SQL, Excel/Word, and more. |

## Commands — the project lifecycle

> Commands are namespaced under the plugin — type `/fm-rcc:fm-init`, `/fm-rcc:fm-status`, etc. The bare form (`/fm-init`) won't resolve.

| Command | Does |
|---|---|
| **`/fm-rcc:fm-init`** `[file.fmp12]` | Adopt a FileMaker file: doctor → ensure structure → config → baseline Save-as-XML export → seed changelog. Auto-scaffolds if the folder is bare. |
| **`/fm-rcc:fm-scaffold`** `[--full] [--client-kit]` | Lay down the standard project structure without adopting a file. |
| **`/fm-rcc:fm-status`** | Read-only health report: managed files, baselines, patch history + verdicts, backups, recent changelog. |
| **`/fm-rcc:fm-rollback`** `[ts]` | Restore a `.fmp12` to a pre-patch state — safety-copies *now* first, then verifies the change is gone. |
| **`/fm-rcc:fm-docs-sync`** `[--docsets] [--limit]` | Build/refresh the local Claris docs mirror at `~/.fm-rcc/docs-cache`. |

## Agents

- **`fm-patch-builder`** — owns the patch transaction end-to-end (gen → backup → validate → smoke → apply → verify), acting only on a human-approved `selection.json`.
- **`fm-xml-validator`** — an adversarial verifier: it didn't write the change, and its job is to *falsify* it (snippet lint, scoped re-export + re-diff, live probes).

## Under the hood — deterministic Python tools

Skills and agents drive vendored, tested engines under `tools/` via `${CLAUDE_PLUGIN_ROOT}`:

- **`tools/patch/`** — the FM-Patch-Agent pipeline (export/parse/diff/review/gen_patch/apply/scaffold).
- **`tools/ddr/`** — the Save-as-XML / DDR analysis CLI (split/summary/refs/orphans/compare/search/readable).
- **`tools/fmlint/`** — `fmxmlsnippet` linter (180+ step catalog).
- **`tools/docs/`** — the Claris docs mirror.
- **`tools/doctor.py`** — environment preflight.

Backed by a **136-test suite** (131 on the patch pipeline, including E2E against the real Claris CLI tools). `tools/genobj/` is a Phase-3 stub, not yet built. Seed file `resources/fmbase.fmp12` (~360 KB BASE + ProofKit) feeds the scaffold/E2E path.

## Safety model

Changes to a `.fmp12` only land through the pipeline: timestamped backup → `--validatePatch` on a copy → smoke apply on a copy → in-place apply → **verify by re-export + re-diff** (the tool's own success banner is known to lie). Every action appends to `fm/changelog.md`; every patch keeps before/after states under `fm/patches/<ts>/` for rollback. What gets patched is always a **human-approved selection** from the HTML review artifact — the agent never picks for you.

## Per-client kits (overlay model)

fm-rcc is the generic core. Each engagement gets a thin overlay — schema bible, glossary, recipes, guardrails, connection facts — scaffolded by `/fm-rcc:fm-scaffold --client-kit` and shipped to the client as its own plugin. Core updates never touch overlays.

## Status

Tools are vendored and tested, agents and commands are live, and the skill pack is organized as **one verb per skill**. v0.6.0 opened the **hosted-file lane**: the `fm-admin` server door (Admin API download), the `xml_to_fmp12` XML→file converter, and a scaffold that ships the remote-export toolbelt + numbered runbooks. Planned next: a deterministic `genobj` shape compiler, a fuller docs cache, and a `/fm-client-kit` generator.

---

Built by **Joe DaSilva** and **Richard Carlton**. © 2026 RCC — MIT licensed, see [LICENSE](LICENSE).
