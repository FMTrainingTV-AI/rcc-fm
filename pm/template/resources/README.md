# resources/

External inputs — things *you* bring in from outside the Claude-driven workflow. Same taxonomy as the other starters in Joe's library.

**The split — where things go:**

- `resources/` — **you bring it in** from outside (design handoffs, research, third-party docs).
- `artifacts/` — **you bring it in** specifically as project inputs (transcripts, customer docs, exports). The line between `resources/` and `artifacts/` is intentionally blurry; rule of thumb: if it's about the *project's domain or methodology*, use `resources/`; if it's an *input the customer or system provided*, use `artifacts/`.
- `docs/` — **Claude-managed prose** about the work (TASKS, sessions, decisions, notes, quirks).
- `requirements/`, `prototypes/`, `deliverables/` — Claude-generated or you-produced project outputs.

If you're stuck on which side something belongs on: did *you* bring it in (`resources/` or `artifacts/`), is it *prose about the work* (`docs/`), or is it a *generated output* (`requirements/`, etc.)?

## Layout

- **`design-handoff/`** — claude.ai/design bundles: brief, prototype HTML, chat transcripts, CSS. **Read first if a UI task is on deck.**
- **`design-exploration/`** — in-progress mockups, visual iterations, and design briefs you're drafting yourself.
- **`research/`** — market overviews, competitive analyses, methodology references, third-party docs.
- **`history/`** — milestone records: scaffold notes, significant migrations, one-offs worth remembering after the fact. `YYYY-MM-DD-<topic>.md`.

Each subfolder has its own README. If material doesn't fit any of these, create a new subfolder with a short README — better a new home than the wrong one.
