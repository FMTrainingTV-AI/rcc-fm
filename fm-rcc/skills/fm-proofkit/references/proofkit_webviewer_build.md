# Guide: ProofKit Web Viewer Build

> End-to-end playbook for building a FileMaker web viewer app with ProofKit. Real-world workflow, written from a complete build cycle. Pair with `docs/reference/proofkit.md` (orientation) and `webviewer/README.md` (workspace conventions).

## When to use

Anytime you're putting a custom React UI inside a FileMaker layout. If the goal is a UI outside FM (public users, mobile, no FM client), see "External Web Frontend" in the root CLAUDE.md instead — different deploy target, different auth.

## TL;DR — 11 steps

```
1.  User opens FileMaker file. Runs "Connect to MCP" script.
2.  connectedFiles → returns the file name. Empty array = step 1 wasn't done.
3.  layout_metadata → confirm or create dedicated API layouts (list view + detail view).
4.  If drag-reorder is in scope: add SortOrder Number field, indexed, on both layouts.
5.  mkdir webviewer/<app-name> && setup_proofkit_project { targetPath: "<absolute>" }
6.  npx @proofkit/cli@beta init . --app-type webviewer --non-interactive
7.  npx @tanstack/intent@latest install
8.  Edit proofkit-typegen.config.jsonc — list the layouts you want clients for.
9.  npm run typegen     # generates clients from the live FM file via the MCP bridge
10. npm run dev         # http://localhost:5175, already wired to FM
11. npm run build && deploy_html → app is live inside FileMaker
```

Each step has known pitfalls; see "Things that bite" below.

## Pre-flight

```
connectedFiles
```

Returns `["YourFile"]` when the bridge is alive. If empty, ask the user to run **Connect to MCP** in their FileMaker file (a script the ProofKit add-on installs). The script opens a hidden web viewer window that bridges HTTP requests to FM.

If `connectedFiles` lists the file but every other call hangs, the bridge is wedged. Ask the user to re-run Connect to MCP. Don't keep retrying, you're queueing up timeouts.

## Step 1 — Discover or create the API layouts

The Data API operates through layouts, so the layout *is* your schema. Only fields and portals on the layout are visible at runtime.

You need at minimum:

- A **list layout** with the lightweight subset of fields for a table view (title, status, date, sort).
- A **detail layout** with the full record plus any portals (related rows the app needs).

Both should sit on the same base table. Use a consistent prefix (`AI_*`, `api_*`, `zAPI_*`) and stick with one per project.

```
layout_metadata { connectedFileName, layouts: "" }      # list everything
layout_metadata { connectedFileName, layouts: "FooList" }  # confirm fields
```

Pass a comma-separated string in `layouts`. Empty string lists all. If any one in a multi-layout call is missing, the call returns "Layout is missing" with no useful detail. Query individually when in doubt.

**Layout names with spaces work.** The Data API URL-encodes them. They're not forbidden, just easier to typo and harder to read in logs. New layouts: prefer no-space CamelCase (`FooList`, not `Foo List`).

## Step 2 — Add SortOrder if drag-reorder is in scope

Drag-and-drop reordering needs a numeric field to persist position. The schema doesn't get one for free.

Setup:
- Type **Number**, indexed.
- Add to both the list and detail API layouts.
- Auto-enter (Calculated value): `Max ( SelfRelationship::SortOrder ) + 10` (with a self-relationship by table primary key) or as a fallback `Get(RecordID) * 10`.

Why gaps of 10? Drag-reorder writes new positions by interpolation. Gaps let you insert between rows without renumbering everything every drop.

Seed initial values once with parallel `data_api_orchestrator` `update` calls, ordered by whatever default makes sense (due date, creation order).

## Step 3 — Scaffold the project

```bash
mkdir -p webviewer/<app-name>
```

```
setup_proofkit_project { targetPath: "<absolute path to that dir>" }
```

The MCP tool returns instructions but doesn't run them. Copy them into the shell:

```bash
cd webviewer/<app-name>
npx @proofkit/cli@beta init . --app-type webviewer --non-interactive
npx @tanstack/intent@latest install
```

The first creates the project: React 19 + Vite + Tailwind v4 + shadcn + TanStack Router (hash history) + React Query + the @proofkit/fmdapi and @proofkit/webviewer packages with typegen wired up.

The second populates AGENTS.md with skill loading guidance so future agent sessions can load `npx @tanstack/intent@latest load '@proofkit/fmdapi#typegen-fmdapi'` etc. for in-context docs.

## Step 4 — Configure typegen for FM MCP mode

The scaffold creates `proofkit-typegen.config.jsonc` already pointing at FM MCP mode. Fill in `connectedFileName` and the `layouts` list:

```jsonc
{
  "$schema": "https://proofkit.proof.sh/typegen-config-schema.json",
  "config": {
    "type": "fmdapi",
    "path": "./src/config/schemas/filemaker",
    "clearOldFiles": true,
    "clientSuffix": "Layout",
    "validator": "zod/v4",
    "webviewerScriptName": "ExecuteDataApi",
    "fmMcp": {
      "enabled": true,
      "connectedFileName": "<YourFile>"
    },
    "layouts": [
      { "layoutName": "FooList",    "schemaName": "FooList" },
      { "layoutName": "FooDetails", "schemaName": "FooDetails" }
    ]
  }
}
```

Then:

```bash
npm run typegen
```

Generated output:

```
src/config/schemas/filemaker/
  generated/        ← auto-generated, DO NOT EDIT
    FooList.ts
    FooDetails.ts
  client/           ← auto-generated, this is what you import
    FooList.ts
    FooDetails.ts
    index.ts
  FooList.ts        ← override file, safe to edit (Zod transformations)
  FooDetails.ts
```

Each `client/<name>.ts` re-exports a `client` renamed to `<schemaName>Layout`. Import like:

```ts
import { FooListLayout, FooDetailsLayout } from "./config/schemas/filemaker/client";
```

The clients use `WebViewerAdapter`, which routes Data API calls through the FM `ExecuteDataApi` script (installed by the ProofKit add-on). In dev mode, the same adapter goes through the local bridge, so dev and prod behave identically.

After any FM schema change (added a field, renamed a layout), re-run `npm run typegen` and the generated clients pick up the changes.

## Step 5 — Wire the app

Mandatory init line in `App.tsx` (or wherever you mount React):

```tsx
import { globalSettings } from "@proofkit/webviewer";
globalSettings.setWebViewerName("web");  // must match the FM web viewer object name
```

Without this line, callbacks have no idea which web viewer to call back into. The default ProofKit add-on names the web viewer object `"web"`. If you change it, change both.

### Read patterns (React Query)

```ts
// LIST
const tasks = useQuery({
  queryKey: ["foo", "list"],
  queryFn: async () => {
    const res = await FooListLayout.list({
      sort: [{ fieldName: "SortOrder", sortOrder: "ascend" }],
      limit: 1000,
    });
    return res.data; // [{ recordId, fieldData, modId }]
  },
});

// DETAIL with portals
const detail = useQuery({
  queryKey: ["foo", "detail", recordId],
  enabled: !!recordId,
  queryFn: async () => {
    const res = await FooDetailsLayout.get({ recordId });
    const r = res.data[0];
    return {
      ...r.fieldData,
      children: r.portalData["ChildPortal"] ?? [],
    };
  },
});
```

The portal *name* (left-hand label in the FM Inspector) is what comes back as the key in `portalData`, not the table occurrence name.

### Write patterns

```ts
// UPDATE
await FooDetailsLayout.update({
  recordId,
  fieldData: { Status: "Completed" },
});

// CREATE
await FooDetailsLayout.create({
  fieldData: { Title: "...", Status: "Pending" },
});
// NOTE: CreateResponse does NOT have a `data` property. Don't destructure it.

// DELETE
await FooDetailsLayout.delete({ recordId });
```

### Optimistic updates

The bridge isn't fast. Optimistic updates make mark-complete and similar one-click toggles feel native:

```ts
const toggle = useMutation({
  mutationFn: ({ recordId, done }: { recordId: string; done: boolean }) =>
    FooDetailsLayout.update({
      recordId,
      fieldData: {
        Status: done ? "Completed" : "In Progress",
        "Completion Date": done ? formatFmDate(new Date()) : "",
      },
    }),
  onMutate: async ({ recordId, done }) => {
    await qc.cancelQueries({ queryKey: ["foo", "list"] });
    const prev = qc.getQueryData(["foo", "list"]);
    qc.setQueryData(["foo", "list"], /* update locally */);
    return { prev };
  },
  onError: (_e, _v, ctx) => qc.setQueryData(["foo", "list"], ctx?.prev),
  onSettled: () => qc.invalidateQueries({ queryKey: ["foo", "list"] }),
});
```

### Drag-reorder

Reorder is a bulk update of `SortOrder`. Run sequentially, not in parallel — FM doesn't love concurrent writes from the same client.

```ts
const reorder = useMutation({
  mutationFn: async (updates: Array<{ recordId: string; sortOrder: number }>) => {
    for (const u of updates) {
      await FooDetailsLayout.update({
        recordId: u.recordId,
        fieldData: { SortOrder: u.sortOrder },
      });
    }
  },
  onSettled: () => qc.invalidateQueries({ queryKey: ["foo", "list"] }),
});
```

Recompute positions only inside the affected group, anchored to the first item's existing `SortOrder` plus increments of 10. This keeps writes minimal.

### Cross-group drag semantics

When dropping into a group with implied state (a "Done" group, an "On hold" group), update the relevant fields first, then reorder:

```ts
updateTask.mutate(
  { recordId, fieldData: { Status: "Completed", "Completion Date": today } },
  { onSuccess: () => sortUpdates.length && reorder.mutate(sortUpdates) }
);
```

### Date formatting

The Data API parses dates on writes as `MM/DD/YYYY`. ISO and other formats fail silently in unhelpful ways.

```ts
function formatFmDate(d: Date): string {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${mm}/${dd}/${d.getFullYear()}`;
}
```

On reads, dates come back as strings. Format varies (`MM/DD/YYYY` from Data API, ISO from `execute_filemaker_sql`). Parse client-side, don't trust a single format.

## Step 6 — Dev loop

```bash
npm run dev
```

Vite usually picks up `localhost:5173` or `5175`. The dev server's `index.html` includes a `<script src="http://127.0.0.1:1365/fm-mock.js?fileName=YourFile">` that routes Data API calls back through the local bridge. Real reads, real writes, in your browser. Every CRUD path you exercise in dev hits the actual FileMaker file.

To test inside Claude Code with the Claude Preview MCP, drop a `.claude/launch.json`:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "<app-name>",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["--prefix", "<absolute path to project>", "run", "dev"],
      "port": 5175
    }
  ]
}
```

The `--prefix` flag is critical. `preview_start` runs from the agent's CWD, which is usually not the project dir. Without `--prefix` it tries to read `package.json` in the wrong place and fails.

Then `preview_start { name }` returns a `serverId` for `preview_screenshot`, `preview_click`, `preview_fill`, `preview_eval`, etc. Verify writes hit FM with `execute_filemaker_sql`.

## Step 7 — Build and deploy

```bash
npm run build
```

Output: `dist/index.html`, single file with all CSS+JS inlined. Typical size 300–500 KB (gzipped 100–150 KB).

```
deploy_html {
  connectedFileName: "<YourFile>",
  appName: "MyApp",
  path: "<absolute path to dist/index.html>"
}
```

Same `appName` overwrites. The HTML lands in the `ProofKitApps` table; the FM file's launcher renders it inside a web viewer.

**Deploy will time out for builds over ~200 KB but the write usually still completes.** The MCP callback timeout fires before the FM script finishes inserting; FM continues on its own. Verify with:

```sql
SELECT AppName, LENGTH(HTML) FROM ProofKitApps
```

If the LENGTH matches your build's byte count (`ls -l dist/index.html`), the deploy worked. Don't redeploy on a timeout error — you'll just queue another large write.

In FileMaker, navigate to the launcher (e.g. `ProofKitApps` layout) and click your app to load it.

## Things that bite

In rough order of how often they come up.

### 1. Bridge wedges after a slow operation

Symptom: `connectedFiles` returns the file but everything else times out.
Cause: Leftover state from a previous large `deploy_html` or long script.
Fix: User re-runs **Connect to MCP** in FM. Don't retry the failed call — you're queueing more timeouts.

### 2. `deploy_html` times out but succeeds

Symptom: "Timed out waiting for FileMaker callback" on a large build.
Cause: Builds over ~200 KB take longer to write than the MCP timeout window allows.
Fix: Check `SELECT AppName, LENGTH(HTML) FROM ProofKitApps`. If the length matches your build, you're done.

### 3. Object params must be JSON objects, not strings

Several MCP tools type `request` or `requests` as object/array. Stringified JSON is rejected:

```
data_api_orchestrator { request: "{\"layouts\":\"X\"}" }   ← rejected
data_api_orchestrator { request: { "layouts": "X" } }      ← correct
```

In agent tool-call format: `<parameter name="request">{"layouts": "X"}</parameter>`, not the stringified version.

### 4. `get_filemaker_ddl_schema` wants `requests`, an array of objects

```
get_filemaker_ddl_schema {
  connectedFileName: "X",
  requests: [{ tableOccurrenceNames: ["Foo", "Bar"] }]
}
```

Easy to type as `tables: [...]` or `requests: "..."` and watch it reject.

### 5. `CreateResponse` doesn't have `.data`

```ts
const res = await FooDetailsLayout.create({ fieldData });
return res.data;   // ← TS2339, no such property
```

Just await and discard, or read the actual response shape from `@proofkit/fmdapi` types if you need the new recordId.

### 6. Date format on writes is `MM/DD/YYYY`

ISO dates and other formats fail silently. Always format dates client-side before sending. Reads come back as strings in varying formats — parse defensively.

### 7. `webviewerScriptName` defaults to `"ExecuteDataApi"`

The ProofKit add-on installs a script by that name. The generated client uses it. If you renamed it (don't), update `webviewerScriptName` in the typegen config and re-run typegen.

### 8. `setWebViewerName` must match the FM layout object name

The web viewer object in FM has an Object Name set in the Inspector. That string is what `globalSettings.setWebViewerName("web")` needs to match. Default add-on uses `"web"`. Change one, change both.

### 9. SortOrder on new records

If the field has no auto-enter calc, every new record gets `SortOrder = 0` and they all stack. Either:
- Add an auto-enter calc (`Max(self::SortOrder) + 10` via self-relationship), or
- Always pass `SortOrder` explicitly in create calls (compute `max + 10` from the in-memory list).

### 10. Empty/stale rows in `ProofKitApps`

Calling `deploy_html` with empty/different `appName` accumulates rows. Check periodically:

```sql
SELECT AppName, LENGTH(HTML) FROM ProofKitApps
```

Delete duplicates from FM directly.

### 11. Build size

A typical webviewer build with React + Tailwind + Google Fonts + shadcn comes out around 300–500 KB. Most of that is React + Tailwind + the @proofkit packages + react-router + react-query. Trim only if it actually matters: drop unused icon packs, inline fewer fonts, etc.

### 12. Sandbox vs shell network access

The MCP bridge and `npm run typegen` both need to reach `http://127.0.0.1:1365/health`. They use different network paths. If MCP tools work but `npm run typegen` hangs, curl the health endpoint from your shell to confirm — sandbox restrictions can block one without the other.

## Tooling shortcuts

### TanStack Intent skills as in-context docs

The scaffold installs intent-aware packages. Useful skills to load when stuck:

```bash
npx @tanstack/intent@latest list
npx @tanstack/intent@latest load '@proofkit/fmdapi#typegen-fmdapi'
npx @tanstack/intent@latest load '@proofkit/fmdapi#fmdapi-client'
npx @tanstack/intent@latest load '@proofkit/webviewer#webviewer-integration'
```

These return condensed reference docs covering: typegen config, env vars, OttoAdapter vs FetchAdapter vs WebViewerAdapter, fmFetch, callFMScript, callback wiring.

### Claude Preview MCP

Already covered above (`.claude/launch.json` with `--prefix`). Use it to click through CRUD inside Claude Code rather than asking the user to test by hand. Combine `preview_eval` with `execute_filemaker_sql` for end-to-end verification: simulate the click, then SQL-verify the write actually hit FM.

## File map of a built project

```
<app-name>/
├── .claude/
│   ├── launch.json              ← preview-tools config (you may need to add)
│   └── settings.local.json
├── proofkit-typegen.config.jsonc  ← layouts list lives here
├── proofkit.json                  ← project metadata
├── package.json                   ← scripts: dev, build, typegen, proofkit, upload
├── vite.config.ts                 ← has fmBridge() plugin
├── index.html                     ← injects /fm-mock.js in dev
├── src/
│   ├── main.tsx                   ← QueryClientProvider + RouterProvider
│   ├── router.tsx                 ← TanStack Router with hash history
│   ├── App.tsx                    ← your app entry (set webViewerName here)
│   ├── index.css                  ← Tailwind v4 + custom CSS
│   └── config/schemas/filemaker/  ← typegen output (do not edit /generated /client)
└── dist/index.html                ← single-file build, what you deploy
```

Hash history is required because the FM web viewer doesn't expose URL navigation meaningfully. Don't switch to browser history.

## Pre-flight checklist for a brand new app

- [ ] User runs **Connect to MCP** in the FM file
- [ ] `connectedFiles` returns the file name
- [ ] API layouts exist (or get created): list view + detail view
- [ ] If drag-reorder is in scope: `SortOrder` Number field, indexed, on both layouts, with auto-enter calc
- [ ] Both layouts include every field the app reads OR writes
- [ ] `mkdir webviewer/<app-name>` and `setup_proofkit_project` with absolute path
- [ ] `npx @proofkit/cli@beta init . --app-type webviewer --non-interactive`
- [ ] `npx @tanstack/intent@latest install`
- [ ] Edit `proofkit-typegen.config.jsonc`: set `connectedFileName` and `layouts`
- [ ] `npm run typegen` — confirm files in `src/config/schemas/filemaker/`
- [ ] `globalSettings.setWebViewerName("web")` in `App.tsx`
- [ ] `.claude/launch.json` for preview tools (with `--prefix`)
- [ ] `npm run dev` — verify in browser
- [ ] Build app: list, detail, CRUD mutations, drag-reorder if needed
- [ ] `npm run build`
- [ ] `deploy_html` — verify with `SELECT AppName, LENGTH(HTML) FROM ProofKitApps`
- [ ] User opens deployed app from FM launcher and clicks through key flows

## Known gaps

Things this guide doesn't cover yet:

- **Container fields (file uploads).** `WebViewerAdapter` does NOT support `containerUpload`. For attachments, call a custom FM script via `fmFetch` and base64-encode the binary in JS.
- **Production hosted auth.** This guide assumes the FM file is open locally. For a hosted production build (FM Server, OttoFMS), use `OttoAdapter` instead of `WebViewerAdapter` and provision a dedicated API key. Different typegen config: no `fmMcp` block, with `envNames` for credentials. See the typegen-fmdapi skill.
- **Multi-file FM solutions.** Only one file connects to MCP at a time. If your data spans files, decide which is the host and replicate or relate from there.
- **OData schema creation.** OData can create FM tables and add fields programmatically, but it does NOT create layouts. After OData creates a table, go into FM and create the API layout manually.
- **Performance with large lists.** Tested up to ~20 records. For thousands, paginate via `offset`/`limit` and prefer `find` with criteria over `list`.

## Quick reference card

```
# Health
connectedFiles                                    → file names that are bridged

# Schema for app build
layout_metadata { layouts: "" }                   → list all layouts
layout_metadata { layouts: "Foo" }                → fields on one layout

# Schema for exploration (not for app builds)
table_metadata { tables: "" }
get_filemaker_ddl_schema { requests: [{ tableOccurrenceNames: [...] }] }
get_relation_info { tableName: "X" }

# Read data
execute_filemaker_sql { intent: "SELECT ..." }    # SQL or natural language
data_api_orchestrator { action: "read", request: { layouts: "X", limit: 10 } }

# Write data (ad-hoc / seeding)
data_api_orchestrator { action: "create", request: { layouts: "X", fieldData: {...} } }
data_api_orchestrator { action: "update", request: { layouts: "X", recordId: "1", fieldData: {...} } }
data_api_orchestrator { action: "delete", request: { layouts: "X", recordId: "1" } }

# Web viewer build
setup_proofkit_project { targetPath: "<absolute>" }
deploy_html { appName, path: "<absolute path to dist/index.html>" }

# Verify deploy
SELECT AppName, LENGTH(HTML) FROM ProofKitApps
```

---

*Fold improvements back into this guide as you discover them. Each project is a chance to make the next one faster.*
