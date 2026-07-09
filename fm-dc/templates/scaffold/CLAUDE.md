# CLAUDE.md — <Project Name>

FileMaker engagement workspace, scaffolded by the **fm-dc** plugin (`/fm-scaffold`). FM capability — patching, XML, connections, ProofKit, docs lookup — comes from the plugin's skills; this file only carries what is specific to THIS project.

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
schema/       analysis pipeline — ddrs/ (raw exports, date-stamped) → parsed/ → readable/ (agent
              knowledge base) → reports/
dev/          working scratch: XML drafts, POCs, throwaway proofs
fm/           created by /fm-init — managed-file config, baseline export, patches, backups, changelog
.env          FM credentials (gitignored): FM_HOST, FM_DATABASE, FM_USERNAME, FM_PASSWORD
```

## Working rules

- **Same-commit rule:** when work ships, remove it from `_pm/TASKS.md` and add it to today's session file in the same commit.
- **Schema questions** run through the pipeline: export → `ddr.py split` → `summary`/`search`/`refs` (tools live in the fm-dc plugin; see the `ddr` skill).
- **Changes to the .fmp12** go through the fm-patch skill / fm-patch-builder agent — never hand-applied without the backup→validate→smoke→verify sequence.
- **Snippets are validated** with fmlint before any paste (fm-xml skill rule).
- **Connection mode choice** (ProofKit MCP vs Data API vs OData vs pipeline) follows the fm-connections four-mode doctrine.
