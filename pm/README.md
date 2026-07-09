# dc-project

Claude Code plugin that packages Joe's project-management starter. Provides:

- **`/pm:scaffold <ClientName>`** — stands up a new client engagement: copies the `_pm/` / `docs/` / `resources/` starter into `datacraft-<ClientName>/`, renames the placeholder, and runs the skeleton interview.
- **`whats-next`** skill — morning open: reads project memory, proposes a pick-up, drafts the day's Intent block.
- **`stepping-away`** skill — end-of-day close: compares Intent to what shipped, writes the session entry, updates TASKS.
- **`design-handoff`** skill — writes a lean brief for pasting into Claude Design (data-driven or concept-driven).
- **`html-artifacts`** skill — produces rich editorial HTML artifacts (plans, brainstorms, status reports) instead of long markdown.

## Install

```
/plugin marketplace add datacraftdevelopment/dc-plugins
/plugin install pm
```

After install, `/pm:scaffold` and the bundled skills are available in every session on that machine.

## Use

```
/pm:scaffold Acme
```

Creates `datacraft-Acme/` in the current directory, ready to work.

## Layout

This plugin lives in the `pm/` subfolder of the [`dc-plugins`](../) marketplace:

```
pm/
├── .claude-plugin/
│   └── plugin.json          ← plugin manifest (marketplace.json is one level up)
├── commands/
│   └── scaffold.md          ← /pm:scaffold
├── skills/
│   ├── whats-next/
│   ├── stepping-away/
│   ├── design-handoff/
│   └── html-artifacts/
├── template/                ← the starter that /pm:scaffold copies
└── _starter-design/         ← design rationale for the starter (reference only)
```

## Updating

Edit `template/` to change what new projects get. Edit `commands/scaffold.md` to change what the command does. Bump `version` in `plugin.json`, commit, push — machines pick it up on `/plugin marketplace update dc-plugins`.
