# Vendored Skill — Provenance

**Source:** https://github.com/andykear/FileMaker-XMLsnippet-Claude-Skill
**Author:** Andy Kear
**License:** CC BY 4.0 (attribution required) — see README.md badge and license section
**Vendored:** 2026-07-02, commit `0906585` (upstream date 2026-06-28)
**Local patches:** none — copied verbatim (SKILL.md, references/, README.md; `.git` excluded)

Covers FileMaker script + custom-function XML in the `fmxmlsnippet` clipboard format: 220+ step IDs, element-ordering rules, silent paste-handler failure modes, FileMaker 2026 steps (PDF category, Configure Persistent Data, image captions). Progressive loading via the SKILL.md routing index.

## Refreshing from upstream

```bash
git clone --depth 1 https://github.com/andykear/FileMaker-XMLsnippet-Claude-Skill.git /tmp/kear-script
rsync -a --exclude='.git' --exclude='VENDOR.md' /tmp/kear-script/ .claude/skills/filemaker-xml/
```

Then update the commit hash + date above. Keep this file.
