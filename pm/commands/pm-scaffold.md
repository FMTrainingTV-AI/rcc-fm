---
description: Scaffold a project from the PM starter — client engagement, personal project, or in-place _pm/ for an existing folder — and run the skeleton interview.
argument-hint: <ClientName> | self <ProjectName> | here
---

# /pm-scaffold

Stand up a project from the bundled starter. The starter is **deliberately
minimal** — only day-one files; every other folder is created on first write
(the taxonomy in the stamped `CLAUDE.md` is the map). Moves, in order:
**copy → rename → git → orient**. Don't skip the interview.

The argument is: **$ARGUMENTS**

## 1. Resolve the mode and name

Three modes — read the argument (and the user's phrasing) to pick one:

| Mode | Trigger | Target |
|---|---|---|
| **Client** (default) | A bare name: `Acme` | `client-<ClientName>/` |
| **Personal** | `self` / `personal` / "for me" / "no client", plus a name: `self HomeLab` | `<ProjectName>/` — no prefix; `client-` is reserved for client work |
| **In-place** | `here`, `.`, "this folder" | `_pm/` + `docs/` wiring added to the current directory |

- If `$ARGUMENTS` is empty, ask ONE question: *"What are we standing up? A client name (→ `client-<Client>/`), a personal project (`self <Name>` → plain `<Name>/`), or `here` to add `_pm/` to this folder."* **A missing client is never a blocker** — personal and in-place modes don't have one.
- Normalise the name to a folder-safe token (strip spaces/punctuation, keep it readable — "Acme Corp" → `AcmeCorp`).
- New-folder modes create the target **in the current working directory**. If the target folder already exists, stop and tell the user — don't overwrite.
- In-place mode: if `./_pm/` already exists, stop — this folder is already scaffolded.

## 2. Copy the template

The starter lives inside this plugin.

**Client / personal** — copy it wholesale (it's minimal now — this creates no ballast):

```bash
cp -R "${CLAUDE_PLUGIN_ROOT}/template/." "./<TargetFolder>/"
find "./<TargetFolder>" -name .DS_Store -delete
```

**In-place** — copy ONLY `_pm/`; the copy step touches nothing else that
already exists (step 5 makes small, additive edits — that's its contract,
not this step's):

```bash
cp -R "${CLAUDE_PLUGIN_ROOT}/template/_pm" "./_pm"
find "./_pm" -name .DS_Store -delete
```

The session skills (`whats-next`, `stepping-away`, `checkpoint`, …) ship
globally with this plugin — never copy them into the project.

**Never pre-create taxonomy folders** (`_pm/transcripts/`, `resources/`,
`knowledge/`, …). They're documented in the stamped `CLAUDE.md` and get
created the first time something is written into them.

## 3. Rename the placeholder

*(Skip for in-place.)* In the **copied** files:

- `CLAUDE.md`: replace the "This is a STARTER" banner block with a one-line
  project header naming the client (or personal project) and today's date.
  **Personal mode:** where a line reads wrong without a client
  ("engagement"), soften to "project" — touch only the lines that read
  wrong. Leave the rest intact.
- `README.md`: set the title to the project name.

## 4. Git

The workflow's first artifact (`docs/intent/<slug>.md` from `discovery`) is
a *committed* file, so the project must be a repository.

- **New-folder modes:** if the target is not already inside a git worktree,
  `git init` it and make one baseline commit of the scaffold
  (`chore: scaffold from pm starter`). If it IS inside an existing worktree
  (e.g. a monorepo), say so and skip the init.
- **In-place mode:** don't init anything — but if the folder isn't a git
  repo, tell the user plainly that discovery and the credential-guard hook
  both assume one, and ask whether to `git init`.

## 5. Wire the shared record

- **`docs/intent/` and `docs/adr/`** ship in the template for new-folder
  modes. In-place mode: create them (with their one-line READMEs copied from
  `${CLAUDE_PLUGIN_ROOT}/template/docs/`) if absent.
- **The tracker.** Matt Pocock's `/setup-matt-pocock-skills` writes
  `docs/agents/issue-tracker.md`; `/wayfinder`, `/to-spec`, `/to-tickets`
  read it. It is user-invoked — you can't run it. If the file is missing,
  tell the user that without it wayfinder falls back to local markdown under
  `.scratch/`, and that the fix is one command: `/setup-matt-pocock-skills`
  (GitHub Issues for team repos; local markdown is fine for solo/plugin
  repos). Don't improvise the file yourself.
- **`.gitignore`** — the template's covers new-folder modes. In-place mode:
  ensure `.env`, `account.md`, and `_pm/transcripts/` are ignored (append
  additively; the `credential-guard` hook blocks staging them, but the
  ignore is the belt to that brace).
- **Verification block** — the template `CLAUDE.md` already carries
  `## Verifying your work`. In-place mode: if `CLAUDE.md` exists without
  that section, append the contents of
  `${CLAUDE_PLUGIN_ROOT}/skills/verify-before-done/claude-md-block.md`; if
  there is no `CLAUDE.md` at all, create a minimal one (project one-liner +
  that block) and say you did.

**In-place mutation contract:** the additive edits above (`.gitignore`
lines, `CLAUDE.md` section, `docs/` stubs) are the ONLY changes allowed
outside `_pm/`; never rewrite or reorganize existing content, and name every
touched file in the sign-off.

## 6. Run the skeleton interview

`_pm/skeleton.md` is the default planning artifact (Wei Hao's 5-step) —
every mode gets one. Don't leave it as a placeholder — interview the user,
briefly. Ask these one at a time, conversationally, and keep it short (a
change-request job only needs a paragraph):

1. **Outcome sentence** — when this project is done, what's true that wasn't before?
2. **Critical user journey** — the one path through the deliverable that has to work.
3. **Minimum capabilities** — the few things that path requires. (Only what would *break the journey* if removed.)
4. **Fundamental enablers** — what has to exist underneath (data, access, integrations)?
5. **Non-negotiables** — hard constraints (deadline, budget, tech, compliance).

Write the answers into `_pm/skeleton.md` in that 5-step structure. If the
user says it's a small job, collapse it to a single tight paragraph — the
artifact scales with content.

## 7. Sign off

Confirm what you did in 3–4 lines: what was created (new folder or in-place
`_pm/`), git state (initialized / existing / declined), renames done,
skeleton captured, tracker wired or not, and — in-place — every file
touched. Then point at the next step: *"Run `discovery` on the first piece
of work — it writes `docs/intent/<slug>.md` and makes the size call. Then
`whats-next` when you start a working session."*

Don't start doing project work — scaffolding ends here.
