---
name: mbs
description: >
  Use when a FileMaker task involves the MBS (MonkeyBread Software) plugin — when you see
  MBS("...") calls, or when the task needs a capability native FileMaker lacks and MBS
  provides: sending email or making HTTP/FTP/REST API requests (CURL), creating or editing
  PDFs (DynaPDF), generating or scanning barcodes and QR codes (Barcode), resizing or
  converting images (GMImage), connecting to external SQL or MongoDB databases, reading or
  writing Excel (XL) or Word files, zipping, hashing, encrypting, or running shell commands.
  Also when registering/licensing the plugin, debugging MBS errors, freeing MBS references,
  or finding the right MBS function or example file.
---

# MBS Plugin (MonkeyBread Software) for FileMaker

The MBS plugin adds ~8,000 functions to FileMaker through a **single external function named
`MBS`**, with the real function name passed as a quoted string. It does the things native
FileMaker can't: HTTP/email, PDF, barcodes, image processing, external databases, Office
files, shell commands, and hundreds more.

This skill is the **mental model + on-demand lookup**. It deliberately does NOT memorize the
catalog — there are ~8,000 functions and they change every release, so an embedded list would
be wrong within months. When you need an exact signature, **you fetch it** (see "Don't guess").

MBS code lives inside FileMaker calculations and `Set Variable` steps, so the broader
`filemaker` skill still governs: write paste-ready **fmxmlsnippet**, **lint with `fmlint`
before presenting**, and grep the **schema snapshot** for real field/script names. This skill
adds the MBS-specific knowledge on top.

## The one thing to know: the calling convention

Every MBS call is the function `MBS` with the `Component.Function` name as the first (quoted)
argument, then its parameters:

```
MBS( "Component.Function" ; param1 ; param2 ; … )
```

Verified examples:
- `MBS( "Version" )` → plugin version string (e.g. "14.2.0.01")
- `MBS( "Barcode.Generate" ; "QRCODE" ; "https://example.com" )` → a barcode image container
- `MBS( "CURL.New" )` → a CURL session handle (a number ≥ 16000)

## Don't guess — fetch the signature

**Never invent an MBS function name or its parameters.** With ~8,000 functions that shift
between releases, memory is unreliable, and inventing functions destroys trust (house rule:
*don't guess FileMaker facts*). Look it up:

- **One function:** `https://www.mbsplugins.eu/<Function.Name>.shtml`
  — keep the period: `CURL.New` → `https://www.mbsplugins.eu/CURL.New.shtml`
- **Browse / discover (authoritative full list):** `https://www.mbsplugins.eu/index.shtml`
- **What's new in this release:** `https://www.mbsplugins.eu/new.shtml`

Each function page gives the parameters, description, the platforms it runs on, the version it
was introduced, related functions, **and a worked example in both plain text and ready-to-paste
fmxmlsnippet XML**. Full lookup mechanics — plus the **666 example databases** you can mine as
verified starter code — are in `references/lookup.md`.

## Critical conventions (verified)

### Licensing / registration
Unregistered, the plugin runs time-limited in **trial mode**, then functions start returning
errors. Register **once at solution startup** (a script triggered on file open), before any
other MBS call:

```
MBS( "Register" ; LicenseeName ; "Complete" ; "5 Seats" ; 202612 ; SerialNumber )
```

Arguments: licensee name · licensed component (e.g. `"Complete"`) · seats/type · expire month
in `YYYYMM` format · serial number. Returns `OK` on success. Related: `IsRegistered`,
`StoreRegistration` (persist the registration), `Plugin.State`, `Plugin.LicenseeName`.

### Error handling
MBS functions return their **error message _as the result_** on failure — so you can't always
tell a valid value from an error by looking at the text. Check explicitly, right after the call:

```
Set Variable [ $r ; Value: MBS( "Something.Do" ; … ) ]
If [ MBS( "IsError" ) ]
  # $r now holds the error text — log it / show it / exit
End If
```

`MBS("IsError")` returns 1 if the **last** MBS call errored, else 0. Related: `ClearErrors`,
`HadErrors`. (Check `IsError` immediately — the next MBS call resets it.)

### Memory release — the #1 MBS leak
Many components return a **reference number (a handle)**: CURL sessions, DynaPDF instances,
GMImage images, SQL connections, and more. Every `…New` / `…Open` / `…Create` that returns a
handle **must** be matched by its `…Release` / `…Free` / `…Cleanup` — **including on error
paths** — or you leak memory and eventually destabilize the FileMaker session.

```
Set Variable [ $curl ; Value: MBS("CURL.New") ]
# … set options, perform, read result …
Set Variable [ $del ; Value: MBS("CURL.Release"; $curl) ]   # ALWAYS, even after an error
```

If a function page says it returns a reference/handle, find and call its release function.

### Environment checks
`MBS("Version")`, `MBS("IsServer")`, `MBS("IsClient")`, `MBS("IsRuntime")` let you branch —
useful because many functions are macOS-only, Windows-only, or server-only. The platform table
at the top of each function page tells you where it runs.

## Where to look next

- `references/components-map.md` — the components you'll actually reach for, grouped by job, so
  you know *which* component to look up before you fetch its page.
- `references/lookup.md` — exact URL patterns, how to read a function page, lifting the
  fmxmlsnippet, the WebSearch fallback, and mining the 666 example databases as starter code.
- `references/recipes.md` — proven paste-ready patterns (CURL HTTP call, send email, barcode,
  PDF, image resize, Excel) with the lifecycle spelled out.

## Top gotchas

1. **Trial mode expires mid-session** if unregistered → register at startup before any MBS call.
2. **Forgetting `…Release`** leaks handles and destabilizes the session → pair every New/Open/Create.
3. **Use `MBS("IsError")`, not text inspection** — error messages look like ordinary results.
4. **Platform matters** — many functions are macOS / Windows / iOS / server-only; check the
   page's platform table before promising it works everywhere.
5. **Don't invent signatures** — fetch the function page; parameters change between releases.
6. **The plugin must be installed on every machine that runs the calc** — that means the
   **server too** for Perform Script on Server and server schedules, not just the client. It
   lives at `…/FileMaker Pro/<version>/Extensions/MBS.fmplugin`.
