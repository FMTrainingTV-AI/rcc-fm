# Database Access — the Four Modes

Pick the mode by what you're doing. They coexist — a real dev session weaves between them turn by turn: read schema via MCP, mutate via OData, verify via a refreshed MCP call, query data via the Data API. That's normal, not a workflow failure.

| Mode | Requires | Best for |
|------|----------|---------|
| **ProofKit MCP** | ProofKit app + FM file open (bridge active) | Active dev: live schema exploration, SQL queries, CRUD testing, web viewer builds |
| **Data API** (`fm-dataapi` skill: `fm.py` / `fm_client.py`; or `@proofkit/fmdapi`) | FM Server reachable (no app needed) | Headless/automated: agents, scripted workflows, layout-scoped reads/writes |
| **OData** | FM Server with OData enabled | **Schema mutations** (create tables, add fields) — the only live path that exposes these. Also bulk/typed table access |
| **Schema pipeline** (`${CLAUDE_PLUGIN_ROOT}/tools/ddr/ddr.py`) | DDR or FM 2026 Save-as-XML export | Deep static analysis: calcs, scripts, relationship graph, offline reference, agent knowledge base |

## How to pick

**Default to ProofKit MCP when the bridge is up.** Verify with `connectedFiles` at session start — if it returns the file name, everything works; if empty, ask the user to run the "Connect to MCP" script in FileMaker.

| You need to… | Reach for |
|---|---|
| Browse live schema, run ad-hoc SQL, check what's on a layout | **ProofKit MCP** (`table_metadata`, `layout_metadata`, `execute_filemaker_sql`) |
| Read/write records with typed/scoped layout access | **Data API** |
| Create a table, add a field, change schema programmatically | **OData** (Data API can't; MCP doesn't expose it) |
| Read the whole graph offline — calcs, scripts, value lists at depth | **Schema pipeline** (`ddr.py`) |
| Write scripts/layouts/fields as XML | **fm-xml skill** (generation) → fmlint (check) → patch via fm-patch or clipboard paste |

## Key constraints

- **The Data API is layout-based.** You query a layout, not a table; only fields on the layout come back. Always use dedicated API layouts with a consistent prefix (`AI_*`, `zAPI_*` — one convention per project). The layout is the security boundary.
- **OData creates tables/fields but not layouts.** After an OData schema mutation, someone must create the API layout in FileMaker before the Data API can see the new table. The fm-xml skill's layout references soften this: generate the layout as clipboard XML for a human paste.
- **Date format on Data API writes is `MM/DD/YYYY`.** ISO fails silently.
- Credentials come from `.env`: `FM_HOST`, `FM_DATABASE`, `FM_USERNAME`, `FM_PASSWORD`. Read-only service accounts scoped to API layouts by default; write operations need an explicit flag plus human confirmation.

## A normal four-mode task

Spot a missing field via MCP → add it via OData → refresh MCP to confirm → create the API layout in FM (human step, or clipboard XML) → query via Data API to verify the round-trip. Four modes, one task, correct answer.
