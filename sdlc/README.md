# sdlc

Repo-level enforcement kits for the agentic SDLC. `pm` runs the session: intent,
tickets, verification, delivery. This plugin holds what `pm` leaves to
deterministic tools: gates a session cannot talk its way past, and a written
review policy read by a reviewer that did not write the change.

It uses Claude Code features only and does not depend on `pm`, so the same kit
works in a repo without it.

```
skills, CLAUDE.md      advise      nothing makes a session comply
       │
gate-hooks             enforce     one script and one config, in the repo
review-policy          re-check    REVIEW.md, read by a fresh reviewer
       │
managed settings       lock        the admin's layer; mapped here, not deployed
```

## What is in it

| Piece | What it does |
|---|---|
| skill `gate-hooks` | Installs the gate kit into a repo and writes its rules with the user. |
| `kit/sdlc_gate.py` | The gate. A PreToolUse and Stop hook: production commands, protected paths, a test lock for fix tasks, a commit backstop, and protection for its own files. It also provides the `lock`, `unlock`, `status` and `check` commands. The lock and the decision log are kept in `.git/sdlc-gate/`, where `git clean` cannot remove them. |
| `scripts/install_gates.py` | Copies the kit into `<repo>/.claude/`, merges the hook entries into `settings.json`, backs up what it replaces. Safe to repeat. |
| skill `review-policy` | Sets up and tunes `REVIEW.md`; runs a policy review of a diff. |
| agent `policy-reviewer` | Fresh context, read-only (`Read, Grep, Glob`). Reports findings against `REVIEW.md` and the intent, spec or plan. Never edits. |
| `templates/REVIEW.md` | The policy template: passes, severity, nit cap, do-not-report, evidence rule, tuning log. |

## Install

```
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install sdlc
```

Then, in a repo, ask for a gate or a review policy and the skills take it from
there. By hand, with the absolute path of the folder sessions start in:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_gates.py" --repo /absolute/path/to/repo --dry-run
```

## Not yet proven

- **The interactive approval prompt.** Every `ask` in the table ran headless,
  where it refuses. Nobody has seen the prompt in a session in default
  permission mode yet.
- **`ask` in auto mode does not reach the user.** Seen once, on 2.1.286 in the
  desktop app (2026-10-04): the hook returned `ask` twice in a session in auto
  mode, no prompt appeared, and each command ran, 18 and 67 seconds later. The
  transcript carries auto mode's classifier records on both calls and no
  record of a person's answer. So in auto mode an `ask` rule is answered by
  the classifier, and only `deny` stops the call. This contradicts the docs,
  which say a hook's `ask` still prompts in auto mode, and it contradicts the
  no-skill baseline session's report that its own gate's `ask` held in auto
  mode on 2.1.285.
- **`ask` in bypass-permissions mode.** Not documented and not tested here.
  `deny` blocks in every mode.
- **The decision log in a worktree session.** In that same session neither
  `ask` was written to the log, although the gate logs before it answers. The
  same event fed to the same script from a terminal was logged. Cause not
  found; a write the session was not allowed to make under the main repo's
  `.git/` is the guess.
- **Managed settings.** `skills/gate-hooks/managed-settings.md` is checked
  against the docs and deployed nowhere.
- **The review skill on a real change.** The reviewer's read-only tool list is
  asserted by a test; its findings have not been judged on real work.
- **Windows.** The hook command is POSIX shell.

## Limits worth knowing

- A gate reads five tools: Bash, Monitor, Edit, Write and NotebookEdit. An MCP
  tool that reaches the same database or host goes round it. Cover those with
  permission rules in `.claude/settings.json`.
- It is not a sandbox. It refuses a shell write only when it can read it with
  certainty: a redirect, or `rm`, `mv`, `cp`, `tee` or `sed -i` naming the path.
  Everything else in a shell line gets through: git, `find`, a formatter, a
  generator, a script, inline code. A protected file changed that way is caught
  when a commit is attempted through Claude. A locked file is also caught at
  Stop. When the check cannot parse a command, it lets it through.
- The Stop hook pushes back once. If the session still ends with a locked file
  changed, the user gets a warning and the commit gate keeps refusing.
- The hooks load only in a session started in the folder that holds `.claude/`.
  A session started in a subfolder runs with no gates, and so does a nested
  `claude` run that is told to skip project settings.
- The gates bind Claude Code only. Other agents working in the same
  repo do not read these hooks.
- Production rules match text. The real production boundary is credentials the
  session does not hold.
- A Claude Code mod installed on the machine can approve a call the gate
  refused. Only a hook in managed settings is final. See
  `skills/gate-hooks/managed-settings.md`.

## Layout

```
sdlc/
├── .claude-plugin/plugin.json
├── agents/policy-reviewer.md
├── kit/
│   ├── sdlc_gate.py           ← copied to <repo>/.claude/hooks/
│   └── gates.starter.json     ← becomes <repo>/.claude/sdlc/gates.json
├── scripts/install_gates.py
├── skills/
│   ├── gate-hooks/            ← SKILL.md, managed-settings.md
│   └── review-policy/         ← SKILL.md
└── templates/REVIEW.md
```
