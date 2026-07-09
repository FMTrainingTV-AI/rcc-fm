# BE SMTP Email recipes

BE sends email over SMTP directly through the cURL engine — more control than the native Send Mail
step (HTML + text, multiple attachments, custom headers, keep-alive connection), and it runs on
**FileMaker Server** for scheduled/server-side sending.

## Two-step pattern: configure the server, then send

```
# 1. store the connection (sticky — set once, reused by later sends)
Set Variable [ $r ; BE_SMTPServer (
    "smtp.example.com" ;
    587 ;                    // port (25 / 465 / 587)
    $username ;
    $password ;
    False                    // keepOpen: True = keep the connection open for a batch of sends
) ]

# 2. send
Set Variable [ $r ; BE_SMTPSend (
    "from@example.com" ;
    "to@example.com" ;
    "Subject line" ;
    $plainTextBody
) ]
Set Variable [ $err   ; BE_GetLastError ]   // 0 = sent; non-zero = cURL/SMTP failure
Set Variable [ $trace ; If ( $err <> 0 ; BE_CurlTrace ; "" ) ]   // transcript for diagnosis
```

## Full send — cc/bcc, reply-to, HTML, attachments

```
Set Variable [ $r ; BE_SMTPSend (
    "from@example.com" ;
    "a@x.com¶b@y.com" ;                 // multiple recipients: ¶-separated
    "Monthly report" ;
    $plainTextBody ;                    // text part (fallback)
    "cc@x.com" ;                        // cc
    "bcc@x.com" ;                       // bcc
    "replyto@example.com" ;             // reply-to
    $htmlBody ;                         // html part
    "/posix/path/doc.pdf¶/posix/path/sheet.csv"   // attachments: ¶-separated POSIX paths
) ]
```

Signature: `BE_SMTPSend ( from ; to ; subject ; text ; { cc ; bcc ; replyTo ; html ; attachments } )`.
- Multiple addresses and multiple attachment paths are **¶ (pilcrow) separated**.
- Attachment paths are **native/POSIX** — convert with `ConvertFromFileMakerPath ( ... ; PosixPath )`.
- Provide both `text` and `html` for a proper multipart email.

## Attaching a container (not a disk file)

When the file lives in a container field rather than on disk, queue it with
`BE_SMTPAddAttachment ( attachment ; contentType )` — `attachment` is the **container field itself**
(not a path); `contentType` is its MIME type:

```
Set Variable [ $r ; BE_SMTPAddAttachment ( MyTable::PdfContainer ; "application/pdf" ) ]
# call it again for more attachments, then send.
# FileMaker has no named params — count the positions: text, cc, bcc, replyTo, html.
Set Variable [ $r ; BE_SMTPSend (
    $from ; $to ; $subject ;
    $textFallback ;   // text part
    "" ;              // cc
    "" ;              // bcc
    "" ;              // replyTo
    $htmlBody         // html (8th arg). attachments param omitted — the queued container is sent.
) ]
```

- `BE_SMTPSend` **clears the queued attachment list after every send** (success or not) — re-queue for
  the next email.
- The plugin writes queued attachments to the OS **temp folder** to send them, so the account needs a
  working temp folder.
- An attachment failure may not surface until after the send — check `BE_CurlTrace` (look for the file
  path + error) when a send with attachments fails.

## Custom headers

```
Set Variable [ $r ; BE_SMTPSetHeader ( "X-Priority" ; "1" ) ]   // before the send
```

## Notes

- **Check `BE_GetLastError` after the send**, then `BE_CurlTrace` if non-zero — auth failures, TLS
  problems, and rejected recipients all surface there.
- `BE_SMTPServer` settings persist across sends; with `keepOpen = True` the connection stays open for a
  batch — send your loop, then the connection closes when settings change or the file closes.
- SSL/TLS: port 465 (implicit TLS) or 587 (STARTTLS) are typical. If the server uses a self-signed cert
  in dev, you can relax verification via `BE_CurlSetOption ( "CURLOPT_SSL_VERIFYPEER" ; 0 )` — never in
  production.
- **Most common send failure:** the `from` address must usually match the authenticated SMTP user (or a
  permitted alias). A non-zero `BE_GetLastError` on send is very often this, or wrong port/credentials —
  check `BE_CurlTrace`.
- Runs on FileMaker Server (good for scheduled scripts); does NOT run in FileMaker Go / WebDirect.
- Fetch the doc for exact params:
  `curl -sL https://raw.githubusercontent.com/GoyaPtyLtd/BaseElements-Plugin/main/docs/Functions/BE_SMTPSend.md`
