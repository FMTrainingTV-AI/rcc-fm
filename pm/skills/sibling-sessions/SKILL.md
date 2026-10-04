---
name: sibling-sessions
description: Run two or three independent ready tickets at the same time, each in its own fresh interactive session that owns its ticket through to its own merge, with nobody watching the others. Use when the user says "sibling sessions", "implement sibling sessions if appropriate", "spin up a sibling session for that", "run these in parallel sessions", "open another session for that ticket", or when ready tickets look independent and the user wants them moving at once. This is the default way to parallelize. NOT unattended workers.
---

# Sibling sessions

Two or three ordinary sessions running side by side. Each one is the normal
loop (`whats-next` → work → `stepping-away`) on its own ticket, in its own
worktree and branch, with the user in the loop. They are siblings, not parent
and children: no session reports to another, and **nobody watches them**.

Why this shape: a sibling costs what any session costs. A coordinating session
that stays alive polling, sweeping and integrating the others costs more than
it saves. Siblings keep the parallel wall-clock and drop it.

## 1. Decide whether it is appropriate

"If appropriate" is a real question. Answer it out loud, yes or no, with the reason.

Say **yes** only when all of these hold:

- There are at least two ready tickets (this session's own counts as one), each
  a meaningful outcome. Small fixes stay in this session, done serially.
- **Disjoint files.** List what each ticket will touch. Any overlap, including
  lockfiles, generated code, migrations, schema or config registries, means
  those two run one after the other.
- **At most one database writer**, and no shared port, dev server, browser
  profile or other single resource.
- No ticket depends on another's output.
- The machine has room. Check memory and CPU (`memory_pressure`, `uptime` on
  macOS). Three sessions building at once ran a 16 GB Mac out of memory.
- The user will be around to answer each window. A sibling that asks a question
  nobody sees sits idle for hours.

Otherwise say **no** and name the alternative: do them serially in this
session.

**Three siblings at once is the ceiling**, counting this session.

## 2. Open each sibling

One sibling per ticket. Use the host's session-creation control with a short
self-contained prompt:

```
Repo: <main checkout path>. You are one of <N> sibling sessions; the others are
working <ticket ids>, leave those alone.
Run whats-next bound to ticket <id>: <title>. Do not pick other work.
Work in your own worktree on branch <name>. Set the worktree up from
docs/agents/worker-env.md if the repo has one.
You own this ticket through its merge: rebase on <base branch>, get green on the
rebased tree, then merge only when the user says so. Close with stepping-away.
Do not message or wait on the other sessions.
Handoff: <this session's file>.
```

Claim nothing on the sibling's behalf; its own `whats-next` claims the ticket.
Name the ticket so two siblings never pick the same one.

A fresh worktree is what a sibling wants, but it lacks uncommitted work and
everything git ignores: env files, dependencies, local databases, and `_pm/` in
repos that ignore it. Commit what the sibling needs first, and say in the prompt
what it has to set up. Where `_pm/` is ignored, tell the sibling to write its
session file in the main checkout.

Report each one as **created and pending**, never running, until it has actually
started. A click-to-start chip is pending until the user clicks it. No
session-creation control on this host: print the prompts for the user to paste.

## 3. Let go

After launching, this session goes back to its own ticket, or closes with
`stepping-away`. Do not poll the siblings, read their transcripts, wait for
reports, sweep their worktrees or integrate their branches. If the user asks how
a sibling is doing, look once and answer; that is not monitoring.

## 4. What each sibling does

The normal loop, plus its own merge:

1. `whats-next` bound to the named ticket.
2. The work, in its worktree, committing at green checkpoints so a crash costs
   reasoning, not work.
3. Rebase on the base branch, run the project's checks on the rebased tree, and
   show the user the result. The first sibling ready merges first; later ones
   rebase onto it. A conflict is that sibling's to resolve, in its own window.
4. Merge on the user's word. Push, deploy and client messages keep their own
   authorization.
5. `stepping-away`, then remove its worktree (`git merge-base --is-ancestor`
   before deleting the branch).

## What this skill does not do

- No orchestrator, no report-in channel, no lane board.
- No unattended work. Every sibling has the user in the loop.
- No chain. One launch per ticket.
- No tracker, changelog or client-face edits on a sibling's behalf. Each sibling
  settles its own ticket in its own close-out.
