# Decisions

ADR-style records of durable choices worth retrieving later by topic. **Opt-in** — most projects won't need this folder. Use when a choice is:

- Likely to be questioned later ("why did we pick X?")
- Worth surfacing in onboarding a new teammate
- Architectural or contractual, not tactical

For tactical "why we did this today" reasoning, the session entry is enough — don't write a decision for it.

## File naming

`YYYY-MM-DD-short-topic.md` — e.g. `2026-06-10-odata-for-schema-mutations.md`. The date is when the decision was made.

## Workflow

- Copy [`_template.md`](_template.md) to a new dated file.
- Reference it from the session entry the day you wrote it (so it's discoverable from the timeline too).
- **Don't edit a decision in place** to record a change of mind. Write a new decision that supersedes the old one, link to it, and update the old one's status.

## Why separate from sessions

Sessions are scanned by date — "what happened on June 10?" Decisions are searched by topic — "why did we pick OData?" Burying a durable choice inside a per-day session file makes it findable only by remembering when you made it. Most projects won't hit this need; when they do, this folder exists.
