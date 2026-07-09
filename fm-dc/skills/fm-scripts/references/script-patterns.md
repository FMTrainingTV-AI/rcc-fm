# FileMaker Script Patterns Reference

## Table of Contents
1. Standard Script Template
2. Error Handling
3. Parameter Passing
4. PSOS (Perform Script on Server)
5. AI Integration (FM 2024)
6. API / cURL Calls
7. Looping Patterns
8. Record Navigation & Context
9. Transaction Pattern

---

## 1. Standard Script Template

```
# ================================================
# Script: Purpose of script
# Parameters: Description of expected params
# Returns: What Exit Script returns
# ================================================

Set Error Capture [On]
Allow User Abort [Off]

# --- Parse parameters ---
Set Variable [$param ; Get ( ScriptParameter )]

# --- Validate ---
If [IsEmpty ( $param )]
  Exit Script [JSONSetElement ( "{}" ; "error" ; "Missing parameter" ; JSONString )]
End If

# --- Main logic ---
# ... your steps here ...

# --- Commit & exit ---
Commit Records/Requests [No dialog]
Exit Script [1]
```

---

## 2. Error Handling

### Basic error capture
```
Set Error Capture [On]
# ... do something that might fail ...
Set Variable [$error ; Get ( LastError )]
If [$error <> 0]
  Show Custom Dialog ["Error" ; "Error code: " & $error]
  Exit Script [0]
End If
```

### Common error codes
- 0 = No error
- 1 = User canceled
- 9 = Insufficient privileges
- 101 = Record is missing
- 102 = Field is missing (often a DataAPI field-level privilege issue)
- 200 = Record access is denied (check privilege set Create permissions)
- 200-299 = Field-related errors
- 301 = Record in use by another user
- 400 = Find criteria are empty
- 401 = No records match
- 500-599 = Date/time validation errors
- 718 = XML/XSLT processing error
- 729 = Insufficient privileges for network operation
- 1626-1638 = AI/LLM specific errors (FM 2024)

### Structured error returns with JSON
```
Exit Script [
  JSONSetElement ( "{}" ;
    [ "success" ; False ; JSONBoolean ] ;
    [ "error" ; $error ; JSONNumber ] ;
    [ "message" ; "Record locked by another user" ; JSONString ]
  )
]
```

---

## 3. Parameter Passing

### JSON parameters (preferred)
**Calling script:**
```
Perform Script ["Target Script" ;
  Parameter: JSONSetElement ( "{}" ;
    [ "id" ; $recordID ; JSONNumber ] ;
    [ "mode" ; "edit" ; JSONString ]
  )
]
```

**Receiving script:**
```
Set Variable [$param ; Get ( ScriptParameter )]
Set Variable [$id ; JSONGetElement ( $param ; "id" )]
Set Variable [$mode ; JSONGetElement ( $param ; "mode" )]
```

### Button parameter (for layout buttons)
```
JSONSetElement ( "" ;
  [ "TripClientPartyID" ; 1234 ; JSONNumber ] ;
  [ "email" ; "client@example.com" ; JSONString ]
)
```

### Script result retrieval
```
Perform Script ["Some Script" ; Parameter: $data]
Set Variable [$result ; Get ( ScriptResult )]
Set Variable [$success ; JSONGetElement ( $result ; "success" )]
```

---

## 4. PSOS (Perform Script on Server)

### When to use
- Long-running operations (bulk updates, API calls)
- Operations that don't need UI feedback during execution
- Server-side data processing

### What works on server
- Set Variable, Set Field, Commit Records
- ExecuteSQL
- Loop, If/Else, Exit Script
- Insert from URL (cURL)
- Generate Response from Model (FM 2024)

### What does NOT work on server
- Any UI steps: Show Custom Dialog, Show/Hide Toolbars
- Layout-dependent steps when targeting fields: Insert Text, Go to Field, Set Selection
- Window management: New Window, Select Window
- Print/Preview steps
- Install OnTimer Script

### Pattern
```
# Client-side script
Set Variable [$param ; JSONSetElement ( "{}" ; "id" ; $id ; JSONNumber )]
Perform Script on Server ["Server Script" ; Parameter: $param ; Wait for completion: On]
Set Variable [$result ; Get ( ScriptResult )]
# Process result on client side
```

---

## 5. AI Integration (FM 2024)

### Complete AI script pattern
```
# ================================================
# Script: AI - Generate Summary
# Purpose: Send data to AI model and save structured response
# ================================================

Set Error Capture [On]
Allow User Abort [Off]

# --- Get API key from config ---
Set Variable [$apiKey ;
  Trim ( ExecuteSQL ( "SELECT APIKey_AI FROM zDataAPI WHERE DataAPIID = ?" ; "" ; "" ; 1 ) )
]
If [IsEmpty ( $apiKey )]
  Exit Script [0]
End If

# --- Collect data to send ---
Set Variable [$qaText ; List ( RelatedTable::DataField )]
If [IsEmpty ( $qaText )]
  Exit Script [0]
End If

# --- Configure ---
Set Variable [$model ; "gpt-4o"]

# --- Instructions (system prompt) ---
# Use Insert Text for long literal instructions — avoids concatenation complexity
Insert Text [Select ; $instructions ; "You are a helpful assistant..."]

# --- User prompt with dynamic data ---
Set Variable [$prompt ;
  "Process this data:" & ¶ &
  $qaText & ¶ &
  "Today's date is " &
  Year ( Get ( CurrentDate ) ) & "-" &
  Right ( "0" & Month ( Get ( CurrentDate ) ) ; 2 ) & "-" &
  Right ( "0" & Day ( Get ( CurrentDate ) ) ; 2 )
]

# --- Call AI ---
Configure AI Account [Account Name: "MyAccount" ; API Key: $apiKey ; Model Type: ChatGPT]
Generate Response from Model [
  Account Name: "MyAccount" ;
  Model: $model ;
  User Prompt: $prompt ;
  Instructions: $instructions ;
  Response: $response
]

# --- Check for errors ---
Set Variable [$error ; Get ( LastError )]
If [$error <> 0]
  Exit Script [0]
End If

# --- Validate JSON response ---
If [Left ( JSONFormatElements ( $response ) ; 1 ) = "?"]
  # Response is not valid JSON — save raw for debugging
  Set Field [Table::AI_RawResponse ; $response]
  Exit Script [0]
End If

# --- Save response ---
Set Field [Table::AI_Summary ; $response]
Commit Records/Requests [No dialog]

Show Custom Dialog ["Complete" ; "AI summary saved."]
```

### Model Provider values for Configure AI Account
(Current docs call the option "Model Provider"; older snippets/UI say "Model Type".)
- `ChatGPT` — OpenAI models (e.g. `gpt-4o`, `gpt-4o-mini`)
- `Anthropic` — Claude models (e.g. `claude-sonnet-4-5`, `claude-opus-4`). Native support in FM 22 — no Custom endpoint needed.
- `Gemini` — Google models. Native support in FM 26 for text generation and embeddings.
- `Custom` — Any OpenAI-compatible endpoint (requires Endpoint URL ending with `/`). Claris AI Model Server goes here, e.g. `"https://myserver.example.com/llm/v1/"` with an Admin Console API key.

**XML schema note:** The Configure AI Account XML uses `<LLMType value="ChatGPT"/>` or `<LLMType value="Anthropic"/>`. The rest of the step structure is identical — just swap the provider value. Same `APIKey_AI` field can hold either key; account is per-session so you can switch providers mid-file by running Configure AI Account again.

### AI error codes (FM 2024)
- 1626 = AI account not configured
- 1627 = AI model not found
- 1628 = AI request failed (network/API)
- 1629-1638 = Various AI/tool-related errors

### FM 2026 AI changes (version 26, June 2026)
- New steps: **Insert Image Caption** / **Insert Image Captions in Found Set** — container image → caption text via an image-captioning model. Claris AI Model Server accounts only (Custom provider).
- **Generate Response from Model**: new **Include tool calls and tool results** option for fuller saved message history. Bug fixed: with Stream off, the message-history variable now populates after the step completes.
- **Parameters** option on Insert Embedding / Insert Embedding in Found Set / Perform Semantic Find accepts provider-specific params (e.g. `dimension`). The `CURLOPT_TIMEOUT` key (seconds) caps request time on Generate Response, the natural-language query steps, and Perform RAG Action.
- **Perform RAG Action**: returns the document ID when adding a doc (store it — no more parsing GetRAGSpaceInfo to remove later); per-request Similarity Threshold and Top-N in Parameters; new **Tokens per Text Chunk** option.
- **Field annotations**: AI-only field descriptions set in Advanced Options for Field, sent by Perform SQL Query / Find by Natural Language. Read with `FieldAnnotation()`; included in `GetFieldsOnLayout()`.
- Authoritative per-step docs: `curl -sL https://help.claris.com/markdown/en/pro-help/{slug}.md` (see SKILL.md "First-Party Docs on Demand").

---

## 6. API / cURL Calls

### Building cURL options in FileMaker
```
Set Variable [$curlOptions ;
  "--request POST" & ¶ &
  "--header " & Quote ( "Content-Type: application/json" ) & ¶ &
  "--header " & Quote ( "Authorization: Bearer " & $apiKey ) & ¶ &
  "--data @$body"
]
```

**Critical rules:**
- Separate cURL options with `¶` (pilcrow) — NOT `\n`. FM calcs treat `\n` as literal backslash-n.
- Wrap header values with `Quote()` — handles special characters and quoting.
- Tokens in headers **cannot start with `-`** — cURL parses leading dashes as option flags. Use hex tokens (`secrets.token_hex()`) or ensure first character is alphanumeric.
- `--data @$variableName` sends the variable's content as the POST body.
- `--FM-return-data=true` forces FM to return the response body (useful for error inspection).

### Insert from URL pattern
```
Set Variable [$url ; "https://api.example.com/endpoint"]
Set Variable [$body ; JSONSetElement ( "{}" ; "key" ; "value" ; JSONString )]
Set Variable [$curlOptions ;
  "--request POST" & ¶ &
  "--header " & Quote ( "Content-Type: application/json" ) & ¶ &
  "--header " & Quote ( "X-Auth: " & $authToken ) & ¶ &
  "--data @$body"
]
Insert from URL [No dialog ; $response ; $url ; cURL: $curlOptions]

Set Variable [$error ; Get ( LastError )]
If [$error <> 0]
  # Handle error
End If
```

---

## 7. Looping Patterns

### Loop through found set
```
Go to Record/Request/Page [First]
Loop
  # Process current record
  Set Field [Table::Processed ; 1]
  Commit Records/Requests [No dialog]

  Go to Record/Request/Page [Next ; Exit after last]
End Loop
```

### Loop through a list
```
Set Variable [$i ; 1]
Set Variable [$count ; ValueCount ( $list )]
Loop
  Exit Loop If [$i > $count]
  Set Variable [$item ; GetValue ( $list ; $i )]

  # Process $item

  Set Variable [$i ; $i + 1]
End Loop
```

### Loop with JSON array building
```
Set Variable [$json ; "[]"]
Set Variable [$i ; 0]
Go to Record/Request/Page [First]
Loop
  Set Variable [$obj ; JSONSetElement ( "{}" ;
    [ "id" ; Table::ID ; JSONNumber ] ;
    [ "name" ; Table::Name ; JSONString ]
  )]
  Set Variable [$json ; JSONSetElement ( $json ; $i ; $obj ; JSONObject )]
  Set Variable [$i ; $i + 1]

  Go to Record/Request/Page [Next ; Exit after last]
End Loop
```

---

## 8. Record Navigation & Context

### Find records
```
Enter Find Mode [Pause: Off]
Set Field [Table::Status ; "active"]
Set Error Capture [On]
Perform Find []
Set Variable [$error ; Get ( LastError )]
If [$error = 401]
  # No records found
  Show All Records
  Exit Script [0]
End If
```

### Go to related record
```
Go to Related Record [
  Show only related records ;
  From table: "RelatedTable" ;
  Using layout: "RelatedLayout" ;
  New window
]
```

### Freeze/refresh window for performance
```
Freeze Window
# ... bulk operations ...
Refresh Window [Flush cached join results]
```

---

## 9. Transaction Pattern

### Grouped changes with rollback
```
Set Error Capture [On]
Set Variable [$startOK ; True]

# Open transaction (FM 19.6+)
Open Transaction []

  # ... make changes across multiple records/tables ...
  Set Field [Table1::Field ; "new value"]
  Commit Records/Requests [No dialog]
  If [Get ( LastError ) <> 0]
    Set Variable [$startOK ; False]
  End If

  Set Field [Table2::Field ; "another value"]
  Commit Records/Requests [No dialog]
  If [Get ( LastError ) <> 0]
    Set Variable [$startOK ; False]
  End If

# Commit or rollback
If [$startOK]
  Commit Transaction []
Else
  Revert Transaction []
End If
```
