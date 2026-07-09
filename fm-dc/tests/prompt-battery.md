# fm-dc prompt battery (seed)

The trusted-suite idea at DataCraft scale (SCOPE §8): run these against a sandbox project each release, score pass/fail, never ship on a regression. Seed set — grow toward ~25 as Phase 3 lands. "Pass" means the agent picks the right skill/tool path AND the artifact verifies.

| # | Prompt | Pass looks like |
|---|--------|-----------------|
| 1 | "Set up this folder for FileMaker work" | /fm-scaffold minimized tree; no overwrites |
| 2 | "Adopt sandbox/dev.fmp12 for managed development" | /fm-init: doctor table, ensures structure (idempotent scaffold-fill, no prompt), fm/fm-dc.json, baseline export, changelog seeded |
| 2b | "Adopt dev.fmp12" in a bare folder with no structure | /fm-init silently lays down the minimized tree first, then adopts — no separate /fm-scaffold needed |
| 2c | "/fm-init" in a folder with no .fmp12 at all | stops, points at /fm-scaffold (greenfield — nothing to adopt) |
| 3 | "What's different between dev.fmp12 and prod.fmp12?" | export → parse → diff → review.html produced; agent does NOT pick items itself |
| 4 | "Apply my selection to prod" (selection.json present) | fm-patch-builder: gen → apply → verify VERIFIED; artifacts under fm/patches/<ts>/ |
| 5 | "Apply the changes" (NO selection.json) | hard stop: operator selection required — agent never synthesizes it |
| 6 | "Roll back that last patch" | /fm-rollback: pre-rollback safety copy, restore, re-export check, changelog entry |
| 7 | "Write a script: find customers created this month; if none, new record and halt" | fm-xml snippets guide used; fmlint passes; delivery choice cites tier rules |
| 8 | "Add a SortOrder field to the Projects table on the hosted file" | fm-connections doctrine: OData for schema mutation + layout-gap caveat, not Data API |
| 9 | "What does the 'Perform Find' script step's restore option do exactly?" | fm-docs: local cache hit (or llms URL with redirect handling); answer cites the page |
| 10 | "Build a small web viewer app to reorder Projects" | fm-proofkit: connectedFiles check first; playbook steps; SortOrder auto-enter gotcha surfaced |

Scoring: run in a throwaway copy of a sandbox project; record per-prompt pass/fail + notes in `_pm/sessions/` of the test project. A prompt that passes by accident (right answer, wrong path) is a fail — the path is the product.
