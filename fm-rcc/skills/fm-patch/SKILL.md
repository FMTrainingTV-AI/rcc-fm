---
name: fm-patch
description: >
  Apply changes to FileMaker .fmp12 files programmatically — export Save-as-XML, diff dev
  vs prod, generate and safely apply FMUpgradeTool patches, verify, and roll back. Also
  converts a Save-as-XML export into a NEW working .fmp12 (xml_to_fmp12, creation-only).
  Use when the user wants to patch/deploy/migrate changes into a FileMaker file, diff two
  versions of a file, push dev work to prod, scaffold schema from a spec, rebuild a file
  from an XML export, inspect patch history, or roll back a patch. Requires the Claris CLI
  tools (FMDeveloperTool, FMUpgradeTool) and local file access — hosted files must be
  closed/downloaded first (fm-admin can download them).
---

# FileMaker Patching

Deterministic pipeline: the model decides *what* changes; these tools compile and apply the XML. Never hand-write or hand-edit FMUpgradeTool patch XML — `gen_patch.py` is the only author.

## The pipeline

```
export → parse → diff → review (human) → gen_patch → apply (backup→validate→smoke→inplace) → verify
```

All tools live in `${CLAUDE_PLUGIN_ROOT}/tools/patch/`. Exact commands:

```bash
PT=${CLAUDE_PLUGIN_ROOT}/tools/patch

# 1. Export Save-as-XML (headless; closes/reopens an open local file safely)
python3 $PT/fm_export.py dev.fmp12  -o dev.xml  --stamp-guids
python3 $PT/fm_export.py prod.fmp12 -o prod.xml --stamp-guids

# 2. Parse into per-catalog JSON snapshots
python3 $PT/saxml_parser.py dev.xml  -o dev_parsed
python3 $PT/saxml_parser.py prod.xml -o prod_parsed

# 3. Diff (classifies added/removed/modified + patchability tier per object)
python3 $PT/saxml_diff.py dev_parsed prod_parsed -o diff.json

# 4. Human review — self-contained HTML with checkboxes; operator downloads selection.json
python3 $PT/make_review.py diff.json -o review.html

# 5. Compile the patch from the approved selection
python3 $PT/gen_patch.py --dev-export dev.xml --prod-export prod.xml \
        --diff diff.json --selection selection.json -o patch.xml   # [--allow-caution]

# 6. Apply safely, then verify (re-export + re-diff; every selected key must be gone)
python3 $PT/apply_patch.py apply prod.fmp12 patch.xml --account Admin --pwd "" --backups-dir fm/backups
python3 $PT/apply_patch.py verify --dev-export dev.xml --patched prod.fmp12 \
        --selection selection.json --workdir verify_workdir/ --account Admin --pwd ""   # MANDATORY
```

Spec-driven schema builds (make a file match a JSON spec) use `gen_scaffold.py gen|verify` — additive-only reconciler; drift is reported, never destroyed.

## XML → file: `xml_to_fmp12.py` (creation-only)

There is no Claris CLI verb for XML → file. This tool fakes one: it copies the plugin's `resources/fmbase.fmp12` and grows it to match a Save-as-XML export via the pipeline above (diff → gen → apply → verify), invisibly, with two feedback loops — gen-prune (drop what the generator proves unbuildable) and verify-prune (drop what FMUpgradeTool silently no-ops).

```bash
python3 $PT/xml_to_fmp12.py --input export.xml [--out new.fmp12] [--base themed.fmp12] [--keep-workdir]
```

- **Creation-only, by contract:** the target must not exist; the tool never modifies an existing file — that's what keeps it outside the operator selection gate. To change a real file, use the pipeline above.
- Manual-tier catalogs never travel (accounts, privilege sets, themes, menus). Themed layouts from the source unblock with a `--base` pre-loaded with those themes (layout→theme deps match by name).
- A big result that converged suspiciously *thin* may be the mid-patch-abort mode over-pruning — see the matrix gotchas; re-run with `--keep-workdir` and diagnose with `FMUpgradeTool -v`.
- Reference run: a 561 KB file → full XML → rebuilt and **verified clean** in ~20 s.

## Rules that are not suggestions

1. **Never bypass the sequence** backup → validatePatch → smoke apply → in-place apply → verify. `apply_patch.py` encodes it; don't call FMUpgradeTool directly.
2. **Never trust the tool's "Patch File Applied" banner** — it prints even on silent no-ops. Only `apply_patch.py verify` (re-export + re-diff) counts as success.
3. **Tier gating** (from [references/patchability-matrix.md](references/patchability-matrix.md)):
   - `proven` → patch normally
   - `caution` → requires `--allow-caution` AND explicit human acknowledgment of the specific risk
   - `manual` → the generator refuses; deliver via clipboard XML (fm-xml skill) or document as a manual step. Accounts/privilege sets have no clipboard path either — always manual.
4. **Locked files refuse to patch** (lsof check). Ask the user to close the file in FileMaker Pro; `fm_export.py` can close/reopen automatically for exports only.
5. **Heavy transactions go to the `fm-patch-builder` agent** — a full patch cycle produces thousands of lines of tool output the main conversation doesn't need. Delegate when the change set is approved; the agent returns paths + verify verdict.
6. **Verification of a landed patch belongs to `fm-xml-validator`** when independence matters (the builder should not grade its own homework).

## Project artifact conventions

Inside a project initialized by `/fm-rcc:fm-init`:

```
fm/
├── fm-rcc.json       ← managed files config: {"files":[{"path", "account_env", "password_env"}]}
├── baseline/         ← initial Save-as-XML export (dated)
├── patches/<ts>/     ← per-patch: patch.xml, selection.json, before/ and after/ exports
├── backups/          ← timestamped pre-patch .fmp12 copies (rollback source)
└── changelog.md      ← append-only log of every action taken against the file
```

Every applied patch appends a changelog entry (timestamp, files, catalogs touched, patch path, verify verdict). `/fm-rcc:fm-rollback` restores from `backups/` or a patch's `before/` state.

## References

- [references/patchability-matrix.md](references/patchability-matrix.md) — object type × operation grid with tiers; the ground truth for what FMUpgradeTool can do
- [references/claris-cli-tools.md](references/claris-cli-tools.md) — the four Claris CLI tools (FMDeveloperTool, FMUpgradeTool, FMDataMigration, fmsadmin): verbs, division of labor, what has no verb (XML→file)
- [references/workflows/export-xml.md](references/workflows/export-xml.md) — export SOP incl. open/close choreography and GUID stamping
- [references/workflows/diff-review.md](references/workflows/diff-review.md) — parse/diff/review SOP
- [references/workflows/patch-apply.md](references/workflows/patch-apply.md) — the full apply SOP (the fm-patch-builder agent's playbook)
- [references/workflows/scaffold-file.md](references/workflows/scaffold-file.md) — spec-driven build SOP
