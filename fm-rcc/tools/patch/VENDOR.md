# Vendored: FM-Patch-Agent patch engine

- **Source:** FM-Patch-Agent (private upstream repo), commit `adf7c1d` (2026-06-14)
- **Vendored:** 2026-07-06, seven modules + `saxml_ignore.json`, logic unmodified
- **Tests:** vendored to `tests/patch/` with a new `conftest.py` that prepends this directory to `sys.path` (upstream relied on running pytest from `scripts/` cwd)
- **Modules:** `fm_export.py` (FMDeveloperTool wrapper), `saxml_parser.py`, `saxml_diff.py` (patchability tiers), `make_review.py` (HTML review artifact), `gen_patch.py` (diff→FMUpgradeTool patch, dependency graph), `apply_patch.py` (backup→validate→smoke→inplace→verify), `gen_scaffold.py` (spec-driven builds)
- **Upstream docs:** patchability matrix and workflow SOPs vendored into `skills/fm-patch/references/`
