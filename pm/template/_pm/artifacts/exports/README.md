# Exports

Exports from systems you're integrating with or replacing. Schemas, screenshots, configuration dumps.

## What goes here

- FileMaker DDR XML (if the project touches FM — typically `exports/ddr/YYYY-MM-DD/`)
- Database schemas (SQL dumps, Prisma schemas, JSON Schema)
- Screenshots of existing UI
- API documentation exports from existing systems
- Postman collections or similar

## Why exports, not raw `schema/` or `data/`

In code starters (`datacraft-fm` etc.) there's a dedicated `schema/` pipeline. This starter is codebase-agnostic — `exports/` is a neutral home for whatever you exported. If the project becomes companion-mode with a code starter, the code starter's structured pipeline (e.g. FM's `schema/ddrs/` + `schema/parsed/`) takes over and this folder becomes "miscellaneous exports."
