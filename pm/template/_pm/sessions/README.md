# Sessions

One file per **session**, per person: `YYYY-MM-DD-<name>.md` for the day's
first session, then `YYYY-MM-DD-<name>-2.md`, `-3.md` for later ones (`<name>`
= your short handle). Per-person and append-only, so two people on the same
day never collide and the log never needs merging. Per-session because a
session is the working unit — each one gets its own Intent, its own close, and
its own Intent-vs-outcome. Captures what shipped AND the thinking behind it —
tried, learned, decided, dead-ended.

## Workflow

- **Session open:** `whats-next` creates this session's file from
  [`_template.md`](_template.md) and drafts the Intent block.
- **Mid-session pivot:** normally, close the session and open a new one with a
  fresh Intent. When the session can't be broken, `checkpoint` adds a dated
  re-aim line under the Intent — each re-aim is appended; the latest is live.
- **Session close:** `stepping-away` writes Shipped / Tried-Learned-Decided /
  Intent-vs-outcome and settles the tracker.
- **Sessions that produced nothing don't need a file.**

Durable decisions don't live here — they go to `docs/adr/`. Sessions are the
narrative; the tracker and `docs/` are the truth.
