---
name: fm-otto
description: Talk to OttoFMS on a FileMaker server over its Developer API (/otto/api) with admin-console credentials — READ SERVER LOG CONTENT (Event.log, Access.log, script logs — the thing the FMS Admin API cannot do) and DOWNLOAD A HOSTED FILE OR CLONE WITHOUT CLOSING IT (no downtime, unlike the Admin API), plus deployments, builds, file surgery (recover/encrypt/rename), server-process control and Data API key management. The fourth door. Use whenever the server runs OttoFMS and the question is "what happened on this server", "read the Event log", "why did that script fail", "get me a copy/clone of this hosted file without kicking users off", "deploy this file", "list/undo deployments", "recover this file", or any OttoFMS API question. Ships a ready-to-run driver — RUN IT, do not write your own. For hosted-file inventory and server status use fm-admin (and fm-admin's close-download-reopen only when Otto is absent); for file data/schema use fm-dataapi/fm-odata; for which-door-when see fm-connections.
argument-hint: "[info|logs|log <name>|download <file> [--clone]|deployments|builds|settings|apikeys|files|spec|raw <METHOD> <path>] [--host --user --password | --env <path>] [--profile FMS2]"
allowed-tools: Bash, Read, Write
---

# OttoFMS Developer API — the door that reads the logs and copies live files

[OttoFMS](https://docs.ottofms.com) is a third-party server companion (Proof+Geist)
that installs alongside FileMaker Server and answers on `https://<host>/otto/api`.
It is a **separate service** from the FMS Admin API but shares the **admin-console
identity**, so one `.env` profile drives both this and `fm-admin`.

Not every server has it. `info` is the cheap check — it is the only endpoint that
answers unauthenticated, so it costs nothing to ask.

## Run the driver — don't reinvent it

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-otto/scripts/otto.py <command> \
    --host <server> --user <console-account> --password <pass>
```

Credentials resolve exactly as in `fm-admin` (first wins): inline flags ·
`--key <otto-api-key>` · `--env <path>` · a gitignored `./.env` or `./_fm/.env`
with profile-prefixed keys (`FMS_HOST` / `FMS_ADMIN_USER` / `FMS_ADMIN_PASS`,
plus optional `FMS_OTTO_KEY`; `--profile FMS2` reads `FMS2_*`). Stdlib-only.
Connection flags work before or after the subcommand.

| Command | Does |
|---|---|
| `info` | Otto + FMS versions, licence. **No auth needed — start here.** |
| `logs` | Which log files exist (10 FMS + 5 Otto). |
| `log <name> --tail N` | **The log CONTENT.** `--out <path>` saves the whole file. |
| `download <file> [--clone]` | **The hosted file, no close, no downtime.** `--clone` for schema-only. |
| `deployments` / `builds` | Deployment history · build list. |
| `settings` | Otto server settings. |
| `apikeys` | Data API key **labels** (secrets are never printed). |
| `files [path]` | Browse the server's folders (Backups, Clones, Live Databases…). |
| `spec --out f.json` | The server's own OpenAPI spec, grouped by tag. |
| `raw <METHOD> <path>` | Escape hatch for the ~110 endpoints the driver doesn't wrap. |

## The capability that changes the game: log content

`GET /otto/api/server-info/logs/{name}` returns the log **as plain text**.

This is the direct answer to the limitation `fm-admin` documents: Admin API v2
has **no endpoint that returns log file content**, and the Admin Console's log
viewer uses a private API. If a server runs OttoFMS, that wall is gone — you can
read `Event.log`, `Access.log`, `scriptEvent.log` and Otto's own logs over HTTPS
without filesystem access to the box.

```bash
otto.py logs                              # what's available
otto.py log Event.log --tail 100          # recent server events
otto.py log scriptEvent.log --tail 200    # why that scheduled script failed
otto.py log Event.log --out ./ev.log      # the whole file, for grep/analysis
```

Verified live against FMS 26.0.2 + OttoFMS 4.18.2: `Event.log` came back as
1,020,622 bytes of text in one call.

**Available:** FMS — `Access`, `Event`, `Stats`, `TopCallStats`, `fmdapi`,
`fmodata`, `fmshelper`, `scriptEvent`, `wpe0`, `wpe_debug`. Otto — `otto-error`,
`otto-info`, `otto-receiver`, `app-info`, `app-error`.

`Event.log` grows large and the driver prints only `--tail` lines by default.
For real analysis, `--out` it to disk and grep locally rather than pulling a
megabyte of text through the context window.

## The other one: a hosted file copied with zero downtime

`GET /otto/api/fm-file/{filename}/download` streams the hosted file **without
closing it**. Otto snapshots into its own temp backup folder server-side and
serves that, so clients keep working throughout. Add `?clone=1` for a
schema-only clone.

```bash
otto.py download MyFile            # the data file
otto.py download MyFile --clone    # schema-only clone (conversion base)
```

This is the same outcome as `fm-admin`'s `download`, minus the close → download
→ reopen dance and minus the outage. **When a server runs Otto, this is the way
to get a file local**; `fm-admin`'s path is the fallback for servers without it.

Verified live: a 24,592,384-byte hosted file and its 16,179,200-byte clone both
landed locally with valid FileMaker magic bytes, while the server reported the
file still `NORMAL` throughout — no close, no kicked clients.

Two things to know before leaning on it: the endpoint is **rate limited**
(10 requests/minute — `ratelimit-policy: 10;w=60`), and the snapshot briefly
costs disk on the server, so it is not free for a very large file.

## Hard-won facts (verified against a live server)

- **The server documents itself** — but not where you'd guess. The spec is at
  `https://<host>/otto/apidoc/openapi.json` (Redoc UI at `/otto/apidoc/`).
  **`/otto/openapi.json` is a trap**: see below.
- **`/otto/` is a single-page app with a catch-all.** Any unmatched path returns
  the app's HTML shell with **HTTP 200**. Probing for endpoints by status code
  gives false positives — check for `content-type: application/json`. The driver
  guards this and tells you the path doesn't exist rather than parsing HTML as
  success; keep that guard if you ever hand-roll a call.
- **Auth is per-request, no login/logout dance.** Admin-console **Basic**, or an
  Otto Admin API key as **Bearer**. An FMS Admin API session token also works as
  Bearer — Otto validates by proxying to the local Admin API, which is why a bad
  token surfaces as `Local Admin API error … code: 1703` wearing an Otto envelope.
- **Two different Otto faces, don't confuse them.** `/otto/api/...` is this
  Developer API (server ops). `/otto/fmi/data/...` and `/otto/fmi/odata/...` are
  Otto's **data proxy**, where an Otto Data API key replaces file-account auth —
  that's a `fm-dataapi`/`fm-odata` concern, covered in `fm-connections`.
- **Both APIs share one envelope:** `{"messages":[{"code":0,"text":"ok"}],
  "response":{…}}`. Otto uses integer `code`, the Admin API uses string `"0"`.
  Auth failure is Otto code `18000`.

## Beyond the driver

126 operations across 20 tags. Run `spec` for the current list on *that* server —
endpoints move between Otto releases, so read its copy rather than memory. The
groups worth knowing:

| Tag | What lives there |
|---|---|
| **Deployment** (16) | `POST /deployment` starts one (async — poll `/deployment`). A deployment is a **batch of sub-deployments**, each with its own status, `undo`, `resume`. `undoFull` reverses the batch. |
| **FileMaker Files** (18) | `recover`, `check-consistency`, `copy-compress`, `copy-self-contained`, `encrypt`/`decrypt`, `rename`, `reset-file-uuid`, `save-as-xml`, `remove-admin-access`. Downloads are two-step: ask for a link, get a token, fetch the token URL. `?clone=1` gets a clone. |
| **Build** (15) | Build from source control, publish, rerun, download. |
| **Settings** (19) | Server settings; offsite backup remotes/schedules/notifications. |
| **Scripts** (1) | `POST /script/run-via-schedule` — runs a script through the FMS **scheduled-script engine**, so the account needs **no** `fmrest`/`fmxml` extended privilege. Body: `{file:{name,user,password}, script:{name,param,timeout}}`. |
| **Server Processes** (1) | `POST /fms-process` — `start`/`stop`/`restart` on `wpe`, `fmse`, `adminserver`, `httpserver`, `fmsib`, `xdbc`, `server`, `fmdapi`, `odata`. |
| **MCP Servers / Tools** (10) | Otto 4.18+ hosts MCP servers and their tools as first-class server objects. |
| Keys, Webhooks, Config Transfer, Plugins, File Notes, OData grants | the rest |

## Guardrails — this API can break a production server

Every named subcommand is **read-only**. Writes go through `raw`, which refuses a
non-GET method unless you pass `--yes`. That friction is deliberate: this API can
restart the Web Publishing Engine, delete builds, undo a deployment, and remove
admin access from a file. `POST /fms-process {command:"restart"}` kills whatever
is running on that process.

Treat every write as destructive-by-default: say what you're about to do, name
the server, and get a human yes first. `undo`/`undoFull` are the escape hatch for
a bad deployment, not a licence to deploy casually.

## Workflow

1. `info` — is Otto even here, and what version? (free, no creds)
2. `logs` then `log <name> --tail` — the usual reason you're here. For anything
   beyond a skim, `--out` to disk and grep locally.
3. `spec` before reaching for an endpoint you haven't used on this server.
4. Anything that writes: `raw … --yes`, after telling the human what it does.

## Sibling skills

- **`fm-admin`** — the FMS-native server door: hosted-file inventory, server
  status, client counts, schedules. Its `download` (close → download → reopen)
  is the **fallback**, for servers without Otto — when Otto is present, prefer
  `otto.py download`, which costs no downtime. Same credentials, both doors.
- **`fm-connections`** — which door for which job.
- **`fm-patch`** — once a file is local, the patch cycle.
