---
description: Build or refresh the local Claris documentation mirror (~/.fm-rcc/docs-cache)
argument-hint: "[--docsets slugs] [--limit N]"
allowed-tools: Bash, Read
---

Build or refresh the local Claris docs cache so the fm-docs skill can answer from disk instead of the network.

1. Run the sync tool, passing through any arguments the user gave ($ARGUMENTS):

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/docs/sync_claris_docs.py $ARGUMENTS
   ```

   Defaults: docsets `pro-help,data-api-guide,odata-guide,app-upgrade-tool-guide,sql-reference` → `~/.fm-rcc/docs-cache/`. The full default pull is ~1,300 pages at a polite 0.2 s/page (≈ 5–10 minutes) — tell the user this before starting, and offer `--limit 50` if they just want a taste. Run it in the background for the full pull.

2. When it finishes, report the counts line (fetched / invalid-skipped / indexed) and the cache location.

3. If a page count looks truncated or the run errored partway, it's safe to re-run — fetches are idempotent overwrites.
