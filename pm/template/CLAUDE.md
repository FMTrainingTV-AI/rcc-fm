# CLAUDE.md

This file orients Claude Code when working in this repository.

> **This is a STARTER, not a live project.** `/pm:pm-scaffold` stamps it and
> replaces this banner with the project header. The scaffold is designed in
> the pm plugin (`FMTrainingTV-AI/rcc-fm`, `pm/template/`); the
> workflow it serves is that plugin's `SDLC.md`.

## What this is

The **project-management connective tissue** around an engagement — genuinely
light: the scaffold contains only what every project uses from day one.
Everything else is *known but not built* — see the taxonomy below. Agnostic to
codebase: the deliverable might be FileMaker, web, SaaS, or pure consulting.

## Day-one layout

```
<project>/
├── CLAUDE.md            ← you are here
├── README.md
├── .gitignore
├── docs/                ← SHARED record — collaborators and clients read it
│   ├── intent/          ← one intent per stream of work (discovery skill)
│   │   └── inbox.md     ← loose asks and ideas, one line each, no status
│   ├── adr/             ← decisions, one file per durable choice
│   ├── TASKS.md         ← the task list: Current / Next / Done
│   └── quirks.md        ← technical gotchas, fast-capture
└── _pm/                 ← PERSONAL log — per-person, append-only, never authoritative
    ├── README.md
    ├── skeleton.md      ← Wei Hao 5-step; the macro why. Always populated.
    └── sessions/        ← per-session, per-person: YYYY-MM-DD-<name>[-N].md
```

**The one rule** (pm `SDLC.md`): `docs/` + the tracker are authoritative;
`_pm/` records what I did and what I'm doing — never what is true. Decisions
go to `docs/adr/`, work items to the tracker, never to files in `_pm/`.

**Three tiers, an item only moves down:** `docs/intent/inbox.md` (loose, one
line, no status) → `docs/intent/<slug>.md` (shaped by `discovery`) →
`docs/TASKS.md` (work items — implementation, or a question whose answer is
the work; never a loose idea). Waiting is a tracker state: a `Waiting on:`
note on the item.

**The tracker** is `docs/TASKS.md`. A project that already runs another
system — GitHub Issues, a ticket folder, another tool's plans — replaces this
line with where its work items live, and the pm skills read and settle that
instead.

## The taxonomy — known folders, created on first write

**Never pre-create a folder.** Each of these exists the moment something is
first written into it (`mkdir -p` then write) — presence means it was needed.

| Folder | Purpose | Sprout when |
|---|---|---|
| `docs/notes/` | Scratch, meeting notes, ad-hoc Claude-generated analysis | first ad-hoc doc that isn't PM workflow |
| `knowledge/` | Curated project knowledge — always an OKF bundle (`okf` skill), never homegrown | facts turn entity-shaped: same tables/systems re-described across sessions, or a second consumer needs them |
| `resources/` | Material **you bring in** from outside the Claude-driven workflow (`design-handoff/`, `design-exploration/`, `research/`, `history/` as needed) | first external file arrives |
| `docs/agents/worker-env.md` | What a fresh worktree lacks, the repo's own verify command, off-limits paths (`sibling-sessions` reads it) | the first sibling session in this repo needs setup notes |
| `docs/agents/client-face.md` | Optional: names a client-facing tracker and its close-out steps; `stepping-away` follows it (contract in the pm `stepping-away` skill) | the client-face tool's own setup writes it |
| `_pm/transcripts/` | Meeting transcripts — client conversations, **gitignored** | first transcript kept (e.g. `granola-transcript` skill) |
| `_pm/artifacts/` | Other raw inputs — customer docs, exports, recordings | first raw input that isn't a transcript |
| `_pm/prototypes/` | HTML mockups for customer validation (code prototypes live in their surface container) | first validation mockup |
| `_pm/deliverables/` | What you hand to the client — reports, dashboards | first deliverable produced |
| `_app/` · `_ws/` · … | Code surfaces — **one underscore container per surface**, coined as surfaces emerge | the surface becomes real |

Claude-generated docs go in `docs/`; external material goes in `resources/` —
provenance decides, not file type. FileMaker-specific structure comes from the
fm-rcc plugin, not from sprouting here.

## The skeleton — default planning artifact

`_pm/skeleton.md`: outcome sentence → critical user journey → minimum
capabilities → fundamental enablers → non-negotiables. A paragraph for a
change-request job, a longer doc for a six-month engagement — one artifact,
scales with content.

## Sessions and the Intent block

`_pm/sessions/YYYY-MM-DD-<name>.md` — **one file per session, per person**,
append-only. Later sessions the same day take an ordinal (`-2`, `-3`), so two
people never collide and each session keeps its own Intent. Set an Intent block
(2–3 sentences: push, why, done-for-this-session, not-in-scope) at the session
open — `whats-next` drafts it; `stepping-away` closes with Shipped /
Tried-Learned-Decided / Intent-vs-outcome. Keep the allocator's exact session path and ID in the conversation/handoff; close by that binding, never by the newest filename. Reread the Intent/latest re-aim at resume, checkpoint, and the next ticket. A mid-session pivot is normally a
new session; `checkpoint` appends a dated re-aim only when the session can't be
broken. The session skills ship globally with the pm plugin — they are not
copied here.

## Working conventions

- **Skeleton first** — even a paragraph — before user stories or specs.
- **One session, one outcome.** `whats-next` opens, the work happens in that
  session, `stepping-away` closes and offers a fresh session for the next ready
  work. Two or three independent ready items
  can run as **sibling sessions** (pm `sibling-sessions` skill): each its own
  ordinary session through its own merge, nobody watching the others.
- **Outcome-sized items.** An item on the task list is a meaningful outcome,
  not every implementation step. Small direct requests need no item. Planning
  and additional review address named uncertainties, not every stage.
- **Discover only missing intent.** A clear request or accepted item proceeds
  to execution. Duration across sessions does not itself require a planning map.
- **One in, one out** (Wei Hao) — new request under fixed scope: "if this
  comes in, what comes out?" Document the trade in the session entry.
- **`whats-next` opens each session, `stepping-away` closes it.** The unit is
  the session, not the day — several a day is normal. Don't ramble; the skills
  handle the checklists.
- **One place for questions.** Real human dependencies live on their item in
  the tracker as `Waiting on:`. Present them together and continue independent
  work.

## Verifying your work

Before reporting any task done, fixed, or passing:

- **Run the check fresh** — after the last edit — and **paste its output**. Tests, build, lint, a real request, a screenshot: whichever would catch the failure you'd most plausibly have caused.
- The claim is exactly what the output supports. Red → report it verbatim. Partial → say which parts. Nothing runnable → say what *would* verify it and that it wasn't run.
- Fix the code, not the test. Never skip or delete a failing test to get green.

(The full self-report rule: the pm plugin's `verify-before-done` skill.)
