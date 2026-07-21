# specs/ — schema specs for scaffold builds

One JSON file per built solution. The spec is the **living source of truth**
for a built file's schema; re-running the scaffold workflow (runbook
`../workflow/07-scaffold-file.md`) reconciles the file to match —
additive-only, drift reported never destroyed.

Authored by Claude during a design conversation and **approved in chat** —
never hand-edited. Built `.fmp12` files land in `../dev/builds/` (binaries
never committed); specs ARE committed — they're the schema's history.

`crm.example.json` shows the shape: tables → fields, where a field is either
a bare type (`"text"`, `"date"`, `"fk"`) or an object with `type`, optional
`comment`, and for calcs a `result` + `formula`. The `IDText` /
`GetAsText ( ID )` calc-twin pattern exists because the Data API serializes
big UUIDNumber IDs lossily — web apps read IDs through the text twins.
