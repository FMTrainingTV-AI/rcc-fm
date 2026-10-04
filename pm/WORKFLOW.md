# WORKFLOW — how the pieces fit

The binding of [SDLC.md](SDLC.md) to the skills in this marketplace. The
default is one session working one outcome with the user in the loop.
Everything else is added only when a named uncertainty calls for it.

```
whats-next ──► the work, in this session ──► stepping-away ──► fresh session
                  │
                  ├─ two or three independent items?   sibling-sessions
                  ├─ a risk the checks don't settle?   adversary-review
                  └─ delivering an intent?             ship-acceptance
```

## Default loop

`whats-next` opens a session and sets its Intent. The work happens in that
session. `stepping-away` closes it and offers a fresh session for the next
ready work. Each session's context ends with the session, which keeps cost flat
and handoffs short.

`verify-before-done` applies to every completion claim: run the check fresh,
read the output, report the claim and the evidence together.

## Work in parallel: sibling sessions

Two or three ready items that have nothing to do with each other can each run
in their own ordinary session: own worktree, own branch, the user in the loop,
owned through to its own merge. Nobody watches them. The `sibling-sessions`
skill owns the screen (disjoint files, one database writer at most, no shared
port or dev server) and the launch prompt. Three at once is the ceiling.

There is no orchestrator in this edition. A coordinating session that polls
and integrates cost more than it saved when it was tried.

## Add process only to resolve an uncertainty

| Situation | Reach for |
|---|---|
| Outcome or scope is unclear | `discovery`, to shape the missing intent. |
| A change is risky, or a doubt remains after the checks pass | `adversary-review`, with the doubt named first. |
| An intent is being delivered | `ship-acceptance`, against the revision that is released. |
| Reviews disagree about what matters | `sdlc:review-policy`, to write `REVIEW.md`. |
| A command or path must never be touched without a person | `sdlc:gate-hooks`, installed once in the repo. |
| The session has drifted from its Intent and cannot be closed | `checkpoint`. |

No review at every plan or every green change. State the uncertainty, say why
the existing evidence does not settle it, and run the smallest review that
would. Another round needs a material change or an open finding.

## Review rules

- The reviewer is never the session that wrote the change. It is a fresh
  subagent given the diff, the acceptance lines and the proof, and no summary.
- A reviewer reports. It does not go on to fix. The working session applies
  the accepted findings and re-runs the checks.
- Every finding gets a disposition: fix, decline with a reason, or ask the user.
- A subagent review is same-vendor. It does not replace a person's approval,
  and it never approves a release.

## Authorization and questions

Carry the user's existing scope and permissions forward. Do not ask again
because a new item, skill or session is involved. Ask when the answer changes
the outcome, the scope, or an action that lacks permission. Publishing,
production and messages to clients each need their own authorization.

Real human dependencies live on their item in the tracker as `Waiting on:`.
Present them together and keep working on what does not depend on them.

## Shared record and delivery

`docs/` and the tracker hold project truth. `_pm/sessions/` holds per-session,
append-only logs; it is not a second tracker. Loose asks go to
`docs/intent/inbox.md`, matched against what is already there first.

Closing an item proves its own work. Delivering an intent goes through
`ship-acceptance`, which records blocked, ready-for-release, shipped or
released-with-exceptions as it actually is. A person releases production.
