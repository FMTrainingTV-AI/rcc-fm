# BE Files / Folders / Zip / Dialogs recipes

## ⚠️ Paths are native/POSIX, not FileMaker paths

Every BE file function expects an OS path (POSIX on Mac/Linux, native on Windows) — **not** a
FileMaker path like `file:/Macintosh HD/...`. Convert FileMaker path functions first:

```
Set Variable [ $folder ; ConvertFromFileMakerPath ( Get ( DocumentsPath ) ; PosixPath ) ]
Set Variable [ $path ; $folder & "export.txt" ]
```

`Get ( DocumentsPath )`, `Get ( TemporaryPath )`, `Get ( DesktopPath )` are the usual starting points.
A folder path from `Get(...)` ends in `/`, so just append the filename.

## Read text

```
Set Variable [ $text ; BE_FileReadText ( $path ) ]                 // whole file
Set Variable [ $err  ; BE_GetLastError ]
```

Optional range args `( pathOrContainer ; start ; to ; eolChar )`:
- `BE_FileReadText ( $path ; 1 ; 100 )` — first 100 characters
- `BE_FileReadText ( $path ; 1 ; 10 ; Char ( 10 ) )` — first 10 lines (eolChar makes start/to count lines)
- `BE_FileReadText ( $path ; 10 ; "" ; Char ( 10 ) )` — from line 10 to the end

## Write / append text

```
Set Variable [ $r ; BE_FileWriteText ( $path ; $text ) ]            // create/overwrite
Set Variable [ $r ; BE_FileWriteText ( $path ; $more ; True ) ]     // append
Set Variable [ $err ; BE_GetLastError ]
```

`BE_FileWriteText` can also target a container field (it returns file data you Set Field with):
`Set Field [ T::file ; BE_FileWriteText ( "notes.txt" ; $text ) ]`.

`BE_FileReplaceText ( pathOrContainer ; expression ; replaceString { ; options } )` is Substitute,
but operating directly on a file on disk. `BE_FilePatternCount ( path ; searchText )` counts matches
inside a file without reading it all into memory.

## Exists / delete / copy / move / info

```
If [ BE_FileExists ( $path ) ]              // True/False — works for files and folders
  Set Variable [ $bytes ; BE_FileSize ( $path ) ]
  Set Variable [ $when  ; BE_FileModificationTimestamp ( $path ) ]
End If

Set Variable [ $r ; BE_FileCopy ( $src ; $dst ; True ) ]   // True = overwrite destination
Set Variable [ $r ; BE_FileMove ( $src ; $dst ; True ) ]   // move / rename
Set Variable [ $r ; BE_FileDelete ( $path ) ]
Set Variable [ $r ; BE_FileOpen ( $path ) ]                // open in OS default app
```

## List a folder

```
# everything in the folder (files + folders), names only
Set Variable [ $items ; BE_FileListFolder ( $folder ) ]

# folders only, no subdirs, full paths, include hidden — uses BE_FileType* constants
Set Variable [ $dirs ; BE_FileListFolder ( $folder ; BE_FileTypeFolder ; False ; True ; True ) ]
```

Signature: `( path { ; type ; includeSubdir ; useFullPath ; includeHidden } )`.
`type`: `BE_FileTypeAll` (0), `BE_FileType_File` (1), `BE_FileTypeFolder` (2).

Filter the result with regex — e.g. only `.fmp12` files (drops non-matching blank lines with
`BE_ValuesUnique`, see `data-processing.md`):

```
BE_ValuesUnique ( BE_RegularExpression ( BE_FileListFolder ( $folder ) ; "^.*\\.fmp12$" ; "v" ) )
```

## Create folders / import a file into a container

```
Set Variable [ $r ; BE_FolderCreate ( $folder ) ]          // creates intermediate folders too

# Like Insert File, but ALSO works on FileMaker Server (the native step doesn't):
Set Field [ Imports::Doc ; BE_FileImport ( $path ) ]
Set Field [ Imports::Doc ; BE_FileImport ( $path ; True ) ]   // True = gzip-compress in the field
```

Export a container to disk: `BE_ExportFieldContents ( field ; { outputPath } )` (see
`system-and-containers.md`).

## Zip / Gzip

```
# zip specific files (build the path list first; paths are POSIX)
Let ( [
  p = ConvertFromFileMakerPath ( Get ( DocumentsPath ) ; PosixPath ) ;
  files = List ( p & "file1.pdf" ; p & "file2.pdf" )
] ;
  BE_Zip ( files ; p & "archive.zip" )
)

Set Variable [ $r ; BE_Unzip ( $archivePath ; $outputFolder ) ]   // outputFolder optional
Set Variable [ $gz ; BE_Gzip ( MyTable::Container ) ]             // gzip a file/text/container
Set Variable [ $raw ; BE_UnGzip ( $gz ) ]
```

## Dialogs (OS file/folder pickers + custom alerts)

```
Set Variable [ $file   ; BE_FileSelectDialog ( "Choose a CSV" ) ]            // returns a POSIX path (empty if cancelled)
Set Variable [ $folder ; BE_FolderSelectDialog ( "Choose a destination" ) ]
Set Variable [ $save   ; BE_FileSaveDialog ( "Save report as" ; "report.pdf" ) ]

# custom alert from a calc (no fields, unlike Show Custom Dialog)
Set Variable [ $btn ; BE_DialogDisplay ( "Confirm" ; "Delete this record?" ; "Cancel" ; "Delete" ) ]
If [ $btn = BE_ButtonCancel ]   // BE_ButtonOK=1 (defaultButton), BE_ButtonCancel=2, BE_ButtonAlternate=3
  Exit Script [ Text Result: "" ]
End If

# progress dialog for a long loop
Set Variable [ $r ; BE_DialogProgress ( "Importing" ; "Processing rows…" ; $totalRows ) ]
# … inside the loop:
Set Variable [ $r ; BE_DialogProgressUpdate ( $i ; "Row " & $i & " of " & $totalRows ) ]
# … when done:
Set Variable [ $r ; BE_DialogProgressUpdate ( $totalRows ) ]   // reaching max closes it
```

Leave `maximum` out of `BE_DialogProgress` for an indeterminate barber-pole.

## Notes

- Always check `BE_GetLastError` right after — a missing file, permission denial, or full disk shows
  up there, not always in the return value.
- File functions run on **FileMaker Server** too (a big reason to use them over native steps in
  server-side / PSOS scripts), but NOT in FileMaker Go / WebDirect.
