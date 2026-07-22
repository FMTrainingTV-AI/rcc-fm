---
name: fm-xml
description: >
  The FileMaker XML wire format — generating paste-ready fmxmlsnippet XML for scripts,
  custom functions, layout objects, and field definitions; reviewing snippet XML for
  silent paste-handler failures; and the fmxmlsnippet element/step-ID grammar itself.
  Use whenever the user wants FileMaker XML generated from a description or pseudocode,
  mentions LayoutObjectList or FMObjectList, asks about the XML SHAPE of a script step or
  field definition, or needs a snippet's format reviewed/validated. This owns the FORMAT.
  To modify a pasted script's logic/targets against THIS project's schema → fm-scripts
  (it drives the round-trip and consults this skill for the shape). To parse/audit a whole
  Save-as-XML or DDR export → fm-saxml. Do not attempt FileMaker XML from memory alone —
  always load the matching guide below first.
---

# FileMaker XML

One skill owns "producing or reading FileMaker XML." Route by task, load only the guide you need (each is self-contained with worked examples):

| Task | Load |
|---|---|
| Script XML or custom-function XML (generate, modify, review) | [references/snippets/GUIDE.md](references/snippets/GUIDE.md) — 220+ step IDs, element ordering, silent-failure rules, FM 2026 steps |
| Layout object XML (fields, portals, tab controls, popovers, button bars, web viewers — all 18 object types) | [references/layout/GUIDE.md](references/layout/GUIDE.md) — always run its theme pre-flight before generating |
| Field definition XML for Manage Database (auto-enter, validation, calc/summary fields) | [references/field/GUIDE.md](references/field/GUIDE.md) — note: pasting field defs requires the MBS plugin |
| Understanding a Save-as-XML / DDR export's structure (catalogs, references, step text) | [references/ddr_xml_structure.md](references/ddr_xml_structure.md) |
| Ground truth for any XML shape question | [references/ooe-source.md](references/ooe-source.md) — Mislav Kos's One-of-Everything file, the canonical corpus |

## Non-negotiable rules

1. **Validate every snippet before it goes anywhere near FileMaker:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/tools/fmlint/validate_snippet.py <file-or-dir>
   ```
   Catches unbalanced blocks, unknown step names, unclosed calculations, naming/documentation issues. No exceptions — a snippet that fails lint does not get pasted or patched. (Use a throwaway temp file for the lint; don't leave it in the user's project.)
2. **Never invent XML shape from memory.** The shape comes from the guides and the OOE corpus; the model's job is slotting values into known shapes. If a shape isn't covered, say so and check a real export rather than guessing.
3. **DEFAULT output: the paste-ready XML, inline on screen.** Present the generated `fmxmlsnippet` / layout XML **in the chat, in a fenced code block the user copies** — the user pastes it into FileMaker themselves (scripts into the Script Workspace, layout objects in Layout mode). **Do NOT save it to a file** unless the user explicitly asks, and **never hand over pseudo-code instead of the XML.** Only reach for the patch pipeline (fm-patch / fm-patch-builder) when the user asks to *apply* the change to a `.fmp12`, not merely to see the XML.
4. **Round-trip edits of an existing database's scripts** (paste in → modify with schema awareness → paste back) are the fm-scripts skill's job — it layers this skill's formats over the project's `schema/readable/` knowledge base.
5. **Name references resolve byte-for-byte — whitespace included.** FileMaker's paste handler resolves script/layout/field references by exact name match. Names with decorative whitespace (e.g. FMSP-style scripts named `     (0306) Go To Projects`, five leading spaces) must be reproduced exactly, or the reference lands unresolved — silently. When generating a `Perform Script` step against an existing file, copy the name from the schema knowledge base, never retype it.
