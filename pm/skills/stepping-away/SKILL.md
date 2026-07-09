---
name: stepping-away
description: End-of-day ritual that closes the working session — compares today's Intent to what shipped, drafts today's session entry, updates TASKS, optionally writes a decision. Use when the user says "stepping away," "wrapping up," "I'm done for the day," "let's call it," or similar end-of-session signals.
---

# Stepping Away

End-of-day ritual. Capture what happened, compare it to the Intent set this morning, and update project memory so the next session picks up cleanly. **Don't make the user ramble — that's why this skill exists.**

## Checklist

**1. Gather context.** Read:
- `_pm/TASKS.md` — current state
- `_pm/sessions/YYYY-MM-DD.md` for today — especially the Intent block if one was set
- `git log --since=midnight --oneline` (if git repo)
- The conversation since the last stepping-away
- `_pm/skeleton.md` if you need to confirm alignment

**2. Draft (show user before writing).** Update today's session entry with three sections — leave the Intent block from this morning untouched:

- **Shipped** — tight bullets. Files touched by path. Omit if nothing shipped.
- **Tried / Learned / Decided** — narrative. Candid about dead-ends. "Tried X, abandoned because Y" beats silence.
- **Intent vs. outcome** — the drift-catching section. Did we hit the Done-for-today bar? Did we stay inside "Not in scope"? If we crossed it: was that a deliberate pivot or unnoticed drift, and what was the cause? If no Intent was set: note that, suggest setting one tomorrow.

**3. Update `_pm/TASKS.md`.** Move shipped items OUT of Current (they live in the session entry now). Promote Next → Current as warranted (add Why + Done-when). Flag anything in Waiting on that's over a week old.

**4. Decision entry — only if warranted.** A durable choice retrievable by topic? Draft `_pm/decisions/YYYY-MM-DD-<topic>.md`. Most days, skip. Ask before writing.

**5. Sign off.** One short summary: what shipped vs. intended (call out drift), what's queued, anything to surface tomorrow.

## What this skill does NOT do

- Doesn't auto-commit.
- Doesn't touch external ticket systems without asking.
- Doesn't rewrite the Intent to match the outcome — that defeats the purpose. Intent stays as set; outcome is reported honestly against it.
