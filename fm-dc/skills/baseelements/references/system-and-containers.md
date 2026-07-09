# BE System / SQL / Scripts / Containers / PDF / Misc recipes

## Run a shell command — `BE_ExecuteSystemCommand`

```
Set Variable [ $out ; BE_ExecuteSystemCommand ( "ls -la /tmp" ; 30000 ) ]   // 30000 = timeout in MILLISECONDS
Set Variable [ $err ; BE_GetLastError ]
```

Signature: `( command ; { timeout ; executeUsingShell } )`.
- `timeout` is in **milliseconds** (not seconds). Omitting it waits indefinitely (not recommended); `0`
  returns immediately.
- `executeUsingShell` (default **True**) runs via the shell, so pipes / redirection / `&&` work, and you
  can string several commands in one call separated by `Char ( 10 )` (Mac) or `Char ( 13 )` (Windows).
  Set it False to run the command directly without a shell.
- ⚠️ It does **not** inherit Terminal/CMD's working directory or environment — use absolute paths, and
  expect behavior to differ from the same command typed in a terminal.
- Captures stdout as the result. Runs on Mac/Win/Linux/Server — a common reason to use BE server-side.
- ⚠️ **Never build a command by concatenating untrusted input** — shell-inject risk. Quote/escape, or
  set `executeUsingShell` False and pass args directly.
- (The old `BE_ExecuteShellCommand` is deprecated — use `BE_ExecuteSystemCommand`.)

## Internal SQL — `BE_FileMakerSQL`

Unlike the native read-only `ExecuteSQL()`, this can **write**: INSERT / UPDATE / DELETE and DDL
(CREATE/ALTER/DROP TABLE, ADD FIELD).

```
# read
Set Variable [ $rows ; BE_FileMakerSQL ( "SELECT name, total FROM Invoices WHERE total > 100" ) ]
# write
Set Variable [ $r ; BE_FileMakerSQL ( "UPDATE Invoices SET status = 'paid' WHERE id = 42" ) ]
Set Variable [ $err ; BE_GetLastError ]
Set Variable [ $ddlErr ; BE_GetLastDDLError ]   // for CREATE/ALTER/DROP, check THIS too
```

Signature: `( sqlStatement ; { columnSeparator ; rowSeparator ; databaseName ; asText ; outputPath } )`.
- Uses **table occurrence names** (the names on the relationship graph), same as native `ExecuteSQL` —
  not base-table names. The optional `databaseName` targets another open file.
- For DDL, check `BE_GetLastDDLError` (not just `BE_GetLastError`).
- ⚠️ Writing SQL bypasses field validation, auto-enters, and triggers — use deliberately.

## Run FileMaker scripts & custom script steps

```
# run a script by name (optionally in another file, with a parameter)
Set Variable [ $r ; BE_ScriptExecute ( "Process Queue" ; "" ; $param ) ]

# define and run a plugin-provided custom script step
Set Variable [ $id ; BE_ScriptStepInstall ( $name ; $definitionXML ; $id ; $description ; $calc ) ]
Set Variable [ $r  ; BE_ScriptStepPerform ( $id ) ]
Set Variable [ $r  ; BE_ScriptStepRemove ( $id ) ]
```

## Evaluate JavaScript — `BE_EvaluateJavaScript`

```
Set Variable [ $result ; BE_EvaluateJavaScript ( "1 + 2 * 3" ) ]   // "7"
```

Runs JS text and returns the result — useful for logic easier to express in JS, without a web viewer.

## Version, machine & system info

```
BE_Version              // "5.0.4" — also the install check (returns ? if not loaded)
BE_VersionAutoUpdate    // "05000400" 8-digit form for numeric comparison against a known-good build
BE_GetMachineName       // computer name / hardware id
BE_GetSystemDrive       // like Get(SystemDrive) but ALSO works on FileMaker Server
```

## Preferences (persist small values in the OS prefs store)

```
BE_SetPreference ( "lastSync" ; Get ( CurrentTimestamp ) ; "com.mycompany.myapp" )
Set Variable [ $v ; BE_PreferenceGet ( "lastSync" ; "com.mycompany.myapp" ) ]
BE_PreferenceDelete ( "lastSync" ; "com.mycompany.myapp" )
```

`domain` (optional) namespaces your keys. Survives across sessions; distinct from `BE_VariableSet`
(session-only, in plugin memory — see `data-processing.md`).

## Timing

```
Set Variable [ $start ; BE_TimeCurrentMilliseconds ]
# … work …
Set Variable [ $elapsedMs ; BE_TimeCurrentMilliseconds - $start ]
```

`BE_TimeUTCMilliseconds` (UTC) and `BE_TimeZoneOffset` (minutes from UTC) help with timestamps across
timezones.

## Clipboard

```
Set Variable [ $formats ; BE_ClipboardFormats ]              // what's on the clipboard
Set Variable [ $text ; BE_ClipboardGetText ( "public.utf8-plain-text" ) ]
Set Variable [ $r ; BE_ClipboardSetText ( $text ; "public.utf8-plain-text" ) ]
```

Format identifiers differ by OS (e.g. macOS UTIs). `BE_ClipboardGetFile`/`BE_ClipboardSetFile` move
binary data. This is the same machinery the MBS Clipboard Converter uses for FM-object ⇄ XML
round-trips, but lower-level.

## Containers

```
BE_ExportFieldContents ( MyTable::Doc ; $posixPath )    // container → disk
BE_FileImport ( $posixPath )                            // disk → container (see files-folders-zip.md)
BE_ConvertContainer ( field ; type )                    // swap internal image/file type
BE_ContainerCompress ( data ) / BE_ContainerUncompress ( data )   // internal gzip of container storage
BE_JPEGRecompress ( jpegContainer ; level ; scale )     // shrink/scale a JPEG
```

## PDF assembly (pre-2026 FM had no native equivalent)

```
BE_PDFPageCount ( $pdfPathOrContainer )                          // count pages
BE_PDFAppend ( $pdfA ; $pdfB ; $destinationPath )               // merge two PDFs → destination
BE_PDFGetPages ( $pdf ; $newPDFPath ; 2 ; 5 )                   // extract pages 2–5 → new PDF
```

Inputs accept a POSIX path **or** a container. (FileMaker 2026 added native PDF Create/Append/Open
steps — prefer those on 2026+ if available.)

## Notes

- Check `BE_GetLastError` after every call (and `BE_GetLastDDLError` for DDL).
- Paths everywhere are **native/POSIX** — `ConvertFromFileMakerPath ( ... ; PosixPath )`.
- Fetch a function's doc for exact params:
  `curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/BE_FileMakerSQL.md`
