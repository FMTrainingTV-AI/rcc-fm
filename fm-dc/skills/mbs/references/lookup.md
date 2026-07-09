# Looking up MBS functions and mining example files

The whole point of this skill: **don't memorize the catalog, fetch what you need.** Here is how.

## URL patterns (verified)

| What | URL |
|---|---|
| A single function's reference page | `https://www.mbsplugins.eu/<Function.Name>.shtml` |
| Browse all components / functions | `https://www.mbsplugins.eu/index.shtml` |
| New functions in the current release | `https://www.mbsplugins.eu/new.shtml` |
| The 666 example databases | `https://www.mbsplugins.eu/MBS-FileMaker-Plugin-Examples/` |

**Keep the period in dotted names.** `CURL.New` → `https://www.mbsplugins.eu/CURL.New.shtml`;
`Barcode.Generate` → `https://www.mbsplugins.eu/Barcode.Generate.shtml`. Single-word functions
work the same way: `Version` → `https://www.mbsplugins.eu/Version.shtml`.

(Both forms resolve: `CURL.New.shtml` and the dot-less `CURLNew.shtml`. MBS's own internal links
and search results use the **dot-less** form, so you'll often land on that — either works.)

(`mbsplugins.eu` is the function-reference host. The main site
`monkeybreadsoftware.com/filemaker/` carries the product overview, the user **guide**
`/guide/`, downloads, release notes, and pricing.)

## How to read a function page

Each page is structured the same way. Pull these out:

1. **Platform compatibility table** (top) — macOS / Windows / Linux / iOS SDK / Server. Check
   this before promising the function works on the user's platform or on the server (PSOS).
2. **Parameters** — name, whether optional (shown in `{ }`), and meaning. Optional params are
   in braces in the syntax line, e.g.
   `MBS( "Barcode.Generate"; symbology; Text { ; Width; Height; Rotation; Scale; … } )`.
3. **Description** — behavior, gotchas, return value, whether it returns a **reference/handle**
   you must later release.
4. **Version** — the plugin version the function was introduced in (so you know it exists in the
   user's installed version).
5. **Example** — given in **both plain text and fmxmlsnippet XML**. See below.
6. **Related functions** — the neighbors you'll usually need (e.g. `CURL.New` links to the
   options, perform, result, and release functions). Follow these to assemble a full workflow.

## Lift the fmxmlsnippet

Function-page examples include the calculation/script in **fmxmlsnippet** format — the same
clipboard XML the paste loop uses. You can adapt it directly into what you hand the user. Still
**lint it with `fmlint`** and adjust real field/table names from the schema snapshot before
presenting (per the `filemaker` skill).

## When you don't know the function name

1. **Browse the component** on `index.shtml`, or read the component group in
   `components-map.md` to pick the component, then scan its functions.
2. **WebSearch** `MBS FileMaker <capability>` (e.g. "MBS FileMaker send email with attachment",
   "MBS FileMaker resize image"). MBS pages and blog posts rank well and link to the exact
   functions and examples.
3. **Verify** the candidate by fetching its function page before you write it. Never ship a
   function name you haven't confirmed exists.

## Mining the example databases as starter code

MBS ships **666 example databases**, browsable online at
`https://www.mbsplugins.eu/MBS-FileMaker-Plugin-Examples/`, grouped by component and
subcategory (e.g. `CURL/Email`, `Barcode`, `DynaPDF`). These are the single best source of
*known-good* MBS code — written and tested by MBS themselves.

**The directory and category pages are link lists only — no code.** The top
`…/MBS-FileMaker-Plugin-Examples/` page and its category listings (e.g. `…/CURL/Email/`) just
link to examples. **The code lives one level deeper, on the individual example page:**
`https://www.mbsplugins.eu/MBS-FileMaker-Plugin-Examples/<Category>/<Example%20Name>.shtml`
(spaces become `%20`), e.g.
`…/MBS-FileMaker-Plugin-Examples/CURL/Email/Build%20and%20send%20Email.shtml`.

**That individual example page shows the complete code inline** — the actual FileMaker script
steps and calculations, e.g. `Set Variable [$img; Value:MBS("Barcode.Generate"; …)]`, the
table/field structure, the function list, and a `.zip` download of the `.fmp12`. Drill into the
example page; don't stop at the listing.

How to use them:
- When a task matches an example, **fetch the example page and read MBS's working code**, then
  adapt it to the user's schema (real field/table/script names from the snapshot).
- **Read the example _page_, not the `.fmp12`** — the downloaded file is binary and you can't
  parse it directly; the page already contains the code in readable form.
- Prefer adapting verified example code over hand-writing from scratch — it's faster and avoids
  signature mistakes.
- The full set of example files also installs alongside the plugin if the user downloads the
  complete MBS package; point them there if they want to open and run an example themselves.

## A worked lookup (what good looks like)

> Task: "Have FileMaker download a JSON feed from an API and store the response."
>
> 1. Capability = HTTP request → component **CURL** (`components-map.md`).
> 2. Fetch `https://www.mbsplugins.eu/CURL.New.shtml` → confirms it returns a handle that
>    **must** be released, and links to the options / perform / result functions.
> 3. Follow related links: `CURL.SetOptionURL`, `CURL.Perform`, `CURL.GetResultAsText`,
>    `CURL.GetResponseCode`, `CURL.Release` — confirm each signature.
> 4. Assemble the recipe (see `recipes.md`), lint it, present it paste-ready.
