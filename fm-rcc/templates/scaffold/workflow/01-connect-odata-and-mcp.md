# 01 — Connect the agent to the hosted file (OData + ProofKit MCP)

## What

Fill in [`../hostedFile.md`](../hostedFile.md) first — server, file, account,
pass. Every later step (and every script in `../scripts/`) reads connection
details from that file instead of repeating them. Real projects: mind the
credentials note there — the `pass` line points at `.env`, and never gets
committed with a real value.

Two independent connections get set up:

### 1. OData — straight to FileMaker Server

FileMaker Server exposes every hosted file over **OData**, a REST standard
for working with databases over HTTP. Nothing has to be installed and the
file doesn't need to be open anywhere — if the server is up, this door is
open:

```
https://<server>/fmi/odata/v4/<file-without-.fmp12>
```

Prove it from any terminal with nothing but `curl`:

```bash
curl -s -u '<account>:<pass>' 'https://<server>/fmi/odata/v4/<database>'
```

A JSON list of every entity set (table) in the file comes back.

### 2. ProofKit MCP — through FileMaker Pro

**MCP** (Model Context Protocol) is the standard way coding agents plug in
outside tools. **ProofKit** is a FileMaker plugin + MCP server pair: with the
file open in FileMaker Pro and its "Connect to MCP" script run, the agent
gets a toolbelt that works *through the running client* — SQL queries, Data
API record operations, layout and schema metadata, script lists, and
web-viewer deployment.

Setup on the FileMaker side: ProofKit installed (https://proofkit.proof.sh/),
the file open in FileMaker Pro, bridge connected. On the agent side, the
ProofKit MCP server registered in the agent's MCP configuration. Verify with
the MCP `connectedFiles` tool — it should list this file. (Empty list → run
the "Connect to MCP" script inside the file; call fails outright → the
plugin bridge isn't reachable.)

## Why

An agent is only as capable as the doors it has into the file — and no
single door does everything:

- **OData is the schema door.** It's the one live channel that can *change
  schema* (add tables and fields) on a hosted file without downloading it or
  opening it in Pro. It also does record CRUD. But it's comparatively
  low-level, and it can't see scripts or layouts.
- **ProofKit MCP is the toolbelt.** Much richer for working *inside* the
  file — querying with SQL, reading layout metadata, listing scripts,
  pushing web-viewer apps. But it depends on FileMaker Pro running with the
  plugin bridge connected.
- **Two doors mean independent verification.** A recurring pattern in agent
  workflows: make a change through one channel, confirm it through the
  other. A table created over OData can be independently confirmed via MCP —
  the agent isn't grading its own homework.

**Caveat that bites later:** a table created over OData exists immediately,
but FileMaker's Data API — and any MCP record tools built on it — can't see
the new table until someone places it on a layout in FileMaker Pro. OData is
the schema side door; the Data API needs a front door. (SQL queries see new
tables regardless.)

## Result — capture when run

Re-run this step against THIS project's file, then record what actually
happened:

- OData connect: <entity-set count, account used>
- Table survey: <base-table count, naming patterns worth knowing>
- ProofKit bridge: <`connectedFiles` output>
