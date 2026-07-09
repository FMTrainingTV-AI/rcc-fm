# Milestones — opt-in

**This folder is empty by default.** Sprout milestone subfolders only when the path from "starting" to "skeleton fulfilled" is too long to track in a single `../TASKS.md`.

For a change-request job: don't use milestones. Tasks live in `TASKS.md`, sessions track the work, done.

For a six-month fixed-bid: do use milestones. Each one is a scoped slice of the skeleton with its own success criteria and verification plan.

## How to sprout one

1. Copy `_template-milestone/` to `M0-<short-name>/` (e.g. `M0-discovery`, `M1-build`, `M2-launch`).
2. Fill in `spec.md` — what this milestone delivers, scoped from the skeleton.
3. Fill in `success-criteria.md` — how the customer (and you) know it's done.
4. Fill in `verification.md` — how it gets tested.
5. Tasks for this milestone can live in milestone-scoped section of TASKS.md OR in a `tasks.md` inside the milestone folder. Pick one per project and stick with it.

## What lives where during a milestone

- **Daily work:** `../sessions/` (always the unified project log — sessions never split by milestone)
- **Milestone-specific narrative (typically retrospective):** `M0-name/retro.md`, written at milestone close
- **Decisions made during the milestone:** `../decisions/` if durable, otherwise just in the session entries

## File naming

`M<n>-<short-name>/` — zero-indexed numbering. `M0-discovery`, `M1-build`, `M2-launch`. Short hyphenated names. The number gives ordering; the name gives meaning.
