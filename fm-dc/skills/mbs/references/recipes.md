# MBS recipes — proven lifecycles for common tasks

These are the **shapes** of the most common MBS jobs: which functions, in what order, and where
the handle gets released. Tag legend:

- **(verified)** — function name AND parameters confirmed against the live function page.
- **(verified name)** — name confirmed real; double-check its exact parameters on its page.
- **(confirm on page)** — fetch the function page to confirm name and/or parameters first.

Signatures and parameters vary between plugin releases, so when in doubt, fetch the page.

**Every recipe still goes through the paste loop:** write it as fmxmlsnippet, **lint with
`fmlint`**, substitute the user's real field/table/script names from the schema snapshot, then
present paste-ready (see the `fm-xml` and `fm-core` skills). When an MBS **example database** matches the
task, prefer adapting its verified code — see `lookup.md` ("Mining the example databases").

---

## 1. HTTP / REST API call (CURL) — verified lifecycle

Build the JSON body first with native `JSONSetElement` (or the MBS `JSON` component — see the
`filemaker` skill), then:

```
# POST a JSON body to a REST API; store status + body into fields
Set Variable [ $curl ;   Value: MBS("CURL.New") ]                                  # (verified) returns a handle ≥ 16000

Set Variable [ $r ;      Value: MBS("CURL.SetOptionURL"; $curl; "https://api.example.com/v1/orders") ]   # (verified)

# Setting PostFields makes this an HTTP POST. For PUT/PATCH/DELETE also call
# CURL.SetOptionCustomRequest; for a plain GET, omit PostFields entirely.
Set Variable [ $r ;      Value: MBS("CURL.SetOptionPostFields"; $curl; $jsonBody) ]                      # (verified)
Set Variable [ $r ;      Value: MBS("CURL.SetOptionHTTPHeader"; $curl; "Content-Type: application/json"; "Authorization: Bearer " & $token) ]   # (verified) one arg per header

Set Variable [ $result ; Value: MBS("CURL.Perform"; $curl) ]                       # (verified) runs the transfer
Set Variable [ $http ;   Value: MBS("CURL.GetResponseCode"; $curl) ]              # (verified) e.g. 200 / 201
Set Variable [ $body ;   Value: MBS("CURL.GetResultAsText"; $curl; "UTF-8") ]     # (verified) response body
If [ MBS("IsError") or $http >= 400 ]
  Set Variable [ $debug ; Value: MBS("CURL.GetDebugMessages"; $curl) ]            # (verified) full transcript for troubleshooting
End If

# Read results into fields BEFORE releasing — CURL.Release frees the result buffer:
Set Field [ YourTable::HTTPStatus   ; $http ]
Set Field [ YourTable::ResponseBody ; $body ]

Set Variable [ $del ;    Value: MBS("CURL.Release"; $curl) ]                       # (verified) ALWAYS release, even on error
```

Notes: `CURL.SetOptionHTTPHeader` accepts multiple header arguments (one per header).
`CURL.GetResultAsText` has an optional `preserveLineEndings` param if a response body gets
mangled. Other options (timeouts, auth, client certs, redirects) have their own
`CURL.SetOption…` functions — fetch the CURL component page.

---

## 2. Send an email with attachment (SendMail builds it, CURL sends it) — verified

**There is no `SendMail.Send`.** SendMail only *composes* the message; the email is actually sent
by **CURL** — create a session, `SendMail.PrepareCURL` to configure it, then `CURL.Perform`.
Release both handles.

```
# --- Build the message ---
Set Variable [ $email ; Value: MBS("SendMail.CreateEmail") ]                       # (verified) returns an email reference
Set Variable [ $r ; Value: MBS("SendMail.SetFrom"; $email; "me@co.com"; "Me") ]   # (verified name)
Set Variable [ $r ; Value: MBS("SendMail.AddTo"; $email; "you@co.com"; "You") ]   # (verified) AddTo(EmailID; Email {; Name})
Set Variable [ $r ; Value: MBS("SendMail.SetSubject"; $email; "Your report") ]    # (verified name)
Set Variable [ $r ; Value: MBS("SendMail.SetHTMLText"; $email; "<p>Report attached.</p>") ]   # (verified name) or SetPlainText

# --- Attach a PDF (from a container, or from a native file path) ---
Set Variable [ $r ; Value: MBS("SendMail.AddAttachmentContainer"; $email; YourTable::PDF; "report.pdf"; "application/pdf") ]   # (verified)
#   from disk instead: MBS("SendMail.AddAttachmentFile"; $email; $nativePath; "report.pdf"; "application/pdf")  — native path, < 100 MB

# --- SMTP credentials ---
Set Variable [ $r ; Value: MBS("SendMail.SetSMTPServer"; $email; "smtp.co.com"; 1) ]   # (verified) 3rd param = TLS: 1 = implicit TLS / port 465; 0 = then configure CURL for STARTTLS
Set Variable [ $r ; Value: MBS("SendMail.SetSMTPUserName"; $email; "user") ]      # (verified name)
Set Variable [ $r ; Value: MBS("SendMail.SetSMTPPassword"; $email; "password") ]  # (verified)

# --- SEND via CURL, then release BOTH handles ---
Set Variable [ $curl ; Value: MBS("CURL.New") ]                                    # (verified) email is sent through CURL
Set Variable [ $r ; Value: MBS("SendMail.PrepareCURL"; $email; $curl) ]            # (verified) PrepareCURL(EmailID; CURLID) — needs the existing CURL session
Set Variable [ $result ; Value: MBS("CURL.Perform"; $curl) ]                       # (verified) THIS sends the email
If [ MBS("IsError") ]
  Set Variable [ $debug ; Value: MBS("CURL.GetDebugMessages"; $curl) ]            # (verified) transcript on failure
End If
Set Variable [ $del ; Value: MBS("CURL.Release"; $curl) ]                          # (verified) release
Set Variable [ $del ; Value: MBS("SendMail.Release"; $email) ]                     # (verified) release
```

The MBS **"Build and send Email"** example (under `CURL/Email`) is the canonical reference for
batch sending, inline images, or extra CURL options (STARTTLS, custom port, verbose logging).

---

## 3. Generate a barcode / QR code (Barcode) — verified

```
# QR code straight into a container field
Set Field [ Table::Image ; MBS("Barcode.Generate"; "QRCODE"; Table::URL) ]
```

Full signature **(verified)**:
```
MBS( "Barcode.Generate" ; symbology ; Text { ; Width ; Height ; Rotation ; Scale ; Transparent ; ShowText ; Encoding } )
```
- Symbologies include `UPCA`, `EAN13`, `CODE128`, `QRCODE`, `PDF417`, `DATAMATRIX`, and more —
  the full list is on the `Barcode.Generate` page.
- To **read** a barcode from an image container, use the Barcode detect/recognize functions —
  confirm exact names on the Barcode component page. **(confirm on page)**

---

## 4. Create a PDF (DynaPDF) — verified anchors (needs an EXTRA license)

**DynaPDF needs its own license**, separate from the MBS plugin license — pass it to
`DynaPDF.Initialize` first or you're limited to demo output. `DynaPDF.New` returns a PDF
reference you MUST release. Verified lifecycle anchors:

```
Set Variable [ $r   ; Value: MBS("DynaPDF.Initialize"; $dynapdfLicenseKey) ]   # (verified) set the DynaPDF license once at startup
Set Variable [ $pdf ; Value: MBS("DynaPDF.New") ]                              # (verified) returns a PDF reference; pair with Release
Set Variable [ $r   ; Value: MBS("DynaPDF.AppendPage"; $pdf) ]                 # (verified) start a page
Set Variable [ $r   ; Value: MBS("DynaPDF.WriteFText"; $pdf; "left"; "Hello, world.") ]   # (verified name) draw text — confirm params on page
# … EndPage, then output: DynaPDF.OpenOutputFile / DynaPDF.Save / DynaPDF.GetPDF … # (confirm on page)
Set Variable [ $del ; Value: MBS("DynaPDF.Release"; $pdf) ]                    # (verified) ALWAYS release
```

DynaPDF is a large engine (import/merge, stamp, fill forms, render to image, OCR). The exact
page/output sequence is fiddly — assemble it from the **DynaPDF examples**, which are the
fastest route to a working flow for your specific task.

---

## 5. Resize / convert an image (GMImage) — verified

```
Set Variable [ $img ; Value: MBS("GMImage.NewFromContainer"; Table::Photo) ]   # (verified) load from a container
Set Variable [ $r ;   Value: MBS("GMImage.Scale"; $img; "800x600") ]           # (verified) resize; geometry "WxH" (+ "!" ignore ratio, "%" percent, ">" / "<" only if larger/smaller)
Set Field [ Table::Thumb ; MBS("GMImage.WriteToPNGContainer"; $img; "thumb.png") ]   # (verified) → PNG container; also WriteToContainer / WriteToTiffContainer / WriteToWebPContainer
Set Variable [ $del ; Value: MBS("GMImage.Release"; $img) ]                     # (verified) ALWAYS release
```

Other ops — crop, rotate, sharpen, filters, format conversion — are all `GMImage.*`; see the
component page.

---

## 6. Read / write Excel (XL) — verified lifecycle

```
Set Variable [ $book ; Value: MBS("XL.LoadBook"; Table::ExcelFile) ]            # (verified) load .xlsx/.xls; or XL.NewBook to create one
Set Variable [ $val ;  Value: MBS("XL.CopyCellValue"; $book; 0; 0; 0) ]         # (verified) read a cell — args are sheet, row, col (confirm 0- vs 1-based on page)
Set Variable [ $r ;    Value: MBS("XL.Sheet.CellWriteText"; $book; 0; 0; 0; "Hello") ]   # (verified) write a cell
Set Variable [ $r ;    Value: MBS("XL.Book.SaveToFile"; $book; $path) ]         # (verified) save the workbook
Set Variable [ $del ;  Value: MBS("XL.Book.Release"; $book) ]                   # (verified) ALWAYS release
```

After saving, FileMaker can **Import Records** from the file. Exact cell indexing and parameter
order vary by function — confirm each on its page.

---

## The pattern behind all of them

1. **Create/open** a reference (if the component uses one).
2. **Configure** with `…SetOption…` / `…Set…` calls.
3. **Perform / Generate / Save** the actual operation.
4. **Read** the result (text, container, response code).
5. **Check `MBS("IsError")`** right after the operation.
6. **Release** every reference you created — even on error paths.

When unsure of any step's exact function or parameters, **fetch the function page or the
matching example** (`lookup.md`). Never present an MBS signature you haven't confirmed.
