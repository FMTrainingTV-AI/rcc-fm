# `docs/agents/client-face.md` — the contract

pm never names a client-facing tool. A repo opts in by placing this file; the
tool's own plugin or skill supplies it. `stepping-away` reads it at close and
follows what it says. Until a real producer ships one, the hook is
**unintegrated and optional**: absence means silence, and a present file is
followed as written, not certified as client integration.

The file must answer, in plain prose or short tables:

1. **Where the close-out steps are.** Either inline, or a path or skill name
   the agent can open. pm does not guess.
2. **What local evidence the steps consume.** At minimum: the ticket path or
   the commit, and the ticket's `Client-ref:` line if it has one.
3. **What to do in each of three cases:**
   - **fully shipped** — every repo item behind the client-facing work is done;
   - **partly shipped** — some are, the rest are still open;
   - **ticketless** — a change shipped from a session Intent with no ticket.
4. **What counts as done** for the close-out itself, so `stepping-away` can
   report it or say it was skipped.

Anything else (ids, list names, voice rules, attachments) is the producer's
business and lives in the file or where it points. `stepping-away` quotes the
matching step for the case at hand, offers it, and records in the session
entry whether it was done, skipped, or blocked.
