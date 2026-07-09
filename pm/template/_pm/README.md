# _pm/ — project management

Everything operational to managing the engagement lives here. Outside this folder, `docs/` is for meta and Claude-generated catch-all (notes, quirks, design history); `resources/` holds material you bring in from outside.

The `_` prefix groups this folder visually at the top of the directory listing and signals "container, not a working folder." Matches Joe's `_app/`/`_ws/` convention in `datacraft-sass`.

## What's inside

| Folder/file | Purpose |
|---|---|
| `skeleton.md` | The macro why — Wei Hao's 5-step structure. Project's planning artifact. Always populated, even if just a paragraph. |
| `TASKS.md` | Current / Next / Waiting on / Backlog. Current items carry one-line Why + Done-when. |
| `sessions/` | Per-day files capturing what shipped AND the thinking behind it. Replaces the older `changelog/` pattern. |
| `decisions/` | Opt-in ADRs for durable choices retrievable by topic. Most projects skip this. |
| `milestones/` | Opt-in expansion when path to skeleton is long. Empty unless sprouted. |
| `requirements/` | User stories, personas, parrot-back validation bundles. Generated from artifacts. |
| `artifacts/` | Raw inputs — transcripts, customer docs, exports, recordings. |
| `prototypes/` | HTML mockups for customer validation. |
| `deliverables/` | What you hand to the client — reports, dashboards. |
| `bridges/` | Manual Claude ↔ ChatGPT PII shuttle (inbox/outbox). |

## How agents use `_pm/`

The two project-local skills in `.claude/skills/` read and write here:

- **`whats-next`** (start of day) reads `_pm/skeleton.md`, `_pm/sessions/`, `_pm/TASKS.md`, `_pm/decisions/`. Drafts today's Intent block into today's session file.
- **`stepping-away`** (end of day) reads the same set plus the conversation. Updates `_pm/TASKS.md` and writes today's `_pm/sessions/YYYY-MM-DD.md` with Shipped / Tried-Learned-Decided / Intent-vs-outcome.

For the active-intent loop and the broader conventions, see the root `CLAUDE.md`.

## Companion mode — dropping `_pm/` into another starter

`_pm/` is **portable**. To add the engagement-management layer to a code starter (e.g., `datacraft-Project-FM` for a FileMaker engagement), drop this whole folder in alongside the code folders. No path changes needed inside — all references are local to `_pm/` or reach up to the shared `../docs/` and `../resources/` which exist in every starter.
