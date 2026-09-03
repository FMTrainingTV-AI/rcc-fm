---
name: whats-next
description: Session open — propose 1-2 things to pick up AND draft this session's Intent block (the agent's anchor while it works). Use when the user says "what's next?", "what should I work on?", "where did we leave off?", "catch me up," or starts a session cold without a specific task in mind.
---

# What's Next

Session open. The user is starting a session — could be the second one today after closing a full thread, future-them four days later, or a teammate cold-starting. Ground the answer in context, not vibes, and **draft an Intent block** they can paste into this session's entry to keep the agent oriented during execution.

**Don't ask "what do you want to work on?"** That's what they're asking *you*. Read first, then propose.

## Checklist

**1. Read.** Shared record first, personal log second (`SDLC.md`: `docs/` is truth, `_pm/` is log).
- `docs/intent/*.md` — every open intent (status draft/accepted): these are the streams of work. Note each one's size call.
- **The tracker** — the frontier: open wayfinder tickets (unblocked, unclaimed) and open implementation tickets. GitHub: `gh issue list --label wayfinder:map`, then children; local: `.scratch/<name>/`. Unreachable → say so, go on with local artifacts.
- `docs/adr/` newest entries, `CONTEXT.md` if present — what's been decided.
- `_pm/skeleton.md` — the macro why of the project.
- Last 1–3 session files in `_pm/sessions/` (any author, most recent first) — especially Open threads and the previous session's Intent-vs-outcome. The immediately preceding session may be earlier the same day; read it as the live handoff.
- `knowledge/index.md` — only if a knowledge bundle exists. Skim; don't crawl.
- **Legacy (pre-0.8 projects only):** if `_pm/TASKS.md` exists, read it as a hint, not a source of truth — anything on it that matters belongs on the tracker. Don't grow it. See `MIGRATION-0.8.md`.

**2. Propose.** Output:

```
Where we are: <one sentence — which streams exist and what stage each is at>.
Frontier: <takeable tickets, or "nothing charted yet">.
Recommended pick-up: <one specific ticket / next stage step> — because <reason tied to context>.
Also worth: <maybe one more>.
Watch-outs: <claimed tickets gone quiet; open threads worth surfacing; an intent still in draft>.
```

**3. Draft the Intent block** for the most likely pick-up. Two or three sentences of plain prose — what we're pushing on, why it matters, what done-for-this-session looks like, anything explicitly not in scope. Scope it to one session's worth of work, not a whole day's. Example:

> Pushing on the search filter UI — Sandy's manual workaround is costing her ~20 min/day, and a working filter unlocks the rest of the search flow. Done for this session is the prototype validated by Sandy. Not touching filter persistence or multi-category yet.

**4. Wait.** Don't start the work. The user picks AND confirms (or amends) the Intent. It's their commitment for this session.

**5. Write.** Once approved, write the Intent block into this session's file in `_pm/sessions/`:

- **One file per session, per person.** The day's first session is `YYYY-MM-DD-<name>.md`; each later session that day appends an ordinal — `YYYY-MM-DD-<name>-2.md`, `-3.md`, and so on. Check what already exists for today and take the next free number. (`<name>` = the user's short handle; ask once if unknown, then remember it in the project `CLAUDE.md`.)
- Per person, so two people on the same day never collide; per session, so each Intent gets its own close and its own Intent-vs-outcome.
- Create from `_pm/sessions/_template.md` if needed. Shipped / Tried-Learned-Decided sections stay empty until the session closes.

If the stream's wayfinder ticket is what's being picked up, **claim it on the tracker** (assign to self) — the assignee is the claim.

## When the project has no history

Brand-new project: propose drafting the skeleton (if still placeholder), or running `discovery` on the first piece of work so there's an intent to stand on. Still draft an Intent block — the push this session IS "draft the skeleton" or "discover the first stream."

## Why this skill matters

> "These systems were built to execute. They nail the *what* and quietly let the *why* go." — Matt Maher

The Intent block is this session's why, written where the agent reads it on every tool call. Without it, the agent has the queue but no orientation.
