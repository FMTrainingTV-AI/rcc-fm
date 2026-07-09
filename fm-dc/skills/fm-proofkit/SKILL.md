---
name: fm-proofkit
description: >
  ProofKit — the bridge between coding agents and FileMaker. Covers the ProofKit MCP server
  (live schema, SQL, CRUD, ERD), building React web viewer apps deployed inside FileMaker,
  and the ProofGeist TypeScript toolchain (@proofkit/fmdapi, typegen, fmodata, better-auth)
  for external web apps. Use when the user mentions ProofKit, web viewers, webviewer apps,
  fmdapi/typegen/fmodata, the MCP bridge, deploy_html, or wants a React UI inside or
  against FileMaker.
---

# ProofKit

## MCP first

When the ProofKit desktop app is running and the FM file is open, the MCP bridge is the fastest path. **Always verify first: call `connectedFiles`.** File name returned → everything works. Empty array → ask the user to run the "Connect to MCP" script in the FM file. If queries time out while `connectedFiles` still answers, the bridge is wedged — re-run "Connect to MCP".

Tool map: `table_metadata`, `layout_metadata`, `get_filemaker_ddl_schema` (diffable DDL), `get_relation_info`, `get_value_list_info`, `get_script_names`, `display_erd_diagram` (schema); `execute_filemaker_sql` (read-only), `data_api_orchestrator` (CRUD); `setup_proofkit_project`, `deploy_html` (web viewer); `clipboard_read`/`clipboard_write` (snippet work). For web viewer app data fetching use `layout_metadata` — the Data API operates through layouts, not tables.

ProofKit's boundaries (v2): it cannot export XML, patch files, or open/close them; schema *editing* is outside its scope (that's OData or the fm-patch pipeline). Its role alongside patching is **verification on open files**. Also: the ProofKit add-on physically modifies every file it's installed in (scripts + layout + table + CF) — the patch pipeline's `saxml_ignore.json` ignore-lists those objects.

## Web viewer apps (inside FileMaker)

Full playbook with real-world gotchas: [references/proofkit_webviewer_build.md](references/proofkit_webviewer_build.md) — read it before starting an app. At a glance:

1. `layout_metadata { layouts: "" }` — pick the layouts the app needs
2. `setup_proofkit_project { targetPath: "<abs path>/webviewer/app-name" }`
3. `npx @proofkit/cli@beta init . --app-type webviewer --non-interactive`, then `npx @tanstack/intent@latest install`
4. Configure `proofkit-typegen.config.jsonc` (connectedFileName, layouts) → `npm run typegen`
5. `npm run dev` against the bridge; build to a single `dist/index.html`
6. `deploy_html { connectedFileName, appName, path }`

Gotchas that bite: `globalSettings.setWebViewerName("web")` must match the FM web viewer object name; Data API date writes are `MM/DD/YYYY` (ISO fails silently); `deploy_html` times out over ~200 KB but usually succeeds — verify with `SELECT AppName, LENGTH(HTML) FROM ProofKitApps`; drag-reorder wants a `SortOrder` number field with auto-enter `Max(self::SortOrder) + 10` on both API layouts.

## External web apps (outside FileMaker)

Default stack: **Next.js (App Router) + `@proofkit/fmdapi` + `@proofkit/typegen`**, plus `@proofkit/better-auth` when there are logged-in users, `@proofkit/fmodata` for bulk/typed table access or live schema mutations. Scaffold with `pnpm create proofkit` or the same CLI (`--app-type <type>`). ProofKit's docs (https://proofkit.proof.sh/docs) are authoritative and move fast — re-read before starting a new app.

Overview of all three integration paths: [references/proofkit.md](references/proofkit.md).

API layouts follow the project's prefix convention (`AI_*`, `zAPI_*`); web viewer apps share the same Data API layouts as agent access — see the fm-connections skill for the doctrine.

## Migrating OFF FileMaker (different from the above)

Everything above keeps FileMaker as the backend. When the goal is instead to **replace** FileMaker with a web stack, that's a different exercise — don't reach for ProofKit's fmdapi/OData bridges:

- **Target stack:** Supabase (PostgreSQL + Auth + Storage) + Vercel (Next.js).
- **Approach:** feature-by-feature migration, not big-bang.
- **Data layer:** FM tables → Postgres tables; FM relationships → foreign keys + RLS policies.
- **Business logic:** FM scripts → Edge Functions or API routes.
- **UI:** FM layouts → React components.
- **Auth:** FM privilege sets → Supabase Auth + RLS.

Use `fm-saxml` to audit the source schema first, then map it over.
