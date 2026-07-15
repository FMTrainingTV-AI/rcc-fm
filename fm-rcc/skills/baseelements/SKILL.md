---
name: baseelements
description: >
  Use when working with the free BaseElements plugin (BE) for FileMaker — any BE_ function
  (BE_HTTP_GET, BE_HTTP_POST, BE_FileWriteText, BE_FileReadText, BE_SMTPSend, BE_Encrypt_AES,
  BE_CipherEncrypt, BE_MessageDigest, BE_JSON_jq, BE_XPath, BE_ExecuteSystemCommand, BE_Zip, etc.),
  or when a FileMaker solution needs capabilities the plugin provides that native FileMaker can't do
  well: HTTP/cURL beyond Insert From URL, FTP/SFTP transfers, reading/writing files and folders on
  disk, running shell commands, sending SMTP email with attachments, AES/RSA encryption, hashing
  (MD5/SHA), zip/gzip, XML/XSLT/XPath processing, jq JSON queries, PDF assembly, clipboard control,
  or custom dialogs. This is the Goya Pty Ltd BaseElements plugin (free, open source).
---

# BaseElements Plugin (BE) for FileMaker

The BaseElements plugin — built by **Goya Pty Ltd** — is the de-facto free, open-source plugin that
extends FileMaker with ~129 `BE_*` functions: filesystem access, HTTP/cURL/FTP, SMTP email,
encryption, XML/XSLT/XPath, jq JSON queries, shell commands, zip, PDF, and more. No registration, no
license, no usage tracking.

**Authoritative docs:** https://github.com/GoyaPtyLtd/BaseElements-Plugin/tree/main/docs

## When to reach for BE (vs. native FileMaker)

Use native FileMaker steps/functions first when they cover the need (Insert From URL, `CryptEncrypt`,
JSON functions, `Save Records as PDF`). Reach for BE when you need something native FM doesn't do, or
does worse:

| Need | BE function(s) | Why over native |
|---|---|---|
| HTTP with full cURL control, separate response code/headers | `BE_HTTP_GET/POST/PUT/PATCH/DELETE` | More cURL options than Insert From URL; `BE_HTTP_ResponseCode`/`ResponseHeaders` give clean diagnostics; not a single script step (callable in a calc) |
| FTP / SFTP / FTPS upload & delete | `BE_FTP_Upload`, `BE_FTP_UploadFile`, `BE_FTP_Delete` | Native FM has no real FTP |
| Read/write/append/copy/move files on disk | `BE_FileReadText`, `BE_FileWriteText`, `BE_FileCopy`, `BE_FileMove` | Native FM can't manipulate arbitrary files on disk |
| List a folder, check existence, get size/timestamp | `BE_FileListFolder`, `BE_FileExists`, `BE_FileSize` | No native equivalent |
| Run a shell / command-line script | `BE_ExecuteSystemCommand` | No native equivalent |
| Send SMTP email with attachments/HTML directly | `BE_SMTPServer` + `BE_SMTPSend` | More control than native Send Mail SMTP |
| AES / cipher / RSA / digital signatures | `BE_Encrypt_AES`, `BE_CipherEncrypt`, `BE_SignatureGenerateRSA` | Covers cases native `CryptEncrypt` doesn't |
| Zip / unzip / gzip | `BE_Zip`, `BE_Unzip`, `BE_Gzip` | No native zip |
| XPath / XSLT / XML tidy & validate | `BE_XPath`, `BE_XSLTApply`, `BE_XMLValidate` | No native XPath/XSLT |
| jq query over JSON | `BE_JSON_jq` | Far more powerful than `JSONGetElement` for complex queries |
| Assemble / split PDFs by page | `BE_PDFAppend`, `BE_PDFGetPages` | Pre-2026 FM had no PDF assembly |

## ⚠️ The #1 rule: check `BE_GetLastError` after every call

This is the single most important habit with this plugin. **The return value is not a reliable
success signal** — many functions return `?` or empty on failure, but the authoritative check is the
error function, called *immediately* after (it reports the last plugin call only):

```
Set Variable [ $result ; BE_FileWriteText ( $path ; $text ) ]
Set Variable [ $err ; BE_GetLastError ]          // 0 = success, non-zero = failure
If [ $err <> 0 ]
  # handle / log the failure — do NOT trust $result
End If
```

- **`BE_GetLastError`** → `0` on success, non-zero error code otherwise. Call it right after the BE
  function, before any other BE call overwrites it.
- **HTTP/cURL/FTP/SMTP** errors come from the **cURL library**, not the plugin. After a transfer:
  - `BE_HTTP_ResponseCode` → the HTTP status (200, 404, 500…). A non-zero `BE_GetLastError` means the
    request couldn't even be made; a `BE_GetLastError` of 0 with a 4xx/5xx `BE_HTTP_ResponseCode`
    means it reached the server but the server rejected it.
  - `BE_HTTP_ResponseHeaders` → response headers for diagnosis.
  - `BE_CurlTrace` → full connection transcript when the error code alone isn't enough.
  - cURL error reference: https://curl.se/libcurl/c/libcurl-errors.html
- **`BE_GetLastDDLError`** → for DDL run via `BE_FileMakerSQL` (CREATE/ALTER/DROP).

## Compatibility — where the plugin runs (and doesn't)

Plugins only load where FileMaker supports plugins. BE runs in:

- **FileMaker Pro** — Mac (Intel & Apple Silicon), Windows (x86)
- **FileMaker Server** — Mac (Intel & Apple Silicon), Windows (x86), Linux (x86 only)
- **Custom iOS apps** built with the iOS App SDK (and the Xcode simulator on macOS)

**It does NOT run in (no plugin support on these platforms):**

- ❌ **FileMaker Go** (iPhone/iPad) — design around this; a solution that must run in Go can't rely on BE.
- ❌ **FileMaker Cloud 2.0+** (Claris-hosted Cloud)
- ❌ **WebDirect** clients (plugin runs on the server side only, not in the browser)

Per-function support varies — each function's doc has a **Compatibility** table (Mac/Win/FMS/iOS/Linux).
The plugin does NOT trap for platform; calling an unsupported function may silently give a false result,
so confirm the function's table for the target platform.

## Installing / enabling the plugin

- **Download:** the GitHub releases page (https://github.com/GoyaPtyLtd/BaseElements-Plugin/releases)
  or the Goya site. File is a `.fmplugin` (Mac) / `.fmx64` (Windows).
- **Manual:** drop the plugin in FileMaker's **Extensions** folder, restart, then enable it under
  **Settings/Preferences → Plug-ins**.
- **Script-deployed (preferred for distribution):** store the plugin file in a container field and
  install it with the native **Install Plug-In File** script step — lets a solution deploy/update the
  plugin to clients itself. `BE_VersionAutoUpdate` returns the version as an 8-digit number for
  comparing against a known-good build.
- **Verify it loaded:** `BE_Version` returns the version string (e.g. `"5.0.4"`). If it returns `?`
  or is undefined, the plugin isn't installed/enabled.

## Fetch the authoritative doc on demand (don't guess signatures)

Every function has its own Markdown doc with the exact signature, parameters, version history,
per-platform compatibility table, notes, and example code. **When you need precise parameter details,
edge cases, or version history — fetch the real page rather than relying on memory.** The index below
gives you the function name; this gives you the rest:

```bash
# One function (replace BE_HTTP_POST with the function name):
curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/BE_HTTP_POST.md

# Full categorized index of every function:
curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions.md

# Named constants (button/encoding/algorithm/filetype constants):
curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/Constants.md
```

This mirrors how the `filemaker` skill fetches Claris docs — get the source of truth, don't invent it.

## Recipes by topic (full signatures + worked examples)

The reference files carry copy-paste recipes with error handling for the high-value clusters:

- `references/http-and-curl.md` — HTTP GET/POST/PUT/PATCH/DELETE, custom headers, response code/headers, cURL options, FTP/SFTP, proxy, the full error-diagnosis flow
- `references/files-folders-zip.md` — read/write/append text, exists/delete/copy/move, list folders, import/export containers, zip/gzip, file & folder pick dialogs
- `references/encryption.md` — AES, cipher with IV, MD5/SHA hashing (+ HMAC), RSA keypair/encrypt/sign/verify, encodings
- `references/email-smtp.md` — SMTP server config, send (text + HTML + cc/bcc/reply-to), attachments, custom headers
- `references/data-processing.md` — jq JSON queries, JSON array size, XPath/XPathAll, XSLT, XML tidy/validate/strip, arrays, stacks, value-list helpers, vectors, regex
- `references/system-and-containers.md` — shell commands, JavaScript eval, internal SQL, run scripts / custom script steps, version & machine info, preferences, time, clipboard, containers, PDF assembly

## Complete function index (all ~129 functions by category)

Names + one-line purpose. Fetch the per-function doc (pattern above) for exact parameters.
`{ braces }` mark optional parameters.

### Arrays — in-memory arrays stored in plugin memory by index
- `BE_ArraySetFromValueList ( valueList ; { retainEmptyValues } )` — store a value list as an array, returns an index handle
- `BE_ArrayGetValue ( array ; valueNumber )` — read one element
- `BE_ArrayChangeValue ( array ; valueNumber ; newValue )` — change one element
- `BE_ArrayFind ( array ; value )` — find element number by value
- `BE_ArrayGetSize ( array )` — element count
- `BE_ArrayDelete ( array )` — free the array from memory

### Clipboard
- `BE_ClipboardFormats` — list format types on the current clipboard
- `BE_ClipboardGetText ( format )` — get clipboard as text for a format
- `BE_ClipboardSetText ( text ; format )` — set clipboard text + format
- `BE_ClipboardGetFile ( format ; { fileName } )` — get binary clipboard item
- `BE_ClipboardSetFile ( fileData ; format )` — set clipboard to binary data + format

### Containers
- `BE_ContainerCompress ( data ; { filename } )` — convert container data to internal compressed form
- `BE_ContainerUncompress ( gzip_data ; { filename } )` — reverse of compress
- `BE_ContainerIsCompressed ( containerField )` — was it compressed on insert?
- `BE_ContainerGetType ( container ; type )` — get container content in a given internal type
- `BE_ContainerListTypes ( container )` — list internal stored types
- `BE_ConvertContainer ( field ; { type } )` — convert between internal "image" and "file" types
- `BE_ExportFieldContents ( field ; { outputPath } )` — export container to disk
- `BE_JPEGRecompress ( jpeg ; { compressionLevel ; scale } )` — recompress/scale a JPEG in a container

### Data Manipulation — stacks (LIFO), plugin variables, word extraction
- `BE_StackPush ( name ; value )` — push value onto named stack
- `BE_StackPop ( name )` — pop (returns + removes) top value
- `BE_StackCount ( name )` — values remaining in stack
- `BE_StackDelete ( name )` — delete the whole stack
- `BE_VariableSet ( name ; { value } )` — store a value in plugin memory (survives across scripts)
- `BE_VariableGet ( name )` — read a stored plugin variable
- `BE_TextExtractWords ( text ; { wordPrefix } )` — list words, optionally only those starting with a prefix char

### Dialogs
- `BE_DialogDisplay ( title ; message ; defaultButton ; { cancelButton ; alternateButton } )` — custom dialog (returns BE_ButtonOK/Cancel/Alternate)
- `BE_DialogProgress ( title ; description ; { maximum } )` — progress dialog (barber-pole if maximum omitted)
- `BE_DialogProgressUpdate ( number ; { description } )` — advance/close a progress dialog
- `BE_FileSelectDialog ( prompt { ; inFolderPath } )` — OS open-file dialog
- `BE_FileSaveDialog ( prompt ; { fileName ; inFolder } )` — OS save-file dialog
- `BE_FolderSelectDialog ( prompt { ; inFolderPath } )` — OS choose-folder dialog

### Encoding and Encryption
- `BE_Encrypt_AES ( key ; text )` — AES-encrypt text with a key (BE-format)
- `BE_Decrypt_AES ( key ; text )` — reverse of Encrypt_AES
- `BE_CipherEncrypt ( cipher ; data ; key ; iv ; { padding ; fileName } )` — encrypt with a named cipher + IV (interoperable)
- `BE_CipherDecrypt ( cipher ; encryptedData ; key ; iv ; { padding ; fileName } )` — reverse of CipherEncrypt
- `BE_MessageDigest ( text ; { algorithm ; encoding } )` — MD5/SHA hash (use BE_MessageDigestAlgorithm* + BE_Encoding* constants)
- `BE_CreateKeyPair` — generate an RSA private key
- `BE_GetPublicKey ( privateKey )` — derive the public key from a private key
- `BE_EncryptWithKey ( text ; keyText )` — RSA-encrypt with a key
- `BE_DecryptWithKey ( encryptedText ; keyText )` — RSA-decrypt with a key
- `BE_SignatureGenerateRSA ( data ; privateKey ; { password ; algorithm ; fileName } )` — make a digital signature
- `BE_SignatureVerifyRSA ( data ; publicKey ; { signature ; algorithm } )` — verify a signature

### Error Checking
- `BE_GetLastError` — last error from the most recent BE call (0 = success) — **call after every function**
- `BE_GetLastDDLError` — last DDL error from `BE_FileMakerSQL`
- `BE_CurlTrace` — full HTTP/FTP/SMTP transcript of the most recent transfer
- `BE_DebugInformation` — plugin debug info for bug reports

### Files and Folders
- `BE_FileReadText ( pathOrContainer { ; start ; to ; eolChar } )` — read a text file (range optional)
- `BE_FileWriteText ( pathOrContainer ; text ; { append } )` — write/append a text file (or into a container)
- `BE_FileReplaceText ( pathOrContainer ; expression ; replaceString { ; options } )` — Substitute-on-disk
- `BE_FilePatternCount ( path ; searchText )` — count occurrences inside a file on disk
- `BE_FileExists ( path )` — file/folder exists? (True/False)
- `BE_FileDelete ( path )` — delete a file
- `BE_FileCopy ( fromFilePath ; toFilePath { ; replaceDestinationFile } )` — copy a file
- `BE_FileMove ( fromFilePath ; toFilePath { ; replaceDestinationFile } )` — move/rename a file
- `BE_FileSize ( path )` — bytes
- `BE_FileModificationTimestamp ( path )` — OS modification time
- `BE_FileOpen ( path )` — open file/folder in the OS default app
- `BE_FileImport ( filePath ; { compress } )` — import a disk file into a container/variable (optional gzip)
- `BE_FileListFolder ( path { ; type ; includeSubdir ; useFullPath ; includeHidden } )` — list folder (use BE_FileType* constants)
- `BE_FolderCreate ( path )` — create folder (and parents)

### HTTP and URLs
- `BE_HTTP_GET ( url ; { filename ; username ; password } )` — GET/download (http/https/ftp/ftps/sftp)
- `BE_HTTP_POST ( url ; parameters ; { username ; password ; fileName } )` — POST (use `file=@path` for files)
- `BE_HTTP_PUTData ( url ; data ; { username ; password } )` — PUT from data/container
- `BE_HTTP_PUTFile ( url ; pathToFile ; { username ; password } )` — PUT a file from disk
- `BE_HTTP_PATCH ( url ; parameters ; { username ; password } )` — PATCH
- `BE_HTTP_DELETE ( url ; { username ; password } )` — DELETE
- `BE_HTTP_GET_File ( url ; path ; { username ; password } )` — GET straight to a file on disk
- `BE_HTTP_SetCustomHeader ( { header ; value } )` — set a request header before the call (call with no args to clear)
- `BE_HTTP_ResponseCode` — HTTP status code from the last transfer
- `BE_HTTP_ResponseHeaders ( { header } )` — response headers from the last transfer
- `BE_HTTP_Set_Proxy ( ... )` — set proxy before a call
- `BE_CurlSetOption ( { option ; value } )` — set a raw cURL option for subsequent transfers
- `BE_CurlGetInfo ( getInfoOption )` — read cURL info from the last transfer
- `BE_FTP_Upload ( url ; data ; { username ; password } )` — upload container data via ftp/sftp/ftps
- `BE_FTP_UploadFile ( url ; pathToFile ; { username ; password } )` — upload a disk file
- `BE_FTP_Delete ( url ; { username ; password } )` — delete a remote file
- `BE_OpenURL ( url )` — open a URL in the user's default browser

### Miscellaneous
- `BE_ExecuteSystemCommand ( command ; { timeout ; executeUsingShell } )` — run a shell/command-line command
- `BE_EvaluateJavaScript ( javaScript )` — evaluate JavaScript text, return result
- `BE_FileMakerSQL ( sqlStatement ; { columnSep ; rowSep ; databaseName ; asText ; outputPath } )` — internal SQL incl. INSERT/UPDATE/DELETE/DDL (unlike read-only `ExecuteSQL`)
- `BE_RegularExpression ( text ; expression ; { options ; replaceString } )` — PCRE match/replace
- `BE_ScriptExecute ( scriptName ; { fileName ; parameter ; scriptControl } )` — run a FileMaker script by name
- `BE_ScriptStepInstall ( name ; definitionXML ; id ; description ; calculation )` — register a plugin-defined script step
- `BE_ScriptStepPerform ( scriptStepId )` — perform an installed custom step by id
- `BE_ScriptStepRemove ( scriptStepId )` — remove an installed custom step
- `BE_Version` — plugin version string (e.g. "5.0.4")
- `BE_VersionAutoUpdate` — version as an 8-digit number for comparisons
- `BE_GetMachineName` — computer name / hardware id
- `BE_GetSystemDrive` — like Get(SystemDrive) but also works on FileMaker Server
- `BE_Pause ( milliseconds )` — pause inside the plugin (doesn't return to FMP)
- `BE_SetTextEncoding ( { encoding } )` — set encoding used by file read/write functions

### PDF
- `BE_PDFAppend ( pdfPathOrContainer ; appendPathOrContainer ; { destinationPath } )` — join two PDFs
- `BE_PDFGetPages ( pdfPathOrContainer ; newPDFPath ; fromPageNum ; { toPageNum } )` — extract a page range to a new PDF
- `BE_PDFPageCount ( pdfPathOrContainer )` — page count

### Preferences — values persisted in the OS preferences store
- `BE_SetPreference ( key ; value ; { domain } )` — store a preference
- `BE_PreferenceGet ( key ; { domain } )` — read a preference
- `BE_PreferenceDelete ( key ; { domain } )` — delete a preference

### SMTP Email
- `BE_SMTPServer ( server ; { port ; username ; password ; keepOpen } )` — store SMTP connection details
- `BE_SMTPSend ( from ; to ; subject ; text ; { cc ; bcc ; replyTo ; html ; attachments } )` — send an email
- `BE_SMTPAddAttachment ( { attachment ; contentType } )` — queue an attachment for the next send
- `BE_SMTPSetHeader ( { header ; value } )` — set a custom SMTP header

### Time
- `BE_TimeCurrentMilliseconds` — current time in ms (high-resolution; good for timing)
- `BE_TimeUTCMilliseconds` — current UTC time in ms
- `BE_TimeZoneOffset` — minutes between UTC and local time

### Value Lists — list/value utilities (FileMaker value-list format, ¶-separated)
- `BE_ValuesUnique ( listOfValues ; { caseSensitive } )` — de-duplicate a list
- `BE_ValuesSort ( listOfValues ; { ascending ; type } )` — sort a list
- `BE_ValuesTrim ( listOfValues )` — trim whitespace from each value
- `BE_ValuesFilterOut ( textToFilter ; filterValues ; { caseSensitive } )` — remove listed values (inverse of FilterValues)
- `BE_ValuesContainsDuplicates ( listOfValues ; { caseSensitive } )` — True if any duplicates
- `BE_ValuesTimesDuplicated ( listOfValues ; numberOfTimes )` — values repeated exactly N times

### Vectors — numeric vector math (e.g. for embeddings)
- `BE_VectorDotProduct ( a ; b )` — dot product of two number lists
- `BE_VectorEuclideanDistance ( a ; b )` — Euclidean distance between two vectors

### XML, XSLT, and JSON
- `BE_JSON_jq ( json ; filter ; { options } )` — run a jq filter over JSON (powerful queries; `"r"` = raw output)
- `BE_JSON_ArraySize ( json ; { path } )` — number of elements in a JSON array
- `BE_XPath ( xmlText ; xpathText ; { namespaceList ; asText } )` — first node matching an XPath
- `BE_XPathAll ( xmlText ; xpathText ; { namespaceList } )` — all nodes matching an XPath
- `BE_XSLTApply ( xmlFilePath ; xsltText ; outputFilePath )` — apply XSLT to an XML file → output file
- `BE_XSLT_ApplyInMemory ( xmlText ; xsltText )` — apply XSLT in memory, return result
- `BE_XMLParse ( pathOrXMLText )` — check XML is well-formed
- `BE_XMLValidate ( xmlText ; schemaText )` — validate XML against an XSD
- `BE_XMLTidy ( xml )` — reformat/pretty-print XML
- `BE_XML_Canonical ( xml )` — canonical (normal-form) XML for comparison
- `BE_XMLStripInvalidCharacters ( path ; { resultFilePath } )` — remove invalid XML chars from a file
- `BE_XMLStripNodes ( inputFilePath ; outputFilePath ; nodeNames )` — remove named nodes from an XML file

### Zip and Gzip
- `BE_Zip ( filePathList ; { archiveFilePath } )` — zip one or more files
- `BE_Unzip ( archiveFilePath ; { outputFolderPath } )` — unzip an archive
- `BE_Gzip ( data ; { filename } )` — gzip a file/text/container
- `BE_UnGzip ( gzip_data ; { filename } )` — un-gzip

## Named constants (use names, not magic numbers)

Fetch `Functions/Constants.md` for the full table. Most-used:

- **Dialog buttons** (return of `BE_DialogDisplay`): `BE_ButtonOK` (1), `BE_ButtonCancel` (2), `BE_ButtonAlternate` (3)
- **File list types** (`BE_FileListFolder`): `BE_FileTypeAll` (0), `BE_FileType_File` (1), `BE_FileTypeFolder` (2)
- **Hash encoding** (`BE_MessageDigest`): `BE_EncodingHex` (1), `BE_EncodingBase64` (2)
- **Hash algorithm** (`BE_MessageDigest`): `BE_MessageDigestAlgorithmMD5` (1), `BE_MessageDigestAlgorithmSHA256` (2), and other SHA variants

## Common mistakes

1. **Trusting the return value instead of `BE_GetLastError`.** Always check the error function right
   after the call. (See "The #1 rule" above.)
2. **Calling `BE_GetLastError` too late.** It reports the *most recent* BE call — another BE function
   in between overwrites it. Capture it into a variable immediately.
3. **Assuming it works in FileMaker Go / WebDirect / Cloud.** It doesn't — plan around it.
4. **Setting headers/options after the transfer.** `BE_HTTP_SetCustomHeader` / `BE_CurlSetOption` must
   run *before* the `BE_HTTP_*` call; they apply to subsequent transfers, then persist until cleared.
5. **Forgetting to clear sticky state.** Custom headers, cURL options, and SMTP server settings persist
   across calls. Clear headers with `BE_HTTP_SetCustomHeader` (no args) when you don't want them reused.
6. **Magic numbers.** Use the named constants, not `1`/`2`, so the calc stays readable.
7. **Inventing a signature from memory.** ~129 functions with optional-param variations — fetch the
   function's doc (pattern above) when you're not certain.
