---
name: gate-hooks
description: Use when a repo rule has to hold whatever the session decides — production deploys that need a human, paths an agent must not edit (generated code, frozen packages, migrations, infra), or a bug fix where the failing test must stay untouched. Also when the user says "add a gate", "protect this path", "lock the tests", "block prod deploys", or asks why a skill or CLAUDE.md rule did not stop something.
---

# Gate hooks

A skill or a CLAUDE.md line advises; nothing makes a session follow it. A hook runs on every matching tool call and can refuse. This kit puts one gate script and one config file in the repo, so the rules travel with the code and hold for anyone who clones it.

Gate only what must hold every time. A gate that prompts often puts a person back in the middle of the work.

## What it gates

| Gate | Fires on | Does |
|---|---|---|
| Production | a Bash or Monitor command matching a rule | `deny`, or `ask` the user |
| Protected path | Edit, Write or NotebookEdit on a matching path, or a shell command that plainly writes one (a redirect, `rm`, `mv`, `cp`, `tee`, `sed -i`) | `deny`, or `ask` |
| Test lock | the same, on a file frozen by `lock` | `deny` until `unlock` |
| Commit | `git commit` while protected paths have changes | `ask`; blocked while the test lock is violated |
| Stop | the session ending with a locked file changed | sends the session back once, then warns the user |
| Self | a change to the gate's script, config or settings | `ask` |

## Install

1. Run the installer against the folder sessions start in, which is normally the repo root. Give the absolute path, and run it with `--dry-run` first: the `target:` line it prints is where the kit will go. It is safe to repeat, backs up what it replaces and never overwrites an existing config.
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_gates.py" --repo /absolute/path/to/repo --dry-run
   ```
2. Ask the user which rules must hold. Three questions settle most repos:
   - Which commands reach production or shared data? These become `production` rules.
   - Which paths must an agent not edit? These become `protected` rules.
   - Which connector (MCP) tools reach those same systems? The gate never sees an MCP tool. Put each one in `permissions.ask` or `permissions.deny` in `.claude/settings.json`, as `mcp__<server>__<tool>`.

   Write the answers into `.claude/sdlc/gates.json`. Once the hooks are live, that edit asks the user. The prompt is the gate working.
3. Validate: `python3 .claude/hooks/sdlc_gate.py check`
4. Prove it with two checks. Neither one runs anything real.
   - Is the gate live in this session? Run `true .claude/sdlc/gates.json`. The command does nothing. A live gate stops it anyway, because it names a gate file. If it runs with no prompt and no refusal, the hooks are not loaded: start a new session in the repo root and check again.
   - Does the rule match? Run a stand-in that the rule matches and that cannot do anything, then read the refusal. For a rule that matches text anywhere in a command, that is `echo` followed by the text. A rule anchored to the command being run is different: `echo` does not match it, so use the command at a path that does not exist, such as `/nonexistent/deploy.sh`. If the gate is live and the stand-in still goes through, the rule does not match it. Fix the pattern. A new session will not help.

   Never prove a rule with the real command. If nothing stops it, it runs.
5. Commit `.claude/hooks/sdlc_gate.py`, `.claude/sdlc/gates.json` and `.claude/settings.json`. The commit asks too, because gate files changed.

## Configuration

```json
{
  "version": 1,
  "production": [
    {"name": "vercel-prod", "match": "\\bvercel\\b.*--prod\\b", "action": "deny",
     "reason": "Production deploys are applied by a human.",
     "approval": "Ask the user to run the deploy, then re-run acceptance against production."}
  ],
  "protected": [
    {"name": "migrations", "paths": ["migrations/", "infra/**"], "action": "ask",
     "reason": "Schema and infrastructure changes reach shared data.",
     "approval": "The user approves the prompt after reading the change."}
  ],
  "tests": ["tests/**", "**/*.test.*"]
}
```

- Every rule states its `reason` and its `approval` route. A block has to say why, and what to do instead.
- `match` is a Python regex searched anywhere in the command, with case ignored. A mention inside a commit message or an echo command triggers it too, so keep the pattern tight, and use `ask` where a false hit would be noisy.
- To fire only when a script is run, and not when it is read, staged or named in a message, anchor the pattern to the start of a command and allow a path in front: `"(?:^|[;&|]\\s*)(?:(?:bash|sh)\\s+)?(?:\\S*/)?deploy\\.sh\\b"`. `echo` does not match a rule like this.
- `paths` are repo-relative globs: `**` spans directories, `*` and `?` stay inside one, a trailing `/` means the whole tree. Case is ignored.
- `deny` is for what an agent never does. `ask` is for what a person may approve, and it only reaches a person in a session in default permission mode. In a headless run (`claude -p`) nobody can answer, so `ask` refuses. In auto mode the one run on record (2.1.286, desktop app) showed no prompt: auto mode answered the `ask` itself and the command ran. Bypass-permissions mode is not documented and not tested here. So ask the user which mode their sessions run in, and use `deny` for anything that must hold whatever the mode. With `deny`, the person runs the command themselves in a terminal.

## The test lock

For a bug fix, the proof is a test that failed before the fix and that the fixer could not rewrite.

1. Reproduce the bug as a test. Run it and confirm it fails for the expected reason. Commit it.
2. Lock it: `python3 .claude/hooks/sdlc_gate.py lock --reason "fix <bug>" tests/test_x.py`. With no paths, the `tests` globs are locked.
3. Fix the code until the test passes. New test files can still be added. Locked ones cannot change.
4. The user releases it: `python3 .claude/hooks/sdlc_gate.py unlock`. Run from a session, `unlock` asks the user.

If a locked file changed, and you did not change it, the user edited it by hand. Leave it alone and tell them.

The lock freezes files. It does not freeze what decides whether they run: a new `conftest.py` or a change to the test runner's settings can skip a locked test without touching it. Lock those files too, and check that the locked test's name appears in the passing run.

The lock and the log are kept inside the git directory (`.git/sdlc-gate/`), so `git clean` cannot remove them. Each worktree has a lock of its own.

## What a gate does not do

- It reads five tools: Bash, Monitor, Edit, Write and NotebookEdit. An MCP tool that reaches the same database or host goes round it. Permission rules cover those.
- It is not a sandbox. It refuses a shell write only when it can read it with certainty: a redirect, or `rm`, `mv`, `cp`, `tee` or `sed -i` naming the path. Everything else in a shell line gets through: git, `find`, a formatter, a generator, a script, inline code. That change is caught when a commit is attempted through Claude. Only a changed locked file is also caught at Stop.
- It loads only in a session started in the folder that holds `.claude/`. A session started in a subfolder runs with no gates, and so does a nested `claude` run that is told to skip project settings.
- It binds Claude Code only. Codex and other agents working in the same repo do not read these hooks.
- It matches text. A deployment wrapped in a script the rule does not name gets through. The real production boundary is credentials the session does not hold.
- It can be overruled by a mod. A Claude Code mod installed on the machine can approve a call this gate refused. Only a hook in managed settings is final.
- It lives in files that anyone who can write to the repo can change, with a prompt. A rule nobody may switch off belongs in managed settings: see [managed-settings.md](managed-settings.md).
- It blocks on anything it cannot read: a broken `gates.json`, unreadable lock state, missing `python3`. The user repairs it by hand.

Deny and ask decisions are logged to `.git/sdlc-gate/gate-log.jsonl`. Each entry holds the first 200 characters of the refused command, with URL passwords and values after names such as `token` or `password` masked. `python3 .claude/hooks/sdlc_gate.py status` shows the rules, the lock and recent decisions.

To remove the kit, delete the two `sdlc_gate.py` hook entries from `.claude/settings.json`, then `.claude/hooks/sdlc_gate.py`, `.claude/sdlc/` and `.git/sdlc-gate/`.
