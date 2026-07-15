---
name: fm-odata
description: Connect DIRECTLY to a hosted FileMaker file over OData with supplied credentials, and change its schema (create tables/fields) — the live "side door." Use when the user hands you a server + file + account + password and wants to connect over OData, list/read tables, or create/alter a table or field on a hosted file. Ships a ready-to-run client — RUN IT, do not write your own. NEVER use the fixed-connection fm_odata_* MCP tools for an arbitrary file; they only carry pre-wired connections. For record CRUD use fm-dataapi; for which-method-when see fm-connections.
argument-hint: "[connect|tables|schema|create-table|add-record|get|drop-table] [--server --file --account --password | --config]"
allowed-tools: Bash, Read, Write
---

# FileMaker OData — direct connection & schema side-door

OData is the one live connection that can **change schema** (add tables and fields) on a running, hosted file — nothing to download or open. This skill ships a **pre-built, tested, zero-dependency client** so you connect and mutate immediately instead of writing one from scratch.

## Run the script — don't reinvent it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-odata/scripts/fm_odata.py <command> \
    --server <host> --file <DB.fmp12> --account <user> --password <pass>
```

Credentials three ways (first wins): inline flags · `--config <file>` (a `hostedFile.md`-style `server/file/account/pass` file, or `.json`) · a sibling `hostedFile.md`. No `.env`, no `pip install` — the client is `urllib`-only.

| Command | Does |
|---|---|
| `connect` | Confirm auth, count entity sets. **Start here.** |
| `tables [--all]` | Base tables (`--all` includes relationship occurrences). |
| `schema <table>` | Fields + types for one table. |
| `create-table <name> [--field Name:VARCHAR(255) ...]` | Create a table. Omit `--field` for a default task table. |
| `add-record <table> --data '{...}'` | Insert a record (or `--name/--status/--due/--notes`). |
| `get <table> [--top N]` | Read records back. |
| `drop-table <name>` | Delete a table (cleanup). |

For anything the CLI doesn't cover, import the client: `from odata_client import ODataClient, resolve_config`.

## Three hard rules (each one cost a real debugging session)

### 1. Go DIRECT — never the MCP for an arbitrary hosted file
The pre-installed `fm_odata_*` MCP tools carry only **fixed, pre-wired connection IDs** (e.g. `CONN_A`, `CONN_B`). They take **no** server/account/password, so they can't touch a file you were just handed credentials for — you'll get auth failures against the wrong database. For any arbitrary hosted file, **use the script above.** (The MCP is fine for its own pre-configured connections — that's `fm-connections`' call.)

### 2. create-table uses SQL DDL types, NOT FileMaker types
FileMaker's OData create-table API wants **SQL DDL** type names. The client validates and rejects FileMaker-style names before sending, so error **`8310` ("internal data formatting error") can't recur** — but know the mapping:

| FileMaker type | SQL DDL type to send |
|---|---|
| string / text | `VARCHAR(255)` (or larger) |
| number | `NUMERIC` / `INT` / `DECIMAL` |
| date | `DATE` |
| time | `TIME` |
| timestamp | `TIMESTAMP` |
| container | `BLOB` |

`8310` on a schema request almost always means "unrecognized field type."

### 3. OData adds tables/fields — but NOT layouts
After an OData schema change, the new table exists but **nothing sees it through the Data API** (`fm-dataapi`) until someone opens the file in FileMaker Pro and places it on a layout. OData is the schema side door; the Data API needs a front door (a layout). Tell the user this every time you create a table.

## Workflow

1. `connect` to confirm you're live (auth + table count).
2. `tables` / `schema <t>` to see what's there.
3. `create-table` / `add-record` to change it — explain each schema change before you make it.
4. Remind the user: new tables need a **layout** before the Data API can read them.

Full backstory (the two blockers, diagnosed): `references/odata-lessons.md`.
