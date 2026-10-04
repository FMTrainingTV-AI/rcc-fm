# 01 — Connect the agent to the hosted file (OData)

## What

Fill in [`../hostedFile.md`](../hostedFile.md) first — server, file, account,
pass. Every later step (and every script in `../scripts/`) reads connection
details from that file instead of repeating them. Real projects: mind the
credentials note there — the `pass` line points at `.env`, and never gets
committed with a real value.

### OData — straight to FileMaker Server

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

## Why

An agent is only as capable as the doors it has into the file:

- **OData is the schema door.** It's the one live channel that can *change
  schema* (add tables and fields) on a hosted file without downloading it or
  opening it in Pro. It also does record CRUD. But it's comparatively
  low-level, and it can't see scripts or layouts.
- **The export loop is the second witness.** Steps 02–03 pull the file's
  whole design out over this same connection. A recurring pattern in agent
  workflows: make a change through one channel, confirm it through another.
  A table created over OData shows up in the next structure export — the
  agent isn't grading its own homework.

**Caveat that bites later:** a table created over OData exists immediately,
but FileMaker's Data API can't see the new table until someone places it on
a layout in FileMaker Pro. OData is the schema side door; the Data API needs
a front door. (SQL queries see new tables regardless.)

## Result — capture when run

Re-run this step against THIS project's file, then record what actually
happened:

- OData connect: <entity-set count, account used>
- Table survey: <base-table count, naming patterns worth knowing>
