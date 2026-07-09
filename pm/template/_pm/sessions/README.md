# Sessions

One file per working day, named `YYYY-MM-DD.md`. Captures **what shipped that day** and **the thinking behind it** — tried, learned, decided, pivoted, dead-ended. Single shared log per project: every team member writes to the same daily file via their own Claude session.

This replaces the older `changelog/` pattern. Sessions own both the ledger of shipped work and the narrative of why.

## Workflow

- **Starting a new day:** copy [`_template.md`](_template.md) to `YYYY-MM-DD.md`.
- **End-of-day:** use the `stepping-away` skill — it reads TASKS, today's session (if any), git log, and the conversation, then writes the entry for you. You confirm or correct.
- **Same-commit rule:** when work ships, update `TASKS.md` AND add the entry to today's session file in the **same commit**.
- **Empty days don't need a file.**

## When to also write a decision

If the day produced a durable choice worth retrieving later by topic — "why did we pick OData?", "why is this not a microservice?" — also write an entry in [`../decisions/`](../decisions/). Otherwise the session entry is enough; rationale lives there.

## Why one shared log (not per-milestone, not per-person)

Charlie Bailey's pattern (Codence, Elevate FM 2026). A single coherent narrative survives team handoffs, future-you reading four days later, and milestone transitions. Splitting by milestone or person produces sprawl that nobody reads.

If a milestone needs its own narrative arc (typically a retrospective at the end), that lives in `milestones/M0-name/retro.md` — not a parallel session log.
