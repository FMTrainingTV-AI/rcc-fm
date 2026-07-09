# dc-plugins

Datacraft's Claude Code plugin marketplace. One repo, added once per machine, hosting all of Joe's plugins. Each plugin lives in its own subfolder; `.claude-plugin/marketplace.json` lists them.

## Install

Add the marketplace once, then install whichever plugins you want:

```
/plugin marketplace add datacraftdevelopment/dc-plugins
/plugin install pm
```

Update everything later with:

```
/plugin marketplace update dc-plugins
```

## Plugins

| Plugin | Command / skills | What it does |
|---|---|---|
| **pm** | `/pm:scaffold`, `whats-next`, `stepping-away`, `design-handoff`, `html-artifacts` | Scaffolds a client engagement from the datacraft starter and runs the day-to-day PM + delivery workflow. See [`pm/README.md`](pm/README.md). |

## Adding a new plugin

1. Create a subfolder `<plugin-name>/` with its own `.claude-plugin/plugin.json`.
2. Add a line to `.claude-plugin/marketplace.json` pointing `source` at `./<plugin-name>`.
3. Commit and push.
4. On each machine: `/plugin marketplace update dc-plugins` then `/plugin install <plugin-name>`.

No new marketplace is ever needed — this repo is the single marketplace for everything.

## Layout

```
dc-plugins/
├── .claude-plugin/
│   └── marketplace.json     ← lists every plugin
└── pm/                      ← plugin: project management
    ├── .claude-plugin/plugin.json
    ├── commands/            ← /pm:scaffold
    ├── skills/              ← whats-next, stepping-away, design-handoff, html-artifacts
    ├── template/            ← the starter /pm:scaffold copies
    └── _starter-design/     ← design rationale (reference only)
```
