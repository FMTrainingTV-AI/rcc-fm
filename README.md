# rcc-fm — RCC's Claude Code plugin marketplace

Three plugins for agentic development work. They run on Claude Code alone.

**fm-rcc** — agentic FileMaker development: calculation language, paste-ready
validated XML, Save-as-XML/DDR schema analysis, and safe `.fmp12` patching
(backup → validate → verify → rollback), plus Data API / OData integration
and offline Claris docs lookup.

**pm** — the project-management layer used in the workshop: `/pm:pm-scaffold`
stands a project up with a `docs/TASKS.md` task list, `whats-next` and
`stepping-away` open and close a working session and keep that list current,
`checkpoint` re-aims a long one, `sibling-sessions` runs independent items side
by side, `verify-before-done` gates completion claims on fresh evidence, and a
credential-guard hook blocks staging credential-shaped files. `adversary-review`
hands a risky change to a fresh Claude subagent that tries to break it, and
`ship-acceptance` checks a deliverable against its accepted intent.

**sdlc** — enforcement installed once per repo: `gate-hooks` puts a gate in the
repo's `.claude/` (production commands, protected paths, a test lock for bug
fixes), and `review-policy` sets up `REVIEW.md` with a read-only reviewer.

## Install

```bash
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install fm-rcc
/plugin install pm
/plugin install sdlc

# one-time per machine — the tools run on system python3
pip3 install lxml requests python-dotenv
```

Full documentation: [fm-rcc/README.md](fm-rcc/README.md) · [pm/README.md](pm/README.md) · [sdlc/README.md](sdlc/README.md).

---

Built by **Joe DaSilva** and **Richard Carlton**. © 2026 RCC — [MIT licensed](LICENSE).
