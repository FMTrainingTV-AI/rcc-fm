# The Claris CLI tools — the landscape under the patch pipeline

> Researched 2026-07-16 against the installed tools — all 22.0.5.500
> (01-13-2026 build), in `/usr/local/bin` with FileMaker Server's
> command-line tools. Each tool's own `--help` is the source of truth;
> re-run it after any FileMaker upgrade and update this page.

Four tools plus one helper, with a clean division of labor: **FMDeveloperTool**
operates on files, **FMUpgradeTool** changes structure, **FMDataMigration**
moves data, **fmsadmin** runs the server.

## FMDeveloperTool — the file utility knife

Verbs: `--copy` · `--clone` · `--copyCompress` · `--copySelfContained` ·
`--saveAsXML` · `--enableEncryption`/`--removeEncryption` ·
`--removeAdminAccess` · `--enableKiosk` · `--recover` · `--checkConsistency` ·
`--renameFiles` · `--querySize`/`--sortBySize` · `--uploadDatabases` ·
`--resetFileUUID`

- **The pipeline uses:** `--saveAsXML` (via `fm_export.py` — see
  [workflows/export-xml.md](workflows/export-xml.md)) and
  `--checkConsistency` (the XML→file converter's final sanity check).
- **Worth knowing:**
  - `--clone` = all structure, zero records — **the perfect conversion base
    when the original file is obtainable**; the XML route matters when it isn't.
  - `--uploadDatabases` pushes files to a server from the CLI (incl. secure
    folder targets) — a scripted deploy step.
  - `--querySize`/`--sortBySize` — table/field/index size forensics without
    opening the file.
  - `--recover` with granular flags (skip schema/structure, rebuild index
    timing, bypass startup).
  - `--resetFileUUID` — new file identity (relevant when cloning solutions
    for reuse).
- **The limit that shaped the toolchain:** there is **no create-from-XML
  verb** — `--saveAsXML` is one-way. That's why the XML→file converter
  exists (base file + patch pipeline).

## FMUpgradeTool — the patcher

Verbs: `--update` · `--validatePatch` · `--encryptPatch` · `--decryptPatch` ·
`--generateGUIDs` · `--regenerateGUIDs` · common `-inplace` / `-force` /
`-v` / `-q`

- **The pipeline uses:** `--update`, `--validatePatch`, `--generateGUIDs` —
  always through `apply_patch.py` / `fm_export.py --stamp-guids`, never bare.
- **Worth knowing:**
  - `--encryptPatch`/`--decryptPatch` — passkey-encrypted patch files for
    **secure patch delivery** to client sites (validate works on encrypted
    patches too).
  - A dedicated **`fmupgrade` account** tier can apply patches without Full
    Access credentials — deployment nicety for client servers.
  - `--regenerateGUIDs` resets ALL object identities (vs. generate-missing) —
    relevant to cross-lineage identity questions.
  - **`-v` verbose mode — unused by the pipeline so far.** First diagnostic
    to reach for on the silent no-op classes (mid-patch abort, cross-lineage
    relationship/custom-function drops — see
    [patchability-matrix.md](patchability-matrix.md), gotchas).
- **Limits** (see the matrix): the success banner lies; Replace can't
  carry script step bodies; custom functions can't be Replace'd at all;
  accounts/privilege sets/menus are untouchable (themes: Add capability-proven
  for custom themes, generator support queued).

## FMDataMigration — the data mover

One job: migrate **all record data** from a source file into a copy of a
clone (`-src_path` + `-clone_path` → target).

- **The deployment complement to patching:** patching changes structure in
  place and keeps data; migration rebuilds from a dev clone and imports
  prod's data. Big structural jumps where patching is impractical go this
  way.
- **Worth knowing:** `-ignore_valuelists` / `-ignore_accounts` (take the
  clone's), `-reevaluate` (stored calcs), `-rebuildindexes`, dedicated
  **FMMigration account** tier, `-target_locale`.
- **Conversion angle:** XML→file converter output (structure) +
  FMDataMigration (records) = a full file **when the original .fmp12 is
  locally available**. Matching behavior against a non-clone-lineage target
  (like a converted rebuild) is untested — probe before relying on it.
  Hosted-only scenarios get records via OData/Data API instead.

## fmsadmin (+ fmsgetpasskey) — the server console

Administers the Database Server on the **local machine** — i.e., run it on
the server host (or over SSH). Commands: `LIST`/`STATUS`, `OPEN`/`CLOSE`,
`PAUSE`/`RESUME`, `BACKUP`, `VERIFY`, `DISCONNECT`, `REMOVE`, schedules,
certificates, `WPE`.

- **Relevance — on servers you control:** scripted `BACKUP` before any
  server-side change window; `CLOSE` a hosted file to download/patch it;
  `VERIFY` consistency in place; `REMOVE` to pull a file out of hosting.
- **Not usable against third-party hosts** (a class or client server you
  don't shell into) — those stay on the HTTPS doors: OData/Data API for
  data and remote export, the Admin API for server operations.
- `fmsgetpasskey` is a local helper for saved admin credentials — it errors
  off-server, which is expected.

## The map

| Need | Tool |
|---|---|
| File → XML snapshot | FMDeveloperTool `--saveAsXML` ([workflows/export-xml.md](workflows/export-xml.md)) |
| XML → file | **no verb exists** → the XML→file converter (base + patch) |
| Change structure, keep data, in place | FMUpgradeTool ([workflows/patch-apply.md](workflows/patch-apply.md)) |
| New structure + old data | FMDataMigration (clone-based deploy) |
| Structure copy, no data | FMDeveloperTool `--clone` |
| Hosted file, no server shell | OData (remote export + clipboard round-trips) |
| Hosted file, admin console creds | **Admin API v2** — close → download zip → reopen |
| Hosted file, your server (shell) | fmsadmin (close/backup/open around the work) |
