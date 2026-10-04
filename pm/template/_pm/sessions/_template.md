# YYYY-MM-DD — <name> — session N

_One file per session. The day's first session is `YYYY-MM-DD-<name>.md`;
later ones that day take an ordinal: `-2`, `-3`. Set N to match._

Session-ID: <allocator UUID>
Started: <ISO-8601 timestamp>

_Keep this exact path and ID in the conversation/handoff. Use scripts/session.py to allocate and close; append Closed: <timestamp> only when closing._

## Intent

_Set at the session open, before executing. Two or three sentences: what we're pushing on, why it matters, what done-for-this-session looks like, anything explicitly not in scope. Scope it to this session, not the whole day. Reread the Intent and latest re-aim at resume/context recovery, before the next item, and at checkpoint._

_Example:_ Pushing on the search filter UI — Sandy's manual workaround is costing her ~20 min/day, and a working filter unlocks the rest of the search flow. Done for this session is the prototype validated by Sandy. Not touching filter persistence or multi-category yet.

_Skip for quick fixes._

_Mid-session pivots: prefer closing the session and opening a new one with a fresh Intent — that's the clean re-aim. When the session can't be broken (a long charting run, a task already in flight), leave this block as written and let the `checkpoint` skill append a dated **Re-aimed <timestamp>** section at the end (earlier re-aims stay; the file is append-only). The latest re-aim is the live aim._

## Shipped

- _Tight bullets. Files touched by path. Link commits if relevant. Omit if nothing shipped._

## Tried / Learned / Decided

_Narrative. What was explored, what didn't work, pivots and why. Be candid — "tried X, abandoned because Y" beats silence._

## Intent vs. outcome

_Session-close check (handled by `stepping-away`). Did we hit done-for-this-session? Did we stay in scope? If we drifted: deliberate pivot or unnoticed drift, and what caused it. If the intent itself turned out wrong, say so — that correction belongs in `docs/intent/<slug>.md`, not just here._

## Open threads

- _"Hey future me" callouts — read at the next session open. Questions for the customer. Anything not yet a task worth not losing._
