# CLAUDE.md — <Project Name>

FileMaker engagement workspace, scaffolded by the **fm-rcc** plugin (`/fm-rcc:fm-scaffold`). FM capability — patching, XML, connections, ProofKit, docs lookup — comes from the plugin's skills; this file only carries what is specific to THIS project.

## Project facts (fill in)

- **Client:**
- **FileMaker Server host:**
- **Database(s):**
- **Key contacts:**
- **API layout prefix convention:** `AI_*` <!-- pick one per project and stick with it -->

## Folder map

```
_pm/          engagement management — skeleton.md (plan), TASKS.md (Current/Next/Waiting/Backlog),
              sessions/YYYY-MM-DD.md (per-day what + why)
hostedFile.md connection facts for the hosted file — server, file, account, OData URL, export
              drop-box choices. Scripts and runbooks read THIS file; nothing is hardcoded.
scripts/      the project toolbelt — export_saxml.py (pull structure remotely over OData;
              --catalogs all for a full structural export), parse_saxml.py (build the readable
              knowledge base). Plain python3, stdlib only.
workflow/     numbered runbooks: 01–03 hosted-file setup (connect → install export script →
              export), 04–07 the patch cycle, 08 the Admin API. Re-run per project; capture
              results in place.
logs/         per-workflow run journals — rolling ~10 entries, Learnings first-class.
              Run → Log → Reflect → Update. See logs/README.md.
specs/        JSON schema specs for spec-driven builds (workflow/07). See specs/README.md.
schema/       analysis pipeline — ddrs/ (raw exports, date-stamped) → parsed/ → readable/ (agent
              knowledge base) → reports/
dev/          working scratch: XML drafts, POCs, throwaway proofs, downloads
fm/           created by /fm-rcc:fm-init — managed-file config, baseline export, patches, backups, changelog
.env          credentials (gitignored): FM_* file creds, FMS_* admin-console creds
```

## Working rules

- **Same-commit rule:** when work ships, remove it from `_pm/TASKS.md` and add it to today's session file in the same commit.
- **Schema questions** run through the pipeline: export → `ddr.py split` → `summary`/`search`/`refs` (tools live in the fm-rcc plugin; see the `fm-saxml` skill).
- **Changes to the .fmp12** go through the fm-patch skill / fm-patch-builder agent — never hand-applied without the backup→validate→smoke→verify sequence.
- **Snippets are validated** with fmlint before any paste (fm-xml skill rule).
- **Connection mode choice** (ProofKit MCP vs Data API vs OData vs Admin API vs pipeline) follows the fm-connections doctrine.
- **Hosted-file structure reads** go through the remote export loop (workflow/01–03): export brackets the session — baseline at open, re-export + diff at close; clipboard round-trips fill the middle.
- **Run → Log → Reflect:** every workflow run appends to its journal in `logs/` — that feedback loop is how gotchas get caught before they harden into habits.
