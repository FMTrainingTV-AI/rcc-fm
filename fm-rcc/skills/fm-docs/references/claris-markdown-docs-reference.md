# Claris Markdown Documentation Reference

Claris publishes its entire help corpus as agent-friendly Markdown alongside the HTML help site, following the [llms.txt convention](https://llmstxt.org). This makes first-party FileMaker documentation directly consumable by Claude Code, MCP tools, RAG pipelines, and any fetch-capable agent — no HTML scraping required.

*Verified June 10, 2026.*

---

## Entry Points

| Resource | URL | Notes |
|---|---|---|
| llms.txt index | https://help.claris.com/llms.txt | ~4 KB orientation file describing the corpus |
| Full page index | https://help.claris.com/llms-full.txt | ~2 MB, enumerates all ~19,300 Markdown pages across 12 locales |
| HTML help home | https://help.claris.com/ | Human-facing site |

## URL Pattern

The Markdown path is **flatter** than the HTML path — no `/content/` segment:

```
HTML:     https://help.claris.com/en/pro-help/content/{topic}.html
Markdown: https://help.claris.com/markdown/en/pro-help/{topic}.md
```

Locale substitution works the same way for both (`/en/`, `/fr-ca/`, `/ja/`, `/de/`, `/es/`, etc. — 12 locales total).

> **Gotcha:** Markdown URLs return a **302 redirect** before resolving. Always follow redirects:
> ```bash
> curl -sL https://help.claris.com/markdown/en/pro-help/generate-response-from-model.md
> ```
> A bad/guessed path redirects to claris.com's 404 page, so check that the response body starts with YAML frontmatter (`---`) rather than `<!DOCTYPE`.

## Page Format

Every page ships with YAML frontmatter that's genuinely useful for indexing and retrieval:

```yaml
---
title: "Generate Response from Model"
topic_type: "script-step-reference"
sections: ["See also", "Options", "Compatibility", "Originated in version",
           "Description", "Notes", "Example 1", "Example 2", "Related topics"]
locale: "en-US"
product: "FileMaker Pro"
doc: "Claris FileMaker Pro Help"
version: 22
version_year: 2025
url: "https://help.claris.com/en/pro-help/content/generate-response-from-model.html"
id: "en/pro-help/generate-response-from-model.md"
keywords: []
---
```

The `topic_type` field (e.g. `script-step-reference`, `function-reference`) and `sections` manifest make these easy to filter and chunk for RAG or context assembly.

---

## English Doc Sets (page counts)

| Doc set | Pages | Markdown root | HTML root |
|---|---:|---|---|
| FileMaker Pro Help | 1,104 | [/markdown/en/pro-help/](https://help.claris.com/markdown/en/pro-help/index.md) | [/en/pro-help/](https://help.claris.com/en/pro-help/content/index.html) |
| FileMaker Server Help | 172 | [/markdown/en/server-help/](https://help.claris.com/markdown/en/server-help/index.md) | [/en/server-help/](https://help.claris.com/en/server-help/content/index.html) |
| Claris Studio Help | 158 | [/markdown/en/studio-help/](https://help.claris.com/markdown/en/studio-help/index.md) | [/en/studio-help/](https://help.claris.com/en/studio-help/content/index.html) |
| Claris Connect Reference | 149 | [/markdown/en/connect-reference/](https://help.claris.com/markdown/en/connect-reference/index.md) | [/en/connect-reference/](https://help.claris.com/en/connect-reference/content/index.html) |
| Server Install & Config Guide | 78 | [/markdown/en/server-installation-configuration-guide/](https://help.claris.com/markdown/en/server-installation-configuration-guide/index.md) | [/en/server-installation-configuration-guide/](https://help.claris.com/en/server-installation-configuration-guide/content/index.html) |
| Claris Connect Help | 72 | [/markdown/en/connect-help/](https://help.claris.com/markdown/en/connect-help/index.md) | [/en/connect-help/](https://help.claris.com/en/connect-help/content/index.html) |
| Security Guide | 60 | [/markdown/en/security-guide/](https://help.claris.com/markdown/en/security-guide/index.md) | [/en/security-guide/](https://help.claris.com/en/security-guide/content/index.html) |
| OData Guide | 57 | [/markdown/en/odata-guide/](https://help.claris.com/markdown/en/odata-guide/index.md) | [/en/odata-guide/](https://help.claris.com/en/odata-guide/content/index.html) |
| Customer Console Help | 57 | [/markdown/en/customer-console-help/](https://help.claris.com/markdown/en/customer-console-help/index.md) | [/en/customer-console-help/](https://help.claris.com/en/customer-console-help/content/index.html) |
| SQL Reference | 42 | [/markdown/en/sql-reference/](https://help.claris.com/markdown/en/sql-reference/index.md) | [/en/sql-reference/](https://help.claris.com/en/sql-reference/content/index.html) |
| WebDirect Guide | 40 | [/markdown/en/webdirect-guide/](https://help.claris.com/markdown/en/webdirect-guide/index.md) | [/en/webdirect-guide/](https://help.claris.com/en/webdirect-guide/content/index.html) |
| Data API Guide | 40 | [/markdown/en/data-api-guide/](https://help.claris.com/markdown/en/data-api-guide/index.md) | [/en/data-api-guide/](https://help.claris.com/en/data-api-guide/content/index.html) |
| FileMaker Cloud Help | 34 | [/markdown/en/cloud-help/](https://help.claris.com/markdown/en/cloud-help/index.md) | [/en/cloud-help/](https://help.claris.com/en/cloud-help/content/index.html) |
| FileMaker Go Help | 29 | [/markdown/en/go-help/](https://help.claris.com/markdown/en/go-help/index.md) | [/en/go-help/](https://help.claris.com/en/go-help/content/index.html) |
| SVG Grammar for Button Icons | 22 | [/markdown/en/pro-svg-grammar-for-button-icons/](https://help.claris.com/markdown/en/pro-svg-grammar-for-button-icons/index.md) | [/en/pro-svg-grammar-for-button-icons/](https://help.claris.com/en/pro-svg-grammar-for-button-icons/content/index.html) |
| Admin API Guide | 20 | [/markdown/en/admin-api-guide/](https://help.claris.com/markdown/en/admin-api-guide/index.md) | [/en/admin-api-guide/](https://help.claris.com/en/admin-api-guide/content/index.html) |
| Pro Network Install Setup Guide | 17 | [/markdown/en/pro-network-install-setup-guide/](https://help.claris.com/markdown/en/pro-network-install-setup-guide/index.md) | [/en/pro-network-install-setup-guide/](https://help.claris.com/en/pro-network-install-setup-guide/content/index.html) |
| Pro Installation Guide | 17 | [/markdown/en/pro-installation-guide/](https://help.claris.com/markdown/en/pro-installation-guide/index.md) | [/en/pro-installation-guide/](https://help.claris.com/en/pro-installation-guide/content/index.html) |
| iOS App SDK Guide | 13 | [/markdown/en/ios-app-sdk-guide/](https://help.claris.com/markdown/en/ios-app-sdk-guide/index.md) | [/en/ios-app-sdk-guide/](https://help.claris.com/en/ios-app-sdk-guide/content/index.html) |
| Claris MCP Help | 11 | [/markdown/en/claris-mcp-help/](https://help.claris.com/markdown/en/claris-mcp-help/index.md) | [/en/claris-mcp-help/](https://help.claris.com/en/claris-mcp-help/content/index.html) |
| App Upgrade Tool Guide | 11 | [/markdown/en/app-upgrade-tool-guide/](https://help.claris.com/markdown/en/app-upgrade-tool-guide/index.md) | [/en/app-upgrade-tool-guide/](https://help.claris.com/en/app-upgrade-tool-guide/content/index.html) |
| Go Development Guide | 9 | [/markdown/en/go-development-guide/](https://help.claris.com/markdown/en/go-development-guide/index.md) | [/en/go-development-guide/](https://help.claris.com/en/go-development-guide/content/index.html) |
| Data Migration Tool Guide | 6 | [/markdown/en/data-migration-tool-guide/](https://help.claris.com/markdown/en/data-migration-tool-guide/index.md) | [/en/data-migration-tool-guide/](https://help.claris.com/en/data-migration-tool-guide/content/index.html) |
| Developer Tool Guide | 5 | [/markdown/en/developer-tool-guide/](https://help.claris.com/markdown/en/developer-tool-guide/index.md) | [/en/developer-tool-guide/](https://help.claris.com/en/developer-tool-guide/content/index.html) |
| Release Notes (Pro/Server/Go/Cloud/Connect) | 1 each | e.g. [/markdown/en/pro-release-notes/](https://help.claris.com/markdown/en/pro-release-notes/index.md) | [/en/pro-release-notes/](https://help.claris.com/en/pro-release-notes/content/index.html) |

---

## Curated: AI Script Steps & Functions (Pro Help)

The high-value pages for AI/agent development work, all in Markdown:

### Overviews

- [Artificial intelligence script steps](https://help.claris.com/markdown/en/pro-help/artificial-intelligence-script-steps.md)
- [Artificial intelligence functions](https://help.claris.com/markdown/en/pro-help/artificial-intelligence-functions.md)

### Setup & Configuration

- [Configure AI Account](https://help.claris.com/markdown/en/pro-help/configure-ai-account.md)
- [Configure Prompt Template](https://help.claris.com/markdown/en/pro-help/configure-prompt-template.md)
- [Configure RAG Account](https://help.claris.com/markdown/en/pro-help/configure-rag-account.md)
- [Configure Regression Model](https://help.claris.com/markdown/en/pro-help/configure-regression-model.md)
- [Set AI Call Logging](https://help.claris.com/markdown/en/pro-help/set-ai-call-logging.md)

### Generation & Natural Language

- [Generate Response from Model](https://help.claris.com/markdown/en/pro-help/generate-response-from-model.md) — agentic mode, tool calls, conversation memory
- [Perform SQL Query by Natural Language](https://help.claris.com/markdown/en/pro-help/perform-sql-query-by-natural-language.md)
- [Perform Find by Natural Language](https://help.claris.com/markdown/en/pro-help/perform-find-by-natural-language.md)

### Embeddings & Semantic Search

- [Insert Embedding](https://help.claris.com/markdown/en/pro-help/insert-embedding.md)
- [Insert Embedding in Found Set](https://help.claris.com/markdown/en/pro-help/insert-embedding-in-found-set.md)
- [Perform Semantic Find](https://help.claris.com/markdown/en/pro-help/perform-semantic-find.md)
- [GetEmbedding](https://help.claris.com/markdown/en/pro-help/getembedding.md)
- [GetEmbeddingAsFile](https://help.claris.com/markdown/en/pro-help/getembeddingasfile.md)
- [GetEmbeddingAsText](https://help.claris.com/markdown/en/pro-help/getembeddingastext.md)
- [CosineSimilarity](https://help.claris.com/markdown/en/pro-help/cosinesimilarity.md)
- [NormalizeEmbedding](https://help.claris.com/markdown/en/pro-help/normalizeembedding.md)
- [AddEmbeddings](https://help.claris.com/markdown/en/pro-help/addembeddings.md)
- [SubtractEmbeddings](https://help.claris.com/markdown/en/pro-help/subtractembeddings.md)

### RAG & Fine-Tuning

- [Perform RAG Action](https://help.claris.com/markdown/en/pro-help/perform-rag-action.md)
- [GetRAGSpaceInfo](https://help.claris.com/markdown/en/pro-help/getragspaceinfo.md)
- [Fine-Tune Model](https://help.claris.com/markdown/en/pro-help/fine-tune-model.md)
- [Save Records as JSONL](https://help.claris.com/markdown/en/pro-help/save-records-as-jsonl.md)

### Schema & Utility

- [GetTableDDL](https://help.claris.com/markdown/en/pro-help/gettableddl.md) — schema as DDL for AI context
- [GetTextFromPDF](https://help.claris.com/markdown/en/pro-help/gettextfrompdf.md)
- [GetTokenCount](https://help.claris.com/markdown/en/pro-help/gettokencount.md)

## Curated: Claris MCP Help

- [Introduction to Claris MCP](https://help.claris.com/markdown/en/claris-mcp-help/index.md)
- [Getting started](https://help.claris.com/markdown/en/claris-mcp-help/getting-started.md)
- [Claude Desktop setup](https://help.claris.com/markdown/en/claris-mcp-help/claude-desktop.md)
- [Tools guide](https://help.claris.com/markdown/en/claris-mcp-help/tools-guide.md)
- [Working with connections](https://help.claris.com/markdown/en/claris-mcp-help/working-with-connections.md)
- [Managing connections](https://help.claris.com/markdown/en/claris-mcp-help/managing-connections.md)
- [Configuring your integration](https://help.claris.com/markdown/en/claris-mcp-help/integration-configuration.md)
- [Best practices](https://help.claris.com/markdown/en/claris-mcp-help/best-practices.md)
- [Troubleshooting and common issues](https://help.claris.com/markdown/en/claris-mcp-help/troubleshooting-common-issues.md)
- [Additional resources](https://help.claris.com/markdown/en/claris-mcp-help/additional-resources.md)

---

## Practical Recipes

### Mirror a doc set locally (e.g. for a Claude Code context folder)

```bash
# Pull the index, extract pro-help markdown URLs, download each
curl -s https://help.claris.com/llms-full.txt \
  | grep -oP 'https://help\.claris\.com/markdown/en/pro-help/[a-z0-9.-]+\.md' \
  | sort -u \
  | while read url; do
      fname=$(basename "$url")
      curl -sL "$url" -o "claris-docs/pro-help/$fname"
      sleep 0.2   # be polite
    done
```

Swap `pro-help` for `data-api-guide`, `sql-reference`, `claris-mcp-help`, etc. to grab other sets. A curated AI subset (~30 pages above) is small enough to drop wholesale into a project context folder or an AI Enablement Kit.

### Point an agent at docs on demand

In a `CLAUDE.md` / agent instructions file:

```
FileMaker documentation is available as Markdown at:
  https://help.claris.com/markdown/en/pro-help/{topic}.md
Index of all pages: https://help.claris.com/llms-full.txt
Follow redirects when fetching (curl -L). Frontmatter includes
topic_type, product, and version for filtering.
```

### Verify a fetched page is real (not a 404 redirect)

```bash
body=$(curl -sL "$url")
[[ "$body" == ---* ]] && echo "valid markdown" || echo "bad path (404 redirect)"
```

---

## Notes & Caveats

- **Version currency:** Content updated for FileMaker 2026 (the release notes carry a full "FileMaker Pro 2026 / Version 26.0.1 – June 2026" section and new FM 26 pages like `insert-image-caption.md` exist), but frontmatter still reports `version: 22 / version_year: 2025` as of June 10, 2026 — don't use frontmatter version to judge currency. Re-pull any local mirrors now that 2026 content is live.
- **llms-full.txt is the authoritative index.** Don't guess slugs; the Markdown filenames don't always match the HTML filenames (e.g. HTML has `/content/` paths and occasionally different slugs).
- **Redirect behavior:** every `.md` URL 302s once before serving; invalid paths 302 to `https://www.claris.com/error/404.html`.
- **Locales:** en, ja, fr, fr-ca, de, es, it, nl, pt, sv, ko, zh — not every doc set exists in every locale; llms-full.txt is the per-locale source of truth.
- **Release notes** are single-page-per-product in the Markdown corpus (e.g. `pro-release-notes/index.md` contains the full rolling release notes).
