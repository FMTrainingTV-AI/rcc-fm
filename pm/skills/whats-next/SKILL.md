---
name: whats-next
description: Morning open — propose 1-2 things to pick up AND draft today's Intent block (the agent's anchor for the day). Use when the user says "what's next?", "what should I work on?", "where did we leave off?", "catch me up," or starts a session cold without a specific task in mind.
---

# What's Next

Morning open. The user is starting a session — could be future-them four days later, or a teammate cold-starting. Ground the answer in context, not vibes, and **draft an Intent block** they can paste into today's session entry to keep the agent oriented during execution.

**Don't ask "what do you want to work on?"** That's what they're asking *you*. Read first, then propose.

## Checklist

**1. Read.**
- `_pm/skeleton.md` — the macro why of the project
- Last 1–3 session files in `_pm/sessions/` (most recent first) — especially Open threads
- `_pm/TASKS.md` — Current (with Why / Done-when), Next, Waiting on
- Most recent `_pm/decisions/` (if any)

**2. Propose.** Output:

```
Where we are: <one sentence>.
Active: <Current items if any, with their Why>.
Recommended pick-up: <one specific thing> — because <reason tied to context>.
Also worth: <maybe one more>.
Watch-outs: <Waiting on items rotting; open threads worth surfacing>.
```

**3. Draft the Intent block** for the most likely pick-up. Two or three sentences of plain prose — what we're pushing on, why it matters, what done-for-today looks like, anything explicitly not in scope. Example:

> Pushing on the search filter UI today — Sandy's manual workaround is costing her ~20 min/day, and a working filter unlocks the rest of the search flow. Done-for-today is the prototype validated by Sandy via parrot-back. Not touching filter persistence or multi-category yet.

**4. Wait.** Don't start the work. The user picks AND confirms (or amends) the Intent. It's their commitment for the day.

**5. Write.** Once approved, write the Intent block into today's `_pm/sessions/YYYY-MM-DD.md` (create from `_pm/sessions/_template.md` if needed). Shipped / Tried-Learned-Decided sections stay empty until end-of-day.

## When the project has no history

Brand-new project: propose drafting the skeleton (if still placeholder) or distilling the most recent transcript in `_pm/artifacts/transcripts/` into user stories. Still draft an Intent block — the push that day IS "draft the skeleton" or "distill the discovery call."

## Why this skill matters

> "These systems were built to execute. They nail the *what* and quietly let the *why* go." — Matt Maher

The Intent block is the why-of-the-day, written where the agent reads it on every tool call. Without it, the agent has the queue but no orientation.
