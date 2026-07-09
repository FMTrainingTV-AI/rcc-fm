# Design — fm-odata + fm-dataapi tool-skills, fm-connections as router

## Why

A live test exposed a real gap: asked to "connect to this hosted file over OData," Claude (1) reached for the fixed-connection `fm_odata_*` MCP tools and got auth failures, then (2) hand-built an OData client and hit error `8310` by using FileMaker type names instead of SQL DDL. It eventually worked and produced good scripts + a tech-support note — but it should never have had to reinvent.

Root cause: the connection skill is **knowledge, not tools**. `fm-connections` tells Claude *how* to connect but ships no turnkey, credentials-in, ready-to-run client for an arbitrary hosted file — and its doctrine leads with the MCP.

**Fix:** ship pre-built, tested, zero-dependency scripts for **both** direct methods so Claude *runs* a client instead of writing one. Keep the MCP available for pre-wired connections; add direct scripts for any file you have credentials for. Three connection paths: MCP · direct OData · direct Data API.

## Structure — two tool-skills + a router (approved)

fm-dc goes 10 → 12 skills.

### 1. `fm-odata` (NEW tool-skill) — the OData side-door
- **Scripts** (adapted from the training code at `…/Part2-oData/scripts/`, already tested, stdlib-only):
  - `scripts/odata_client.py` — reusable `ODataClient` (urllib/base64/json; no pip). Connect, list_tables, table_fields, query, `create_table` **with SQL-DDL type validation**, add_fields, create_record, get_records, delete_table.
  - `scripts/fm_odata.py` — CLI: `connect · tables · schema · query · create-table · add-record · get · drop-table`.
- **Credentials — turnkey, no `.env`:** inline flags `--server <host> --file <db> --account <user> --password <pass>`, OR `--config <path>` to a key-value file (the `hostedFile.md` pattern) / JSON. Inline flags override the file. Generalize the existing `load_config()` (currently hard-wired to a sibling `hostedFile.md`).
- **Lessons baked into SKILL.md (front and center):**
  - **Go DIRECT, never the MCP** for an arbitrary hosted file — the `fm_odata_*` MCP tools carry only fixed pre-wired connection IDs and cannot take your credentials.
  - **create-table uses SQL DDL types** (`VARCHAR(255)`, `DATE`, `NUMERIC`, `INT`, `TIMESTAMP`, `TIME`, `DECIMAL`, `BLOB`), not FileMaker types (`string`/`date`). The client validates; error `8310` = unrecognized type. Include the mapping table.
  - **OData adds tables/fields but not layouts** — the Data API can't see the new table until a layout exists in FileMaker.
- **Trigger:** "connect to a hosted FileMaker file over OData with these credentials," "create a table/field over OData," "change/add schema on a hosted file."
- **references/odata-lessons.md** — fold in the tech-support note so the *why* travels.

### 2. `fm-dataapi` (NEW tool-skill) — the Data API record door
- **Scripts:** move `fm_client.py` + `fm.py` out of `fm-connections/scripts/` into `fm-dataapi/scripts/`. Both are already stdlib-only. Generalize credential input to match fm-odata: inline flags + `--config` file, while KEEPING the existing `.env` / `--profile` support (backward-compat for configured project DBs).
  - CLI: `test · tables · schema · query · get · create · update · delete · find · count`.
- **Lessons baked in:** Data API needs a **layout** (can't see OData-only tables until one is placed); date writes are `MM/DD/YYYY` (ISO fails silently); IDs as strings (57-digit UUIDs); never send auto-managed fields (`CreationAccount`/`ModifyAccount`/timestamps); hybrid ID systems (`recordID` vs `ID`).
- **Trigger:** "query/create/update/delete records in a hosted file with these credentials," "read records via the Data API," "find records where …".

### 3. `fm-connections` (RESHAPED → pure router/doctrine)
- Strip the CLI how-to (that's now fm-dataapi). Keep and lead with `references/four-mode-doctrine.md`. SKILL.md becomes the **which-method-when brain**:
  - MCP → pre-wired connections someone already configured.
  - direct **OData** (`fm-odata`) → schema mutations (create tables/fields), bulk.
  - direct **Data API** (`fm-dataapi`) → record CRUD, needs a layout.
  - schema pipeline (`fm-saxml`) → offline deep analysis.
  - **The rule that fixes the bug:** *an arbitrary hosted file you were handed credentials for → go DIRECT (fm-odata / fm-dataapi), never the fixed-connection MCP.*
  - Layout-as-security-boundary doctrine stays.
- Keeps `references/filemaker_integration_guide.md`, `references/filemaker_api_reference.md`.
- **Trigger:** "which way should I connect," "how do the FileMaker APIs relate," mode-selection questions — NOT the turnkey connect itself.

## Credentials — shared design (both CLIs)

Resolution order (first hit wins), so "give it the file/server/account/password" always works:
1. Inline flags `--server --file --account --password`.
2. `--config <path>` — a key-value file (`server`/`file`/`account`/`pass`, the `hostedFile.md` shape) or `.json`.
3. (fm-dataapi only) `.env` / `--profile` as today.

No `.env` required, no `pip install` — both clients are urllib-only.

## Cross-references to update (grepped 2026-07-09)

Moving `fm.py`/`fm_client.py` → `fm-dataapi`:
- `commands/fm-scaffold.md:29` — client-kit copies `fm_client.py` from `fm-connections/scripts/` → change to `fm-dataapi/scripts/fm_client.py`.
- `agents/fm-xml-validator.md:40` — Data API probe path `fm-connections/scripts/fm.py` → `fm-dataapi/scripts/fm.py`.
- `skills/fm-connections/references/four-mode-doctrine.md:8` — `fm.py`/`fm_client.py` reference → note they live in `fm-dataapi`.
- `skills/fm-proofkit/references/proofkit.md:58` — references the *client-kit's own* `plugin/skills/client-filemaker/scripts/fm_client.py` (a different copy) → leave.
- `SCOPE.md`, `docs/superpowers/plans/2026-07-06-fm-dc-build.md` — design history → leave as-is.

## Naming, deps, versioning

- Both `fm-` prefixed (native FileMaker connection methods; `baseelements`/`mbs` stay unprefixed as third-party plugins).
- Zero pip dependencies (urllib-only) — update fm-dataapi's SKILL.md to drop the stale "pip install requests".
- Bump `fm-dc` → **v0.5.0** (adds two skills, re-scopes one).

## Verification (the ship gate)

1. **`pytest tests -q` stays green** (136) — no tool code under `tools/` changes.
2. **Smoke-test both CLIs** offline: `--help` on each subcommand parses; `create_table` type validation rejects `string` and accepts `VARCHAR(255)` (unit-level, no live server).
3. **Blind routing test** (as in the v0.4.0 refactor): confirm fm-odata / fm-dataapi / fm-connections triggers don't collide, and that "connect to this hosted file over OData with these creds" routes to `fm-odata`, "query records in this file" → `fm-dataapi`, "which way should I connect" → `fm-connections`. Fix trigger wording before shipping if any case misroutes.

## Tasks

- [ ] **T1** — Create `skills/fm-odata/`; copy + generalize `odata_client.py`/`fm_odata.py` (inline creds + `--config`); write SKILL.md (lessons + trigger); `references/odata-lessons.md` from the tech-support note.
- [ ] **T2** — Create `skills/fm-dataapi/`; `git mv` `fm.py`/`fm_client.py` from fm-connections; add inline-cred + `--config` (keep `.env`); write SKILL.md (moved CLI how-to + lessons + trigger).
- [ ] **T3** — Reshape `skills/fm-connections/SKILL.md` to pure doctrine/router; keep the three reference docs.
- [ ] **T4** — Update cross-refs (fm-scaffold, fm-xml-validator, four-mode-doctrine).
- [ ] **T5** — Smoke-test both CLIs; `pytest tests -q`; blind routing test; fix triggers if needed.
- [ ] **T6** — Update READMEs (fm-dc "10→12 skills"; top-level marketplace row); bump v0.5.0; commit + push; refresh cache.

## Out of scope

- No live-server integration test (no shared test file in the plugin; the training file is throwaway).
- No new `tools/` code — clients live in the skills as bundled scripts, consistent with fm-connections today.
- Not touching the fm-patch pipeline's OData usage (separate concern; it exports/patches, doesn't connect-by-creds).
