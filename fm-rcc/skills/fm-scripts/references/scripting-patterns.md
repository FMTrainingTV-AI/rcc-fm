# FileMaker Scripting Patterns & Step Reference

Script structure, error handling, PSOS, and the FM 2024–2026 AI/script-step catalog. (Calc-level syntax, JSON, and ExecuteSQL live in the `fm-core` skill; XML wire format in `fm-xml`.)

## Standard script structure

Every script should follow this pattern:
1. `# (comment)` — script purpose
2. `Set Error Capture [On]`
3. `Allow User Abort [Off]`
4. Parameter parsing (if applicable)
5. Validation / early exits
6. Main logic
7. Error handling
8. Commit Records
9. Exit Script with result

## Error handling pattern

```
Set Error Capture [On]
# ... do something ...
Set Variable [$error ; Get ( LastError )]
If [$error <> 0]
  # Handle error — log, show dialog, or exit
  Exit Script [0]
End If
```

## Variable scoping

- `$var` — local to current script execution
- `$$var` — global, persists until file closes or explicitly cleared
- **Convention**: prefix with purpose: `$apiKey`, `$qaText`, `$response`

## Perform Script on Server (PSOS)

- Runs on FileMaker Server — no layout context, no dialogs
- Cannot access global variables from the client
- Pass data via script parameter, return via Exit Script [result]
- **Common gotcha**: steps that require layout context (Insert Text, Go to Field, etc.) fail silently on server

## Insert Text vs Set Variable

- `Insert Text` inserts literal text into a field or variable — great for long multi-line text (like AI instructions) because you avoid CDATA/concatenation complexity. Line breaks are `&#13;` in the XML.
- `Set Variable` evaluates a calculation — use for dynamic values, field references, function calls
- **Insert Text requires layout context** for fields (not for variables) — won't work via PSOS when targeting a field
- **Rule of thumb**: Insert Text for long literal strings (instructions, templates); Set Variable for everything else.

## AI script steps (FM 2024+)

**Configure AI Account:**
```
Configure AI Account [Account Name: "name" ; API Key: $apiKey ; Model Provider: ChatGPT]
```
- Model Provider options (docs call it "Model Provider"; older snippets say "Model Type"): **ChatGPT** (OpenAI), **Anthropic** (Claude — native in FM 22), **Gemini** (Google — native in FM 26), **Custom** (any OpenAI-compatible endpoint, requires Endpoint URL ending with `/`)
- Claris AI Model Server = **Custom** provider with the endpoint from Admin Console (e.g. `"https://myserver.example.com/llm/v1/"`)
- Account name is a label you define — used to reference in Generate Response
- Account is per-file, per-session — cleared when the file closes
- Model name strings: `gpt-4o` / `gpt-4o-mini` for ChatGPT; `claude-sonnet-4-5` / `claude-opus-4` etc. for Anthropic; check Claris tech specs for currently recommended models per provider

**Generate Response from Model:**
```
Generate Response from Model [
  Account Name: "name" ;
  Model: $model ;
  User Prompt: $prompt ;
  Instructions: $instructions ;
  Response: $response
]
```
- `Instructions` = system prompt (persistent context/persona)
- `User Prompt` = the actual request with variable data
- Response goes into a variable or field
- Inject dynamic context (dates, IDs, user info) into the User Prompt, not Instructions
- Check `Get ( LastError )` immediately after — network/API failures are common
- Stream option: On = incremental delivery, Off = wait for complete response

**Best practice for AI prompts returning JSON:**
- Instructions: define the persona, output format, and rules
- User Prompt: include the data + `"Today's date is " & <formatted date>`
- Always include: "Return ONLY the JSON object. No markdown, no commentary, no code fences."
- Validate response with `Left ( JSONFormatElements ( $response ) ; 1 ) <> "?"`

## FM 2026 AI additions

- **Insert Image Caption** / **Insert Image Captions in Found Set** — send container images to an image-captioning model, caption into field/variable. **Claris AI Model Server only** (Custom provider account).
- **Generate Response from Model** gains **Include tool calls and tool results** — richer saved message history for agentic flows. (Also fixed in 26: with Stream off, the message-history variable now populates.)
- **Parameters option** on Insert Embedding / Insert Embedding in Found Set / Perform Semantic Find — pass provider-specific params like `dimension`. `CURLOPT_TIMEOUT` key sets a max request time (seconds) on Generate Response, NL query steps, and Perform RAG Action.
- **Perform RAG Action** now returns the document ID on add (store it for later removal), accepts per-request Similarity Threshold / Top-N, and has a **Tokens per Text Chunk** option.
- **Field annotations** — per-field AI description set in Advanced Options for Field ("Add annotation in DDL"); sent to models by Perform SQL Query / Find by Natural Language without touching field comments. Read via new `FieldAnnotation()`; `GetFieldsOnLayout()` includes them.
- Cohere image embeddings supported on the embedding steps and `GetEmbedding()`.

## FM 2026 non-AI script-step highlights

- **Persistent data store** — named values saved in the schema (not records): app version, JS libraries for web viewers, fixed AI prompts, add-on config. `Configure Persistent Data` script step + `GetPersistentData()` / `ListPersistentDataIDs()`.
- **PDF script step suite** — Create / Open / Append / Close / Cancel / Print PDF compose multi-source PDFs in memory; Save Records as PDF gains **Save to** (path, container, variable, or append to open PDF).
- **Window UUID** — Select/Close/Move-Resize/Set Window Title can target by UUID; `Get(WindowUUID)` returns the active window's.
- **Insert from URL**: `application/json` responses stored in a variable are auto-parsed and cached — faster subsequent JSON ops. New `--proxy-negotiate` / `--proxy-ntlm` options.
- `Export Field Contents` now works from FileMaker Server, Data API, and OData scripts.

## Script gotchas

1. **PSOS has no UI access** — no dialogs, no layout-dependent steps.
2. **Insert Text requires layout context for fields** — use Set Variable for portability, especially via PSOS. Insert Text works fine targeting `$variables` without layout context.
3. **Commit Records after Set Field** — changes aren't saved until committed.
4. **cURL options use `¶` (pilcrow) as line separator** — `\n` produces literal backslash-n. Use `& ¶ &` between options.
5. **cURL header values need `Quote()`** — e.g. `"--header " & Quote ( "Authorization: Bearer " & $token )`.
6. **Tokens/secrets in cURL headers cannot start with `-`** — cURL parses a leading dash as a flag. Use hex tokens or regenerate until the first character is alphanumeric.
7. **Configure AI Account misspells "Account"** — the XML schema uses `<AccoutName>` and `<SetLLMAccout>`. Not your typo — it's in FileMaker's actual XML format.
