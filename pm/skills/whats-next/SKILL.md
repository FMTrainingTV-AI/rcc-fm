---
name: whats-next
description: Session open — propose 1-2 things to pick up AND draft this session's Intent block (the agent's anchor while it works). Use when the user says "what's next?", "what should I work on?", "where did we leave off?", "catch me up," or starts a session cold without a specific task in mind.
---

# What's Next

Session open. The user is starting a session — could be the second one today after closing a full thread, future-them four days later, or a teammate cold-starting. Ground the answer in context, not vibes, and **draft an Intent block** they can paste into this session's entry to keep the agent oriented during execution.

**Don't ask "what do you want to work on?"** That's what they're asking *you*. Read first, then propose.

**If the user already named the work, there is no selection to make.** Skip the proposal round: read enough context to draft the Intent block for the named work, write it, and start. Don't re-open the pick, don't run the full survey below, and don't ask for approval the naming already gave.

## Checklist

**1. Read.** Shared record first, personal log second (`SDLC.md`: `docs/` is truth, `_pm/` is log).
- `docs/intent/*.md` — every open intent (status draft or accepted, not yet marked shipped): these are the streams of work. Note each one's size call.
- **The tracker** — the frontier. By default `docs/TASKS.md`: its **Current** and **Next** sections. If the project's `CLAUDE.md` names another tracker (GitHub Issues: `gh issue list`; a ticket folder; another tool's plans), read that instead. Unreachable → say so, go on with local artifacts. **Waiting items** — anything carrying `Waiting on:` — are not frontier: list them under *Waiting on you* with who and since when, never as the pick-up.
- **`docs/intent/inbox.md`** — the ungroomed list: loose asks and ideas that have not been shaped. Read it after intents and the frontier. A line here is a discovery candidate, not a task. **Grooming is optional, never a gate on starting work:** if the file holds more than twelve lines, or any line is dated before the last four session files, note that in the proposal and *offer* a keep / promote (→ `discovery`) / merge (into an existing intent or ticket) / retire pass — a retired line is deleted from the file and the reason goes in this session's entry. The user can decline or defer; proceed to the pick-up either way. Otherwise say nothing about age.
- `docs/adr/` newest entries, `CONTEXT.md` if present — what's been decided.
- `_pm/skeleton.md` — the macro why of the project.
- Last 1–3 session files in `_pm/sessions/` (any author, most recent first) — especially Open threads and the previous session's Intent-vs-outcome. The immediately preceding session may be earlier the same day; read it as the live handoff.
- `knowledge/index.md` — only if a knowledge bundle exists. Skim; don't crawl.
- **A task file in `_pm/`** (`_pm/TASKS.md`, from pm ≤ 0.7): legacy. Read it as a hint only and offer to move what still matters into the tracker. A file whose first line says `> Legacy` is skipped entirely.

**2. Propose.** Output:

Keep **actionable work** and **decisions waiting on the user** as separate lists — a ticket the agent can take next is not the same thing as a question only the user can answer, and mixing them buries both.

```
Where we are: <one sentence — which streams exist and what stage each is at>.
Frontier (actionable): <takeable items, or "nothing listed yet">.
Waiting on you: <decisions only the user can make — waiting items
  with who and since when, a draft intent needing acceptance; or "nothing">.
Ungroomed: <inbox lines, or "inbox empty"; stale/excess lines offered for keep / promote / merge / retire>.
Recommended pick-up: <one specific item / next stage step / "discover <inbox line>"> — because <reason tied to context>.
Also worth: <maybe one more>.
Watch-outs: <items in Current gone quiet; open threads worth surfacing>.
```

**3. Draft the Intent block** for the most likely pick-up. Two or three sentences of plain prose — what we're pushing on, why it matters, what done-for-this-session looks like, anything explicitly not in scope. Scope it to one session's worth of work, not a whole day's. Example:

> Pushing on the search filter UI — Sandy's manual workaround is costing her ~20 min/day, and a working filter unlocks the rest of the search flow. Done for this session is the prototype validated by Sandy. Not touching filter persistence or multi-category yet.

**4. Resolve the pick-up.** Named work or existing authorization to continue the
ready work within a settled scope is the selection: proceed without another
approval round. Otherwise present the recommendation and wait for the user's
selection. A missing outcome or permission is a real question; choosing the next
ready item in an already authorized scope is routine.

**5. Write.** Once the selection is settled (named work counts as settled), write the Intent block into this session's file in `_pm/sessions/`:

Use the bundled allocator after the user has selected the work (an explicit task already states the selection):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session.py" --root . open --name <handle> --intent '<session intent>'
```

Keep the returned `path` and `id` in this conversation and its handoff/compaction summary. They bind this conversation to this session; never select a newer file by ordinal. The allocator creates the next readable date/person filename with exclusive creation and adds `Session-ID` and `Started`. Local concurrent allocations cannot overwrite each other. Offline replicas of a synced folder do not share a lock: use separate project checkouts for simultaneous work across machines and preserve conflicting files for reconciliation.

On resume/context recovery, read that file's opening Intent and latest Re-aimed section, then reconcile with the tracker and shared docs. If the binding was lost and more than one file could belong to this conversation, ask once. Legacy files without an ID remain readable; do not adopt one merely because it is newest. An explicit session path supplied by the user can be continued manually with the same append-only rules.

**Claim the pick-up on the tracker**: in `docs/TASKS.md`, move the item to **Current**; on a ticket tracker, assign it to yourself. That is the claim.

**6. Execute.** Do the work in this session, one outcome at a time, with the
user in the loop. Two or three ready items that are independent of each other
can run as sibling sessions: use the
[sibling-sessions](../sibling-sessions/SKILL.md) skill, which decides whether it
is appropriate, launches them and then leaves them alone. Keep human questions
on the tracker and surface them together in this conversation.

## When the project has no history

Brand-new project: propose drafting the skeleton (if still placeholder), or running `discovery` on the first piece of work so there's an intent to stand on. Still draft an Intent block — the push this session IS "draft the skeleton" or "discover the first stream."

## Why this skill matters

> "These systems were built to execute. They nail the *what* and quietly let the *why* go." — Matt Maher

The Intent block is this session's why. Reread it at resume/context recovery, before the next item, and at checkpoint. Without it, the agent has the queue but no orientation.
