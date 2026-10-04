# When a gate must not be switchable: managed settings

The gate kit lives in the repo. Anyone who can write the repo can change it, and
so can a session, after a prompt. That is the right strength for a solo repo or
a small team. Where a rule has to hold against the people working in the repo,
it moves up a layer.

```
project hooks      .claude/settings.json in git        the team can change them
managed settings   deployed by an admin                nobody working in the repo can
sandbox            OS-level file and network limits    holds even for shell commands
credentials        what the session can reach at all   the real production boundary
```

Each layer covers what the one above cannot. A hook reads tool calls and can be
edited. A permission rule governs Claude's own tools. It does not govern what a
shell command does. The sandbox limits the shell itself. A credential the session never holds
cannot be misused at any layer.

## A starting point

Managed settings are deployed by an administrator: through the Claude admin
console, an MDM profile, or a `managed-settings.json` in the system directory
(`/Library/Application Support/ClaudeCode/` on macOS, `/etc/claude-code/` on
Linux). Settings there outrank user, project and local settings.

```json
{
  "allowManagedHooksOnly": true,
  "allowManagedPermissionRulesOnly": true,
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]
  },
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "allowedDomains": ["github.com", "registry.npmjs.org"]
    }
  }
}
```

What each key does:

| Key | Effect |
|---|---|
| `allowManagedHooksOnly` | Only hooks from managed settings run. Project, user and plugin hooks are blocked, **including the gate kit's own entry in `.claude/settings.json`**. |
| `allowManagedPermissionRulesOnly` | Managed settings become the only source of permission rules, so no project file or flag can widen them. |
| `permissions.disableBypassPermissionsMode` | `"disable"` stops anyone entering bypass mode. |
| `permissions.deny` | Keeps Claude's file tools away from secrets. |
| `sandbox.enabled` | Shell commands run inside OS-level limits. |
| `sandbox.failIfUnavailable` | Claude Code refuses to start when the sandbox cannot. |
| `sandbox.allowUnsandboxedCommands` | `false` stops a command that failed in the sandbox from being retried outside it. |
| `sandbox.network.allowedDomains` | The shell reaches these hosts and nothing else. |

Because `allowManagedHooksOnly` blocks the project hook, a managed deployment
that wants the gate has to declare it again in the managed file's own `hooks`
block. This kit cannot be used for that yet. The script finds its repo from its
own location, so it runs only from `<repo>/.claude/hooks/`, and a managed hook
that points there hands control back to anyone who can write to the repo. A
managed deployment needs a variant of the script that lives outside the repo and
takes the repo root from `$CLAUDE_PROJECT_DIR`. That variant is not built.

## Mods can overrule a project hook

Since Claude Code 2.1.287 a plugin can carry a mod: code that runs inside Claude
Code and sees every tool call. A mod the user installed decides after the
permission rules and the settings hooks have decided, and its answer replaces
theirs. It can approve a call that a rule set to `ask` would have prompted for, and a
call that a hook in project or user settings blocked, which includes this kit.

Two things hold over a mod the user installed:

- A block from a hook in managed settings is final. That hook runs before any
  mod sees the call.
- On a machine with managed settings, or under a Team or Enterprise sign-in, a
  built-in guard loads first. With the guard loaded, a user's mod cannot approve
  a call that a deny rule refuses.

On a machine with neither, the protection is the one the mods docs give: install
mods only from sources you trust, and list what a mod does before installing it
with `claude plugin validate <dir>`.

An organization that also controls its tool surface uses four more keys:
`strictKnownMarketplaces`, `allowManagedMcpServersOnly`, `disableSideloadFlags`
and `requiredMinimumVersion`.

## Before you copy this

- Every deny rule removes a capability. Set the balance from the data the repo
  holds. This example is only a starting point.
- Every key above was checked against the Claude Code settings, permissions,
  sandboxing and managed-settings docs on 2026-10-03, on Claude Code 2.1.285.
  Keys move. Check the settings reference before deploying.
- Nothing in this file has been deployed or tested here. The gate kit is tested.
  This page only describes the layer above it.

Docs: <https://code.claude.com/docs/en/managed-settings>,
<https://code.claude.com/docs/en/settings-reference>,
<https://code.claude.com/docs/en/sandboxing>,
<https://code.claude.com/docs/en/hooks>.
