---
name: fm-core
description: >
  The FileMaker calculation language — formula syntax, functions, ExecuteSQL, JSON, text
  styling, date/number handling, and calc-level patterns and gotchas. Use for questions
  about writing or fixing a calculation or formula, Let/Case/If, JSONGetElement/JSONSetElement,
  ExecuteSQL queries, TextStyleAdd/TextColor, date formatting for APIs, or field/table naming
  conventions. This is the language foundation — NOT the default for every FileMaker task.
  Route elsewhere: scripts/script steps/AI steps → fm-scripts; fmxmlsnippet or Save-as-XML
  wire format → fm-xml; schema audit from an export → fm-saxml; patching a file → fm-patch;
  Data API/OData → fm-connections; exact doc lookups → fm-docs.
---

# FileMaker Calculation Language

The foundation layer: how to write correct FileMaker **calculations** — syntax, functions, SQL, JSON, text, dates. For anything above the formula level, hop to the related skill (see the map at the bottom).

- Detailed patterns: `references/calc-patterns.md` (JSON handling, text formatting, ExecuteSQL recipes).

## Version naming map

| Marketing name | Internal version |
|---|---|
| FileMaker 2023 | 20 |
| FileMaker 2024 | 21 (AI steps originated here) |
| FileMaker 2025 | 22 |
| FileMaker 2026 | 26 — number jumped to match the year |

For authoritative, per-version behavior and exact option names, use the **`fm-docs`** skill (local-first Claris docs) rather than answering from memory.

## Calculation fundamentals

### Syntax rules
- Line separator: `¶` (pilcrow) for carriage returns in text; `&` for concatenation
- String delimiter: double quotes `"` — escape with `\"` inside strings
- Comparison: `=`, `<>` (not equal), `<`, `>`, `≤`, `≥`
  - **IMPORTANT**: use `<>` not `≠` in calculations — `≠` causes issues in some contexts
- Boolean: `True` / `False` or `1` / `0`
- Comments: `/* comment */` or `// comment`
- Null/empty: `""` — FileMaker has no null concept; empty string is the closest
- Field references: `TableOccurrenceName::FieldName`

### Core functions

**Let (single or multiple variables):**
```
Let ( [
  _var1 = "value" ;
  _var2 = SomeField ;
  _var3 = _var1 & " " & _var2
] ;
  _var3
)
```
- `_` prefix is convention for Let variables; `$var` = script-scoped; `$$var` = file-scoped global

**Case:**
```
Case (
  condition1 ; result1 ;
  condition2 ; result2 ;
  defaultResult
)
```

**If (calc function, not the script step):** `If ( condition ; trueResult ; falseResult )`

### JSON functions (FM 16+)
```
JSONSetElement ( json ; keyOrPath ; value ; type )
JSONGetElement ( json ; keyOrPath )
JSONListValues ( json ; keyOrPath )           // value-per-line from an array
JSONListKeys ( json ; keyOrPath )
JSONFormatElements ( json )                   // pretty-print; returns "?" on invalid JSON
JSONDeleteElement ( json ; keyOrPath )
```
- Types: `JSONString` (1), `JSONNumber` (2), `JSONObject` (3), `JSONArray` (4), `JSONBoolean` (5), `JSONNull` (6), `JSONRaw` (0)
- Nested access: `JSONGetElement ( $json ; "ratings.overall" )`
- Validate: `Left ( JSONFormatElements ( $json ) ; 1 ) <> "?"`

### Text styling
```
TextStyleAdd ( text ; Bold )        TextStyleAdd ( text ; Bold + Italic )
TextStyleRemove ( text ; AllStyles )
TextColor ( text ; RGB ( r ; g ; b ) )        TextSize ( text ; pointSize )
```
- Only renders in text fields on layouts / merge fields; number & date result types ignore styling.

### ExecuteSQL
```
ExecuteSQL ( "SELECT field FROM TableOccurrenceName WHERE id = ?" ; fieldSep ; rowSep ; arg1 )
```
- **Uses table occurrence (TO) names**, not base table names. If the base table is `DataAPI` but the TO is `zDataAPI`, use `FROM zDataAPI` — the base name returns `?`.
- Use `?` placeholders — prevents injection, handles quoting
- Returns `?` on error — always check: `Left ( $result ; 1 ) <> "?"`
- **Read-only** — no INSERT/UPDATE/DELETE. Date literals: `DATE '2026-04-13'`.
- FM 2026: FileMaker SQL adds `FOREIGN KEY` in `CREATE/ALTER TABLE` and quoted `"ROWID"`/`"ROWMODID"`; `ExecuteSQL()` itself stays read-only.

### Date formatting for APIs
```
Year ( Get ( CurrentDate ) ) & "-" &
Right ( "0" & Month ( Get ( CurrentDate ) ) ; 2 ) & "-" &
Right ( "0" & Day ( Get ( CurrentDate ) ) ; 2 )
```
Guarantees YYYY-MM-DD regardless of the user's system date format.

### FM 2026 new calc functions
`FieldAnnotation`, `BaseTableComment`, `FieldDisplayNames`, `GetPersistentData`, `ListPersistentDataIDs`, `Get(WindowUUID)`, `Get(AccountPasswordDaysRemaining)`, `Get(GuidedAccessState)`, `GetEmbedding` (Cohere image embeddings).

## Common calc patterns

### Display calc for JSON data
```
Let ( [
  _json = Table::JsonField ;
  _valid = not IsEmpty ( _json ) and Left ( JSONFormatElements ( _json ) ; 1 ) <> "?"
] ;
  Case ( not _valid ; "" ;
    Let ( [ _val1 = JSONGetElement ( _json ; "key1" ) ] ;
      TextStyleAdd ( "Label" ; Bold ) & "¶" & _val1
    )
  )
)
```

### Bullet list from JSON array
```
Let ( [ _items = JSONListValues ( _json ; "arrayKey" ) ] ;
  Case ( IsEmpty ( _items ) ; TextStyleAdd ( "None" ; Italic ) ;
    "• " & Substitute ( _items ; "¶" ; "¶• " )
  )
)
```

### API key retrieval via ExecuteSQL
```
Set Variable [$apiKey ;
  Trim ( ExecuteSQL ( "SELECT APIKey_AI FROM zDataAPI WHERE DataAPIID = ?" ; "" ; "" ; 1 ) )
]
```

### Collect related data
```
Set Variable [$qaText ; List ( RelatedTable::TextField )]
```
`List()` across a relationship returns all related values, one per line — respects the relationship sort order; no null-check needed (empty relationship → empty).

## Schema & naming conventions

- **Tables:** utility/system tables prefix `z` (`zFormSubmission`, `zDataAPI`); junction `TableA_TableB`; meaningful TO names on the graph.
- **Fields:** PK `TableNameID`; FK matches the parent (`ClientID`); timestamps `CreationTimestamp` / `ModificationTimestamp`; audit `CreatedBy` / `ModifiedBy`; display/calc fields descriptive (`AI_Summary`, `Name_First_Last`).

## Calc & SQL gotchas

1. **Get ( CurrentDate ) format varies by system** — always format explicitly for APIs.
2. **JSONGetElement returns empty string for missing keys** — not an error, not "null".
3. **ExecuteSQL uses table occurrence names** — `FROM DataAPI` fails if the TO is `zDataAPI`.
4. **List() on an empty relationship returns empty** — safe without null checking.
5. **TextStyleAdd only visible in text fields** — number/date result types ignore it.
6. **FileMaker "null" is empty string** — when building JSON, use `JSONNull` explicitly.
7. **The `≠` operator** — works in most contexts but can misbehave; prefer `<>`.

---

## Related skills (hop here — don't do their job in fm-core)

| Task | Skill |
|---|---|
| Write/modify a **script**, error handling, PSOS, **AI script steps** | `fm-scripts` |
| Generate/review **fmxmlsnippet** or read Save-as-XML **wire format** | `fm-xml` |
| **Audit** a schema from a DDR / Save-as-XML export | `fm-saxml` |
| **Patch** / deploy changes into a `.fmp12` | `fm-patch` |
| **Data API / OData** query or CRUD | `fm-connections` |
| Exact **doc** lookup (step semantics, option names, versions) | `fm-docs` |
| BaseElements (`BE_*`) or MBS (`MBS(...)`) **plugin** functions | `baseelements` / `mbs` |
| **Web app** against FileMaker, or migrating off FileMaker | `fm-proofkit` |
