# logs/ — per-workflow run journals

One log file per workflow (`<workflow-name>.log.md`), appended **once per
run**, rolling ~10 entries. This is the institutional memory of the FM
workbench — "never trust the banner," the silent-calc class, and the
catalog-order rule were all captured this way before they hardened into the
runbooks and tools.

**The feedback loop: Run → Log → Reflect → Update the runbook or script →
next run is smarter.** When a log entry's learning gets baked into a runbook
or tool, the entry has done its job — prune it when the window rolls.

Entry format:

```markdown
## YYYY-MM-DD HH:MM
- **Status:** Success / Partial / Failed
- **Records:** X/Y processed
- **Issues:** What went wrong (or "None — clean run")
- **Learnings:** What was discovered that should inform future runs
```

The journals start empty on a fresh scaffold — the inherited learnings that
came out of past runs are already baked into the plugin's runbooks, tools,
and patchability matrix. What accumulates here is THIS project's history.
