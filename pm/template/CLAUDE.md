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
│   ├── adr/             ← decisions (Matt's /domain-modeling format)
│   └── quirks.md        ← technical gotchas, fast-capture
└── _pm/                 ← PERSONAL log — per-person, append-only, never authoritative
    ├── README.md
    ├── skeleton.md      ← Wei Hao 5-step; the macro why. Always populated.
    └── sessions/        ← per-session, per-person: YYYY-MM-DD-<name>[-N].md
```

**The one rule** (pm `SDLC.md`): `docs/` + the tracker are authoritative;
`_pm/` records what I did and what I'm doing — never what is true. Decisions
go to `docs/adr/`, work items to the tracker, never to files in `_pm/`.

## The taxonomy — known folders, created on first write

**Never pre-create a folder.** Each of these exists the moment something is
first written into it (`mkdir -p` then write) — presence means it was needed.

| Folder | Purpose | Sprout when |
|---|---|---|
| `docs/notes/` | Scratch, meeting notes, ad-hoc Claude-generated analysis | first ad-hoc doc that isn't PM workflow |
| `knowledge/` | Curated project knowledge — always an OKF bundle (`okf` skill), never homegrown | facts turn entity-shaped: same tables/systems re-described across sessions, or a second consumer needs them |
| `resources/` | Material **you bring in** from outside the Claude-driven workflow (`design-handoff/`, `design-exploration/`, `research/`, `history/` as needed) | first external file arrives |
| `_pm/transcripts/` | Meeting transcripts — client conversations, **gitignored** | first transcript kept (e.g. `granola-transcript` skill) |
| `_pm/artifacts/` | Other raw inputs — customer docs, exports, recordings | first raw input that isn't a transcript |
| `_pm/prototypes/` | HTML mockups for customer validation (code prototypes live in their surface container) | first validation mockup |
| `_pm/deliverables/` | What you hand to the client — reports, dashboards | first deliverable produced |
| `_app/` · `_ws/` · … | Code surfaces — **one underscore container per surface**, coined as surfaces emerge | the surface becomes real |

Claude-generated docs go in `docs/`; external material goes in `resources/` —
provenance decides, not file type. FileMaker-specific structure comes from the
fm-dc plugin, not from sprouting here.

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
Tried-Learned-Decided / Intent-vs-outcome. A mid-session pivot is normally a
new session; `checkpoint` appends a dated re-aim only when the session can't be
broken. The session skills ship globally with the pm plugin — they are not
copied here.

## Working conventions

- **Skeleton first** — even a paragraph — before user stories or specs.
- **Anything non-trivial starts with `discovery`** → `docs/intent/<slug>.md`
  + a size call. Trivial edits: just do them.
- **One in, one out** (Wei Hao) — new request under fixed scope: "if this
  comes in, what comes out?" Document the trade in the session entry.
- **`whats-next` opens each session, `stepping-away` closes it.** The unit is
  the session, not the day — several a day is normal. Don't ramble; the skills
  handle the checklists.

## Verifying your work

Before reporting any task done, fixed, or passing:

- **Run the check fresh** — after the last edit — and **paste its output**. Tests, build, lint, a real request, a screenshot: whichever would catch the failure you'd most plausibly have caused.
- The claim is exactly what the output supports. Red → report it verbatim. Partial → say which parts. Nothing runnable → say what *would* verify it and that it wasn't run.
- Fix the code, not the test. Never skip or delete a failing test to get green.

(Deterministic backing and the full rule: the pm plugin's `verify-before-done` skill.)
