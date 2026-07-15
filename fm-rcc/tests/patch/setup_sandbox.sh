#!/bin/bash
# Builds the sandbox from the repo's own tracked fixtures (portable across
# machines — no external repo dependency). If the Claris CLI tools are
# installed, also produces the exports/snapshots/diff the integration tests use.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FX="$ROOT/tests/patch/fixtures"
SB="$ROOT/sandbox"
PY="$ROOT/.venv/bin/python"
mkdir -p "$SB"
cp -f "$FX/dev.fmp12"  "$SB/dev.fmp12"
cp -f "$FX/prod.fmp12" "$SB/prod.fmp12"
echo "sandbox fixtures ready: $SB (account Admin, empty password)"
if [ -x /usr/local/bin/FMDeveloperTool ] && [ -x "$PY" ]; then
  echo "Claris tools found — building exports, snapshots, and diff…"
  "$PY" "$ROOT/tools/patch/fm_export.py" "$SB/dev.fmp12"  -o "$SB/dev.xml"  --stamp-guids
  "$PY" "$ROOT/tools/patch/fm_export.py" "$SB/prod.fmp12" -o "$SB/prod.xml" --stamp-guids
  "$PY" "$ROOT/tools/patch/saxml_parser.py" "$SB/dev.xml"  -o "$SB/dev_parsed"
  "$PY" "$ROOT/tools/patch/saxml_parser.py" "$SB/prod.xml" -o "$SB/prod_parsed"
  "$PY" "$ROOT/tools/patch/saxml_diff.py" "$SB/dev_parsed" "$SB/prod_parsed" -o "$SB/diff.json"
  echo "sandbox fully built — integration + E2E tests will run"
else
  echo "FMDeveloperTool or .venv missing — only fixture .fmp12s staged"
  echo "(install FileMaker Server command-line tools for the full pipeline)"
fi
