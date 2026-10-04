# pm — Project-Management Plugin

Claude Code plugin that packages a light project-management layer for agentic
work. **Read [`WORKFLOW.md`](./WORKFLOW.md) first** for how the skills fit together, then [`SDLC.md`](./SDLC.md) for the principles: meaningful
outcomes, proportionate verification, and the one rule: `docs/` is shared
record, `_pm/` is personal log. pm is the discovery on-ramp, the session
layer and a plain task list; it doesn't replace a planning tool you already use.

Provides:

- **Default loop** — `whats-next` opens a session, the work happens in it,
  `stepping-away` closes it and offers a fresh session for the next ready work.
- **`/pm:pm-scaffold <name>`** — stands up a project from the bundled
  starter: a client engagement (`Acme` → `client-Acme/`), a personal
  project (`self HomeLab` → plain `HomeLab/`), or `here` to add `_pm/` to an
  existing folder. The starter is **minimal by design** — day-one files only
  (`CLAUDE.md`, `docs/intent/`, `docs/adr/`, `docs/TASKS.md`, `_pm/` with
  skeleton and sessions); every other folder is documented in the stamped
  `CLAUDE.md`'s taxonomy table and created on first write, never pre-built.
  Runs the skeleton interview and ensures a git repo.
- **The task list** — `docs/TASKS.md` (Current / Next / Done) is the tracker
  unless the project's `CLAUDE.md` names another (GitHub Issues, a ticket
  folder, another system's plans). `whats-next` reads it and claims the
  pick-up; `stepping-away` moves verified work to Done and adds what surfaced.
  Loose ideas stay out of it, in `docs/intent/inbox.md`.
- **`discovery`** skill — the stage before planning: a loose conversational
  riff to find the shape and intent of a piece of work, written to
  `docs/intent/<slug>.md` with acceptance checks and a size call (one session
  → build it; several → outcome-sized items on the task list).
- **`whats-next`** skill — session open: reads intents, the task list, the
  inbox (flags stale or excess lines for keep / promote / merge / retire),
  waiting items, and recent sessions; proposes a pick-up; drafts this
  session's Intent block into a per-session, per-person file; claims the item.
- **`stepping-away`** skill — session close: compares Intent to what shipped,
  writes the session entry, settles the task list, captures loose asks into
  the inbox after matching them against what exists, follows
  `docs/agents/client-face.md` if the repo has one (contract in
  `skills/stepping-away/client-face-contract.md`), routes durable knowledge to
  shared libraries.
- **`checkpoint`** skill — mid-session re-aim, for sessions too long or too
  costly to close and reopen: appends a dated re-aim under the Intent
  (append-only — earlier re-aims stay) and pushes the change into the
  affected items. Short sessions don't need it — the session boundary is the
  re-aim.
- **`sibling-sessions`** skill — two or three independent ready items, each
  in its own ordinary session that owns its item through its own merge. No
  coordinating session, no report-in.
- **`verify-before-done`** skill — evidence before claims: run the
  verification fresh, read the output, report claim + evidence together.
  Ships the `## Verifying your work` block the template carries (and
  pm-scaffold stamps in-place), so the floor holds without the plugin.
- **`adversary-review`** skill and the **`adversary-reviewer`** agent — for a
  risky change or a doubt the checks don't settle: a fresh, read-only Claude
  subagent that did not write the change gets the diff, the acceptance lines
  and the proof, and reports where the change fails them. It never edits and
  never approves.
- **`ship-acceptance`** skill — the last handoff: the accepted intent's
  lines checked by someone who did not build it, a person releasing, and a
  record in `docs/shipped/` that says blocked, ready-for-release, shipped or
  released-with-exceptions as it actually is.
- **`okf`** skill *(utility)* — format contract for the opt-in `knowledge/`
  bundle: OKF conventions, sprout tripwires, boundaries.
- **Session helper** — `scripts/session.py` allocates distinct session files
  and closes by exact path/ID with an explicit closure marker; no
  newest-file guessing.
- **`credential-guard` hook** — a bounded filename guard: a `PreToolUse`
  hook on Bash that blocks `git add` / `git stage` / `git commit` when a
  credential-shaped file would be staged or committed — including literal
  directory changes, scoped subshells, explicit commit paths, forced adds,
  and quoted/chained `-C` paths. Removing tracked credentials remains allowed.
  This protects tool invocations, not arbitrary subprocesses or file
  contents. Examples/templates (`*.example`, `*.sample`) pass. Regression
  tests in [`hooks/test-credential-guard.sh`](./hooks/test-credential-guard.sh).

> Upgrading from pm 0.12? New projects get `docs/TASKS.md` and
> `docs/intent/inbox.md` from the scaffold; an existing project can add both
> by hand or run `/pm:pm-scaffold here` (it writes them only if absent).

## Install

```
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install pm
```

After install, `/pm:pm-scaffold` and the bundled skills are available in
every session on that machine.

## Use

```
/pm:pm-scaffold Acme
```

Creates `client-Acme/` in the current directory, ready to work.

## Layout

```
pm/
├── .claude-plugin/
│   └── plugin.json          ← plugin manifest (marketplace.json is one level up)
├── agents/
│   └── adversary-reviewer.md ← the read-only reviewer subagent
├── commands/
│   └── pm-scaffold.md       ← /pm:pm-scaffold
├── hooks/
│   ├── hooks.json · credential-guard.sh · test-credential-guard.sh
├── scripts/                 ← session.py, credential guard and policy
├── skills/
│   ├── discovery/ · whats-next/ · checkpoint/ · stepping-away/
│   ├── sibling-sessions/ · verify-before-done/ · okf/
│   ├── adversary-review/ · ship-acceptance/
└── template/                ← the minimal starter /pm:pm-scaffold copies
```

Run `bash hooks/test-credential-guard.sh` after touching the hook.
