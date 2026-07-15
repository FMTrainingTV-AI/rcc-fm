# Vendor Notes — fmlint

## Source

Vendored from **agentic-fm** (John Petrowsky) on 2026-04-21.

- Upstream repo: https://github.com/petrowsky/agentic-fm
- Upstream path: `agent/fmlint/`
- License: Apache 2.0 (see `LICENSE` in this directory)
- Upstream commit: shallow clone `main` on 2026-04-21 (commit not pinned — see `git log` of `/tmp/agentic-fm-src/` if regenerating)

Also vendored:

- `catalogs/step-catalog-en.json` — copied from upstream `agent/catalogs/step-catalog-en.json`. Single source of truth for all 180+ FileMaker script steps (step IDs, parameter schemas, block-pair relationships, selfClosing flags, help URLs).

## Why vendored rather than pip-installed

Upstream ships a `pyproject.toml` but doesn't publish to PyPI. The module is pure stdlib, so there's no dependency resolution to gain from pip. Vendoring keeps this toolkit self-contained and lets us upgrade deliberately rather than silently.

## Local modifications

Kept to the minimum needed to make the package importable from our layout. Everything else is verbatim so upstream updates can be re-pulled cleanly.

### `__init__.py`
- Docstring import example: `from agent.fmlint import …` → `from fmlint import …`
- Added pointer to this VENDOR.md.

### `__main__.py`
- Module docstring CLI examples updated from `python3 -m agent.fmlint …` → `python3 -m fmlint …`.
- `_resolve_project_root()` reduced to `return None`. The catalog lookup now happens inside the package (see engine.py change below), so there's no sibling `agent/` tree to walk up to.
- Removed the default target fallback to `agent/sandbox/`. Path argument is now required (the CLI still supports any file or directory).
- `--path` help text updated accordingly.

### `engine.py`
- `LintRunner.__init__` catalog-path resolution: first looks for `fmlint/catalogs/step-catalog-en.json` inside the package (the vendored location). Falls back to upstream behaviour (`{project_root}/agent/catalogs/step-catalog-en.json`) only if the vendored catalog is missing.

### Not modified

- All 18 rule modules (`rules/*.py`, `formats/*.py`)
- `config.py`, `context.py`, `catalog.py`, `types.py`
- `fmlint.config.json` (built-in defaults)
- `README.md` — upstream documentation kept as reference. Its `agent.fmlint` and `agent/sandbox/` references describe upstream usage, not our CLI. **Use `scripts/validate_snippet.py` as the canonical entry point from this repo.**
- `rules/best_practices.py` contains two docstring references to `agent/docs/knowledge/`. Not reached unless we create that tree.

## How to refresh from upstream

```bash
# 1. Clone upstream fresh
git clone --depth 1 https://github.com/petrowsky/agentic-fm.git /tmp/agentic-fm-src

# 2. Diff against current vendored copy to see what's new
diff -r /tmp/agentic-fm-src/agent/fmlint/ scripts/fmlint/ | grep -v '^Only in scripts/fmlint/:'

# 3. Copy changes, reapplying the local patches above
cp -r /tmp/agentic-fm-src/agent/fmlint/. scripts/fmlint/
cp /tmp/agentic-fm-src/agent/catalogs/step-catalog-en.json scripts/fmlint/catalogs/

# 4. Re-apply the patches listed above
#    (They're small — reading this file top-to-bottom is faster than scripting them.)

# 5. Update the Vendored-on date at the top of this file.
```

## Tier availability in this repo

- **Tier 1 (offline)**: always. All `S`, `N`, `D`, `B`, and `C001–C003` rules. This is what you get by default.
- **Tier 2 (context)**: not wired up yet. Requires a `CONTEXT.json` in the solution-specific layout agentic-fm expects. Planned in Phase 2 of the integration — see `docs/changelog/2026-04-21.md`.
- **Tier 3 (live FM eval)**: intentionally out of scope for this repo. Depends on OData + companion server.
