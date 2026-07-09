# BE HTTP / cURL / FTP recipes

All HTTP/FTP/SMTP functions share one cURL engine. State (custom headers, cURL options, proxy) is
**sticky** — set it *before* the transfer, and it persists for later transfers until you clear it.

## The error-handling flow (do this every time)

```
# 1. (optional) set headers / options BEFORE the call
Set Variable [ $h ; BE_HTTP_SetCustomHeader ( "Authorization" ; "Bearer " & $token ) ]
Set Variable [ $h ; BE_HTTP_SetCustomHeader ( "Content-Type" ; "application/json" ) ]

# 2. make the request
Set Variable [ $response ; BE_HTTP_POST ( $url ; $jsonBody ) ]

# 3. capture BOTH the plugin error and the HTTP status, immediately
Set Variable [ $curlErr ; BE_GetLastError ]        // 0 = request was made; non-zero = couldn't connect (cURL error)
Set Variable [ $httpCode ; BE_HTTP_ResponseCode ]  // 200, 401, 404, 500, ...

# 4. clear sticky headers so they don't leak into the next call
Set Variable [ $h ; BE_HTTP_SetCustomHeader ]

If [ $curlErr <> 0 ]
  # transport failure — get the transcript
  Set Variable [ $trace ; BE_CurlTrace ]
  # log $curlErr + $trace ; cURL error meanings: https://curl.se/libcurl/c/libcurl-errors.html
Else If [ $httpCode < 200 or $httpCode >= 300 ]
  # reached the server but it rejected the request
  Set Variable [ $respHeaders ; BE_HTTP_ResponseHeaders ]
  # inspect $httpCode + $response body + $respHeaders
Else
  # success — $response holds the body
End If
```

**`$curlErr` vs `$httpCode`:** a `BE_GetLastError` of 0 means the request reached the server — even a
404/500 is "success" at the cURL layer. So you must check `BE_HTTP_ResponseCode` separately for the
server's verdict.

## GET

```
Set Variable [ $response ; BE_HTTP_GET ( "https://api.example.com/items?limit=10" ) ]
Set Variable [ $err ; BE_GetLastError ]
Set Variable [ $code ; BE_HTTP_ResponseCode ]
```

Download straight to disk (no round-trip through a variable — good for large files):

```
Set Variable [ $path ; ConvertFromFileMakerPath ( Get ( DocumentsPath ) & "report.pdf" ; PosixPath ) ]
Set Variable [ $r ; BE_HTTP_GET_File ( "https://example.com/report.pdf" ; $path ) ]
Set Variable [ $curlErr  ; BE_GetLastError ]
Set Variable [ $httpCode ; BE_HTTP_ResponseCode ]
# ⚠️ On a 404/500 the server's error page can still be written to $path. ALWAYS confirm the status —
# BE_GetLastError = 0 only means the transfer happened, not that you got the file you wanted.
If [ $curlErr <> 0 or $httpCode <> 200 ]
  Set Variable [ $d ; BE_FileDelete ( $path ) ]   // discard the bad / partial download
  # handle failure
End If
```

## POST

```
Set Variable [ $body ; JSONSetElement ( "{}" ; "name" ; "Acme" ; JSONString ) ]
Set Variable [ $h ; BE_HTTP_SetCustomHeader ( "Content-Type" ; "application/json" ) ]
Set Variable [ $response ; BE_HTTP_POST ( "https://api.example.com/clients" ; $body ) ]
Set Variable [ $h ; BE_HTTP_SetCustomHeader ]   // clear
```

Form-encoded body: pass `"key1=val1&key2=val2"` as `parameters`.
Upload a file in a POST field: use `file=@/posix/path/to/file` in `parameters` (cURL `-F` semantics).

## PUT / PATCH / DELETE

```
Set Variable [ $r ; BE_HTTP_PUTData ( $url ; $data ) ]                 // PUT from a variable/container
Set Variable [ $r ; BE_HTTP_PUTFile ( $url ; $posixPath ) ]           // PUT a file from disk
Set Variable [ $r ; BE_HTTP_PATCH ( $url ; $jsonBody ) ]
Set Variable [ $r ; BE_HTTP_DELETE ( $url ) ]
```

## Authentication

- **Basic:** pass `username ; password` as the optional params, or set
  `BE_CurlSetOption ( "CURLOPT_HTTPAUTH" ; CURLAUTH_BASIC )`.
- **Bearer / token / API key:** set it as a header — `BE_HTTP_SetCustomHeader ( "Authorization" ; "Bearer " & $token )`.
- Other auth schemes: `CURLAUTH_DIGEST`, `CURLAUTH_NTLM`, etc. via `BE_CurlSetOption ( "CURLOPT_HTTPAUTH" ; ... )`.

## Custom headers (sticky — set before, clear after)

```
BE_HTTP_SetCustomHeader ( "X-Api-Key" ; $key )    // add one (call repeatedly for more)
BE_HTTP_SetCustomHeader                            // no args = clear ALL custom headers
```

## Raw cURL options

```
BE_CurlSetOption ( "CURLOPT_TIMEOUT" ; 30 )           // seconds
BE_CurlSetOption ( "CURLOPT_SSL_VERIFYPEER" ; 0 )     // ⚠️ disables cert checks — only for trusted/dev endpoints
BE_CurlSetOption ( "CURLOPT_FOLLOWLOCATION" ; 1 )     // follow redirects
BE_CurlSetOption ( "CURLOPT_HTTPAUTH" )               // no value = reset THAT option to default
BE_CurlSetOption                                       // no args = reset ALL options to default
```

Read info about the last transfer with `BE_CurlGetInfo ( "<CURLINFO_…>" )`.

## FTP / SFTP / FTPS

```
# upload container data
Set Variable [ $r ; BE_FTP_Upload ( "sftp://host/path/file.csv" ; MyTable::FileContainer ; $user ; $pass ) ]
# upload a file from disk
Set Variable [ $r ; BE_FTP_UploadFile ( "ftps://host/path/file.csv" ; $posixPath ; $user ; $pass ) ]
# delete a remote file
Set Variable [ $r ; BE_FTP_Delete ( "sftp://host/path/old.csv" ; $user ; $pass ) ]
```

`BE_HTTP_GET` also handles `ftp://`, `ftps://`, `sftp://` URLs for downloads.

## Proxy

```
BE_HTTP_Set_Proxy ( "proxy.host" ; 8080 ; $user ; $pass )   // fetch the doc for exact params
BE_CurlSetOption ( "CURLOPT_PROXYAUTH" ; CURLAUTH_NTLM )
```

## Notes

- The native **Insert From URL** step now covers many simple cases. Prefer BE when you need: the
  separate `BE_HTTP_ResponseCode`/`ResponseHeaders`, more cURL options, FTP/SFTP, or calling it from a
  calculation (not just a script step).
- Paths for `BE_HTTP_GET_File` / `BE_HTTP_PUTFile` are **native/POSIX** — convert FileMaker paths with
  `ConvertFromFileMakerPath ( ... ; PosixPath )`.
- Fetch any function's doc for exact params:
  `curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/BE_HTTP_POST.md`
