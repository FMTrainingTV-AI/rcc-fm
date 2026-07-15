# Vendored: DDR / Save-as-XML analysis engine

- **Source:** the author's prior FileMaker DDR analysis toolkit (private upstream, synced 2026-07-02)
- **Vendored:** 2026-07-06, logic unmodified
- **Modules:** `ddr.py` (CLI: split/summary/search/refs/orphans/compare/readable — auto-detects classic DDR and FM 2026 split-catalog), `fmsaveasxml.py`, `readable.py` (agent knowledge base), `ddr_xml_utils.py`, `test_fmsaveasxml.py`
- **Note:** fmlint lives separately at `tools/fmlint/` (wrapper `validate_snippet.py` + `fmlint/` package; upstream provenance in `tools/fmlint/fmlint/VENDOR.md`)
