# 08 — The Admin API (the server door)

> Explored 2026-07-16 against two live FMS 22.0.5.500 boxes. Driver: the
> plugin's **fm-admin** skill —
> `${CLAUDE_PLUGIN_ROOT}/skills/fm-admin/scripts/fms_admin.py` (stdlib-only;
> credentials from this project's gitignored `.env`, profile-based —
> `FMS_*`, `FMS2_*`, …). After every run: append to
> [`../logs/admin-api.log.md`](../logs/).

## What

FileMaker Server's **Admin API v2** (`https://<host>/fmi/admin/api/v2`) is
the third door into a deployment: OData/Data API talk to the *data*
(runbooks 01–03); this talks to the *server*. Auth: `POST /user/auth` with
the **admin console** account over Basic → short-lived Bearer token (the
driver logs out after every run; admin sessions are limited).

The server publishes its own complete API reference at
`https://<host>/fmi/admin/apidoc/` — the full OpenAPI spec is embedded in
that page (111 paths on 22.0.5). When in doubt, read the server's copy, not
memory.

## The capability that changes the game: Download Database

`GET /databases/{id}` returns the hosted file **as a zip** — but only while
the file is CLOSED (error 1708 otherwise). The driver packages the safe
dance:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-admin/scripts/fms_admin.py --profile FMS2 download <name-or-id>
```

close → download → **reopen (always — even when the download fails)** →
unzip → sha256. Guardrails: refuses a file with connected clients unless
`--force-close`; touches only the named file. Verified: a 3.8 MB hosted file
landed locally, consistency-checked clean (940/940 blocks), server back to
NORMAL — ~15 seconds end to end.

**Why it matters:** "get the file locally" stops being a blocker on any
server you hold console credentials for. Local file → `FMDeveloperTool
--clone` (perfect conversion base) or the full patch cycle (runbooks 04–06).
`POST /databases/upload` exists for the return trip.

## Other useful reads (all in the driver or one `call()` away)

- `GET /databases` — every hosted file with id, size, status, client count.
- `GET /server/metadata`, `GET /server/status` — identity, version, state.
- `GET /fmdapi/usage` — Data API usage stats.
- `GET /clients` (+ DELETE to disconnect, POST message) — session control.
- `POST /remotebackup/backup` "Back up Now", `GET /remotebackup/list`,
  `POST /remotebackup/restore` ("Restore **or Download** a remote backup") —
  the no-close-needed path to a file copy; not yet exercised.
- Schedules CRUD (`/schedules/*`) — incl. creating backup schedules with
  clone options and running any schedule on demand.
- `GET /modelserver/*` — FMS AI model server config/status (future probe).

## The logs verdict (asked and answered)

`GET /server/scripterrorslog` returns **settings only** (three booleans:
FMSE / DAPI / WPE script-error logging — verified live). **Admin API v2 has
no endpoint that returns log file content** — the Admin Console's log
viewer uses a private API. For "agent, help me with a server problem":
status / clients / usage / schedules come from this API; reading Event.log
itself still needs `fmsadmin`/filesystem access on a box you control.

## Result — capture per server

- Host + FMS version: <from `metadata`>
- Console auth: <works? account name quirks?>
- Download dance: <file, size, sha256, round-trip time, reopened NORMAL?>
- Notes: <hosting-provider quirks, firewalled ports, etc.>
