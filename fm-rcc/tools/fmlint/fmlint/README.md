# FMLint

A rule-based linter for FileMaker scripts. Validates both **fmxmlsnippet XML** (the clipboard format agents produce) and **human-readable (HR) script text** (what developers write and read).

FMLint is designed to be flexible — every rule can be enabled, disabled, or tuned via a JSON config file. Teams with different coding standards can adjust the linter to match their conventions rather than fighting a fixed set of opinions.

---

## Quick Start

```bash
# Lint all XML files in the sandbox
python3 -m agent.fmlint agent/sandbox/

# Lint a specific file
python3 -m agent.fmlint agent/sandbox/MyScript.xml

# Lint a human-readable script
python3 -m agent.fmlint --input-format hr path/to/script.txt

# JSON output for programmatic use
python3 -m agent.fmlint --format json agent/sandbox/

# Use a custom config
python3 -m agent.fmlint --config path/to/fmlint.config.json agent/sandbox/

# Disable specific rules for this run
python3 -m agent.fmlint --disable N002,D001 agent/sandbox/
```

**Exit codes:** `0` = no errors or warnings, `1` = errors found, `2` = warnings only.

---

## Rule Categories

Rules are organized into six categories, each with a letter prefix. The prefix tells you at a glance what kind of issue a rule catches.

### S — Structure

Structural integrity of the script. These rules catch problems that would cause FileMaker to reject the script or behave incorrectly at paste time.

| ID | What It Checks |
|----|----------------|
| S001 | XML is well-formed (parseable) |
| S002 | Root element is `<fmxmlsnippet type="FMObjectList">` |
| S003 | Output is steps only — no `<Script>` wrapper tags |
| S004 | Every `<Step>` has required attributes (`enable`, `id`, `name`) |
| S005 | Block pairs are balanced: If/End If, Loop/End Loop, Open Transaction/Commit Transaction |
| S006 | Else ordering: Else If must come before Else, no duplicate Else |
| S007 | Inner steps are inside their required block: Exit Loop If inside Loop, Else inside If |
| S008 | Step name exists in the step catalog |
| S009 | XML self-closing form matches catalog expectation |
| S010 | Script contains no steps (empty file) |
| S011 | XML comments detected — FileMaker silently discards `<!-- -->` on paste |

### N — Naming & Conventions

Coding style and formatting preferences. These are the most team-specific rules — what one team considers standard, another may not use at all.

| ID | What It Checks |
|----|----------------|
| N001 | ASCII operators (`<>`, `<=`, `>=`) instead of Unicode (`≠`, `≤`, `≥`). **Disabled by default** — both forms are valid FM |
| N002 | Variable names follow configured patterns (`$camelCase`, `$$ALL_CAPS`, etc.) |
| N003 | Boolean variables use descriptive prefixes (`$isActive`, `~hasPermission`) |
| N004 | Multi-line calculations use the configured indent character (tab or space) |
| N005 | Space after semicolons in function calls |
| N006 | Alignment padding (extra spaces for column alignment). **Disabled by default** |
| N007 | Single-line `Let()` with multiple variables — suggests multi-line formatting |

### D — Documentation

Script documentation practices. These help maintain readable, self-documenting scripts.

| ID | What It Checks |
|----|----------------|
| D001 | First step is a comment containing a configurable keyword (default: `PURPOSE:`) |
| D002 | Scripts that read `Get(ScriptParameter)` should have a doc block (disabled Insert Text → configurable variable, default `$README`) |
| D003 | Scripts over a configurable step count (default: 20) have no blank comment lines for section separation |

### R — References

Cross-references against CONTEXT.json or index files. These are **tier 2** rules — they only run when context data is available.

| ID | What It Checks |
|----|----------------|
| R001 | Field name in `Table::Field` reference exists in context |
| R002 | Field ID in XML matches CONTEXT.json |
| R003 | Layout name exists in context |
| R004 | Layout ID in XML matches CONTEXT.json |
| R005 | Script name in Perform Script exists in context |
| R006 | Script ID in XML matches CONTEXT.json |
| R007 | Table occurrence name is recognized in context |
| R008 | CONTEXT.json is older than a configurable threshold (default: 60 minutes) |
| R009 | Reserved for scope mismatch detection (stub) |

### B — Best Practices

Common scripting patterns that help avoid bugs. These are suggestions based on FileMaker development experience.

| ID | What It Checks |
|----|----------------|
| B001 | `Set Error Capture [On]` without a `Get(LastError)` check within a configurable number of subsequent steps (default: 10) |
| B002 | Script navigates to a layout but has no `Commit Records/Requests` step anywhere — uncommitted edits may be lost |
| B003 | Reserved for parameter validation checking (stub, **disabled by default**) |
| B004 | Script has no `Exit Script` step — callers can't check the result |
| B005 | `?` character in a calculation — FileMaker has no ternary operator. Skips non-calculation steps like Insert Text |

### C — Calculations

Calculation expression analysis. Tier 1 rules check syntax offline. Tier 3 rules validate against a live FileMaker engine.

| ID | What It Checks |
|----|----------------|
| C001 | Unclosed string literal (odd number of `"` in calculation) |
| C002 | Unbalanced parentheses |
| C003 | Function name not in built-in FM function list. Custom functions can be added via config (`extra_known_functions`) |
| C004 | **Tier 3 only.** Calculation fails when evaluated by the live FM engine via AGFMEvaluation over OData |
| C005 | **Tier 3 only.** Reserved for non-fatal evaluation issues (stub) |
| C006 | HTML/XML entities (`&gt;`, `&lt;`, `&amp;`, `&ge;`, `&le;`) in calculation expressions — these must be literal operators inside CDATA blocks |

---

## Validation Tiers

FMLint operates in three progressive tiers based on what data is available:

| Tier | When Available | What It Adds |
|------|---------------|--------------|
| **1 — Offline** | Always | All S, N, D, B, and C001–C003 rules. Needs only the step catalog. |
| **2 — Context** | CONTEXT.json or index files present | Adds R001–R009 (reference validation against the solution) |
| **3 — Live FM** | OData configured + FM Server reachable | Adds C004–C005 (calculation evaluation against the live FM engine) |

The tier is auto-detected. Override with `--tier N` on the CLI.

---

## Configuration

FMLint loads configuration from JSON files in this priority order (later files override earlier ones):

1. **Built-in defaults** — `agent/fmlint/fmlint.config.json` (shipped with the linter)
2. **Project-level overrides** — `agent/config/fmlint.config.json` (gitignored, per-solution)
3. **CLI override** — `--config path/to/file.json`
4. **CLI flags** — `--disable` takes highest priority

### Config file format

A config file contains a `rules` object where each key is a rule ID:

```json
{
  "rules": {
    "N001": {
      "enabled": true,
      "severity": "warning"
    },
    "C003": {
      "extra_known_functions": ["MyCustomFunc", "FormatPhone"]
    }
  }
}
```

You only need to include the rules you want to change — everything else inherits from the defaults.

### Common customizations

**Suppress custom function warnings:**

The most common source of noise in real solutions. Add your custom function names to C003:

```json
{
  "rules": {
    "C003": {
      "extra_known_functions": [
        "FormatPhone", "fmErrorMessage", "CardWindowHeight",
        "getLayoutID", "dateFormatForQBO"
      ]
    }
  }
}
```

**Change variable naming conventions:**

If your team uses `$snake_case` for locals and `$$PascalCase` for globals:

```json
{
  "rules": {
    "N002": {
      "patterns": {
        "$$~": { "regex": "^\\$\\$~[A-Z][A-Z0-9._]*$", "label": "$$~ALL_CAPS" },
        "$$":  { "regex": "^\\$\\$[A-Z][a-zA-Z0-9]*$",  "label": "$$PascalCase" },
        "~":   { "regex": "^~[a-z][a-z0-9_]*$",          "label": "~snake_case" },
        "$":   { "regex": "^\\$[a-z][a-z0-9_]*$",        "label": "$snake_case" }
      }
    }
  }
}
```

The patterns are regular expressions. Each key (`$$~`, `$$`, `~`, `$`) is a variable prefix — the linter matches the longest prefix first, then tests the variable name against that prefix's regex.

Set `"allow_repetition_suffix": true` (the default) to accept `$var[1]` repetition syntax.

**Change the documentation keyword:**

If your team uses `DESCRIPTION:` instead of `PURPOSE:`:

```json
{
  "rules": {
    "D001": {
      "keyword": "DESCRIPTION:",
      "case_sensitive": false
    }
  }
}
```

**Change the doc block variable:**

If your team uses `$DOC` instead of `$README`:

```json
{
  "rules": {
    "D002": {
      "doc_variable": "$DOC"
    }
  }
}
```

**Prefer spaces over tabs in calculations:**

```json
{
  "rules": {
    "N004": {
      "indent_char": "space"
    }
  }
}
```

**Adjust error capture lookahead:**

If your error handling pattern puts more steps between `Set Error Capture` and the error check:

```json
{
  "rules": {
    "B001": {
      "lookahead_steps": 20
    }
  }
}
```

**Adjust section separation threshold:**

If you want the section separator suggestion to apply only to scripts with 50+ steps:

```json
{
  "rules": {
    "D003": {
      "min_steps": 50
    }
  }
}
```

**Adjust context staleness threshold:**

```json
{
  "rules": {
    "R008": {
      "stale_minutes": 120
    }
  }
}
```

**Enable the Unicode operator rule:**

If your team follows filemakerstandards.org conventions:

```json
{
  "rules": {
    "N001": {
      "enabled": true,
      "severity": "warning"
    }
  }
}
```

### Severity levels

Each rule can be set to one of four severity levels:

| Level | Meaning | CLI exit code |
|-------|---------|---------------|
| `error` | Will break in FileMaker or is a definite bug | 1 |
| `warning` | Likely problem or convention violation | 2 |
| `info` | Style suggestion | 0 |
| `hint` | Minor recommendation | 0 |

Change any rule's severity in your config:

```json
{
  "rules": {
    "B002": { "severity": "warning" },
    "D001": { "severity": "error" }
  }
}
```

---

## Programmatic Use

```python
from agent.fmlint import lint

result = lint(content, fmt="xml", project_root=".")

for d in result.diagnostics:
    print(f"{d.severity.value} [{d.rule_id}] line {d.line}: {d.message}")

print(f"OK: {result.ok}")  # True if no errors
```

### JSON output

```bash
python3 -m agent.fmlint --format json agent/sandbox/MyScript.xml
```

Returns:

```json
{
  "files": [
    {
      "source": "agent/sandbox/MyScript.xml",
      "ok": true,
      "error_count": 0,
      "warning_count": 2,
      "diagnostics": [
        {
          "rule_id": "N002",
          "severity": "warning",
          "message": "Variable \"$Bad_Name\" does not match...",
          "line": 5,
          "column": 0,
          "end_line": 0,
          "end_column": 0
        }
      ]
    }
  ],
  "summary": {
    "total_files": 1,
    "files_with_errors": 0,
    "total_errors": 0,
    "total_warnings": 2
  }
}
```

---

## TypeScript / Webviewer

FMLint has a TypeScript implementation at `webviewer/src/linter/` that runs a subset of tier 1 rules directly in the Monaco editor for instant feedback while typing.

### Shared config

The TypeScript linter reads the same `fmlint.config.json` as the Python linter. On startup, the Monaco diagnostics provider fetches the merged config from the webviewer API server (`GET /api/lint-config`), which loads and merges:

1. Built-in defaults (`agent/fmlint/fmlint.config.json`)
2. Project-level overrides (`agent/config/fmlint.config.json`)

This means a single config file controls both the CLI linter and the editor diagnostics. If you disable N001 in the config, it stops firing in both places.

### Available TypeScript rules

The TypeScript linter implements a subset of rules optimized for real-time feedback:

| Rule | What It Checks |
|------|----------------|
| S005 | Block pairing: If/End If, Loop/End Loop (includes S006 Else ordering, S007 inner step context) |
| S008 | Unknown step names vs. step catalog |
| N001 | ASCII operators (disabled by default, same as Python) |
| C001 | Unclosed string literals |
| C006 | HTML/XML entities in calculations (same as Python) |
| D001 | PURPOSE comment on first line |

For the full rule set (tier 2 references, tier 3 live eval, all N/B/C rules), the webviewer calls the Python linter via the companion server's `POST /lint` endpoint.

### TypeScript API

```typescript
import { createLinter, fetchLintConfig } from '@/linter';
import type { LintConfig } from '@/linter';

// Load config from server (reads fmlint.config.json)
const config: LintConfig = await fetchLintConfig();

// Create linter with catalog and config
const linter = createLinter(catalog, config);

// Lint HR script text
const result = linter.lint(scriptText);

for (const d of result.diagnostics) {
  console.log(`${d.severity} [${d.ruleId}] line ${d.line}: ${d.message}`);
}
```

### Monaco integration

The diagnostics adapter at `webviewer/src/linter/diagnostics-adapter.ts` wires FMLint into Monaco's marker system:

- `createLintDiagnosticsProvider(editor, catalog)` — attaches the linter to a Monaco editor. Fetches config on init, debounces validation at 300ms, sets markers with source `fmlint(ruleId)`.
- `updateConversionDiagnostics(model, errors)` — separate marker source for HR-to-XML conversion errors.

### Extending with new TypeScript rules

Rules are registered via side-effect imports in `webviewer/src/linter/index.ts`. To add a new rule:

1. Create a file in `webviewer/src/linter/rules/`
2. Implement the `LintRule` interface and call `registerRule()`
3. Import the file in `index.ts`

```typescript
import { registerRule } from '../engine';
import { isRuleEnabled, getRuleSeverity } from '../config';
import type { LintConfig } from '../config';
import type { Diagnostic } from '../types';

registerRule({
  ruleId: 'X001',
  name: 'my-custom-rule',
  severity: 'warning',
  check(lines: string[], catalog: Set<string>, config: LintConfig): Diagnostic[] {
    if (!isRuleEnabled('X001', config)) return [];
    const sev = getRuleSeverity('X001', 'warning', config);
    // ... rule logic
    return [];
  },
});
```

### File layout

```
webviewer/src/linter/
  index.ts                Public API: createLinter(), fetchLintConfig()
  engine.ts               Rule registry and runner
  types.ts                Diagnostic, Severity, LintResult
  config.ts               Config loading, isRuleEnabled(), getRuleSeverity()
  diagnostics-adapter.ts  Monaco marker integration
  rules/
    structure.ts          S005/S006/S007, S008
    naming.ts             N001
    calculations.ts       C001
    documentation.ts      D001
```

---

## File Layout

```
agent/fmlint/
  __init__.py           Public API: lint(), lint_file(), LintRunner
  __main__.py           CLI entry point
  engine.py             Rule registry, runner, tier detection
  types.py              Diagnostic, Severity, LintResult, ParsedHRLine
  config.py             Config file loading and merging
  catalog.py            Step catalog lazy loader
  context.py            CONTEXT.json + index file loader
  fmlint.config.json    Built-in default configuration
  pyproject.toml        For standalone pip installation
  formats/
    detect.py           Auto-detect XML vs HR format
    xml_parser.py       fmxmlsnippet XML parser
    hr_parser.py        Human-readable script parser
  rules/
    __init__.py          Imports all rule modules
    structure.py         S001–S011
    naming.py            N001–N007
    documentation.py     D001–D003
    references.py        R001–R009
    best_practices.py    B001–B005
    calculations.py      C001–C003
    live_eval.py         C004–C005
```
