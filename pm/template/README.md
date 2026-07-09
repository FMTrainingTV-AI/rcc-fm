# datacraft-Project

Project-management starter for client engagements. Light by default; scales up via opt-in `milestones/` when warranted.

## Quick start

1. Rename this folder: `datacraft-Project/` → `datacraft-<ProjectOrClientName>/` (e.g., `datacraft-Acme`). The capital `P` is a placeholder slot.
2. Fill in `_pm/skeleton.md` — even a paragraph is fine to start.
3. Drop transcripts, customer docs, exports into `_pm/artifacts/` as they arrive.
4. Add tasks to `_pm/TASKS.md` as work surfaces.
5. End each working day with the `stepping-away` skill (it writes today's session entry and updates TASKS).

For the full picture — folder layout, the four skills, companion mode for code projects — read `CLAUDE.md`.

## Design rationale

The "why this looks this way" reference: `docs/_design/2026-06-06-starter-design.html`. Open it in a browser.

Built from two transcripts at Elevate FM 2026: Charlie Bailey (Codence) on AI-PM operations, and Wei Hao (Direct Impact Solutions) on Magic-the-Gathering-style scope control. Both lived in this starter's design conversation.

## Sibling starters

- `../datacraft-fm/` — FileMaker development projects
- `../datacraft-web/` — single-site web projects
- `../datacraft-sass/` — SaaS workspaces (multi-repo)
- `../datacraft-agent/` — agent-framework projects
- `../task-changelog/` — canonical task + session scaffolding (copied verbatim into each starter's `docs/`)
