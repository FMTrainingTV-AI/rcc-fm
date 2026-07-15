# OOE fixture — the "one of everything" conformance corpus

`Ooe__saxml_v2_2_3_0__fm_v22_0_4.xml.gz` is a gzipped FileMaker Save-as-XML export of
**Mislav Kos's `Ooe.fmp12`** ("One Of Everything") — a sample file that aims to contain
one of every kind of FileMaker solution element.

- **Source:** <https://github.com/mislavkos/ooe-fm> (commit `27711f1`)
- **License:** MIT (see `LICENSE` in this folder — © 2025 mislavkos)
- **This export:** SaXML format `2.2.3.0`, FileMaker `22.0.4`, UTF-8 (the non-DDR variant).

Used by `scripts/tests/test_ooe_conformance.py` to verify the pipeline against the
canonical corpus: the parser ingests every catalog, and the differ assigns each object
kind the documented patchability tier (the green/yellow/red matrix in
`docs/patchability-matrix.md`). Gzipped (~654 KB vs 2.5 MB raw) to keep the repo lean;
the test decompresses to a temp dir.

To refresh: re-clone `ooe-fm`, then
`gzip -c saxml_utf8/Ooe__saxml_v2_2_3_0__fm_v22_0_4.xml > Ooe__saxml_v2_2_3_0__fm_v22_0_4.xml.gz`.
