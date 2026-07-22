# 02 — Install the export capability in the hosted file (one-time)

## What

Doc 01 gave the agent two doors into the hosted file. This step gives it
**eyes**: a way to read the file's complete structure — tables, fields,
scripts, relationships — without downloading the file or closing it.

FileMaker can save a file's structure as XML (`Save a Copy as XML`), and
since the file is hosted, the fastest place to run that is **on the server
itself**. So the hosted file gets two paste-in objects, shipped in the
plugin:

| Asset | What it is | Pastes into |
|---|---|---|
| `${CLAUDE_PLUGIN_ROOT}/templates/saxml-table.xml` | `SAXML` — a dedicated drop table: run log + XML transport | Manage Database → **Tables** tab |
| `${CLAUDE_PLUGIN_ROOT}/templates/agent-saxml-export-v5.xml` | `Agent_SaXML_Export` — the export script | Script Workspace → **script list** |

The agent triggers the script over OData; the script exports the requested
catalogs server-side, loads the result into the SAXML row it opened for the
run, and returns a JSON summary. Install is a one-time paste of the pair;
after that the agent runs the whole loop alone.

## Setup is a paste-in pair, not an interview

**Every file gets the same dedicated `SAXML` table**, so nothing is chosen
and nothing is substituted. The table XML carries full field definitions
that OData DDL can't express (auto-enter UUID key, audit stamps, un-indexed
multi-MB text fields), and the script pastes unmodified because every name
it references travels with it. Pointing at a new file means pasting the
same pair again — that's the whole setup.

What the table gives each run, beyond transport: a logged row — `RunID`,
`Status` (`running | done | error`), `Stage` (furthest stage reached),
`ErrorCode` / `ErrorMessage`, and the exact `RequestJSON` for replay — so a
failed export still leaves something to read over OData.

**Why a *text* field (`ResponseText`) for the XML payload?** Two hard-won
facts: OData never returns container contents in JSON (always `null` —
binary is a separate `$value` endpoint), and that `$value` endpoint can 502
outright on some servers. SaXML output is plain UTF-8 text, so a text field
carries it perfectly over the ordinary JSON API. The `XMLDrop` container is
the bonus copy (`.../SAXML('<pk>')/XMLDrop/$value` where it works); the
text field is the transport.

## The script

What it does, in order:

1. Reads a JSON parameter — `{"runId": "...", "options": {...}}`, both
   optional. No `runId` → `Get(UUID)`; no `options` → the full default
   catalog set named inside the script. Per-run catalog selection (just
   `ScriptCatalog` after script work, `FieldCatalog` after schema work) is
   what keeps exports small and fast.
2. **Creates the SAXML row first** and commits it (`Status=running`) — a
   failed export still leaves a record to read.
3. Runs `Save a Copy as XML` to the server's temp folder, options driven by
   that JSON. On `Get(LastError)` ≠ 0 it marks the row `error` and exits
   with an error JSON — the script never claims success it can't back up.
4. Reads the exported file back with `Insert from URL` into a **variable**,
   then Set Fields it into `XMLDrop` (container) and `ResponseText` (text),
   plus `CharCount` so the agent can size the read before fetching.
   (Inserting straight into a field fails with error 102 whenever that
   field isn't on the current layout — the variable hop ships in the asset.)
5. Exits with
   `{ok, stage, error, runId, primaryKey, recordId, chars, path}`.
   `primaryKey` is the pickup ticket: the SAXML table's validated-unique
   `PrimaryKey` is its OData **entity key**, so the driver GETs
   `SAXML('<primaryKey>')?$select=ResponseText`.

## Install procedure (the one manual step in the whole workflow)

Order matters: **table → layout → script.** The script paste resolves the
`SAXML` layout and field references by name — paste the script first and
those references land broken, silently.

1. **Paste the table.** The agent prints the table XML **on screen** —
   visible and versioned, never invisibly on a clipboard. Copy it; in
   FileMaker Pro, on the hosted file: File → Manage → Database → **Tables**
   tab → paste. (A clipboard converter — the MBS plugin's clipboard
   functions or FmClipTools — turns copied XML text into FileMaker's native
   clipboard format; plain ⌘V without one pastes nothing. Same for the
   script below.) A table named `SAXML` with 15 fields appears; click OK to
   close. FileMaker adds the `SAXML` table occurrence to the graph on the
   way out.
2. **Confirm the layout.** A layout named `SAXML` showing that occurrence
   must exist. FileMaker normally auto-creates it when the table is added;
   if this file is set not to, make one — New Layout, name `SAXML`, blank
   is fine (Set Field doesn't need the fields placed on it).
3. **Paste the script.** Copy the script XML → Script Workspace → paste
   into the **script list** (the sidebar, not an open script's step area —
   this asset is a whole `<Script>` object, which is what carries the name
   and the full-access flag; steps-area paste expects steps-only XML and
   fails silently on it). The script arrives named `Agent_SaXML_Export`.
4. **Check "Run script with full access privileges."** The asset ships with
   it on — verify it survived the paste. `Save a Copy as XML` needs
   full-access privileges, and the OData account shouldn't hold them itself.
5. **Save the script** (⌘S). An unsaved script runs its *old* version — a
   classic source of confusing no-ops.
6. **Grant the OData account access:** its privilege set needs records
   access to `SAXML` (create + edit) and the script at least
   "executable only". (The `fmodata` extended privilege was doc 01.)
7. **Record the choices** in [`../hostedFile.md`](../hostedFile.md) — for
   the standard install that's simply `dropTable - SAXML`,
   `dropLayout - SAXML`, `textField - ResponseText`. The driver reads these
   from config either way, so a renamed install just records its own values.

## Custom installs (the fallback interview)

When the standard `SAXML` table can't land as-is — naming conventions,
an existing log table that must be reused, a privilege regime that forbids
new tables — fall back to the v4 interview flow: choose/create a drop
table over OData (field adds via `PATCH /FileMaker_Tables/<table>` —
**PATCH, not POST; POST errors**), have the operator make the layout, and
generate the script from the placeholder template
`${CLAUDE_PLUGIN_ROOT}/templates/agent-saxml-export.template.xml`,
substituting THIS file's names for every `{{PLACEHOLDER}}`. Record the
chosen names in `../hostedFile.md`; the driver reads config either way.
(The v4 script is steps-only XML: create + name the script first, paste
into the open script's **step area**, then set full access manually.)

## Verify the install

- Copy the script back out of FileMaker and compare against the asset:
  every variable name survived, every field/layout reference resolved to a
  real name — nothing displays as `<Field Missing>` or `<unknown>`.
  (FileMaker's paste handler drops parts of malformed XML *silently* — this
  check matters.)
- A trigger fired immediately after install may 404 — FileMaker Server
  takes up to ~30 seconds to notice a newly saved script. Retry before
  diagnosing.
- Then run doc 03's export: its verification ladder (bytes > 0, XML parses,
  self-reference, hash) is the real proof.

## Result — capture when run

- Install: <standard pair / custom interview — and why, if custom>
- Paste-back comparison: <clean / what needed fixing>
- First trigger: <result JSON, or the 404-then-retry note>
