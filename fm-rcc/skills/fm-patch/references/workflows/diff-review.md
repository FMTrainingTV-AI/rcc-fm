# Diff and Review

## Overview

Parse two SaXML exports (dev and prod) into per-catalog JSON snapshots, diff them to identify added/removed/modified objects with patchability tiers, generate an HTML review artifact, and produce a `selection.json` that gates the patch generator. **Patch generation MUST NOT proceed without an explicit `selection.json` produced by the operator reviewing the HTML artifact.** This is the human decision point in the pipeline.

## Scripts Used

- `saxml_parser.py` — parses a SaXML export into per-catalog JSON snapshots (one file per object type).
- `saxml_diff.py` — diffs two parsed snapshots; classifies changes as added/removed/modified with tiers: `proven`, `caution`, `manual`.
- `make_review.py` — generates a self-contained HTML review UI; the operator selects items and downloads/copies `selection.json`.

## Inputs

- Required: `exports/dev.xml` — dev SaXML export (from export-xml workflow, with `--stamp-guids`)
- Required: `exports/prod.xml` — prod SaXML export (from export-xml workflow)
- Required: `scripts/saxml_ignore.json` — ignore list (ProofKit add-on objects and other known-noise items)
- Optional: `--ignore <path>` — alternate ignore list (default: `scripts/saxml_ignore.json`)

## Steps

### 1. Parse the dev export

```bash
.venv/bin/python scripts/saxml_parser.py exports/dev.xml -o parsed/dev/
```

Output: `parsed/dev/` directory containing one JSON file per catalog (base_tables.json, fields.json, scripts.json, layouts.json, etc.).

### 2. Parse the prod export

```bash
.venv/bin/python scripts/saxml_parser.py exports/prod.xml -o parsed/prod/
```

Output: `parsed/prod/` directory with the same catalog structure.

**Note on content hashes:** The parser strips `UUID`, `SourceUUID`, `OwnerID`, `id`, `hash`, and `nextvalue` attributes (and the element forms of the first three) before hashing. This is essential: FMUpgradeTool stamps `SourceUUID` and `OwnerID` onto every object it patches — without stripping these, a perfectly applied patch would re-diff as 100% modified on the next run. Layout hashes additionally go through a per-instance view: `<Accessibility><Label>` internal-id references are stripped and bit 26 of the layout-level `<Options>` is masked — both are engine/tool-managed state that FMUpgradeTool rewrites on layout insert (2026-06-12 real-file run).

### 3. Diff dev vs prod

```bash
.venv/bin/python scripts/saxml_diff.py parsed/dev/ parsed/prod/ \
    -o diffs/diff.json \
    --ignore scripts/saxml_ignore.json
```

Output: `diffs/diff.json` containing added/removed/modified entries keyed by catalog+name, each with a `patchability` field.

**Patchability tiers:**
- `proven` — safe to automate (tables, fields, TOs, relationships, value lists, layouts)
- `caution` — can be patched but requires `--allow-caution` flag (scripts, deletes, relationships-with-external-sources)
- `manual` — cannot be patched automatically; must be done in FileMaker directly (custom functions, duplicate-named objects)

**Key learnings baked into this step:**
- Calc formulas are extracted from BOTH the inline-Calculation shape and the nameless-sibling shape in the SaXML — both must match for an object to be considered unchanged.
- Script step bodies are part of script hashes — step-only edits surface as modified with `(deep structure)` noted.
- Duplicate-named objects (e.g., two fields named "Status") are forced to `patchability=manual`. Resolve duplicates in FileMaker before running the differ.
- ProofKit add-on objects are excluded via `scripts/saxml_ignore.json` — the add-on physically modifies files it's installed in, causing false positives.

### 4. Generate the HTML review artifact

```bash
.venv/bin/python scripts/make_review.py diffs/diff.json -o review/review.html
```

Output: `review/review.html` — a self-contained, single-file HTML review UI. Open in any browser; no server required.

### 5. Operator reviews and selects items

- MUST open `review/review.html` in a browser and inspect each changed item.
- SHOULD review `manual`-tier items separately — they require direct FileMaker action, not a patch.
- MUST select only items the operator has verified are safe to apply.
- MUST download or copy `selection.json` from the review UI before proceeding.
- MUST save `selection.json` to a known path (e.g., `selections/selection.json`). The HTML's "Download selection.json" button saves to the browser's download folder (typically `~/Downloads/selection.json`) — move it into `selections/`; or use "Copy selection JSON" and paste into the file directly.

**This step cannot be automated.** The operator's explicit selection is the gate. Do not generate a patch without a `selection.json` produced by a human reviewing the diff.

**MUST (agent behavior — non-negotiable):** The agent MUST `open` the `review.html` and WAIT for the operator to tick boxes and download/copy `selection.json` from the UI. The agent MUST NOT synthesize `selection.json` itself from the diff (not even "the obvious proven items," not even as a convenience/time-saver, not even when the choice seems unambiguous). Picking what moves is the operator's job and the whole point of the gate. Summarizing the diff for the operator is fine; deciding the selection for them is not. (Established 2026-06-15 — Joe wants to drive the selection from the website every time.)

### 6. Confirm selection.json is present and non-empty

- MUST verify `selections/selection.json` exists and contains at least one selected key before calling `gen_patch.py`.
- MAY inspect the JSON to confirm selected keys match the operator's intent.

## Validation

- [ ] `parsed/dev/` exists with at least one catalog JSON file
- [ ] `parsed/prod/` exists with at least one catalog JSON file
- [ ] `diffs/diff.json` exists and is valid JSON
- [ ] `review/review.html` opens in a browser without errors
- [ ] `selections/selection.json` exists, is valid JSON, and contains at least one key
- [ ] No `manual`-tier items in selection (they cannot be patched)

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| Parser output empty | Malformed or wrong-version XML | Re-export; check SaXML version |
| Diff shows 100% modified after a previous patch | SourceUUID/OwnerID not stripped from content hashes | Parser bug — `saxml_parser.compute_hash` must strip UUID/SourceUUID/OwnerID/id/hash/nextvalue; re-run tests (`test_hash_ignores_*`) |
| Duplicate-named objects in diff | Naming collision in source file | Resolve duplicates in FileMaker; re-export |
| `selection.json` missing | Operator skipped the review step | Return to step 5; do not proceed |
| `manual`-tier items selected | Operator selected a non-patchable item | Remove from selection; handle in FileMaker directly |
| All items are `manual` tier | No automatable changes | Nothing to patch; document and close |
