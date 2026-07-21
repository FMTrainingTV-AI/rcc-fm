# schema/ — the analysis pipeline

```
ddrs/      raw Save-as-XML exports, one dated folder per export day
           (schema/ddrs/YYYY-MM-DD/saxml_run-*.xml) — tracked in git,
           so consecutive exports line up for diffing
parsed/    structured JSON derived from an export     ← gitignored
readable/  the agent-readable knowledge base (md)     ← gitignored
reports/   analysis writeups worth keeping — tracked
```

`parsed/` and `readable/` are **derived artifacts** — regenerate any time
with `python3 scripts/parse_saxml.py` (newest export) from the
engagement root. Only `ddrs/` (the source of truth) and `reports/` (human
work) are tracked.
