# ProofKit

**Site:** https://proofkit.proof.sh
**Docs:** https://proofkit.proof.sh/docs
**Community:** https://community.proof.sh/c/proofkit

> **ProofKit is evolving fast and is currently pre-stable** (the CLI publishes under `@proofkit/cli@beta`). There's no formal changelog or release-notes page yet, and update mechanisms aren't documented in one place. Before relying on anything described below, **check ProofKit's own site, docs, and community forum for what's current.** Treat this page as a stable-against-the-framework pointer, not a source of truth about ProofKit itself.

ProofKit is a toolkit for building modern web interfaces that talk to FileMaker. It wraps the Data API behind a developer experience designed for AI-assisted work and ships three integration paths the raw FM APIs don't.

## Three things ProofKit gives you

### 1. MCP server

A Model Context Protocol server that connects to an open FileMaker file via the ProofKit desktop app. The agent gets live, structured access to:

- Schema (table occurrences, relationships, layouts, value lists, scripts)
- DDL generation for selected table occurrences
- Read-only SQL via `execute_filemaker_sql`
- Full CRUD via `data_api_orchestrator`
- Web viewer scaffolding (`setup_proofkit_project`) and deployment (`deploy_html`)
- An interactive ERD via `display_erd_diagram`

This is the framework's preferred mode for active development. See "Database Access — Four Modes" and the ProofKit MCP tool list in [`CLAUDE.md`](../../CLAUDE.md) for the working tool surface.

### 2. Web viewers

React + TypeScript + shadcn/ui + TanStack Query apps that build to a single self-contained `index.html`, then get pushed into a FileMaker Web Viewer object via `deploy_html`. They inherit the host file's security, run inside the layout, and can do things native FM layouts can't: kanban boards, calendars, data grids, drag-and-drop, dashboards.

The framework reserves `webviewer/` for these. For the hands-on build playbook with real-world gotchas, see [`docs/guides/proofkit_webviewer_build.md`](../guides/proofkit_webviewer_build.md). The "Web Viewer Apps (ProofKit)" section in [`CLAUDE.md`](../../CLAUDE.md) has the workflow at a glance.

### 3. Full web apps

Standalone web applications that use FileMaker as a backend rather than living inside it. Deployed to a normal hosting target (Vercel, own server, etc.). Useful when the UI needs to live outside FM — public-facing portal, mobile-friendly app, internal dashboard for non-FM users.

ProofGeist publishes a TypeScript toolchain for this — **the recommended stack** when starting a new external web app:

| Package | What it does | Docs |
|---|---|---|
| `@proofkit/fmdapi` | TypeScript Data API client; runs in any Node runtime (Next.js server actions, API routes, scripts) | https://proofkit.proof.sh/docs/fmdapi |
| `@proofkit/typegen` | Generates TypeScript types + validation schemas from live FM layouts | https://proofkit.proof.sh/docs/typegen |
| `@proofkit/fmodata` | TypeScript OData client (bulk/typed table access when layout-scoped reads aren't enough) | https://proofkit.proof.sh/docs/fmodata |
| `@proofkit/better-auth` | Self-hosted auth backed by FileMaker — adds sign-in when the app needs it | https://proofkit.proof.sh/docs/better-auth |

Typical pairing: **Next.js (App Router) + `@proofkit/fmdapi` + `@proofkit/typegen`**, plus `better-auth` when auth is needed.

Scaffold with `pnpm create proofkit` (interactive) or `npx @proofkit/cli@beta init . --app-type <type> --non-interactive`. Same CLI that scaffolds web viewers also scaffolds external apps — different `--app-type`. After scaffolding, run `npx @tanstack/intent@latest install` to load ProofKit's AI-agent skills into the project (gives future sessions current in-context docs for `fmdapi`, `typegen`, and friends).

The framework reserves `web/` for these. See [`web/README.md`](../../web/README.md) for folder conventions and the "External Web Apps" section in [`CLAUDE.md`](../../CLAUDE.md) for the full pattern.

## When to use which

| Goal | Path |
|---|---|
| Live schema exploration, SQL queries, CRUD testing during development | ProofKit MCP |
| Custom UI inside an FM layout (FM users only) | Web viewer |
| UI outside FM (public users, mobile, no FM client) | Full web app — see `web/` and the `@proofkit/fmdapi` stack above |
| Headless / scripted access (Cowork, Codex, no app installed) | `plugin/skills/client-filemaker/scripts/fm_client.py` (Data API) |
| Static structural analysis (calcs, scripts, relationships) | DDR pipeline (`scripts/ddr.py` skill) |

ProofKit is not a replacement for the Data API or OData — it's a developer surface on top of them. For protocol-level integration detail (auth, payloads, OData syntax, OttoFMS), see [`filemaker_integration_guide.md`](filemaker_integration_guide.md).

## Setup and updates

ProofKit's own docs at https://proofkit.proof.sh/docs are authoritative for installing the desktop app, scaffolding projects (`npx @proofkit/cli@beta init`), and configuring the MCP server. This framework deliberately doesn't duplicate that — it would rot.

**Staying current:** because ProofKit doesn't publish a centralized changelog yet, the practical pattern is:

- Re-read the docs site before starting a new ProofKit project — workflows shift between releases.
- Use `npx @proofkit/cli@beta ...` (note the `@beta` tag) to always pull the latest pre-stable CLI rather than pinning a version.
- After scaffolding, **follow the skills the ProofKit CLI installs into the project** — those are versioned with the CLI and reflect current best practice for that release.
- Watch the community forum (https://community.proof.sh/c/proofkit) for announcements.

If your local ProofKit-built code stops working after a CLI update, the cause is almost always a workflow change ProofKit shipped — re-scaffolding or re-running TypeGen against the new CLI usually resolves it.
