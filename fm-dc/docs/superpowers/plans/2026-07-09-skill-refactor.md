# fm-dc Skill Refactor — Split fm-core, add fm-saxml, prefix core skills

> **For agentic workers:** use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. Run the prompt battery + `pytest tests -q` after, before claiming done. Skill edits: follow superpowers:writing-skills.

**Goal:** Turn the current skill set (one fat `fm-core` catch-all + a DDR/SaXML conflation + mixed naming) into a set where **every skill owns one verb with a non-overlapping trigger**, so each is small enough to maintain and routing is clean.

**Three problems being fixed:**
1. `fm-core` is a kitchen sink doing five jobs, with a catch-all trigger ("whenever the user mentions FileMaker…") that crowds out the specific skills.
2. `ddr` conflates two genuinely different formats — classic DDR and the ascending Save-as-XML (SaXML). Workflow is shifting SaXML-ward; it deserves its own skill.
3. Naming is mixed. Decision: **`fm-` prefix = native FileMaker core**; **no prefix = third-party plugin** (`baseelements`, `mbs` stay unprefixed on purpose).

## Target skill set (10 skills — `ddr` renamed, not added)

| Skill | The one verb | Trigger centers on |
|---|---|---|
| `fm-core` | the **language** | calcs, functions, ExecuteSQL, JSON, text/date — formula-level questions |
| `fm-scripts` | **scripting** | script patterns, error handling, PSOS, AI steps, read/write scripts as XML |
| `fm-xml` | the **wire format** | generating/reviewing `fmxmlsnippet`, paste-safety, snippet grammar |
| `fm-saxml` ⬅ renamed from `ddr` | **schema analysis** (SaXML-first, DDR legacy input) | parse/summarize/refs/orphans/diff/readable from a Save-as-XML or classic DDR export |
| `fm-patch` | **mutate** files | the export→diff→apply→verify→rollback pipeline |
| `fm-connections` | **live data** | Data API / OData query, CRUD, schema, connection tests |
| `fm-proofkit` | **web** | ProofKit MCP, web viewers, TS toolchain, FM→web migration |
| `fm-docs` | **authoritative lookups** | "what does step X do", exact option names, version specifics |
| `baseelements` | **BE plugin functions** | `BE_*` functions (unprefixed — third-party) |
| `mbs` | **MBS plugin functions** | `MBS(...)` calls (unprefixed — third-party) |

## Part A — Break up `fm-core`

`fm-core` shrinks to **the FileMaker language only**. Redistribute the rest:

| Section leaving fm-core | Destination |
|---|---|
| Scripting Essentials, Error Handling, PSOS, AI Script Steps (FM 2024/2026), FM 2026 script-step highlights | → **`fm-scripts`** |
| "First-Party Docs on Demand" (curl the Claris markdown) | → **delete**; one-line pointer to `fm-docs` (the cache-backed, better version) |
| "MBS Plugin & Claude Code Integration" (clipboard round-trip) | → **delete**; one-line pointer to `mbs` (+ `fm-xml` for the snippet format) |
| "Migration: FileMaker to Web Stack" (Supabase/Vercel) | → **`fm-proofkit`** (owns the web-stack territory) |

**Stays in `fm-core`:** calc syntax (Let/Case/If), JSON functions, ExecuteSQL, text styling, date formatting, calc-level common patterns, schema/field naming conventions, the calc/SQL gotchas. Keep `references/calc-patterns.md`; move `references/script-patterns.md` → `fm-scripts/references/`.

**Trigger rewrite (the real routing fix):** `fm-core` stops being the net. New trigger = *calculations, formulas, functions, ExecuteSQL, JSON, text/date handling — the FileMaker language*. Explicitly **not** the default for scripts (→ fm-scripts), XML (→ fm-xml), or patching (→ fm-patch). Add a short "Related skills" pointer block so the agent hops to the specific skill.

**Fix stale references in fm-core:** it points at `filemaker-xml` / `filemaker-layout-xml` / `filemaker-field-xml` as skills — those were consolidated into **`fm-xml`**. Update.

## Part B — Rename `ddr` → `fm-saxml` (SaXML-first, single skill)

**Correction (found during implementation):** the `ddr` skill/tool *already* handles Save-as-XML — it auto-detects classic DDR vs FM 2026 split-catalog (`fmsaveasxml.py`) and already calls SaXML "preferred when available." So a *separate* `fm-saxml` skill would duplicate it. Instead:

- **`fm-saxml`** (renamed from `ddr`) — one schema-analysis skill, reframed **SaXML-first**: parse (split), summarize, trace refs/orphans, diff, and export the agent knowledge base. Classic DDR stays supported as the **auto-detected legacy input**, not a separate skill. Trigger centers on "I have a Save-as-XML / schema export and want to read/audit/diff it." `fm-` prefixed (native FM concept).
- **No `fm-ddr`.** One skill, both formats, named for the now-dominant one.
- **`fm-patch`** unchanged — still owns mutation. Boundary written into both: **`fm-saxml` reads/analyzes/diffs to understand; `fm-patch` mutates.**
- **Tool path `tools/ddr/ddr.py` stays** (internal; not renamed). The grammar spec (`fm-xml/references/ddr_xml_structure.md`) stays one physical file — no duplication, so both flags in the review are moot under the rename approach.

## Part C — Naming: `ddr` → `fm-saxml`, keep `baseelements` / `mbs` unprefixed

Decision: **`fm-` prefix = native FileMaker core; no prefix = third-party plugin.** So `ddr` → `fm-saxml` (native), while `baseelements` / `mbs` stay unprefixed (they're the actual plugin product names). Cross-references updated (grepped 2026-07-09):
- [x] `fm-dc/README.md` skills row (`ddr` → `fm-saxml`; fm-core re-scoped to the calc language; fm-scripts now owns scripting patterns)
- [x] top-level `README.md` fm-dc skills list (`ddr` → `fm-saxml`)
- [x] `skills/fm-scripts/SKILL.md` — "see the `ddr` skill" → `fm-saxml`; `filemaker-xml` → `fm-xml`
- [x] `templates/scaffold/CLAUDE.md:28` — "see the `ddr` skill" → `fm-saxml`
- [x] `skills/fm-core` — new Related-skills map points at `fm-saxml`
- [ ] `docs/superpowers/plans/2026-07-06-fm-dc-build.md` — historical; leave as-is (design history)
- [x] `tools/ddr/` path — **unchanged** (the Python tool dir is separate from the skill name)

## Tasks

- [ ] **A1** — Move scripting sections fm-core → fm-scripts; move `script-patterns.md`. Verify fm-scripts still reads coherently.
- [ ] **A2** — Delete docs-on-demand + MBS sections from fm-core; add pointers. Move migration → fm-proofkit.
- [ ] **A3** — Rewrite fm-core trigger (language-only) + fix `filemaker-xml`→`fm-xml` refs. Add Related-skills block.
- [ ] **B1** — Create `skills/fm-saxml/` (SKILL.md + references drawn from the SaXML grammar already in `fm-xml`/`fm-patch` refs; don't duplicate — reference or move).
- [ ] **B2** — `git mv skills/ddr skills/fm-ddr`; update `name:`; narrow trigger to classic DDR; add pointer to fm-saxml.
- [ ] **C1** — Update the cross-references in Part C.
- [ ] **D1** — Prompt battery: add routing cases (calc→fm-core, script→fm-scripts, SaXML export→fm-saxml, classic DDR→fm-ddr, snippet→fm-xml). Run it.
- [ ] **D2** — `pytest tests -q` (should stay 136 green — no tool code changes). Bump `fm-dc` → v0.4.0. Update READMEs (top + fm-dc). Commit + push.

## Risks / watch-outs

- **Don't duplicate SaXML grammar** across fm-xml, fm-saxml, fm-patch — pick one home (fm-saxml) and have the others point to it.
- **Trigger regressions** are the real risk — the prompt battery (D1) is the gate. If routing gets worse for any case, stop and reshape the trigger before shipping.
- Skill renames are safe (names are identifiers); the only breakage vector is unupdated cross-references — Part C enumerates them.
