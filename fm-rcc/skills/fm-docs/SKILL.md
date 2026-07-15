---
name: fm-docs
description: >
  First-party FileMaker/Claris documentation lookup — script step semantics, function
  signatures, exact option names, Data API/OData/Admin API guides, App Upgrade Tool patch
  grammar. Use when precision about what FileMaker actually does matters: "what does script
  step X do", "what are the options for Y", version compatibility, or any claim that should
  be grounded in Claris's docs rather than memory. Local-first: checks the docs cache
  before the network.
---

# FileMaker Documentation Lookup

Claris publishes its entire help corpus as agent-friendly Markdown (llms.txt convention). This skill makes lookups **local-first**: a one-time mirror, then offline reads.

## Order of operations

1. **Local cache first:** `~/.fm-rcc/docs-cache/<docset>/<topic>.md`. Grep it:
   ```bash
   grep -ril "perform find" ~/.fm-rcc/docs-cache/pro-help/ | head
   ```
2. **No cache or missing page → fetch the page directly** (follow redirects — every URL 302s once):
   ```bash
   curl -sL https://help.claris.com/markdown/en/pro-help/<topic>.md
   ```
   Valid pages start with YAML frontmatter (`---`); a body starting `<!DOCTYPE` means bad slug → 404 redirect. Don't guess slugs — the authoritative index is `https://help.claris.com/llms-full.txt`.
3. **Build or refresh the cache:** run `/fm-rcc:fm-docs-sync` (wraps `${CLAUDE_PLUGIN_ROOT}/tools/docs/sync_claris_docs.py`). Default docsets: pro-help, data-api-guide, odata-guide, app-upgrade-tool-guide, sql-reference.

## URL pattern

```
Markdown: https://help.claris.com/markdown/en/{docset}/{topic}.md    (flatter than HTML — no /content/)
HTML:     https://help.claris.com/en/{docset}/content/{topic}.html
```

Frontmatter carries `topic_type` (`script-step-reference`, `function-reference`, …) and a `sections` manifest — filter on these when assembling context. **Don't use frontmatter `version:` to judge currency** — it lags actual content updates.

## High-value docsets

| Docset | Use for |
|---|---|
| `pro-help` (~1,100 pages) | every script step, function, and feature reference |
| `data-api-guide` / `odata-guide` / `admin-api-guide` | server connectivity (pairs with fm-connections) |
| `app-upgrade-tool-guide` | FMUpgradeTool patch grammar (pairs with fm-patch) |
| `sql-reference` | ExecuteSQL / ProofKit SQL dialect |
| `developer-tool-guide` | FMDeveloperTool (Save-as-XML export) |

Full corpus map, curated AI-feature page list, and mirror recipes: [references/claris-markdown-docs-reference.md](references/claris-markdown-docs-reference.md).
