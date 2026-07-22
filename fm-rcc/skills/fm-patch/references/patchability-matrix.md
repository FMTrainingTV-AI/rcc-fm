# Patchability Matrix — what FMUpgradeTool can and can't patch

*Last updated: 2026-07-22*

What works, what's sketchy, and what still has to be done by hand — the traffic-light map the pipeline actually enforces. Every tier here is grounded in real FMUpgradeTool runs (dated in the code) plus Claris's documented limits — not guesses.

## The three tiers (green / yellow / red)

The differ stamps every change with a tier (`scripts/saxml_diff.py`, `PATCHABILITY`); the generator (`gen_patch.py`) honors it.

| Light | Tier | Meaning | Gate |
|---|---|---|---|
| 🟢 Green | `proven` | Round-trip verified: generate → apply → re-export → identical | Auto — applied on operator approval |
| 🟡 Yellow | `caution` | Works, but a known failure mode lurks | Requires `gen_patch.py --allow-caution` |
| 🔴 Red | `manual` | The generator refuses — do it in FileMaker | Blocked; never auto-patched |

## The matrix — object type × operation

Operations map to FMUpgradeTool actions: **Add** = AddAction, **Change** = ReplaceAction, **Remove** = DeleteAction.

| Object type | Add | Change | Remove |
|---|---|---|---|
| Base tables | 🟢 proven | 🔴 manual | 🟡 caution |
| Fields | 🟢 proven⁶ | 🟡 caution | 🟡 caution |
| Table occurrences | 🟢 proven | 🔴 manual | 🟡 caution |
| Relationships | 🟢 proven | 🔴 manual | 🔴 manual |
| Layouts | 🟢 proven | 🔴 manual¹ | 🟡 caution |
| Scripts | 🟡 caution² | 🟡 caution² | 🟡 caution |
| Value lists | 🟡 caution | 🔴 manual | 🟡 caution |
| Custom functions | 🔴 manual³ | 🔴 manual³ | 🟡 caution |
| External data sources | 🟡 caution⁴ | 🔴 manual | 🔴 manual |
| **Accounts** | 🔴 manual | 🔴 manual | 🔴 manual |
| **Privilege sets** | 🔴 manual | 🔴 manual | 🔴 manual |
| **Extended privileges** | 🔴 manual | 🔴 manual | 🔴 manual |
| **Custom menus / menu sets** | 🔴 manual | 🔴 manual | 🔴 manual |
| **Themes** | 🔴 manual⁵ | 🔴 manual | 🔴 manual |
| **File access / security** | 🔴 manual | 🔴 manual | 🔴 manual |

¹ Adds carry the layout intact (the win), but a *changed* layout re-diffs forever — FMUpgradeTool renumbers internal layout ids and flips an Options bit on insert; we hash layouts through a per-instance view to detect real changes, but replacing one in place is not yet proven.
² Added scripts carry their full step bodies (validated by round trip). A *changed* script whose steps differ is **rejected** — ReplaceAction swaps the catalog entry only (name/options), and the format forbids carrying step bodies in a Replace, so it would silently keep the old steps.
³ Custom functions are effectively **untouchable by patch**. Add: silently no-ops — proven 2026-07-22 (FMUpgradeTool 22.0.5.500, same-lineage patch, two `<CustomFunction>` elements, "Patch File Applied", zero landed; corroborates the 2026-07-16 cross-lineage run where all 61 CFs no-opped). Change: **cannot be Replace'd** — an official App Upgrade Tool limitation. Deliver custom functions via clipboard XML (fm-xml skill) instead.
⁴ External data sources add the *reference* only; the path/credentials are environment-specific and still need a human.
⁶ **Container fields are the exception to the green tier**: a Container-datatype field Add silently no-ops (proven 2026-07-22 — validatePatch passed, smoke passed, banner printed, fields absent on re-export; only the verify caught it). It is the **datatype**, not the storage XML — a corrected `<Storage global="False" maxRepetitions="1"/>` no-oped identically. The differ forces container-field adds to `manual`; deliver them via clipboard XML.
⁵ Theme **Add is capability-proven for custom themes** (probe, 2026-07-16): theme definitions harvested verbatim from a full SaXML export, wrapped in the standard patch envelope, applied via AddAction through the normal validate → smoke → backup pipeline — both `com.filemaker.theme.custom.*` themes landed and survived the re-export oracle, consistency clean. A **built-in** theme name (`com.filemaker.theme.enlightened`) silently dropped — engine-reserved; most likely rule: custom themes patchable, built-ins never. The row stays red because `gen_patch.py` does not yet emit Theme AddActions (queued blend item: teach the generator + update `PATCHABILITY` + the matrix-lock tests). Related: the generator matches layout→theme dependencies by NAME, not UUID — so a base file pre-loaded with the source's themes unblocks that source's themed layouts.

## Why the yellow and red exist — the gotchas behind the tiers

- **The tool lies about success.** ReplaceAction can silently no-op: exit 0, banner says "Patch File Applied," zero effect. This is *why* every applied patch is re-exported and re-diffed. Never trust the banner.
- **SaveAsXML only emits "add" actions.** (Mislav Kos, Soliant — see Sources.) Modifications and deletions you build yourself, by hand, in the patch XML — which is exactly the surface area where things break.
- **Calcs arrive commented-out.** A calculation that references fields by name gets silently wrapped in `/* ... */` on apply unless the patch carries a `ModifyAction` re-apply pass mirroring SaveAsXML's own shape (`_calc_modify_action`).
- **Identity must be remapped.** Every new object needs a fresh UUID + a numeric id clear of production's id-space; the patch root version must match the export's SaXML version (FMDeveloperTool emits 2.2.3.0, FM Pro 2026 emits 2.3.0.0); `DDRREF` elements and `hash` attributes are stripped, and FMUpgradeTool stamps `SourceUUID`/`OwnerID` that must be stripped from content hashes or a perfect patch re-diffs as 100% changed.
- **Security and UI catalogs are off-limits.** Accounts, privilege sets, extended privileges, custom menus, file access — DeleteAction explicitly can't touch the privilege/accounts catalog, and the rest are unproven and high-risk. These stay human, always. (Themes are the one crack in this wall: Add is capability-proven for custom themes — see footnote 5 — but generator support is still queued, so the tier holds.)
- **Duplicates force manual.** Any object whose name collides (same name twice) is forced to `manual` — resolve the duplicate in FileMaker before patching.
- **Mid-patch abort at scale.** On a ~2,000-object patch, FMUpgradeTool printed "applied" but abandoned ~1,600 objects mid-patch — catalog-ordered: early catalogs landed, everything after silently dropped (observed 2026-07-16; a distinct mode from the per-object silent no-op). Countermeasures: the re-export verify catches it; **retry-before-drop** (re-apply a patch of just the unresolved objects before treating any of them as unpatchable — a one-bad-apply run otherwise looks like mass per-object refusal); **wave-apply** per catalog (tables+fields → TOs → relationships → VLs+CFs → scripts → layouts), verifying between waves; diagnose with `FMUpgradeTool -v` (verbose — the pipeline doesn't use it by default) to find where it stops.
- **Cross-lineage silent no-ops.** Applying objects exported from one file lineage onto a base from a different lineage hit a new no-op class: relationship and custom-function AddActions "applied" per the banner but never landed (all 76 relationships, all 61 CFs in the observed run), while tables/fields/TOs/scripts landed fine. **Update 2026-07-22: the custom-function part is not lineage-specific** — a same-lineage 2-CF patch no-oped identically, so CF Add is manual-tier outright (footnote 3). Relationships remain a cross-lineage-only observation. Levers for the relationship class: second-pass apply after tables/fields/TOs verify, `-v` diagnosis, `--regenerateGUIDs` on the base.
- **Silent no-ops are datatype-aware.** Container-field adds vanish exactly like custom functions (footnote 6) — the banner, validatePatch, and the smoke apply all pass. The lesson generalizes: *any* new object kind or datatype earns its green only from a re-export round trip, never from the apply pipeline's own success signals.

## Coverage vs. the universe — the "one of everything" file

Mislav Kos's [`ooe-fm`](https://github.com/mislavkos/ooe-fm) ("one of everything") file is the canonical corpus — one of every object type FileMaker can hold, exported to SaXML across FM 18→22. Its FM 22 export holds **17 object catalogs**.

- **9 catalogs the pipeline parses and tiers today** (verified 2026-06-14 — our parser ingests the OOE FM22 export cleanly across the version gap: 4 base tables, 42 fields, 7 table occurrences, 2 relationships, 41 scripts, 14 layouts, 4 value lists, 14 custom functions, 4 external data sources).
- **8 catalogs that are red/manual by design**: accounts, privilege sets, extended privileges, custom menus, custom menu sets, themes, file access, library/base-directory.

## The OOE conformance harness

**Phase 1 — BUILT** (`scripts/tests/test_ooe_conformance.py`, 5 tests, pure Python, no FileMaker tooling; vendored fixture under `scripts/tests/fixtures/ooe/`):

1. **Parse** the OOE export → snapshot, asserting exact counts for all 9 handled catalogs (✅ the parser ingests the FM22 file across the version gap).
2. **Diff tiers** — drop one real OOE object of each kind, diff, and assert every kind lands on its documented tier for **add** and **remove**; mutate a field/script/table and assert the **change** tiers (field/script = caution, table = manual).
3. **Matrix lock** — introspect the generator (`SUPPORTED_KINDS`, `REPLACE_TAGS`, `DELETE_ITEM_REF`) against `PATCHABILITY` and the documented oracle, so the slide/doc can't silently drift from the code.

This turns the matrix from "we believe" into "we tested, against the canonical file" for parse + diff + tier classification.

**Phase 2 — pending** (needs the Claris CLI + file open/close choreography): **Apply** each green/yellow change via FMUpgradeTool against a closed OOE copy → re-export → verify. OOE is FM 22, which aligns with the installed FMUpgradeTool 22.0.5. This is the pass that proves the *apply* end, not just classification.

## Sources

- Mislav Kos, Soliant — ["Using FMUpgradeTool to Patch FileMaker Apps"](https://www.soliantconsulting.com/blog/using-fmupgradetool-to-patch-filemaker-apps/) (Jul 2025) and ["FileMaker SaveAsXML and FMUpgradeTool: Building Automated Deployments"](https://www.soliantconsulting.com/blog/filemaker-saveasxml-fmupgradetool-building-automated-deployments/) (Aug 2025).
- [`ooe-fm`](https://github.com/mislavkos/ooe-fm) — the one-of-everything corpus.
- Claris **App Upgrade Tool Guide** (mirrored under `resources/.../app-upgrade-tool-guide/`).
- Project ground truth: `scripts/saxml_diff.py` (`PATCHABILITY`), `scripts/gen_patch.py` (header + `CATALOG_ORDER`, `REPLACE_TAGS`, `DELETE_ITEM_REF`).
