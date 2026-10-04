# Database Access — the Three Modes

Pick the mode by what you're doing. They coexist — a real dev session weaves between them turn by turn: read the design from the schema pipeline, mutate via OData, verify via a fresh OData `schema` read, query data via the Data API. That's normal, not a workflow failure.

| Mode | Requires | Best for |
|------|----------|---------|
| **Data API** (`fm-dataapi` skill: `fm.py` / `fm_client.py`) | FM Server reachable (no app needed) | Headless/automated: agents, scripted workflows, layout-scoped reads/writes |
| **OData** | FM Server with OData enabled | **Schema mutations** (create tables, add fields) — the only live path that exposes these. Also live table/field listing and bulk/typed table access |
| **Schema pipeline** (`${CLAUDE_PLUGIN_ROOT}/tools/ddr/ddr.py`) | DDR or FM 2026 Save-as-XML export | Deep static analysis: calcs, scripts, relationship graph, offline reference, agent knowledge base |

## How to pick

| You need to… | Reach for |
|---|---|
| List the live tables and fields on a hosted file | **OData** (`fm-odata`: `tables`, `schema <table>`) |
| Read/write records with typed/scoped layout access | **Data API** |
| Create a table, add a field, change schema programmatically | **OData** (Data API can't) |
| Read the whole graph offline — calcs, scripts, value lists at depth | **Schema pipeline** (`ddr.py`) |
| Write scripts/layouts/fields as XML | **fm-xml skill** (generation) → fmlint (check) → patch via fm-patch or clipboard paste |

## Key constraints

- **The Data API is layout-based.** You query a layout, not a table; only fields on the layout come back. Always use dedicated API layouts with a consistent prefix (`AI_*`, `zAPI_*` — one convention per project). The layout is the security boundary.
- **OData creates tables/fields but not layouts.** After an OData schema mutation, someone must create the API layout in FileMaker before the Data API can see the new table. The fm-xml skill's layout references soften this: generate the layout as clipboard XML for a human paste.
- **Date format on Data API writes is `MM/DD/YYYY`.** ISO fails silently.
- Credentials come from `.env`: `FM_HOST`, `FM_DATABASE`, `FM_USERNAME`, `FM_PASSWORD`. Read-only service accounts scoped to API layouts by default; write operations need an explicit flag plus human confirmation.

## A normal multi-mode task

Spot a missing field in the schema pipeline's knowledge base → add it via OData → re-read it with OData `schema <table>` to confirm → create the API layout in FM (human step, or clipboard XML) → query via Data API to verify the round-trip. Three modes, one task, correct answer.
