---
name: okf
description: OKF (Open Knowledge Format) conventions for knowledge/ bundles — concept frontmatter, bundle-relative links, index.md/log.md, sprouting, quirk promotion. Use when creating or editing files in a knowledge/ folder, writing entity docs (tables, systems, endpoints, processes), deciding whether to sprout a knowledge bundle, appending a bundle log entry, or when the user mentions OKF, knowledge bundle, concept files, or a project knowledge base.
---

# OKF — knowledge bundle conventions

Reference skill, not a ritual. This is the single source of truth for how project knowledge is shaped everywhere OKF is used — client projects, domain builders, anywhere a `knowledge/` folder exists. The project's CLAUDE.md owns the *local* rules (when to sprout, what feeds the bundle); this skill owns the *format*.

Spec: [OKF v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — markdown + YAML frontmatter, no required tooling, permissive by design.

## The minimal profile

- **A concept is one `.md` file** with YAML frontmatter. Only `type:` is required. `title` and `description` are recommended; `resource:` (canonical URI) when the concept describes a real asset; `tags` and `timestamp` when useful. Never add frontmatter beyond need.
- **The bundle root is the `knowledge/` folder.** Cross-links are bundle-relative (`/tables/customers.md`), resolved from that root. Broken links are legal — they mark not-yet-written knowledge, so don't "fix" them by deleting.
- **Start flat.** Subdirectories, `index.md`, and `log.md` arrive only when the bundle outgrows one screen. A conformant bundle can be a single file.
- **`index.md` and `log.md` are reserved names** — never concepts. Index = grouped link list with one-line descriptions (progressive disclosure: read this before crawling). Log = dated history, newest first.
- **Taxonomy is the producer's.** Pick `type:` values that are self-explanatory (`FileMaker Table`, `API Endpoint`, `Playbook`, `Metric`, `Reference`); tolerate unknown types when reading.

## Concept template

```markdown
---
type: FileMaker Table
title: Customers
description: One row per client company; hub of the CRM graph.
resource: fmp://server/File.fmp12 (or URL — omit for abstract concepts)
---

# Schema
| Field | Type | Notes |
|---|---|---|
| id | Text | UUID, set on create |

Joined to [invoices](/tables/invoices.md) on `customer_id`.

# Citations
[1] [DDR export 2026-07-01](../_pm/artifacts/exports/ddr-2026-07-01.xml)
```

Favor structural markdown (tables, lists, fenced code) over prose. Conventional headings when applicable: `# Schema`, `# Examples`, `# Citations`.

## Writing into a bundle

- **Skim `index.md` first** (if present) — don't crawl the tree.
- **One entity, one concept.** If a fact spans entities, it lives on the entity it's *about* and links to the others.
- **Cite raw sources** (`# Citations`) instead of copying them in — raw material stays in `resources/`, `_pm/artifacts/`, or wherever the project keeps it.
- **Promotion move:** when a quirk/note has proven durable and entity-shaped, move its content into a concept (create or extend), leave no copy behind, and cite the origin if it matters.
- **If the bundle keeps a `log.md`**, append when concepts meaningfully change:

```markdown
## 2026-07-13
* **Update**: Added join notes to [Customers](/tables/customers.md).
* **Creation**: New [invoicing playbook](/playbooks/invoicing.md).
```

## Don't

- Don't sprout a bundle from this skill — sprouting is the project's call (its CLAUDE.md has the tripwire). Absent local rules: entity-shaped facts recurring across sessions, a catalog as deliverable, or a second consumer.
- Don't force narrative files (sessions, TASKS, scratch notes) into OKF. Narrative stays narrative.
- Don't build tooling: no conformance linting (the spec mandates permissive consumption), no index auto-generation ceremony (synthesize a listing on the fly when none exists), no frontmatter schemas beyond `type:`.
