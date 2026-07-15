#!/usr/bin/env python3
"""Environment doctor for fm-rcc: are the pieces in place to patch FileMaker files?

Checks the Claris CLI tools, Python dependencies, and project .env. Run by
/fm-rcc:fm-init before anything else, or standalone:

    python3 tools/doctor.py
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

CLARIS_BIN = Path("/usr/local/bin")


def _which_claris(tool: str) -> str | None:
    found = shutil.which(tool)
    if found:
        return found
    candidate = CLARIS_BIN / tool
    return str(candidate) if candidate.exists() else None


def run_checks(cwd: Path | None = None) -> list[dict]:
    cwd = cwd or Path.cwd()
    results: list[dict] = []

    for tool in ("FMDeveloperTool", "FMUpgradeTool"):
        path = _which_claris(tool)
        results.append({
            "name": tool,
            "ok": path is not None,
            "detail": path or f"not found (install FileMaker Server command-line tools; expected in {CLARIS_BIN})",
        })

    for mod, label in (("lxml", "python-lxml"), ("requests", "python-requests")):
        present = importlib.util.find_spec(mod) is not None
        results.append({
            "name": label,
            "ok": present,
            "detail": "importable" if present else f"missing — pip install {mod}",
        })

    env = cwd / ".env"
    results.append({
        "name": "env-file",
        "ok": env.exists(),
        "detail": str(env) if env.exists() else "no .env in project (needed only for server connections, not local patching)",
    })

    return results


def main() -> int:
    results = run_checks()
    width = max(len(r["name"]) for r in results)
    for r in results:
        mark = "ok " if r["ok"] else "MISSING"
        print(f"{r['name']:<{width}}  [{mark:^7}]  {r['detail']}")
    claris_ok = all(r["ok"] for r in results if r["name"] in ("FMDeveloperTool", "FMUpgradeTool"))
    return 0 if claris_ok else 1


if __name__ == "__main__":
    sys.exit(main())
