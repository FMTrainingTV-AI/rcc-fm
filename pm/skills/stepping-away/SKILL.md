---
name: stepping-away
description: Session close — compares this session's Intent to what shipped, writes the session entry, closes or comments the tickets that moved, optionally writes an ADR. Use when the user says "stepping away," "wrapping up," "let's close this session out," "starting a fresh session," "I'm done for the day," "let's call it," or similar end-of-session signals.
---

# Stepping Away

Session close. Capture what happened, compare it to the Intent set at the open, and update project memory so the next session — later today, tomorrow, or someone else's — picks up cleanly. **Don't make the user ramble — that's why this skill exists.**

Closing a session is not the same as closing the day. Most sessions end with another one to follow; write the entry so whoever opens next inherits a clean handoff either way.

## Checklist

**1. Gather context.** Read:
- This session's file, `_pm/sessions/YYYY-MM-DD-<name>[-N].md` — especially the Intent block set at the open. If several exist for today, take the highest ordinal; that's the live one.
- The tracker: tickets claimed by this person (wayfinder or implementation) — what moved this session
- `git log --since=<session start> --oneline` (if git repo; fall back to `--since=midnight` when the start time isn't known)
- The conversation since the last stepping-away
- `_pm/skeleton.md` if you need to confirm alignment

**2. Draft (show user before writing).** Update this session's entry with three sections — leave the Intent block from the open untouched:

- **Shipped** — tight bullets. Files touched by path. Omit if nothing shipped.
- **Tried / Learned / Decided** — narrative. Candid about dead-ends. "Tried X, abandoned because Y" beats silence.
- **Intent vs. outcome** — the drift-catching section. Did we hit the done-for-this-session bar? Did we stay inside "Not in scope"? If we crossed it: was that a deliberate pivot or unnoticed drift, and what was the cause? If a `checkpoint` **re-aim** exists, compare against the *latest re-aim* and treat the pivot as deliberate — the re-aim line is its record; note "original → re-aimed" in one clause. If no Intent was set: note that, suggest setting one at the next open.

**3. Settle the tracker.** A wayfinder ticket resolved this session: post the resolution comment, close it, add its line to the map's *Decisions so far* (if the session didn't already). An implementation ticket finished: close it with a link to the commit/PR. Still in flight: one comment with where it stands, so a teammate (or next-session-you) can take it. Unclaim anything you won't continue — including work you'll return to in a later session today, if someone else could pick it up first. **Ask before touching a tracker you don't own.** (Legacy `_pm/TASKS.md`: don't update it — if something on it shipped, note that in the session entry and move the rest to the tracker when convenient.)

**4. Knowledge log — only if the bundle changed.** If `knowledge/` exists and concepts changed this session, append a dated entry to the bundle's `log.md`. Skip if the bundle doesn't keep one — flat one-screen bundles usually don't. Format per the `okf` skill.

**5. Shared-library check — only if something durable surfaced.** If the machine's global instructions (`~/.claude/CLAUDE.md`) name shared knowledge libraries (a domain wiki, a craft library), ask: did this session produce knowledge that belongs *beyond this project*? Route it as those instructions direct — domain facts through the domain library's ingest flow; reusable, client-agnostic craft to the craft library (or its flag mechanism, when this machine can't write to it directly). Project-only knowledge stays here (quirks, sessions, `knowledge/`). Most sessions nothing travels — skip. No libraries named on this machine: skip.

**6. ADR — only if warranted.** A durable choice retrievable by topic, not already recorded on a closed wayfinder ticket? Draft it in `docs/adr/` (Matt's `/domain-modeling` format). Most sessions, skip. Ask before writing.

**7. Push the log.** In a team repo, the session file is how the next person sees this stretch of work: offer to commit `_pm/sessions/YYYY-MM-DD-<name>[-N].md` (and any `docs/` edits) and push the branch. Solo: offer, don't insist.

**8. Sign off.** One short summary: what shipped vs. intended (call out drift), what's queued on the tracker, and the one or two threads the next session should open on.

## What this skill does NOT do

- Doesn't auto-commit — offers.
- Doesn't close or comment tickets on a tracker the user doesn't own without asking.
- Doesn't maintain `_pm/TASKS.md`, `_pm/decisions/`, or `_pm/context-map.md` — those are pre-0.8 (see `MIGRATION-0.8.md`).
- Doesn't rewrite the Intent to match the outcome — that defeats the purpose. Intent stays as set; outcome is reported honestly against it.
- Doesn't fold several sessions into one entry, or reopen a closed session's file. Each session gets its own; the next open starts a new one.
