# CLAUDE.md

This file orients Claude Code when working in this repository.

> **This is a STARTER, not a live project.** Rename `datacraft-Project/` → `datacraft-<ClientName>` to start a new engagement. The capital `P` is a fillable placeholder. See `docs/_design/2026-06-06-starter-design.html` for the design rationale.

## What this is

A **project-management starter** — the connective tissue around a client engagement. Light by default (a three-hour change request uses it without sprouting structure). Scales up (a six-month fixed-bid uses the same scaffold with `_pm/milestones/` and richer `_pm/requirements/`). One structure either way.

Agnostic to codebase. The deliverable might be FileMaker, web, SaaS, or pure consulting. When the engagement *also* needs code, this starter's `_pm/` folder drops alongside the code starter's folders — see "Companion mode" below, and the paired starter `datacraft-Project-FM/` for the FM combination.

## Repository Layout

```
datacraft-Project/
├── CLAUDE.md                  ← you are here
├── README.md
├── .gitignore
├── docs/                      ← meta + ad-hoc Claude-generated catch-all
│   ├── notes/                 ← scratch, meeting notes, ad-hoc analysis
│   └── quirks.md              ← technical gotchas
│
├── resources/                 ← canonical 4-folder taxonomy (matches siblings)
│   ├── design-handoff/
│   ├── design-exploration/
│   ├── research/
│   └── history/
│
└── _pm/                       ← project management — everything operational
    ├── README.md              ← orients agents
    ├── skeleton.md            ← Wei Hao 5-step. Default planning artifact.
    ├── TASKS.md               ← Current / Next / Waiting / Backlog
    ├── sessions/              ← per-day "what + why" log
    ├── decisions/             ← opt-in ADRs
    ├── milestones/            ← OPT-IN. Sprout when path is long.
    ├── requirements/          ← user-stories, personas, parrot-back/
    ├── artifacts/             ← raw inputs (transcripts, customer-docs, exports)
    ├── prototypes/            ← HTML mockups for customer validation
    ├── deliverables/          ← reports, dashboards
    └── bridges/               ← Claude ↔ ChatGPT PII shuttle
```

**The split:** `_pm/` = operational project management. `docs/` = meta and ad-hoc Claude output that isn't PM workflow. `resources/` = material brought in from outside the Claude-driven workflow.

## New Project Setup

1. Rename `datacraft-Project/` → `datacraft-<ClientName>/`.
2. Write `_pm/skeleton.md` — even a paragraph is fine for small jobs.
3. Drop artifacts as they arrive (`_pm/artifacts/transcripts/`, etc.).
4. Add tasks to `_pm/TASKS.md`.
5. End each working day with the `stepping-away` skill.

That's the light mode. Heavier folders (`_pm/milestones/`, `_pm/requirements/`, `_pm/deliverables/`) sprout as warranted.

## The skeleton — default planning artifact

`_pm/skeleton.md` uses Wei Hao's 5-step structure: outcome sentence → critical user journey → minimum capabilities → fundamental enablers → non-negotiables. For a change-request job, a paragraph. For a six-month engagement, a longer doc. **One artifact, scales with content.**

A story belongs in the skeleton only if removing it would break the journey, make the release unusable, or make it untestable.

## Sessions — per-day what + why

`_pm/sessions/YYYY-MM-DD.md` captures **shipped work AND the thinking behind it** in one file per day. Replaces the older `changelog/` pattern. Single shared log per project (no per-milestone, no per-person).

**Same-commit rule:** when work ships, remove from `_pm/TASKS.md` and add to today's session entry in the same commit.

**Optional `_pm/decisions/`** — for durable choices retrievable by topic. Most projects don't need it.

## The active-intent layer

Four temporal layers cover project context:

| Layer | Where | Captures |
|---|---|---|
| Macro why | `_pm/skeleton.md` | Outcome, journey, capabilities |
| What | `_pm/TASKS.md` | Current items WITH `Why` + `Done-when` |
| **Active why** | `_pm/sessions/YYYY-MM-DD.md` `## Intent` | Today's push, why, done-for-today, not in scope |
| Past why | `_pm/sessions/YYYY-MM-DD.md` `## Intent vs. outcome` | Intended vs. shipped (drift check) |

**Why this matters:** agents nail the *what* and quietly let the *why* go. The Intent block (2–3 sentences of prose, set at session start by `whats-next`, checked at session end by `stepping-away`) is the anchor the agent reads on every tool call. Skip it for quick fixes; set it for substantive work.

## Milestones — opt-in

`_pm/milestones/` is empty by default. Sprout `M0-<name>/`, `M1-<name>/` (copy from `_template-milestone/`) when a single TASKS list can't track the path to the skeleton.

**Sessions don't split by milestone.** One unified log per project, always. Per-milestone narrative (if needed) lives in `_pm/milestones/M0-name/retro.md`.

## The two skills

| Skill | When | Reads | Writes |
|---|---|---|---|
| `whats-next` | Start of day / cold-start | Last sessions, TASKS, skeleton (all in `_pm/`) | Today's Intent block |
| `stepping-away` | End of day | TASKS, today's session, git log, conversation | Session entry, updated TASKS, optional decision |

These two skills ship globally with the `pm` plugin (they're no longer copied into each project), so they're available in every session without living in this repo. Joe's other cross-project skills live in `~/.claude/skills/`.

## Companion mode — drop `_pm/` into a code starter

When the engagement IS code, drop the `_pm/` folder alongside the code starter's folders. For FM specifically, use the paired starter `datacraft-Project-FM/` which already has the layout baked in.

```
datacraft-Acme-FM/  (renamed from datacraft-Project-FM)
├── CLAUDE.md
├── README.md
├── .claude/skills/
├── docs/                      ← shared meta + catch-all
├── resources/                 ← shared taxonomy
├── _pm/                       ← engagement management
│
├── plugin/                    ← FM-specific code
├── schema/
├── webviewer/
├── web/
├── scripts/
└── dev/
```

`_pm/` is **portable** — all internal references are local to the folder; outward references reach to `../docs/` and `../resources/` which exist in every starter.

`prototypes/` lives inside `_pm/` because it's customer-validation work — even in code engagements, the validation prototypes are PM artifacts. Code prototypes go in the code starter's `dev/`, `webviewer/`, `web/`.

## Working conventions

- **Skeleton first** — don't write user stories before the skeleton exists. Even a paragraph is fine.
- **Stepping away** ends each working session. Don't ramble — the skill handles the checklist.
- **Set Intent before substantive work.** Two or three sentences in the session entry. The agent reads it before acting.
- **One in, one out** (Wei Hao) — when a new request shows up under fixed scope, the question is *"if this comes in, what comes out?"*, not "where do we squeeze it." Handle in conversation; document the trade in the session entry or a decision.
- **Periodic drift check** (Wei Hao's flavor-check) — every month or at milestone boundaries, restate the release goal in one sentence and compare to what's actively being built. If they've drifted apart, either reshape the backlog or rewrite the skeleton. Handle in conversation; document in the session entry.
- **`docs/` is the catch-all for ad-hoc Claude output.** Drafted emails, technical analyses, one-off summaries that aren't PM-workflow go here. Sprout topic subfolders organically when volume justifies.
- **Resources is for things YOU bring in.** Claude-generated docs go in `docs/` or `_pm/`.

## Design history

The design rationale — sources (Charlie Bailey on AI-PM, Wei Hao on scope control, Matt Maher on agent orientation), the decisions made, what was explicitly trimmed — lives at:

- `docs/_design/2026-06-06-starter-design.html`
- `docs/_design/2026-06-06-session.md`

If you want to change the shape of the starter, write a new design artifact next to those (don't edit history). Re-run the implementation from the new design.
