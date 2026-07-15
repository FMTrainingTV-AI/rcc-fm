# rcc-fm — RCC's Claude Code plugin marketplace

Home of **fm-rcc**, a Claude Code plugin for agentic FileMaker development:
calculation language, paste-ready validated XML, Save-as-XML/DDR schema
analysis, and safe `.fmp12` patching (backup → validate → verify → rollback),
plus Data API / OData / ProofKit integration and offline Claris docs lookup.

## Install

```bash
/plugin marketplace add FMTrainingTV-AI/rcc-fm
/plugin install fm-rcc

# one-time per machine — the tools run on system python3
pip3 install lxml requests python-dotenv
```

Full documentation: [fm-rcc/README.md](fm-rcc/README.md).

---

Built by **Joe DaSilva** and **Richard Carlton**. © 2026 RCC — [MIT licensed](LICENSE).
