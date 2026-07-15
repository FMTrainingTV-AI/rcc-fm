# One-of-Everything (Ooe) — Source Reference

## What it is

**One-of-Everything (Ooe)** is a FileMaker file containing one of every kind of FileMaker object — every script step, field type, layout object, relationship type, value list, privilege set, custom function, custom menu, etc. It is the canonical reference for working with FileMaker's XML formats (DDR and SaXML).

**Author:** Mislav Kos, Claris Practice Director of Engineering at Soliant Consulting  
**Repo:** https://github.com/mislavkos/ooe-fm  
**License:** Check repo (public GitHub)

## Context

Mislav presented Ooe at his August 5, 2025 presentation on SaveAsXML and the FMUpgradeTool, alongside Soliant's PatchLab, the SaXML Delivery toolchain, and the SaXML Exploder. The purpose of Ooe is exactly what the name implies — a FileMaker file with one of every kind of object, useful as a reference when working with SaXML, diffing patches, or testing tooling that has to handle every catalog/object type.

## Files in the repo

```
fm/
  Ooe.fmp12           (1.8 MB) — main file, FM credentials: admin/admin, restapi/restapi
  BrojDva.fmp12       (946 KB) — secondary test database, EAR password: admin

saxml_utf8/           — SaveAsXML exports, UTF-8 encoded (20 files)
saxml_utf16le/        — SaveAsXML exports, UTF-16 LE as exported by FileMaker (12 files)
saxml_paths_depth_4/  — path summaries of SaXML structure (text files)
scripts/              — shell scripts for regenerating exports via FMDeveloperTool
```

## SaXML file naming convention

`[DatabaseName]__saxml_v[SaxmlVersion]__fm_v[FMVersion][__ddr_info].xml`

Example: `Ooe__saxml_v2_2_3_0__fm_v22_0_4__ddr_info.xml`

Files with `__ddr_info` have `Has_DDR_INFO="True"` in the root element and include additional DDR metadata.

## SaXML versions by FM version

From the repo README (kept up-to-date with FMDeveloperTool ⚡️):

| FM Version | SaXML Version |
|------------|---------------|
| 22.x       | 2.2.3.0 ⚡️  |
| 21.x       | 2.2.3.0 ⚡️  |
| 20.x       | 2.2.3.0 ⚡️  |
| 19.x       | 2.1.x         |
| 18.x       | 2.0.x         |

## What was extracted (2026-05-05, FM 22.0.4)

The `saxml_utf8/Ooe__saxml_v2_2_3_0__fm_v22_0_4.xml` file (2.63 MB) was parsed to produce **210 unique script step IDs** — the complete catalog of every script step in FM 22 — which fed the starter's original step-catalog reference.

Key finding from this extraction: `Perform Script on Server` is **id="164"** in FM 22, not 170 as was previously documented. ID 170 does not exist in FM 22.

> **Where step-ID knowledge lives now (2026-07):** the original hand-maintained `step-catalog.md` / `xml-snippets.md` references were retired in favor of the vendored **`filemaker-xml`** skill (Andy Kear's round-trip-verified spec, 220+ steps incl. FM 2026) for *generation*, and **`scripts/fmlint/catalogs/step-catalog-en.json`** (from agentic-fm) for *validation*. OOE remains the ground-truth instrument for verifying either against a new FM release.

## How to refresh when a new FM version ships

1. Download `fm/Ooe.fmp12` from the repo (check if Mislav has pushed an updated version)
2. Open in the new FM version
3. Export: File → **Save a Copy as** → XML (FM 2026+) or File → Manage → **Database Design Report** → XML → drop in `schema/ddrs/YYYY-MM-DD/`
4. Parse: `python3 scripts/ddr.py split schema/ddrs/YYYY-MM-DD/Summary.xml schema/parsed/`
5. Diff the step IDs against `scripts/fmlint/catalogs/step-catalog-en.json` (validation catalog) and the `filemaker-xml` skill's references (generation spec) to find new/changed/removed steps
6. Update the fmlint catalog for anything it's missing; check whether Kear has shipped an updated skill release before patching his

Alternatively, pull the pre-built SaXML file from the repo:
```bash
curl -s "https://raw.githubusercontent.com/mislavkos/ooe-fm/main/saxml_utf8/Ooe__saxml_v[VERSION]__fm_v[FMVER].xml" -o /tmp/ooe_saxml.xml
```
Then run the Python extraction to diff against the current catalogs.

## Format note: SaXML ≠ fmxmlsnippet

The SaXML (`<FMSaveAsXML>`) format is a **different XML format** than the clipboard `fmxmlsnippet` format. They both represent FileMaker objects but with different element structures:

- **SaXML**: uses `<ParameterValues>` with `<Parameter type="...">` children and numeric `<Options>` bitmasks
- **fmxmlsnippet**: uses named child elements (`<NoInteract state="True"/>`, `<Calculation>`, etc.) and is what FileMaker's clipboard accepts

Step IDs are the same in both formats. The `filemaker-xml` skill's references document the fmxmlsnippet side; `docs/reference/ddr_xml_structure.md` documents the SaXML/DDR side.
