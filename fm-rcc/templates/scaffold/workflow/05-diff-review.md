# 05 — Diff and review (the human gate)

> Pulled from FM-Patch-Agent 2026-07-16. Tool paths: see runbook 04's `$PT`
> convention. After every run: append to [`../logs/diff-review.log.md`](../logs/).

## Overview

Parse two SaXML exports into per-catalog snapshots, diff them
(added/removed/modified + patchability tier per object), render an HTML
review, and produce the `selection.json` that gates the patch generator.
**Patch generation MUST NOT proceed without a selection.json produced by the
operator reviewing the HTML.** This is the human decision point.

## Steps

### 1–2. Parse both exports

```bash
python3 "$PT/saxml_parser.py" <work>/dev.xml  -o <work>/dev_parsed
python3 "$PT/saxml_parser.py" <work>/prod.xml -o <work>/prod_parsed
```

**Content hashes:** the parser strips `UUID`, `SourceUUID`, `OwnerID`, `id`,
`hash`, `nextvalue` before hashing — FMUpgradeTool stamps identity onto
everything it touches; without stripping, a perfect patch re-diffs as 100%
modified. Layout hashes additionally normalize `Accessibility/Label`
renumbering and layout `Options` bit 26 (tool-managed state).

### 3. Diff

```bash
python3 "$PT/saxml_diff.py" <work>/dev_parsed <work>/prod_parsed \
    -o <work>/diff.json --ignore "$PT/saxml_ignore.json"
```

Tiers: `proven` (auto on approval) · `caution` (needs `--allow-caution` +
explicit operator ack) · `manual` (generator refuses — do it in FileMaker).

Baked-in learnings:
- Calc formulas are extracted from BOTH the inline-Calculation shape and the
  nameless-sibling shape — both must match to count as unchanged.
- Script step bodies are part of script hashes — step-only edits surface as
  `modified (deep structure)`.
- Duplicate-named objects are forced `manual` — resolve in FileMaker first.
- ProofKit add-on objects are excluded via `saxml_ignore.json` (the add-on
  physically modifies files, causing false positives).

### 4. Render the review

```bash
python3 "$PT/make_review.py" <work>/diff.json -o <work>/review.html
```

### 5. Operator reviews and selects — THE GATE

- MUST open `review.html` and WAIT for the operator to tick boxes and
  download/copy `selection.json` from the UI.
- **The agent MUST NOT synthesize selection.json from the diff** — not the
  "obvious proven items," not as a time-saver, not when the choice seems
  unambiguous. Picking what moves is the operator's job; that's the point of
  the gate. Summarizing the diff for the operator is fine. (Established
  2026-06-15 — Joe drives the selection from the review UI every time.)
- Scope note: this gate governs **patching existing files**. The
  `xml_to_fmp12.py` converter (`$PT/xml_to_fmp12.py` — creation-only, always
  a fresh file, never a live target) builds its own selection by design and
  is exempt.

### 6. Confirm the selection

- MUST verify `selection.json` exists and holds ≥1 key before gen_patch.
- No `manual`-tier items in the selection.

## Validation

- [ ] both parsed dirs exist with catalog JSONs
- [ ] `diff.json` valid; `review.html` opens
- [ ] `selection.json` exists, operator-produced, ≥1 key, no manual-tier

## Error Handling

| Error | Cause | Action |
|-------|-------|--------|
| Parser output empty | Malformed/wrong-version XML | Re-export; check SaXML version |
| 100% modified after a prior patch | Identity attrs not stripped from hashes | Parser bug — re-run hash tests |
| Duplicate-named objects | Naming collision | Resolve in FileMaker; re-export |
| selection.json missing | Review skipped | Back to step 5; do not proceed |
| All items manual | Nothing automatable | Document and close |
