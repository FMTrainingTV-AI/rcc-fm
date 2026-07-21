---
name: fm-admin
description: Talk to a FileMaker SERVER over the Admin API v2 with admin-console credentials — list hosted files, server status/metadata, and DOWNLOAD a hosted .fmp12 (close → download → reopen, safely). The third door — OData/Data API talk to the data; this talks to the server. Use when the user has admin console credentials and wants a hosted file downloaded locally (e.g. to clone it or run the patch pipeline), or wants server status, hosted-file inventory, or client counts. Ships a ready-to-run driver — RUN IT, do not write your own. For file-level data/schema use fm-dataapi/fm-odata; for which-method-when see fm-connections.
argument-hint: "[databases|metadata|status|scripterrorslog|download <file>] [--host --user --password | --env <path>] [--profile FMS2]"
allowed-tools: Bash, Read, Write
---

# FileMaker Server Admin API — the server door

The Admin API v2 (`https://<host>/fmi/admin/api/v2`) is the third door into a
FileMaker deployment: OData and the Data API talk to the *data*; this talks to
the *server*. Auth is the **admin console** account (not a file account):
Basic → short-lived Bearer token. The driver logs out after every run — admin
sessions are limited.

## Run the driver — don't reinvent it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-admin/scripts/fms_admin.py <command> \
    --host <server> --user <console-account> --password <pass>
```

Credentials three ways (first wins): inline flags · `--env <path>` · a
gitignored `./.env` or `./_fm/.env` in the working directory, with
profile-prefixed keys (`FMS_HOST` / `FMS_ADMIN_USER` / `FMS_ADMIN_PASS`;
`--profile FMS2` reads `FMS2_*`). Stdlib-only, no pip installs.

| Command | Does |
|---|---|
| `databases` | Every hosted file: id, name, status, size, client count. **Start here.** |
| `metadata` / `status` | Server identity/version · server state. |
| `scripterrorslog` | Script-error log **settings** (booleans only — see below). |
| `download <name-or-id>` | The game-changer: close → download zip → **reopen** → unzip → sha256. |

## The capability that changes the game: Download Database

`GET /databases/{id}` returns the hosted file **as a zip** — but only while
the file is CLOSED (error 1708 otherwise). The driver packages the safe dance
and **always reopens, even when the download fails**. Guardrails: it refuses a
file with connected clients unless `--force-close` (they'd be kicked), and it
never touches any file other than the one named. Verified live: a 3.8 MB
hosted file landed locally, consistency-checked clean, server back to NORMAL —
~15 seconds end to end.

**Why it matters:** "get the file locally" stops being a blocker on any server
you hold console credentials for. Local file → `FMDeveloperTool --clone`
(perfect conversion base) or the full **fm-patch** cycle. `POST
/databases/upload` exists for the return trip (or `FMDeveloperTool
--uploadDatabases`).

Default download target: `./dev/downloads/` under the working directory
(`--out` to override).

## Hard-won facts (verified against live servers)

- **The server documents itself:** `https://<host>/fmi/admin/apidoc/` embeds
  the full OpenAPI spec (111 paths on 22.0.5). When in doubt, read the
  server's copy, not memory.
- **The logs verdict:** `GET /server/scripterrorslog` returns **settings
  only**. Admin API v2 has **no endpoint that returns log file content** —
  the Admin Console's log viewer uses a private API. Server status / clients /
  usage / schedules come from this API; reading `Event.log` itself needs
  `fmsadmin`/filesystem access on a box you control.
- **Beyond the driver** (one `call()` away — import `Admin` from the script):
  `GET /fmdapi/usage` (Data API stats), `GET /clients` (+ DELETE to
  disconnect, POST to message), `POST /remotebackup/backup` "Back up Now" /
  `list` / `restore` (a no-close-needed path to a file copy — unexercised),
  schedules CRUD, `GET /modelserver/*` (FMS AI model server).

## Workflow

1. `databases` — confirm auth and see what's hosted (status + client counts).
2. Before a `download`, tell the user the file will be briefly closed; check
   the client count from step 1 first.
3. After a download for patching: the local copy is now the working file —
   hand off to **fm-patch** (or `--clone` it for a conversion base).
