# Vendored: FM-Patch-Agent patch engine

- **Source:** FM-Patch-Agent (private upstream repo), commit `adf7c1d` (2026-06-14)
- **Vendored:** 2026-07-06, seven modules + `saxml_ignore.json`, logic unmodified
- **Tests:** vendored to `tests/patch/` with a new `conftest.py` that prepends this directory to `sys.path` (upstream relied on running pytest from `scripts/` cwd)
- **Modules:** `fm_export.py` (FMDeveloperTool wrapper), `saxml_parser.py`, `saxml_diff.py` (patchability tiers), `make_review.py` (HTML review artifact), `gen_patch.py` (diff→FMUpgradeTool patch, dependency graph), `apply_patch.py` (backup→validate→smoke→inplace→verify), `gen_scaffold.py` (spec-driven builds)
- **Upstream docs:** patchability matrix and workflow SOPs vendored into `skills/fm-patch/references/`
- **NOT vendored — fm-rcc-native, lives here because it drives the engine:** `xml_to_fmp12.py` (added 2026-07-21). Builds a new `.fmp12` from a Save-as-XML export by copying `resources/fmbase.fmp12` and growing it through this pipeline (diff → gen → apply → verify, with gen-prune and verify-prune feedback loops). Creation-only, so it sits outside the operator selection gate. Origin: DC-Project-Builder `_fm/scripts/xml_to_fmp12.py`; changed on import to resolve the tools dir and base file from its own location instead of globbing the installed plugin cache, and to look for exports under the CWD.
- **Local changes:**
  - 2026-07-21: `saxml_ignore.json` — added `PK_*` to the script ignore patterns. Evidence: a converter run's verify pass caught `PK_get_proofkit_app_info` as a silent no-op; ProofKit's newer runtime scripts use the `PK_` prefix, which postdates the vendored `ProofKit*`-only patterns.
