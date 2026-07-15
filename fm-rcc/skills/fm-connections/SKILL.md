---
name: fm-connections
description: The FileMaker connection ROUTER — decide HOW to reach a FileMaker file (ProofKit MCP vs direct OData vs direct Data API vs offline schema pipeline) and the layout-as-security-boundary rules. Use when the choice of connection method is the question ("which way should I connect", "why did the MCP fail", "MCP vs Data API vs OData", how the FileMaker server APIs relate). For the actual work: schema changes → fm-odata; record CRUD → fm-dataapi; offline schema analysis → fm-saxml; ProofKit/web viewers → fm-proofkit.
allowed-tools: Bash, Read, Grep, Glob
---

# FileMaker connections — which door, when

FileMaker exposes several ways in. This skill picks the right one; the doing lives in the method skills. **Read `references/four-mode-doctrine.md` first when a task involves choosing a path.**

## The rule that prevents the usual time-waster

**An arbitrary hosted file you were handed credentials for → connect DIRECT, never the fixed-connection MCP.** The `fm_odata_*` / MCP connection tools carry only *pre-wired* connection IDs with their own stored credentials — they cannot take a new server/account/password. Reaching for them on an arbitrary file wastes a debugging cycle on auth failures against the wrong database. Use the direct tool-skills below.

## The four modes

| Mode | Reach for it when | Skill / tool |
|---|---|---|
| **ProofKit MCP** | The connection is already **pre-wired** in the MCP (someone configured it); live schema/SQL/CRUD/ERD on a file that's open in the ProofKit app | `fm-proofkit` |
| **Direct OData** | You have credentials for a hosted file and need **schema changes** (create tables/fields) or bulk access | **`fm-odata`** |
| **Direct Data API** | You have credentials and need **record** CRUD (query/create/update/delete) | **`fm-dataapi`** |
| **Schema pipeline** | **Offline** deep analysis — calcs, scripts, relationship graph, agent knowledge base | `fm-saxml` (`tools/ddr/ddr.py`) |

They coexist — a real session weaves between them: read pre-wired schema via MCP, mutate via direct OData, verify via a refreshed MCP call, query records via the direct Data API. That's normal.

## How to pick

| Task | Mode |
|---|---|
| "Connect to THIS hosted file (server/file/account/password)" | Direct — **`fm-odata`** (schema) or **`fm-dataapi`** (records). Never the MCP. |
| Query / create / update / delete **records** | Direct Data API → **`fm-dataapi`** |
| Create a table, add a field, change schema programmatically | Direct OData → **`fm-odata`** (Data API can't; MCP doesn't expose it) |
| Live schema/SQL on an already-configured, app-open file | ProofKit MCP → `fm-proofkit` |
| Read the whole graph offline — calcs, scripts, value lists | Schema pipeline → `fm-saxml` |
| Write scripts/layouts/fields as XML | `fm-xml` (generate) → fmlint (check) → `fm-patch` or clipboard paste |

## Layout is the security boundary

- **OData creates tables/fields but NOT layouts.** After an OData schema mutation, someone must create the API layout in FileMaker before the **Data API** (`fm-dataapi`) can see the new table. The `fm-xml` skill's layout references soften this: generate the layout as clipboard XML for a human paste.
- The Data API reads/writes **through layouts**, not base tables — read-only service accounts scoped to API layouts by default; write operations need explicit intent + human confirmation.

## Typical multi-mode flow

Spot a missing field via MCP → add it via **`fm-odata`** → refresh MCP to confirm → create the API layout in FileMaker (human step, or `fm-xml` clipboard XML) → query via **`fm-dataapi`** to verify the round-trip. Four modes, one task.

## References

- `references/four-mode-doctrine.md` — the decision doctrine in depth (the source of the tables above).
- `references/filemaker_integration_guide.md` — all three FM server APIs (Data API, OttoFMS, OData): auth, protocol, configuration.
- `references/filemaker_api_reference.md` — Data API endpoint reference.
