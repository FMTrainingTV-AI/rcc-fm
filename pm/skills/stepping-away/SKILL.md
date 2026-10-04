---
name: stepping-away
description: Session close — compares this session's Intent to what shipped, writes the session entry, closes or comments the tickets that moved, optionally writes an ADR. Use when the user says "stepping away," "wrapping up," "let's close this session out," "starting a fresh session," "I'm done for the day," "let's call it," or similar end-of-session signals.
---

# Stepping Away

Session close. Capture what happened, compare it to the Intent set at the open, and update project memory so the next session — later today, tomorrow, or someone else's — picks up cleanly. **Don't make the user ramble — that's why this skill exists.**

Closing a session is not the same as closing the day. Most sessions end with another one to follow; write the entry so whoever opens next inherits a clean handoff either way.

Closing a session is also not the same as stopping background work. **Closing this chat neither stops a running background job nor schedules anything to run later** — never claim it does. A job that is active stays active under its own control: pause it through its own controls and report it paused only once they confirm it. Record in the entry whether each active job was left running, paused (verified), or stopped.

**Use existing authorization.** An explicit request to close this session authorizes
routine local close-out:
write the session entry and authorized tracker updates, then report them. The
show-before-writing steps below apply only where that authorization is missing.
Shared pushes, client messages, production and trackers the user doesn't own
still need their own applicable permission; reuse it when already granted.

## Checklist

**1. Gather context.** Read:
- This session's file, `_pm/sessions/YYYY-MM-DD-<name>[-N].md` — especially the Intent block set at the open. Use the exact path and Session-ID retained at session open or in the handoff summary; never choose the highest ordinal. Recover a lost binding from conversation context, or ask once if ambiguous. If no session was opened, allocate a new record with the context-derived Intent marked retrospective. Read the latest re-aim and reconcile it with docs/tracker.
- The tracker (`docs/TASKS.md` unless `CLAUDE.md` names another): items this person claimed — what moved this session
- `git log --since=<session start> --oneline` (if git repo; fall back to `--since=midnight` when the start time isn't known)
- The conversation since the last stepping-away
- `_pm/skeleton.md` if you need to confirm alignment

**2. Write under existing close-out permission** and report what was written;
otherwise show the draft first. Update this session's entry with three sections
— leave the Intent block from the open untouched:

- **Shipped** — tight bullets. Files touched by path. Omit if nothing shipped.
- **Tried / Learned / Decided** — narrative. Candid about dead-ends. "Tried X, abandoned because Y" beats silence.
- **Intent vs. outcome** — the drift-catching section. Did we hit the done-for-this-session bar? Did we stay inside "Not in scope"? If we crossed it: was that a deliberate pivot or unnoticed drift, and what was the cause? If a `checkpoint` **re-aim** exists, compare against the *latest re-aim* and treat the pivot as deliberate — the re-aim line is its record; note "original → re-aimed" in one clause. If no Intent was set: note that, suggest setting one at the next open.

**3. Settle the tracker.** In `docs/TASKS.md`: move each item verified done this session to **Done** with the date and its evidence (commit, PR, or the check that proved it); leave in-flight items in **Current** with one line on where they stand; move anything you won't continue back to **Next** so someone else can take it; add new work that surfaced to **Next** after matching it against what's already listed (step 3a). On a ticket tracker the project's `CLAUDE.md` names instead, do the equivalent: close verified tickets with evidence, comment on in-flight ones, unclaim what you won't continue. **Never restatus an item an active background job owns** — closing this chat doesn't end that job; note it in the entry. **Ask before touching a tracker you don't own.** An item that gained a question this session gets `Waiting on:` (who, what, since when); a wait that was answered gets its answer recorded and the note removed.

**3a. Capture loose asks — match first.** Anything that surfaced this session and is not a ticket or an intent (a client's someday idea, an ask nobody shaped, a question with no work behind it yet) is offered for capture. **Before adding a line, match it** against `docs/intent/inbox.md`, open intents, and the tracker — by subject, not wording. A repeat adds its date and source to the item that already holds it (an extra `· re-raised YYYY-MM-DD <source>` on the inbox line, or a note on the tracker item), never a second line. A genuinely new ask becomes one inbox line: `- YYYY-MM-DD · <source> · <the ask>`, in client-safe words. A question that needs an answer from someone before work can move is a tracker item with `Waiting on:`, not an inbox line. Retiring an inbox line (moot, merged, declined) **deletes it from the file**; the reason goes in this entry under Tried / Learned / Decided — the session log is the append-only record, the inbox is not.

**3b. Client face — only if `docs/agents/client-face.md` exists.** Read it. It names where the close-out steps are, what evidence they consume, and what to do for fully shipped, partly shipped, and ticketless changes ([client-face-contract.md](./client-face-contract.md)). For each item that moved this session, quote the matching step and offer it; record in this entry whether it was done, skipped, or blocked. No file → say nothing about a client face. pm never names the tool.

**4. Knowledge log — only if the bundle changed.** If `knowledge/` exists and concepts changed this session, append a dated entry to the bundle's `log.md`. Skip if the bundle doesn't keep one — flat one-screen bundles usually don't. Format per the `okf` skill.

**5. Shared-library check — only if something durable surfaced.** If the machine's global instructions (`~/.claude/CLAUDE.md`) name shared knowledge libraries (a domain wiki, a craft library), ask: did this session produce knowledge that belongs *beyond this project*? Route it as those instructions direct — domain facts through the domain library's ingest flow; reusable, client-agnostic craft to the craft library (or its flag mechanism, when this machine can't write to it directly). Project-only knowledge stays here (quirks, sessions, `knowledge/`). Most sessions nothing travels — skip. No libraries named on this machine: skip.

   **The bar for "durable":** if this note vanished, would the next engineer reading the finished code, tests, and docs repeat the mistake or redo the investigation? If not, write nothing — the code already carries it. Effort spent and diff size don't qualify a lesson; only non-obvious reasoning that the artifacts don't show does. (Borrowed from Compound Engineering's `ce-compound` counterfactual, 2026-09-06.)

**6. ADR — only if warranted.** A durable choice retrievable by topic, not already recorded elsewhere? Record it in `docs/adr/` under existing local documentation permission; otherwise show the draft. Most sessions, skip.

**7. Finish the session record.** Settle authorized tracker updates first; on a partial retry check for existing resolution comments before repeating them. Write the three drafted sections into an entry text file, then close the bound session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session.py" --root . close --session <bound-path> --id <bound-id> --entry-file <entry-text-file>
```

The helper checks identity, locks the file locally, appends the entry, and writes `Closed: <timestamp>` last. A repeat reports `already-closed` without rewriting. A legacy session explicitly identified by the user can be closed manually: preserve its Intent, append missing content, then the same marker; never infer closure just from filled headings. Record actual unresolved work as open threads before closing.

**8. Push the log.** In a team repo, the session file is how the next person sees this stretch of work: offer to commit `_pm/sessions/YYYY-MM-DD-<name>[-N].md` (and any `docs/` edits) and push the branch. Solo: offer, don't insist.

Existing permission for these commits/pushes settles the offer; do not ask again.
Keep the close concise: outcome, evidence links, essential decisions, real
blockers and next ready work.

**9. Sign off.** One short summary: what shipped vs. intended (call out drift), what's queued on the tracker, and the one or two threads the next session should open on.

**10. Offer the next session.** If ready work remains, offer to open a fresh session for it. (Several independent tickets to run at once is the [sibling-sessions](../sibling-sessions/SKILL.md) skill, not this step.) One offer, one session, and the user stays in the loop in it. On a yes, use the host's session-creation control with a short self-contained prompt: the checkout path, "run `whats-next`", the one or two threads from the sign-off, and this session's file as the handoff. Check where the host will start it. A control that only starts in a fresh worktree will not see uncommitted work or gitignored files such as `_pm/`; say so, and hand the user the prompt to paste into a session opened in the real checkout instead. A queued session or a click-to-start chip is reported as created and pending, never running. No control on this host: print the prompt. No ready work, or the user is done for the day: skip the offer.

## What this skill does NOT do

- Commits and shared pushes require applicable authorization; reuse existing permission rather than offering the same action again.
- Doesn't claim closing the chat pauses, stops, or schedules background work.
- Doesn't close or comment tickets on a tracker the user doesn't own without applicable authorization.
- Doesn't keep task lists or decisions in `_pm/` — work items live in the tracker (`docs/TASKS.md` by default), decisions in `docs/adr/`.
- Doesn't append an inbox line without matching first, and never appends a status or a checkbox to the inbox — it has none.
- Doesn't rewrite the Intent to match the outcome — that defeats the purpose. Intent stays as set; outcome is reported honestly against it.
- Doesn't fold several sessions into one entry, or reopen a closed session's file. Each session gets its own; the next open starts a new one.
