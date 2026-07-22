# Workflow — FileMaker runbooks

Numbered runbooks for the agent ↔ FileMaker loop on THIS project.

**Reference (lives in the plugin, not here):**

- The four Claris CLI tools — verbs, division of labor, what has no verb
  (XML→file): the fm-patch skill's `references/claris-cli-tools.md`.

**Setup (hosted file):**

- [`01-connect-odata-and-mcp.md`](01-connect-odata-and-mcp.md) — the two doors in
- [`02-install-the-export-script.md`](02-install-the-export-script.md) — give the agent eyes (one-time)
- [`03-export-the-structure-remotely.md`](03-export-the-structure-remotely.md) — the read path, on demand

**Patch cycle (local files — tools ship in the plugin):**

- [`04-export-xml.md`](04-export-xml.md) — local Save-as-XML exports (dev + prod pair)
- [`05-diff-review.md`](05-diff-review.md) — parse, diff, HTML review → operator selection (the human gate)
- [`06-patch-apply.md`](06-patch-apply.md) — gen → apply → verify; never trust the banner
- [`07-scaffold-file.md`](07-scaffold-file.md) — build/evolve a file from `../specs/<name>.json`

**Server (admin console credentials):**

- [`08-admin-api.md`](08-admin-api.md) — the Admin API: download a hosted file (close → zip → reopen), server status, the logs verdict

Each patch-cycle run appends an entry to its journal in [`../logs/`](../logs/)
— that feedback loop is how the gotchas got caught.

They ship pre-seeded as guides — the procedures and the hard-won gotchas are
real, but the results are not yours yet. **Re-run each step against this
project's file and fill in its "Result — capture when run" section as you
go.** New numbered steps the project grows follow the same convention:

1. **What** — what was actually done, concretely enough to reproduce.
2. **Why** — why this step exists; what breaks or gets harder without it.
3. **Result** — how we confirmed it worked — captured after it's done, never
   written speculatively.

The export-install assets ship in the plugin: the standard paste-in pair
`${CLAUDE_PLUGIN_ROOT}/templates/saxml-table.xml` +
`templates/agent-saxml-export-v5.xml` (doc 02's default — no placeholders),
and the legacy `templates/agent-saxml-export.template.xml`
(`{{PLACEHOLDER}}` markers, substituted per file in doc 02's custom-install
interview).
