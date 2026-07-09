---
description: Scaffold a new client project from the datacraft PM starter — copies the template, renames to the client, and runs the skeleton interview.
argument-hint: <ClientName>
---

# /pm:scaffold

Stand up a new client engagement from the bundled starter. Three moves: **copy → rename → orient**. Do them in order; don't skip the interview.

The client name is: **$ARGUMENTS**

## 1. Resolve the client name

- If `$ARGUMENTS` is empty, ask: *"What's the client name? (e.g. Acme — I'll create `datacraft-Acme/`)"* and wait.
- Normalise to a folder-safe token (strip spaces/punctuation, keep it readable — "Acme Corp" → `AcmeCorp`). Call this `<ClientName>`.
- Target folder is `datacraft-<ClientName>/` created **in the current working directory**. If it already exists, stop and tell the user — don't overwrite.

## 2. Copy the template

The starter lives inside this plugin. Copy it wholesale:

```bash
cp -R "${CLAUDE_PLUGIN_ROOT}/template/." "./datacraft-<ClientName>/"
find "./datacraft-<ClientName>" -name .DS_Store -delete
```

The `whats-next` and `stepping-away` skills are **not** in the template — they ship globally with this plugin and are already available. Don't copy them in.

## 3. Rename the placeholder

The template's `CLAUDE.md` opens by describing itself as a starter with `datacraft-Project/` as the fillable placeholder. In the **copied** `datacraft-<ClientName>/CLAUDE.md`:

- Replace the "This is a STARTER, not a live project" banner with a one-line project header naming the client and today's date.
- Replace remaining literal `datacraft-Project` references with `datacraft-<ClientName>`.
- Leave the rest of the structure doc intact — it still describes the layout correctly.

Also set the `README.md` title to the client's project name.

## 4. Run the skeleton interview

`_pm/skeleton.md` is the default planning artifact (Wei Hao's 5-step). Don't leave it as a placeholder — interview the user, briefly. Ask these one at a time, conversationally, and keep it short (a change-request job only needs a paragraph):

1. **Outcome sentence** — when this engagement is done, what's true that wasn't before?
2. **Critical user journey** — the one path through the deliverable that has to work.
3. **Minimum capabilities** — the few things that path requires. (Only what would *break the journey* if removed.)
4. **Fundamental enablers** — what has to exist underneath (data, access, integrations)?
5. **Non-negotiables** — hard constraints (deadline, budget, tech, compliance).

Write the answers into `datacraft-<ClientName>/_pm/skeleton.md` in that 5-step structure. If the user says it's a small job, collapse it to a single tight paragraph rather than five headings — the artifact scales with content.

## 5. Sign off

Confirm what you did in 3–4 lines: folder created, CLAUDE.md/README renamed, skeleton captured. Then point at the next step: *"Drop discovery artifacts in `_pm/artifacts/`, add tasks to `_pm/TASKS.md`, and run `whats-next` when you start a working session."*

Don't start doing project work — scaffolding ends here.
