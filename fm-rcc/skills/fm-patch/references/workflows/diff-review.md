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

**Direction (`--direction push|sync`, default `push`).** `push` treats dev as the source and prod as a file with its own history worth keeping:

- Objects that exist only in prod render in a **"Prod-only — preserved"** section with a lock icon and **no checkbox in the DOM at all**. There is no click, keyboard, or select-all path that puts one into the selection, and the footer states the guarantee: *"N prod-only objects will be preserved. This patch cannot delete anything."*
- `--direction sync` restores the old behaviour, where prod-only objects are selectable and compile to `DeleteAction`.

Choose `push` unless the operator has explicitly asked to delete prod-only objects. `saxml_diff` labels prod-only objects `removed`, which reads like "the dev author deleted this" — but when prod has diverged on purpose, those rows are the operator's own work, and selecting one destroys it. `--allow-caution` alone is not consent for that; the deletion must be named.

### 4a. Dependencies are closed, and gaps block

Ticking any item auto-includes its full transitive dependency closure. Each auto-added row is highlighted, labelled with the tick that pulled it in (*"pulled in by PK_deploy_html (script)"*), and listed in a footer manifest grouped by cause. Unticking releases only what that tick alone pulled in.

Two things this must never do, both of which were real bugs:

- **Silently drop an unreachable dependency.** If a required object cannot travel — it is ignored, `manual`-tier, duplicate-named, or absent from the diff — the *dependent* is rendered **blocked**: unselectable, styled distinctly, and carrying the reason inline. Blocking is transitive, so anything downstream of a blocked object is blocked too. Resolve it in FileMaker (or widen `--ignore`) and re-run the diff.
- **Cover only added objects.** `dependency_analysis()` probes added *and* modified items. Modified items compile to `ReplaceAction` and must be probed with `allow_caution=True`, or they fall out as a `ValueError` with no edges — which is exactly how modified objects came to have an empty graph.

Each row also expands to an object profile: what it references (must travel with it) and what references it (breaks without it), with links that jump to the related row.

**Watch the ignore list.** It exists to suppress add-on noise when the add-on is installed on *both* sides. When it is installed on the source side only, the add-on *is* the change set and the ignore list will hide most of it — you will move a handful of visible scripts whose tables and helpers stay behind. Symptom: a small selection with a `blocked` badge naming an ignored object. Fix: re-run `saxml_diff.py` with a narrower `--ignore`, then regenerate the review page.

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
- [ ] No `blocked` items in selection (the UI prevents it; verify anyway)
- [ ] In `push` mode: no `removed` keys in the selection at all
- [ ] The selection is dependency-closed — `gen_patch.py` raises `DependencyError` if not, which means the review page and the generator disagree and the page is the one to fix

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| Parser output empty | Malformed or wrong-version XML | Re-export; check SaXML version |
| Diff shows 100% modified after a previous patch | SourceUUID/OwnerID not stripped from content hashes | Parser bug — `saxml_parser.compute_hash` must strip UUID/SourceUUID/OwnerID/id/hash/nextvalue; re-run tests (`test_hash_ignores_*`) |
| Duplicate-named objects in diff | Naming collision in source file | Resolve duplicates in FileMaker; re-export |
| `selection.json` missing | Operator skipped the review step | Return to step 5; do not proceed |
| `manual`-tier items selected | Operator selected a non-patchable item | Remove from selection; handle in FileMaker directly |
| All items are `manual` tier | No automatable changes | Nothing to patch; document and close |
