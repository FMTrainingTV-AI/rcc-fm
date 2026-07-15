#!/usr/bin/env python3
"""Thin wrapper around the vendored fmlint package.

Canonical entry point for validating fmxmlsnippet XML (or human-readable
script text) from the repo root:

    python3 scripts/validate_snippet.py <file-or-dir> [options]

All arguments are forwarded to `fmlint.__main__`. See that module's --help
for the full flag list, or scripts/fmlint/README.md for rule documentation.

The step catalog and default rule config ship inside the package
(scripts/fmlint/catalogs/, scripts/fmlint/fmlint.config.json), so this
wrapper works from any working directory without configuration.
"""

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from fmlint.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
