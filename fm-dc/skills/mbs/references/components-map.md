# MBS components — the ones you'll actually reach for

MBS has **200+ components** (~8,000 functions total). This is a curated map of the high-use
ones, grouped by the job you're trying to do, so you can pick the right component *before* you
look up the exact function. It is **not** exhaustive.

**The authoritative, complete list is `https://www.mbsplugins.eu/index.shtml`** (alphabetical,
with platform filters: macOS / Windows / Linux / iOS / Server / Client). When in doubt about
whether a component or function exists, or its exact name, **fetch the page** — don't assume.

A component is just a name prefix on functions: the **CURL** component owns `CURL.New`,
`CURL.Perform`, `CURL.Release`, etc.

## Web, networking & email
| Component | Use it for |
|---|---|
| **CURL** | HTTP/HTTPS/FTP/SFTP/FTPS, REST API calls, file up/download, S3, the transport for sending email |
| **SendMail** | Compose an email (from/to/subject/body/attachments) and hand it to CURL/SMTP to send |
| **EmailParser** | Read/parse incoming email (e.g. fetched via CURL+IMAP) |
| **WebHook** | Receive inbound HTTP callbacks |

## PDF
| Component | Use it for |
|---|---|
| **DynaPDF** | Full PDF engine: create, merge/split, stamp/watermark, fill forms, render to image, OCR (macOS/Windows; has its own license tiers — check the page) |
| **PDFKit** | Simpler macOS-native PDF operations |

## Images & barcodes
| Component | Use it for |
|---|---|
| **GMImage** | GraphicsMagick: resize, crop, rotate, convert formats, filters, compose |
| **Barcode** | Generate (`Barcode.Generate`) and scan/recognize 1D/2D codes incl. QR, PDF417, DataMatrix |
| **Image** | Image metadata, EXIF, basic info |
| **ContinuityCamera / ImageCapture** | Capture/scan from camera or scanner (macOS) |

## Files & system
| Component | Use it for |
|---|---|
| **Files** | Read/write/copy/move/delete files, attributes, existence checks |
| **Path** | Build and parse file paths cross-platform |
| **Folders** | Locate special folders (Documents, Temp, Desktop, …) |
| **Archive** | Zip/unzip, tar, compression |
| **Process / Shell** | Run command-line programs and read their output |

## External databases
| Component | Use it for |
|---|---|
| **SQL** | Connect to MySQL, MS SQL Server, PostgreSQL, Oracle, SQLite, ODBC sources and run queries |
| **MongoDB** | NoSQL document database access |
| **ODBC** | Generic ODBC data sources |

## Office documents
| Component | Use it for |
|---|---|
| **XL** | Read/write native Excel `.xlsx` / `.xls` (cells, formulas, formatting, charts) |
| **WordFile** | Read/write Word `.docx`, template merge |
| **Office** | Other office-format helpers (macOS) |

## Text, data & formats
| Component | Use it for |
|---|---|
| **JSON** | Fast JSON parse/query/build (beyond native, e.g. large payloads, path queries) |
| **XML** | Parse, query (XPath), transform (XSLT), validate XML |
| **RegEx** | Regular-expression match/replace/extract |
| **Text** | Encoding conversions, trimming, transforms |
| **QuickList / Dictionary** | In-memory list and key/value structures |

## Security
| Component | Use it for |
|---|---|
| **Hash** | MD5 / SHA digests, HMAC |
| **Encryption** | AES symmetric encrypt/decrypt |
| **RSA / X509 / JWT** | Public-key crypto, certificates, signed tokens |

## FileMaker control & UI
| Component | Use it for |
|---|---|
| **FM** | Run FileMaker scripts, evaluate calcs, run SQL against FM |
| **Clipboard** | Read/write the clipboard — including converting FileMaker objects ⇄ XML (the mechanism behind the paste-loop "clipboard converter") |
| **WebView / WKWebView** | Embed web content in a layout with a two-way JavaScript bridge |
| **Window / Menu / Schema / Container** | Manipulate windows, menus, inspect schema, work with container data |
| **ScriptWorkspace** | Developer conveniences: script coloring, search, syntax tools |

## Scheduling & events
| Component | Use it for |
|---|---|
| **Schedule / Timer** | Run a FileMaker script after a delay or on an interval |
| **FileMonitor** | Watch a folder/file and react to changes |
| **EventMonitor / IdleTimer** | React to user activity / idleness |

## macOS / iOS native (platform-gated — check the page)
| Component | Use it for |
|---|---|
| **Addressbook / Contacts** | Read/write the system contacts |
| **Calendar / Events** | EventKit calendar and reminders |
| **MapKit / CoreLocation** | Maps and geolocation |
| **AVRecorder / AVExport** | Record and convert audio/video |
| **SerialPort / Bluetooth** | Hardware/peripheral access |
| **Notification / SystemInfo** | System notifications, machine info |

---

**Picking a component you're unsure about:** open `https://www.mbsplugins.eu/index.shtml`, or
WebSearch `MBS FileMaker <what you want to do>`. Confirm the component and the exact function
names on their pages before writing code — see `lookup.md`.
