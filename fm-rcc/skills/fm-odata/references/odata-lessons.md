# OData lessons — the two blockers, diagnosed

Backstory for the two hard rules in SKILL.md. Both came from a real session: "add a table to a live, hosted workshop file over OData." It worked — but only after two separate walls, each of which the bundled scripts now prevent.

## Blocker 1 — the MCP tools were the wrong instrument

**What happened:** the first instinct was the pre-installed FileMaker **MCP** OData tools (`fm_odata_*`). They failed before touching the file.

**Why:** those tools don't take a server / account / password. They expose a fixed set of **pre-configured connection IDs** baked into the MCP server's own config (e.g. `CONN_A`, `CONN_B`, `CONN_C`). Each points at a *different* database with *its own* stored credentials.

- The closest-named ID resolved to a *different* database entirely, and its stored credentials returned `Authentication failed … Invalid user account or password`.
- **None** of the IDs point at an arbitrary hosted file, and there is **no way to feed** supplied credentials into those tools.

**Root cause:** the MCP is a *fixed-connection* tool — great for databases someone already wired in, useless for a file you were just handed credentials for. Wrong tool, not a bug.

**Resolution / prevention:** talk to the OData endpoint **directly** with Basic auth. The bundled `odata_client.py` does exactly this.

## Blocker 2 — direct OData connected, but create-table failed (error 8310)

**What happened:** a small script hit the FileMaker Server **OData v4 REST endpoint** directly. The connection worked immediately (service root `HTTP 200`, all tables listed). But the first create-table returned:

```
HTTP 400  {"error": {"code": "8310", "message": "An internal data formatting error occurred (1)"}}
```

**Diagnosis:** reproduced with a one-line `curl` sending a single field — failed identically, proving the problem was the **request body**, not the script.

**Root cause:** wrong field-**type vocabulary.** The request used FileMaker type words (`string`, `date`, `numeric`); FileMaker's OData create-table API expects **SQL DDL** names (`VARCHAR(255)`, `DATE`, `NUMERIC`). "8310 internal data formatting error" is FileMaker's unhelpful way of saying "I don't recognize that field type."

**Resolution / prevention:** switch every field to a SQL DDL type ([Claris OData docs](https://help.claris.com/en/odata-guide/content/create-table.html)). The bundled `odata_client.create_table` **validates types client-side and rejects FileMaker-style names before sending**, so 8310 can't recur.

## The reusable takeaway

The scripts encode both lessons: they connect direct from supplied credentials (any hosted file), and validate/emit SQL DDL types. Two one-liners worth remembering:

1. **MCP OData tools = fixed, pre-wired connections.** New hosted file + its own credentials → go straight to the OData REST endpoint.
2. **OData create-table uses SQL types, not FileMaker types.** `VARCHAR(255)`, not `string`. `8310` = unrecognized field type.
