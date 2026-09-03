---
name: checkpoint
description: Mid-session re-aim, for sessions too long or too costly to simply close and restart — a long wayfinder charting run, a background task about to continue on a stale brief, a session whose direction changed but whose context is expensive to rebuild. Fires when a consequential result lands, or when the user says "checkpoint", "re-aim", "refresh the state", "update the intent before we keep going". NOT the session open (whats-next) and NOT the session close (stepping-away) — and not needed at all in a short session, where closing and reopening does the same job better.
---

# Checkpoint

**Try the session boundary first.** The natural re-aim is `stepping-away` followed by `whats-next`: the correction lands in a closed session entry, the next session opens on a clean Intent, and the model starts fresh instead of carrying a stale brief through a long thread. In a workflow of short sessions, that is the whole answer and this skill has nothing to add.

This skill is for when you can't take that boundary: a wayfinder charting run mid-flight, a long-running task that will continue whether or not you re-aim it, context too expensive to rebuild. There, the opening brief ages while the work teaches you what the job actually is, and the correction has to reach the work that hasn't happened yet instead of dying in conversation. Done when the state **describes the present rather than narrating how we got here**.

## Checklist

**1. Name what changed.** One sentence: which assumption, direction, or result made the current state stale. **If nothing consequential changed, say so and stop** — this ritual run on noise is how state files rot. **If the session could simply close here, say that instead** and hand off to `stepping-away`.

**2. Re-aim the Intent — don't overwrite it.** In this session's file, `_pm/sessions/YYYY-MM-DD-<name>[-N].md`, leave the original Intent block as written (stepping-away's drift check needs it) and **append** a dated re-aim line beneath it — earlier re-aims stay; the session file is append-only:

> **Re-aimed 14:30:** evidence X replaces the buyer assumption — done for this session is now Y; Z drops out of scope.

The latest re-aim is the live aim; the opening Intent and any earlier re-aims stay as the record of how the session moved.

**3. Push the change into unfinished work — on the tracker.** The change may invalidate an open ticket's premise, graduate a patch of fog into a ticket, or re-scope the map. Comment on the affected tickets (or update the local `.scratch/` map) so the next session inherits the correction; if the intent itself changed, edit `docs/intent/<slug>.md` and say so. Name what you touched. (Legacy `_pm/TASKS.md`: don't maintain it — move anything live to the tracker.)

**4. Archive, don't delete.** A replaced decision that still explains the project gets a `docs/adr/` entry (status: superseded, linked both ways — `/domain-modeling` owns the format) or a line in this session's Tried / Learned / Decided. Preserve hard constraints exactly; don't let a preference quietly harden into a rule — or a rule soften into a preference.

**5. Show before writing.** Short before/after of the re-aim and any ticket comments. Then write.

## What this skill does NOT do

- Doesn't open the session (`whats-next`) or close it (`stepping-away`) — and doesn't compete with them. A session short enough to close should close.
- Doesn't rewrite the session's opening Intent in place — the re-aim line *is* the deliberate-pivot record; erasing the original hides drift.
- Doesn't append a diary. A re-aim is one line; detail goes to the tickets. Keep the file scannable.
- Doesn't auto-commit.
