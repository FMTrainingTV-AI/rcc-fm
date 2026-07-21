# 02 — Install the export script in the hosted file (one-time)

## What

Doc 01 gave the agent two doors into the hosted file. This step gives it
**eyes**: a way to read the file's complete structure — tables, fields,
scripts, relationships — without downloading the file or closing it.

FileMaker can save a file's structure as XML (`Save a Copy as XML`), and
since the file is hosted, the fastest place to run that is **on the server
itself**. So one script, `Agent_SaXML_Export`, gets installed into the
hosted file. The agent triggers it over OData; the script exports the
requested catalogs server-side and parks the XML where the agent can
download it. Install is a one-time paste; after that the agent runs the
whole loop alone.

## Setup is an interview, not a recipe

Every file is different, so this setup runs as a short **agent-led
interview** — the agent asks before acting, and nothing gets hardcoded:

1. **Does the file already have the export capability?** Probe the trigger;
   if it answers, setup is already done.
2. **Choose a drop table** — where the script parks each export result. The
   agent lists the file's tables over OData and offers: *reuse* an existing
   log-ish table that's already on a layout, or *create* a new one (e.g.
   `AgentLog`).
3. **Add the needed fields** (agent, over OData): a text field for the XML
   payload, a label field, a params field, optionally a container. Field
   adds go through `PATCH /FileMaker_Tables/<table>` — **PATCH, not POST;
   POST errors.**
4. **Layout** (human, only if a new table was created): no API can make
   layouts, so the operator makes one layout showing the new table, once.
5. **Generate the script** from the placeholder template — the plugin's
   `${CLAUDE_PLUGIN_ROOT}/templates/agent-saxml-export.template.xml`
   — substituting THIS file's names for every `{{PLACEHOLDER}}`.
6. **Record the choices** in [`../hostedFile.md`](../hostedFile.md)
   (`dropTable` / `dropLayout` / `textField`) so every later step reads them
   from config.

**Why a *text* field for the XML payload?** Two hard-won facts: OData never
returns container contents in JSON (always `null` — binary is a separate
`$value` endpoint), and that `$value` endpoint can 502 outright on some
servers. SaXML output is plain UTF-8 text, so a text field carries it
perfectly over the ordinary JSON API. Keep a container as a bonus copy if
you like; the text field is the transport.

## The script

What it does, in order:

1. Reads a JSON parameter:
   `{"runId": "...", "options": {"catalogs_included": [...], ...}}` — the
   agent picks **which catalogs** to export per run (just `ScriptCatalog`
   after script work, `FieldCatalog` after schema work). Catalog selection
   is what keeps exports small and fast.
2. Runs `Save a Copy as XML` to the server's temp folder, options driven by
   that JSON.
3. Checks `Get(LastError)` and bails out with an error JSON if the export
   failed — the script never claims success it can't back up.
4. Loads the XML file into a **variable** with `Insert from URL` (`file://`
   URL), then `Set Field`s it into the payload text field. (Inserting
   straight into a field fails with error 102 — "field is missing" —
   whenever that field isn't on the current layout. The variable hop is the
   fix, and it ships in the template.)
5. Exits with a result JSON: error code, the new record's ID (the agent's
   pickup ticket), the run ID, and the path.

## Install procedure (the one manual step in the whole workflow)

1. The agent prints the script XML **on screen** — visible and versioned
   (the first step is a comment naming the version), never invisibly on a
   clipboard.
2. In FileMaker Pro, on the hosted file: **Script Workspace → New Script**,
   name it exactly `Agent_SaXML_Export`.
3. Click into the empty step area and **paste**. FileMaker resolves every
   table, field, and layout reference by name and stamps in real internal
   IDs. (Script Workspace only accepts FileMaker's native clipboard format —
   a converter such as the MBS plugin's clipboard functions or FmClipTools
   turns the copied XML text into it. Plain ⌘V without one pastes nothing.)
4. Check **"Run script with full access privileges"** — `Save a Copy as XML`
   requires full access, and the API account shouldn't have it.
5. **Save the script** (⌘S). An unsaved script runs its *old* version — a
   classic source of confusing no-ops.

## Verify the install

- Copy the script back out of FileMaker and compare against what was
  pasted: every variable name survived, every name reference resolved to a
  real ID. (FileMaker's paste handler can silently drop parts of malformed
  XML — this check matters.)
- A trigger fired immediately after install may 404 — FileMaker Server
  takes up to ~30 seconds to notice a newly saved script. Retry before
  diagnosing.

## Result — capture when run

Record THIS file's interview outcomes and any surprises (the choices also
land in `../hostedFile.md`):

- Drop table: <reused / created — which, and why>
- Fields added: <names, and the OData calls that added them>
- Layout: <already existed / operator-created>
- Install verification: <paste-back comparison, first-trigger result>
