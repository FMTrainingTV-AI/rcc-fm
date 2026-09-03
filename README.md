# rcc-fm — RCC's Claude Code plugin marketplace

Two plugins for agentic development work.

**fm-rcc** — agentic FileMaker development: calculation language, paste-ready
validated XML, Save-as-XML/DDR schema analysis, and safe `.fmp12` patching
(backup → validate → verify → rollback), plus Data API / OData / ProofKit
integration and offline Claris docs lookup.

**pm** — the project-management layer used in the workshop: `/pm:pm-scaffold`
stands a project up, `whats-next` and `stepping-away` open and close a working
session, `checkpoint` re-aims a long one, `verify-before-done` gates completion
claims on fresh evidence, and a credential-guard hook blocks staging
credential-shaped files.

## Install

```bash
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install fm-rcc
/plugin install pm

# one-time per machine — the tools run on system python3
pip3 install lxml requests python-dotenv
```

Full documentation: [fm-rcc/README.md](fm-rcc/README.md) · [pm/README.md](pm/README.md).

---

Built by **Joe DaSilva** and **Richard Carlton**. © 2026 RCC — [MIT licensed](LICENSE).
