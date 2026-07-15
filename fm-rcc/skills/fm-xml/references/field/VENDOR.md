# Vendored Skill — Provenance

**Source:** https://github.com/andykear/FileMaker-XML-field-definitions
**Author:** Andy Kear
**License:** CC BY 4.0 (attribution required) — see README.md badge and license section
**Vendored:** 2026-07-02, commit `968792a` (upstream date 2026-06-28)
**Local patches:** none — copied verbatim (SKILL.md, references/, README.md; `.git` excluded)

Covers FileMaker field definition XML (`fmxmlsnippet type="FMObjectList"` with `<Field>` elements) for pasting into Manage Database: all data/field types, auto-enter mechanisms, validation, storage variants, FM 2026 `<Annotation>` + `<DisplayNames>`. Note: pasting requires the MBS Plugin to be installed in FileMaker Pro (presence only, no scripting).

## Refreshing from upstream

```bash
git clone --depth 1 https://github.com/andykear/FileMaker-XML-field-definitions.git /tmp/kear-field
rsync -a --exclude='.git' --exclude='VENDOR.md' /tmp/kear-field/ .claude/skills/filemaker-field-xml/
```

Then update the commit hash + date above. Keep this file.
