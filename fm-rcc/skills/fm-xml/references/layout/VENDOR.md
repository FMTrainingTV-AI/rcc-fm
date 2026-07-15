# Vendored Skill — Provenance

**Source:** https://github.com/andykear/FileMaker-XMLsnippet-Layout-Claude-Skill
**Author:** Andy Kear
**License:** CC BY 4.0 (attribution required) — see README.md badge and license section
**Vendored:** 2026-07-02, commit `2c0e78f` (upstream date 2026-06-28)
**Local patches:** none — copied verbatim (SKILL.md, references/, README.md; `.git` excluded)

Covers FileMaker layout object XML (`fmxmlsnippet type="LayoutObjectList"`): all 18 layout object types, object flag bits, element ordering, script triggers, conditional formatting, hide conditions, theming pre-flight, FM 2026 `CanEntryCalc`. Round-trip verified (generate → paste → save → compare).

## Refreshing from upstream

```bash
git clone --depth 1 https://github.com/andykear/FileMaker-XMLsnippet-Layout-Claude-Skill.git /tmp/kear-layout
rsync -a --exclude='.git' --exclude='VENDOR.md' /tmp/kear-layout/ .claude/skills/filemaker-layout-xml/
```

Then update the commit hash + date above. Keep this file.
