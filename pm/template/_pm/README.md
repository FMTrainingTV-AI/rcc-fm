# _pm/ — personal project log

Per-person operational log. **Never authoritative**: `docs/` and the tracker
carry the shared truth; this folder records *what I did and what I'm doing*.
If `_pm/` disagrees with the tracker, the tracker wins. (The rule and the
stage chain: the pm plugin's `SDLC.md`.)

The `_` prefix groups it at the top of the listing and signals "container,
not a working folder" — same convention as code-surface containers
(`_app/`, `_ws/`).

## What's inside

| File/folder | Purpose |
|---|---|
| `skeleton.md` | The macro why — Wei Hao's 5-step. Always populated, even if just a paragraph. |
| `sessions/` | Per-session, per-person files: `YYYY-MM-DD-<name>.md`, then `-2`, `-3` for later sessions the same day. Intent block at the top, Shipped / Tried-Learned-Decided / Intent-vs-outcome at close. Append-only. |
| `transcripts/`, `artifacts/`, `prototypes/`, `deliverables/` | Created on first write — see the taxonomy in the root `CLAUDE.md`. |

## How the session skills use it

- **`whats-next`** (session open) reads intents, the tracker frontier, and
  recent sessions; drafts this session's Intent block into a new session file.
- **`stepping-away`** (session close) writes the session entry, settles the
  tracker, and compares Intent to outcome.
- **`checkpoint`** (only when a session can't be closed and reopened) adds a
  dated re-aim under the Intent and pushes the change into the affected
  tickets. Short sessions don't need it — the session boundary is the re-aim.

`_pm/` is portable: internal references stay local; outward references reach
`../docs/`, which exists in every stamped project.
