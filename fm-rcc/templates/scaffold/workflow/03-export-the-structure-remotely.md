# 03 — Export the file's structure, remotely, on demand

## What

With the script from doc 02 installed, getting the hosted file's structure
onto local disk is one command from the engagement root:

```bash
python3 scripts/export_saxml.py --catalogs ScriptCatalog
```

No FileMaker Pro. No plugins. Plain Python 3 (standard library only)
talking HTTPS. The export driver can also *borrow* another project's
connection facts via `--project <folder>` — but output always lands in the
running copy's own `schema/ddrs/`: the repo you're working in keeps its
exports. What happens:

1. **Trigger** — `POST .../Script.Agent_SaXML_Export` with the catalog list
   as the script parameter. The script runs server-side and returns its
   result JSON, typically in seconds.
2. **Pickup** — `GET .../<dropTable>('<primaryKey>')?$select=<textField>`
   downloads the XML as ordinary JSON. The script's result JSON carries the
   row's `primaryKey` — the SAXML table's OData entity key (recordId is the
   driver's fallback for custom installs without a validated PK). Table and
   field names come from the `dropTable` / `textField` lines in
   [`../hostedFile.md`](../hostedFile.md) — recorded there during setup,
   never hardcoded in the driver.
3. **Land** — saved under `../schema/ddrs/YYYY-MM-DD/saxml_run-<stamp>.xml`.
   Date-stamped folders follow one rule: one folder per export day, so
   consecutive exports line up for diffing.

## Verified how — never trust "it worked"

Every layer of this workflow assumes tools lie about success, because they
do (a script result can say `error 0` while a field ended up empty). The
driver checks, in order:

1. **The script's own error JSON** — stage and error code, set by
   `Get(LastError)` inside FileMaker at each step.
2. **Byte count > 0** — an empty payload with a clean error code is the
   classic silent failure. The driver hard-fails on zero bytes.
3. **The XML parses** and its root is `FMSaveAsXML`.
4. **Self-reference** — the export *contains `Agent_SaXML_Export` itself*,
   the script installed in doc 02. The map includes the pen that drew it —
   proof the export reflects the file as it is now, not a stale copy.
5. **The hash oracle** — the driver prints a sha256 of the payload.
   Identical hash across runs = nothing changed in the file. After a
   deliberate change the hash *must* differ — if it doesn't, the change
   didn't land, whatever any tool claimed. The cheapest lie detector in the
   whole workflow.

## Build the readable knowledge base

Turn the newest export into something an agent (or human) can actually read:

```bash
python3 scripts/parse_saxml.py
```

- `../schema/parsed/<run>.json` — structured: every script, its flags, its
  ordered steps
- `../schema/readable/<run>.md` — overview + per-script step-by-step, plain
  text

Both are derived artifacts (gitignored) — regenerate from `ddrs/` any time.

## Why this matters

This is the **read path** of agent-driven FileMaker development. The rhythm:

- **Session open** — export. The agent now has a current map of a file it
  may never have seen before.
- **During the session** — work happens: script XML, OData schema changes,
  ProofKit queries.
- **Session close** — export again, diff against the morning's file. The
  diff *is* the changelog: derived from what actually changed, not from
  what anyone remembers doing.

Catalog selection keeps it cheap: pull only `ScriptCatalog` after script
work, `FieldCatalog` + `BaseTableCatalog` after schema work. (A
ScriptCatalog alone can run to many MB — a full export with layouts is far
larger, and layouts are rarely what you need.)

## Result — capture when run

- First export: <catalogs, bytes, sha256, wall time>
- Verification ladder: <all five checks passed?>
- Knowledge base: <parsed/readable generated, script count seen>
