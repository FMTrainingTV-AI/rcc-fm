---
name: fm-dataapi
description: Read and write FileMaker RECORDS over the Data API (+ OData queries) on a hosted file, connecting DIRECTLY with supplied credentials. Use when the user hands you a server + file + account + password (or a configured project .env) and wants to query, create, update, delete, find, or count records, or test a connection. Ships a ready-to-run zero-dependency client — RUN IT, do not write your own. NEVER use the fixed-connection MCP for an arbitrary file. For schema changes (create tables/fields) use fm-odata; for which-method-when see fm-connections.
argument-hint: "[test|tables|schema|query|get|create|update|delete|find|count] [--server --file --account --password | --config | --profile]"
allowed-tools: Bash, Read, Write
---

# FileMaker Data API — direct record access

The Data API is the headless door for **record** work — query, create, update, delete — on a hosted file. This skill ships a **pre-built, tested, zero-dependency client** so you connect and work immediately instead of writing one.

## Run the script — don't reinvent it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-dataapi/scripts/fm.py <command> \
    --server <host> --file <DB.fmp12> --account <user> --password <pass>
```

Credentials, in precedence order: inline flags (`--server --file --account --password`) · `--config <file>` (a `hostedFile.md`-style or `.json` file) · the project `.env` / `--profile` (`FM_HOST`, `FM_DATABASE`, `FM_USERNAME`, `FM_PASSWORD`). No `pip install` — `urllib`-only.

| Command | Does |
|---|---|
| `test` | Confirm auth. **Start here.** |
| `tables` · `schema <table>` | Discovery. |
| `query <table> [--filter .. --orderby .. --limit N --skip N]` | Read records (OData query, fast). |
| `get <table> <recordID>` | One record by simple recordID. |
| `create <table> --data '{...}'` | Create (Data API — safe with large IDs). |
| `update <table> <recordID> --data '{...}'` | Update. |
| `delete <table> <recordID>` | Delete. |
| `find <table> <field> <value> [--op contains]` | Convenience find. |
| `count <table> [--filter ..]` | Count. |

For finer control, import the client: `from fm_client import FileMakerClient` (portable, zero-dep: login/query/CRUD/logout with session hygiene).

## Rules that bite

1. **The Data API needs a LAYOUT.** It reads/writes through layouts, not base tables. A table created over OData (`fm-odata`) is **invisible here until someone places it on a layout** in FileMaker Pro. `404`/"not found" on a table you know exists usually means "no API layout yet."
2. **Dates are `MM/DD/YYYY`** on writes — ISO (`2026-07-15`) fails silently.
3. **IDs as strings.** FileMaker's `ID` is a 57-digit UUID integer — always pass foreign keys as strings (the CLI handles it; hand-built JSON must too).
4. **Never send auto-managed fields** — `CreationAccount`, `ModifyAccount`, `CreationTimestamp`, `ModifyTimestamp`. FileMaker sets them; the CLI strips them with a warning.
5. **Two ID systems:** `recordID` (simple sequential — for get/update/delete) vs `ID` (57-digit UUID — for foreign keys). Don't cross them.

## Server quirks

- `$select` may be rejected — drop it and filter output yourself.
- `$count` may return 0 — query without `--limit` and count `meta.count`.
- Table/layout names are case-sensitive — run `tables` first if unsure.

## Error handling

- **401** — bad credentials; do NOT retry, re-check them.
- **404** — table/layout name wrong, or (common) the table exists over OData but has no API layout yet.
- **"syntax error in URL"** — usually a `$select`/`$count` issue; drop that parameter.
- **Timeout** — retry once, then add `--limit`.
