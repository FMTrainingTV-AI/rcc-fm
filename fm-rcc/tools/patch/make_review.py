"""
make_review.py — build a self-contained HTML diff-review artifact.

API:
    build_html(diff: dict) -> str

CLI:
    python3 scripts/make_review.py diff.json -o review.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ── Human labels for kind values, in display order ─────────────────────────
KIND_ORDER = [
    "base_table",
    "field",
    "table_occurrence",
    "relationship",
    "value_list",
    "custom_function",
    "script",
    "layout",
    "external_data_source",
]

KIND_LABELS = {
    "base_table": "Base Tables",
    "field": "Fields",
    "table_occurrence": "Table Occurrences",
    "relationship": "Relationships",
    "value_list": "Value Lists",
    "custom_function": "Custom Functions",
    "script": "Scripts",
    "layout": "Layouts",
    "external_data_source": "External Data Sources",
}


def build_html(diff: dict, deps: dict | None = None,
               blockers: dict | None = None, direction: str = "push") -> str:
    """Return a single self-contained HTML string for the diff review UI.

    deps: {item_key: [dependency_keys]} adjacency map (from
    gen_patch.dependency_analysis). Ticking an item auto-includes its
    dependencies so the downloaded selection is always closed.

    blockers: {item_key: [{kind, name, reason}]} — dependencies that cannot be
    auto-included (ignored, manual-tier, duplicate-named, or absent). An item
    with blockers is rendered unselectable with the reason shown; it must never
    reach gen_patch, because its closure would be missing a prerequisite.

    direction:
      "push" — dev is the source and prod keeps its own history. Objects that
               exist only in prod are NOT selectable; they render in a
               "Prod-only — preserved" section with no checkbox, so the patch
               cannot delete the target's divergent work.
      "sync" — prod-only objects are selectable and compile to DeleteAction.
    """
    if direction not in ("push", "sync"):
        raise ValueError(f"direction must be 'push' or 'sync', got {direction!r}")
    deps = deps or {}
    blockers = blockers or {}

    # Reverse adjacency for the "referenced by" half of each object profile:
    # what breaks if this object does not travel.
    rdeps: dict[str, list[str]] = {}
    for key, targets in deps.items():
        for t in targets:
            rdeps.setdefault(t, []).append(key)
    for v in rdeps.values():
        v.sort()
    # Escape the diff so it can be embedded inside a <script> block safely.
    # json.dumps produces valid JS (booleans/null map correctly).
    # Replacing "</" with "<\\/" prevents any "</script>" inside string
    # values from terminating the script block.
    # Script-embed safety: "</" can close the script tag early, and "<!--"
    # switches the HTML parser into escaped-script state (either one inside a
    # FileMaker string — e.g. web-viewer HTML in a calc — silently kills the
    # whole artifact). ! is '!' so the JSON stays valid.
    diff_json = (json.dumps(diff, ensure_ascii=False)
                 .replace("</", "<\\/").replace("<!--", "<\\u0021--"))
    deps_json = (json.dumps(deps, ensure_ascii=False)
                 .replace("</", "<\\/").replace("<!--", "<\\u0021--"))
    blockers_json = (json.dumps(blockers, ensure_ascii=False)
                     .replace("</", "<\\/").replace("<!--", "<\\u0021--"))
    rdeps_json = (json.dumps(rdeps, ensure_ascii=False)
                  .replace("</", "<\\/").replace("<!--", "<\\u0021--"))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FM Diff Review</title>
<style>
:root {{
  --bg: #f8f9fa;
  --surface: #ffffff;
  --border: #dee2e6;
  --text: #212529;
  --text-dim: #6c757d;
  --text-small: #495057;
  --accent: #0d6efd;
  --hover-bg: #f1f3f5;
  --added-bg: #d1e7dd;
  --added-text: #0a3622;
  --removed-bg: #f8d7da;
  --removed-text: #58151c;
  --modified-bg: #fff3cd;
  --modified-text: #664d03;
  --caution-bg: #fff3cd;
  --manual-bg: #f8d7da;
  --proven-bg: #d1e7dd;
  --footer-bg: #ffffff;
  --footer-border: #dee2e6;
  --pre-bg: #f8f9fa;
  --section-header-bg: #f1f3f5;
  --chip-active-bg: #0d6efd;
  --chip-active-text: #ffffff;
  --chip-bg: #e9ecef;
  --chip-text: #495057;
  --warning-bg: #fff3cd;
  --warning-border: #ffc107;
  --warning-text: #664d03;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #1a1b1e;
    --surface: #25262b;
    --border: #373a40;
    --text: #c1c2c5;
    --text-dim: #909296;
    --text-small: #a6a7ab;
    --accent: #4dabf7;
    --hover-bg: #2c2d32;
    --added-bg: #0d3321;
    --added-text: #75e09a;
    --removed-bg: #3b1219;
    --removed-text: #f0a0a8;
    --modified-bg: #3b2a00;
    --modified-text: #ffc940;
    --caution-bg: #3b2a00;
    --manual-bg: #3b1219;
    --proven-bg: #0d3321;
    --footer-bg: #25262b;
    --footer-border: #373a40;
    --pre-bg: #1a1b1e;
    --section-header-bg: #2c2d32;
    --chip-active-bg: #4dabf7;
    --chip-active-text: #1a1b1e;
    --chip-bg: #373a40;
    --chip-text: #c1c2c5;
    --warning-bg: #3b2a00;
    --warning-border: #ffc107;
    --warning-text: #ffc940;
  }}
}}

*, *::before, *::after {{ box-sizing: border-box; }}

body {{
  margin: 0;
  padding: 0 0 120px 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
}}

.container {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 16px;
}}

/* ── Header ───────────────────────────────────── */
.header {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 0;
  margin-bottom: 16px;
}}
.header-title {{
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
}}
.header-paths {{
  font-size: 12px;
  color: var(--text-dim);
  margin: 0 0 10px 0;
}}
.header-counts {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}}
.count-pill {{
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}}
.count-pill.added   {{ background: var(--added-bg);    color: var(--added-text); }}
.count-pill.removed {{ background: var(--removed-bg);  color: var(--removed-text); }}
.count-pill.modified{{ background: var(--modified-bg); color: var(--modified-text); }}
.header-version {{
  font-size: 11px;
  color: var(--text-dim);
  margin-left: auto;
}}

/* ── Filter chips ─────────────────────────────── */
.filter-bar {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 12px;
}}
.chip {{
  padding: 4px 12px;
  border-radius: 16px;
  background: var(--chip-bg);
  color: var(--chip-text);
  border: 1px solid var(--border);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.1s, color 0.1s;
  user-select: none;
}}
.chip.active {{
  background: var(--chip-active-bg);
  color: var(--chip-active-text);
  border-color: var(--chip-active-bg);
}}
.chip:hover:not(.active) {{
  background: var(--hover-bg);
}}

/* ── Global actions ───────────────────────────── */
.global-actions {{
  margin-bottom: 16px;
}}
.btn {{
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.1s;
}}
.btn:hover {{ background: var(--hover-bg); }}
.btn-primary {{
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}}
.btn-primary:hover {{ opacity: 0.9; background: var(--accent); }}

/* ── Section ──────────────────────────────────── */
.section {{
  margin-bottom: 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}}
.section-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--section-header-bg);
  border-bottom: 1px solid var(--border);
  user-select: none;
}}
.section-label {{
  font-weight: 600;
  font-size: 13px;
}}
.section-count {{
  font-size: 12px;
  color: var(--text-dim);
  margin-right: auto;
}}
.section-select-btn {{
  font-size: 12px;
  padding: 2px 8px;
}}
.section-body {{ }}

/* ── Item row ─────────────────────────────────── */
.item-row {{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 12px;
  border-bottom: 1px solid var(--border);
  transition: background 0.07s;
}}
.item-row:last-child {{ border-bottom: none; }}
.item-row:hover {{ background: var(--hover-bg); }}
.item-row.hidden {{ display: none; }}

.item-checkbox {{
  margin-top: 3px;
  flex-shrink: 0;
  cursor: pointer;
  accent-color: var(--accent);
}}
.item-checkbox:disabled {{ cursor: not-allowed; opacity: 0.5; }}
.item-details.auto-dep > summary {{ background: var(--added-bg); }}
.item-details.auto-dep .item-name::after {{
  content: " · auto-included dependency";
  color: var(--text-dim);
  font-style: italic;
}}

.item-name {{
  flex: 1;
  font-size: 13px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  word-break: break-all;
}}

.item-badges {{
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}}

.change-pill {{
  display: inline-block;
  padding: 1px 7px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}}
.change-pill.added    {{ background: var(--added-bg);    color: var(--added-text); }}
.change-pill.removed  {{ background: var(--removed-bg);  color: var(--removed-text); }}
.change-pill.modified {{ background: var(--modified-bg); color: var(--modified-text); }}

.patch-badge {{
  display: inline-block;
  font-size: 12px;
  line-height: 1;
}}

.dup-icon {{
  font-size: 12px;
  cursor: help;
}}

/* ── Item details ─────────────────────────────── */
.item-details {{
  width: 100%;
  border-bottom: 1px solid var(--border);
}}
.item-details:last-child {{ border-bottom: none; }}
.item-details summary {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  cursor: pointer;
  list-style: none;
  transition: background 0.07s;
  user-select: none;
}}
.item-details summary:hover {{ background: var(--hover-bg); }}
.item-details summary::-webkit-details-marker {{ display: none; }}
.item-details summary::before {{
  content: "▶";
  font-size: 9px;
  color: var(--text-dim);
  flex-shrink: 0;
  transition: transform 0.1s;
}}
.item-details[open] summary::before {{ transform: rotate(90deg); }}

.details-body {{
  padding: 8px 12px 12px 32px;
  background: var(--bg);
  border-top: 1px solid var(--border);
}}
.details-summary-text {{
  font-size: 12px;
  color: var(--text-small);
  font-style: italic;
}}
.changed-attrs-list {{
  margin: 6px 0 10px 0;
  padding-left: 16px;
  font-size: 12px;
  color: var(--text-small);
}}
.json-panels {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}}
@media (max-width: 700px) {{
  .json-panels {{ grid-template-columns: 1fr; }}
}}
.json-panel-label {{
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  margin-bottom: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.json-panel-single {{
  grid-column: 1 / -1;
}}
pre.json-pre {{
  background: var(--pre-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  font-size: 12px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}}
pre.calc-pre {{
  border-left: 3px solid var(--accent);
}}
.calc-label {{
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  margin-top: 8px;
  margin-bottom: 3px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

/* ── Ignored section ──────────────────────────── */
.ignored-section {{
  margin-top: 20px;
}}
.ignored-section > summary {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--section-header-bg);
  border: 1px solid var(--border);
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  list-style: none;
  user-select: none;
}}
.ignored-section > summary::-webkit-details-marker {{ display: none; }}
.ignored-section > summary::before {{
  content: "▶";
  font-size: 9px;
  color: var(--text-dim);
  transition: transform 0.1s;
}}
.ignored-section[open] > summary::before {{ transform: rotate(90deg); }}
.ignored-section-body {{
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 8px 8px;
  background: var(--surface);
  overflow: hidden;
}}

/* ── Sticky footer ────────────────────────────── */
.sticky-footer {{
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--footer-bg);
  border-top: 1px solid var(--footer-border);
  padding: 10px 16px;
  z-index: 100;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.08);
}}
.footer-inner {{
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}}
.footer-count {{
  font-size: 13px;
  font-weight: 500;
  flex: 1;
  min-width: 140px;
}}
.footer-warning {{
  width: 100%;
  font-size: 12px;
  color: var(--warning-text);
  background: var(--warning-bg);
  border: 1px solid var(--warning-border);
  border-radius: 4px;
  padding: 4px 10px;
  display: none;
}}
.footer-warning.visible {{ display: block; }}

/* ── Dependency + safety affordances ─────────────────────────────────────── */
.dep-manifest {{
  flex-basis: 100%;
  margin-top: 6px;
  padding: 6px 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-small);
  background: var(--added-bg);
  border-left: 3px solid #198754;
  border-radius: 3px;
}}
.dep-trail {{
  font-size: 11px;
  font-style: italic;
  color: #198754;
  margin-left: 6px;
  white-space: nowrap;
}}
.blocked-pill {{
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  padding: 1px 6px;
  border-radius: 9px;
  background: #f8d7da;
  color: #842029;
  margin-left: 4px;
}}
.item-details.blocked > summary {{
  background: #fff5f5;
  opacity: .85;
}}
.item-details.blocked .item-name {{ text-decoration: line-through; }}
.blocked-box, .preserved-box {{
  margin: 8px 0;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 12.5px;
  line-height: 1.55;
}}
.blocked-box {{ background: #f8d7da; color: #842029; }}
.preserved-box {{ background: #e7f1ff; color: #084298; }}
.blocked-title, .preserved-title {{ font-weight: 700; margin-bottom: 4px; }}
.blocked-list {{ margin: 4px 0 0 18px; }}
.blocked-list li {{ margin-bottom: 3px; }}
.preserved-section > summary {{ background: #e7f1ff; color: #084298; }}
.preserved-blurb {{
  padding: 8px 12px;
  font-size: 12.5px;
  line-height: 1.55;
  color: #084298;
  background: #f2f7ff;
  border-bottom: 1px solid var(--border);
}}
.profile-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin: 8px 0;
}}
.profile-col {{
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 8px 10px;
  background: var(--surface);
}}
.profile-title {{ font-weight: 600; font-size: 12px; margin-bottom: 2px; }}
.profile-help {{ font-size: 11px; color: var(--text-dim); margin-bottom: 6px; line-height: 1.45; }}
.profile-empty {{ font-size: 12px; color: var(--text-dim); font-style: italic; }}
.profile-list {{ margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.7; }}
.profile-link {{ color: var(--accent); text-decoration: none; }}
.profile-link:hover {{ text-decoration: underline; }}
.profile-kind {{ font-size: 10px; color: var(--text-dim); margin-left: 6px; }}
.profile-flag.blocked {{
  font-size: 10px; color: #842029; background: #f8d7da;
  padding: 0 5px; border-radius: 8px; margin-left: 6px;
}}
.item-details.flash > summary {{
  animation: flashrow 1.2s ease-out;
}}
@keyframes flashrow {{
  0%   {{ background: #ffe69c; }}
  100% {{ background: transparent; }}
}}
.lock-glyph {{
  font-size: 12px;
  margin-right: 2px;
  opacity: .7;
  flex-shrink: 0;
}}
.direction-pill {{
  font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
  background: #cfe2ff; color: #084298; margin-left: 8px;
}}
.direction-pill.danger {{ background: #f8d7da; color: #842029; }}
.chip-preserved {{ margin-left: auto; }}
.copy-feedback {{
  font-size: 12px;
  color: var(--text-dim);
  min-width: 60px;
}}

.no-items-msg {{
  padding: 12px 16px;
  color: var(--text-dim);
  font-size: 13px;
  font-style: italic;
}}
</style>
</head>
<body>

<div class="header">
  <div class="container">
    <div id="header-title" class="header-title"></div>
    <div id="header-paths" class="header-paths"></div>
    <div id="header-counts" class="header-counts"></div>
    <div class="global-actions">
      <button class="btn btn-primary" onclick="selectAllProvenAdded()">Select all proven added</button>
    </div>
    <div class="filter-bar" id="filter-bar"></div>
  </div>
</div>

<div class="container">
  <div id="sections-container"></div>
  <details class="ignored-section preserved-section" id="preserved-section" style="display:none">
    <summary>
      <span id="preserved-label">Prod-only — preserved</span>
      <span id="preserved-count" style="font-size:12px;color:var(--text-dim);font-weight:400;margin-left:4px"></span>
    </summary>
    <div class="preserved-blurb" id="preserved-blurb"></div>
    <div class="ignored-section-body" id="preserved-body"></div>
  </details>
  <details class="ignored-section" id="ignored-section" style="display:none">
    <summary>
      <span id="ignored-label">Ignored</span>
      <span id="ignored-count" style="font-size:12px;color:var(--text-dim);font-weight:400;margin-left:4px"></span>
    </summary>
    <div class="ignored-section-body" id="ignored-body"></div>
  </details>
</div>

<div class="sticky-footer">
  <div class="footer-inner">
    <span class="footer-count" id="footer-count">0 selected</span>
    <button class="btn" onclick="downloadSelection()">Download selection.json</button>
    <button class="btn" onclick="copySelection()">Copy selection JSON</button>
    <span class="copy-feedback" id="copy-feedback"></span>
    <div class="dep-manifest" id="dep-manifest" style="display:none"></div>
    <div class="footer-warning" id="footer-warning">
      ⚠ caution items require --allow-caution; the applier validates and smoke-applies on a copy first — always run the verify step after
    </div>
  </div>
</div>

<script>
const DIFF = {diff_json};
const DEPS = {deps_json};
const BLOCKERS = {blockers_json};
const RDEPS = {rdeps_json};
const DIRECTION = "{direction}";
// In push mode prod-only objects are never selectable — see buildItemElement.
const PUSH = DIRECTION === "push";

// ── Utility ──────────────────────────────────────────────────────────────────

function esc(text) {{
  const d = document.createElement("div");
  d.textContent = (text === null || text === undefined) ? "" : String(text);
  return d.innerHTML;
}}

function el(tag, attrs, ...children) {{
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {{}})) {{
    if (k === "className") e.className = v;
    else if (k === "textContent") e.textContent = v;
    else if (k === "title") e.title = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }}
  for (const c of children) {{
    if (c == null) continue;
    if (typeof c === "string") e.appendChild(document.createTextNode(c));
    else e.appendChild(c);
  }}
  return e;
}}

// ── Data prep ────────────────────────────────────────────────────────────────

const KIND_ORDER = [
  "base_table","field","table_occurrence","relationship",
  "value_list","custom_function","script","layout","external_data_source"
];
const KIND_LABELS = {{
  base_table: "Base Tables",
  field: "Fields",
  table_occurrence: "Table Occurrences",
  relationship: "Relationships",
  value_list: "Value Lists",
  custom_function: "Custom Functions",
  script: "Scripts",
  layout: "Layouts",
  external_data_source: "External Data Sources"
}};

const allItems = DIFF.items;  // already in display order from differ

// Separate ignored from non-ignored
const ignoredItems = allItems.filter(i => i.ignored);
// In push mode prod-only ("removed") objects are the TARGET's own history.
// They are split out entirely: no checkbox is ever created for them, so there
// is no DOM or keyboard path that puts one into the selection.
const preservedItems = PUSH ? allItems.filter(i => !i.ignored && i.change === "removed") : [];
const mainItems = allItems.filter(i =>
  !i.ignored && !(PUSH && i.change === "removed"));

function blockersFor(key) {{ return BLOCKERS[key] || []; }}
function isBlocked(key) {{ return blockersFor(key).length > 0; }}

// ── State ────────────────────────────────────────────────────────────────────

let currentFilter = "All";  // "All" | "Added" | "Removed" | "Modified" | "Ignored"
// Map from key -> checkbox element (only for main items)
const checkboxMap = {{}};
// User's explicit ticks. The effective selection is their dependency closure
// over DEPS, so ticking one object pulls in everything it needs.
const manualSel = new Set();

// Closure with provenance: `cause[k]` is the item that pulled k in, so the UI
// can say WHY each auto-added row is there instead of silently ticking it.
// Manual ticks are seeded first and never get a cause.
function depClosure(seeds) {{
  const out = new Set(seeds);
  const cause = {{}};
  const stack = [...seeds];
  while (stack.length) {{
    const k = stack.pop();
    for (const d of (DEPS[k] || [])) {{
      if (out.has(d)) continue;
      const cb = checkboxMap[d];
      if (!cb || cb.disabled) continue;   // blocked/unselectable: never auto-add
      out.add(d);
      cause[d] = k;
      stack.push(d);
    }}
  }}
  return {{set: out, cause}};
}}

// Walk provenance back to the tick the operator actually made.
function rootCause(k, cause) {{
  let c = cause[k], guard = 0;
  while (c && cause[c] && guard++ < 500) c = cause[c];
  return c;
}}

let lastClosure = {{set: new Set(), cause: {{}}}};

function recompute() {{
  const eff = depClosure(manualSel);
  lastClosure = eff;
  for (const [key, cb] of Object.entries(checkboxMap)) {{
    const on = eff.set.has(key);
    cb.checked = on;
    const row = cb.closest(".item-details");
    if (!row) continue;
    const auto = on && !manualSel.has(key);
    row.classList.toggle("auto-dep", auto);
    // Inline "pulled in by" trail on the row itself.
    const trail = row.querySelector(".dep-trail");
    if (trail) {{
      if (auto) {{
        const via = eff.cause[key], root = rootCause(key, eff.cause);
        trail.textContent = (root && root !== via)
          ? "pulled in by " + labelKey(via) + " → " + labelKey(root)
          : "pulled in by " + labelKey(via);
        trail.style.display = "";
      }} else {{
        trail.style.display = "none";
      }}
    }}
  }}
  updateFooter();
}}

function shortKey(k) {{
  if (!k) return "?";
  const i = k.indexOf(":");
  return i < 0 ? k : k.slice(i + 1);
}}

// A base table, a table occurrence and a layout can all be called
// "ProofKitApps". Anywhere a key is shown outside its own section, the kind
// has to come with it or the list is unreadable.
const KIND_SHORT = {{
  base_table: "table", field: "field", table_occurrence: "TO",
  relationship: "rel", value_list: "VL", custom_function: "CF",
  script: "script", layout: "layout", external_data_source: "source"
}};
function labelKey(k) {{
  if (!k) return "?";
  const i = k.indexOf(":");
  if (i < 0) return k;
  const kind = k.slice(0, i);
  return shortKey(k) + " (" + (KIND_SHORT[kind] || kind) + ")";
}}

function onItemToggle(e) {{
  const key = e.target.dataset.key;
  if (e.target.checked) manualSel.add(key); else manualSel.delete(key);
  recompute();
}}

// ── Header ───────────────────────────────────────────────────────────────────

function buildHeader() {{
  const meta = DIFF.meta;

  const titleEl = document.getElementById("header-title");
  titleEl.textContent = (meta.dev_file || "dev") + " → " + (meta.prod_file || "prod");

  const pathsEl = document.getElementById("header-paths");
  const devPath = meta.dev_export || meta.dev_parsed || "";
  const prodPath = meta.prod_export || meta.prod_parsed || "";
  pathsEl.textContent = devPath + "  →  " + prodPath;

  const countsEl = document.getElementById("header-counts");

  const addedCount  = mainItems.filter(i => i.change === "added").length;
  const removedCount = mainItems.filter(i => i.change === "removed").length;
  const modifiedCount = mainItems.filter(i => i.change === "modified").length;

  if (addedCount) {{
    const p = el("span", {{className: "count-pill added"}});
    p.textContent = addedCount + " added";
    countsEl.appendChild(p);
  }}
  if (removedCount) {{
    const p = el("span", {{className: "count-pill removed"}});
    p.textContent = removedCount + " removed";
    countsEl.appendChild(p);
  }}
  if (modifiedCount) {{
    const p = el("span", {{className: "count-pill modified"}});
    p.textContent = modifiedCount + " modified";
    countsEl.appendChild(p);
  }}

  // Which direction this page was generated for. Without this the two modes
  // look identical until you go hunting for a checkbox that isn't there.
  const dirPill = el("span", {{className: "direction-pill"}});
  dirPill.textContent = PUSH ? "one-way push · prod-only preserved"
                             : "sync · prod-only objects CAN be deleted";
  dirPill.title = PUSH
    ? "Dev is the source. Objects that exist only in prod are preserved and "
      + "cannot be selected; this patch cannot delete anything."
    : "Prod-only objects are selectable and compile to DeleteAction. "
      + "Requires --allow-caution.";
  if (!PUSH) dirPill.classList.add("danger");
  countsEl.appendChild(dirPill);

  const versionSpan = el("span", {{className: "header-version"}});
  versionSpan.textContent = "saxml " + (meta.saxml_version || "");
  countsEl.appendChild(versionSpan);
}}

// ── Filter bar ───────────────────────────────────────────────────────────────

function buildFilterBar() {{
  const bar = document.getElementById("filter-bar");
  // In push mode prod-only objects live outside the filterable sections, so a
  // "Removed" chip would always match nothing. Swap it for a chip that jumps
  // to the preserved list instead.
  const filters = PUSH ? ["All", "Added", "Modified"]
                       : ["All", "Added", "Removed", "Modified"];
  if (ignoredItems.length) filters.push("Ignored");

  for (const f of filters) {{
    const chip = el("button", {{
      className: "chip" + (f === currentFilter ? " active" : ""),
      textContent: f,
      onclick: () => setFilter(f)
    }});
    chip.dataset.filter = f;
    bar.appendChild(chip);
  }}

  if (PUSH && preservedItems.length) {{
    const chip = el("button", {{
      className: "chip chip-preserved",
      textContent: "🔒 Prod-only (" + preservedItems.length + ")",
      title: "Objects that exist only in prod. Preserved, not selectable.",
      onclick: () => {{
        const sec = document.getElementById("preserved-section");
        sec.open = true;
        sec.scrollIntoView({{behavior: "smooth", block: "start"}});
      }}
    }});
    bar.appendChild(chip);
  }}
}}

function setFilter(f) {{
  currentFilter = f;
  // Update chips
  document.querySelectorAll(".chip").forEach(c => {{
    c.classList.toggle("active", c.dataset.filter === f);
  }});
  applyFilter();
}}

function applyFilter() {{
  const filter = currentFilter.toLowerCase();  // "all"|"added"|"removed"|"modified"|"ignored"
  // Show/hide item rows and details
  document.querySelectorAll("[data-change]").forEach(row => {{
    const inIgnored = !!row.closest("#ignored-section");
    let visible;
    if (filter === "ignored") visible = inIgnored;        // ignored live only in their own section
    else if (filter === "all") visible = true;
    else visible = !inIgnored && filter === row.dataset.change;
    row.classList.toggle("hidden", !visible);
  }});
  // Show/hide sections that are now empty
  document.querySelectorAll(".section").forEach(sec => {{
    const visible = [...sec.querySelectorAll("[data-change]")].some(r => !r.classList.contains("hidden"));
    sec.style.display = visible ? "" : "none";
  }});
  updateFooter();
}}

// ── JSON pretty-print ────────────────────────────────────────────────────────

function prettyObj(obj) {{
  // Return obj without calc_text for the main panel, and calc_text separately
  if (!obj || typeof obj !== "object") return [null, null];
  const calc = obj.calc_text !== undefined ? obj.calc_text : null;
  // Build a copy without calc_text for the main display
  const copy = Object.assign({{}}, obj);
  delete copy.calc_text;
  return [copy, calc];
}}

function makeJsonPanel(label, obj, panelClass) {{
  if (obj === null || obj === undefined) {{
    const wrapper = el("div", {{className: panelClass || ""}});
    const lbl = el("div", {{className: "json-panel-label"}});
    lbl.textContent = label;
    const pre = el("pre", {{className: "json-pre"}});
    pre.textContent = "null";
    wrapper.appendChild(lbl);
    wrapper.appendChild(pre);
    return wrapper;
  }}

  const [mainObj, calcText] = prettyObj(obj);
  const wrapper = el("div", {{className: panelClass || ""}});

  const lbl = el("div", {{className: "json-panel-label"}});
  lbl.textContent = label;
  wrapper.appendChild(lbl);

  const pre = el("pre", {{className: "json-pre"}});
  pre.textContent = JSON.stringify(mainObj, null, 1);
  wrapper.appendChild(pre);

  if (calcText !== null && calcText !== undefined && calcText !== "") {{
    const calcLbl = el("div", {{className: "calc-label"}});
    calcLbl.textContent = "Calculation";
    wrapper.appendChild(calcLbl);
    const calcPre = el("pre", {{className: "json-pre calc-pre"}});
    calcPre.textContent = String(calcText);
    wrapper.appendChild(calcPre);
  }}

  return wrapper;
}}

// One column of the object profile: a titled, explained list of related keys,
// each marked with whether it can travel.
function refColumn(title, keys, help) {{
  const col = el("div", {{className: "profile-col"}});
  col.appendChild(el("div", {{className: "profile-title"}}, title));
  col.appendChild(el("div", {{className: "profile-help"}}, help));
  if (!keys.length) {{
    col.appendChild(el("div", {{className: "profile-empty"}}, "none"));
    return col;
  }}
  const ul = el("ul", {{className: "profile-list"}});
  for (const k of keys) {{
    const li = el("li", {{}});
    const a = el("a", {{className: "profile-link", href: "#"}}, shortKey(k));
    a.title = k;
    a.addEventListener("click", ev => {{ ev.preventDefault(); revealItem(k); }});
    li.appendChild(a);
    const kindTag = el("span", {{className: "profile-kind"}},
                       KIND_SHORT[k.split(":")[0]] || k.split(":")[0]);
    li.appendChild(kindTag);
    if (isBlocked(k)) li.appendChild(el("span", {{className: "profile-flag blocked"}}, "blocked"));
    ul.appendChild(li);
  }}
  col.appendChild(ul);
  return col;
}}

// Jump to a related object and flash it, so the profile links are navigable.
function revealItem(key) {{
  const row = document.querySelector('.item-details[data-key="' + CSS.escape(key) + '"]');
  if (!row) return;
  // A filter may be hiding the target, and it may live inside a collapsed
  // <details> section — clear both before scrolling or the jump goes nowhere.
  if (row.classList.contains("hidden")) setFilter("All");
  for (let p = row.parentElement; p; p = p.parentElement) {{
    if (p.tagName === "DETAILS") p.open = true;
  }}
  row.open = true;
  row.scrollIntoView({{behavior: "smooth", block: "center"}});
  row.classList.add("flash");
  setTimeout(() => row.classList.remove("flash"), 1200);
}}

// ── Build a single item element ───────────────────────────────────────────────

function buildItemElement(item) {{
  // Determine display name
  const displayName = (item.kind === "field" && item.table)
    ? item.table + "::" + item.name
    : item.name;

  const blocks = blockersFor(item.key);
  // Unselectable for any of four reasons. The blocker case is the new one: a
  // dependency exists that cannot travel, so ticking this would compile a
  // patch missing a prerequisite. Previously the closure dropped it silently.
  const isDisabled = item.patchability === "manual" || item.ignored
                  || blocks.length > 0
                  || (PUSH && item.change === "removed");

  // Patchability icon
  const patchIcon = item.patchability === "proven" ? "🟢"
                  : item.patchability === "caution" ? "🟡"
                  : "🔴";

  // Build the <details> element
  const details = document.createElement("details");
  details.className = "item-details" + (blocks.length ? " blocked" : "");
  details.dataset.change = item.change;
  details.dataset.key = item.key;

  // Summary line (checkbox + name + badges)
  const summary = document.createElement("summary");

  // Checkbox. For prod-only objects in push mode NO input is created at all —
  // the guarantee is structural (there is nothing to tick, in the DOM or via
  // the keyboard), not a disabled attribute that can be flipped in devtools.
  const preserved = PUSH && item.change === "removed";
  if (preserved) {{
    const lock = el("span", {{className: "lock-glyph",
                             title: "prod-only — preserved, cannot be selected"}});
    lock.textContent = "🔒";
    summary.appendChild(lock);
  }} else {{
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "item-checkbox";
    cb.disabled = isDisabled;
    cb.dataset.key = item.key;
    cb.dataset.patchability = item.patchability;
    cb.addEventListener("change", onItemToggle);
    if (!isDisabled) checkboxMap[item.key] = cb;
    summary.appendChild(cb);
  }}

  // Name
  const nameSpan = document.createElement("span");
  nameSpan.className = "item-name";
  nameSpan.textContent = displayName;
  summary.appendChild(nameSpan);

  // Badges
  const badges = el("span", {{className: "item-badges"}});

  const changePill = el("span", {{className: "change-pill " + item.change}});
  changePill.textContent = item.change;
  badges.appendChild(changePill);

  const patchBadge = el("span", {{className: "patch-badge", title: item.patchability}});
  patchBadge.textContent = patchIcon;
  badges.appendChild(patchBadge);

  if (item.duplicate_name) {{
    const dupIcon = el("span", {{className: "dup-icon", title: "duplicate name — resolve in FileMaker"}});
    dupIcon.textContent = "⚠️";
    badges.appendChild(dupIcon);
  }}

  if (blocks.length) {{
    const b = el("span", {{className: "blocked-pill",
                          title: blocks.map(x => x.name + " — " + x.reason).join("\\n")}});
    b.textContent = "blocked";
    badges.appendChild(b);
  }}

  // "pulled in by X" — populated by recompute() when auto-included.
  const trail = el("span", {{className: "dep-trail"}});
  trail.style.display = "none";
  badges.appendChild(trail);

  summary.appendChild(badges);
  details.appendChild(summary);

  // Details body
  const body = el("div", {{className: "details-body"}});

  // ── Why this cannot be selected ──────────────────────────────────────────
  if (blocks.length) {{
    const box = el("div", {{className: "blocked-box"}});
    box.appendChild(el("div", {{className: "blocked-title"}},
      "Blocked — cannot be included in a patch"));
    const ul = el("ul", {{className: "blocked-list"}});
    for (const b of blocks) {{
      const li = el("li", {{}});
      li.appendChild(el("strong", {{}}, b.kind + " " + b.name));
      li.appendChild(document.createTextNode(" — " + b.reason));
      ul.appendChild(li);
    }}
    box.appendChild(ul);
    body.appendChild(box);
  }}

  if (PUSH && item.change === "removed") {{
    const box = el("div", {{className: "preserved-box"}});
    box.appendChild(el("div", {{className: "preserved-title"}}, "Prod-only — preserved"));
    box.appendChild(el("div", {{}},
      "This object exists in prod but not in dev. In push mode it is left "
      + "exactly as it is; the generated patch contains no instruction that "
      + "touches it. Switch to --direction sync only if you intend to DELETE it."));
    body.appendChild(box);
  }}

  // ── Object profile: what it needs, and what needs it ─────────────────────
  const out = (DEPS[item.key] || []);
  const inc = (RDEPS[item.key] || []);
  if (out.length || inc.length) {{
    const prof = el("div", {{className: "profile-grid"}});
    prof.appendChild(refColumn("References — must travel with it", out,
      "Everything this object needs that prod does not already have. "
      + "Ticking this row pulls all of it in automatically."));
    prof.appendChild(refColumn("Referenced by — breaks without it", inc,
      "These objects depend on this one. Selecting any of them pulls this "
      + "row in too."));
    body.appendChild(prof);
  }}

  if (item.summary) {{
    const summaryText = el("div", {{className: "details-summary-text"}});
    summaryText.textContent = item.summary;
    body.appendChild(summaryText);
  }}

  if (item.changed_attrs && item.changed_attrs.length > 0) {{
    const attrLabel = el("div", {{className: "json-panel-label"}});
    attrLabel.textContent = "Changed attributes";
    body.appendChild(attrLabel);
    const ul = el("ul", {{className: "changed-attrs-list"}});
    for (const attr of item.changed_attrs) {{
      const li = el("li", {{}});
      li.textContent = attr;
      ul.appendChild(li);
    }}
    body.appendChild(ul);
  }}

  // JSON panels: dev and prod side by side
  const panels = el("div", {{className: "json-panels"}});
  const bothPresent = item.dev !== null && item.prod !== null;
  const panelClass = bothPresent ? "" : "json-panel-single";

  if (item.dev !== null || item.prod === null) {{
    panels.appendChild(makeJsonPanel("DEV", item.dev, bothPresent ? "" : panelClass));
  }}
  if (item.prod !== null || item.dev === null) {{
    panels.appendChild(makeJsonPanel("PROD", item.prod, bothPresent ? "" : panelClass));
  }}
  // If both are present, both were appended without single-class
  if (!bothPresent && item.dev !== null && item.prod === null) {{
    // already done above
  }} else if (!bothPresent && item.prod !== null && item.dev === null) {{
    // already done above
  }} else if (bothPresent) {{
    // both appended; if we re-added, remove the extra
  }}

  body.appendChild(panels);
  details.appendChild(body);

  return details;
}}

// ── Build sections ────────────────────────────────────────────────────────────

function buildSections() {{
  const container = document.getElementById("sections-container");
  container.innerHTML = "";

  for (const kind of KIND_ORDER) {{
    const items = mainItems.filter(i => i.kind === kind);
    if (!items.length) continue;

    const section = el("div", {{className: "section"}});

    // Section header
    const hdr = el("div", {{className: "section-header"}});
    const label = el("span", {{className: "section-label"}});
    label.textContent = KIND_LABELS[kind] || kind;
    hdr.appendChild(label);
    const countSpan = el("span", {{className: "section-count"}});
    countSpan.textContent = "(" + items.length + ")";
    hdr.appendChild(countSpan);

    // "Select all proven" button — selects only visible, enabled, proven added items
    const selectBtn = el("button", {{
      className: "btn section-select-btn",
      textContent: "Select all proven",
      onclick: () => selectAllProvenInSection(kind)
    }});
    hdr.appendChild(selectBtn);
    section.appendChild(hdr);

    // Items
    const body = el("div", {{className: "section-body"}});
    for (const item of items) {{
      body.appendChild(buildItemElement(item));
    }}
    section.appendChild(body);
    container.appendChild(section);
  }}

  buildPreservedSection();
  buildIgnoredSection();
}}

// Prod-only objects in push mode. These render WITHOUT checkboxes — the safety
// property is structural, not a disabled attribute someone can flip in devtools.
function buildPreservedSection() {{
  if (!preservedItems.length) return;
  const sec = document.getElementById("preserved-section");
  sec.style.display = "";
  document.getElementById("preserved-count").textContent =
    "(" + preservedItems.length + ")";
  document.getElementById("preserved-blurb").textContent =
    "These objects exist in prod but not in dev — the target file's own "
    + "history. This is a one-way push, so they are not selectable and the "
    + "generated patch contains nothing that touches them. To delete them "
    + "instead, regenerate this page with --direction sync.";
  const body = document.getElementById("preserved-body");
  body.innerHTML = "";
  for (const item of preservedItems) body.appendChild(buildItemElement(item));
}}

function buildIgnoredSection() {{
  if (!ignoredItems.length) return;

  const sec = document.getElementById("ignored-section");
  sec.style.display = "";
  document.getElementById("ignored-label").textContent =
    "Ignored (" + ignoredItems.length + ")";

  const body = document.getElementById("ignored-body");
  body.innerHTML = "";
  for (const item of ignoredItems) {{
    body.appendChild(buildItemElement(item));
  }}
}}

// ── Selection logic ───────────────────────────────────────────────────────────

function isItemVisibleAndSelectable(key) {{
  const cb = checkboxMap[key];
  if (!cb || cb.disabled) return false;
  // Find the parent details to check visibility
  const details = cb.closest("[data-change]");
  if (!details || details.classList.contains("hidden")) return false;
  return true;
}}

function selectAllProvenAdded() {{
  for (const [key, cb] of Object.entries(checkboxMap)) {{
    if (cb.disabled) continue;
    if (cb.dataset.patchability === "proven") {{
      const details = cb.closest("[data-change]");
      if (!details || details.classList.contains("hidden")) continue;
      if (details.dataset.change === "added") manualSel.add(key);
    }}
  }}
  recompute();
}}

function selectAllProvenInSection(kind) {{
  // Select visible, enabled, proven items of any change in this kind's section
  for (const item of mainItems) {{
    if (item.kind !== kind) continue;
    if (item.patchability !== "proven") continue;
    const cb = checkboxMap[item.key];
    if (!cb || cb.disabled) continue;
    const details = cb.closest("[data-change]");
    if (!details || details.classList.contains("hidden")) continue;
    manualSel.add(item.key);
  }}
  recompute();
}}

// ── Footer ────────────────────────────────────────────────────────────────────

function getSelectedItems() {{
  // Return items in display order (KIND_ORDER, then by appearance in mainItems)
  const checkedKeys = new Set();
  for (const [key, cb] of Object.entries(checkboxMap)) {{
    if (cb.checked) checkedKeys.add(key);
  }}
  return mainItems.filter(i => checkedKeys.has(i.key));
}}

function updateFooter() {{
  const selected = getSelectedItems();
  const provenCount = selected.filter(i => i.patchability === "proven").length;
  const cautionCount = selected.filter(i => i.patchability === "caution").length;
  const autoItems = selected.filter(i => !manualSel.has(i.key));
  const autoCaution = autoItems.filter(i => i.patchability === "caution").length;

  const countEl = document.getElementById("footer-count");
  let txt = selected.length + " selected (" +
    provenCount + " proven / " + cautionCount + " caution)";
  if (autoItems.length) txt += " · " + autoItems.length + " pulled in as dependencies";
  if (preservedItems.length) {{
    txt += " · " + preservedItems.length + " prod-only preserved (this patch cannot delete anything)";
  }}
  countEl.textContent = txt;

  // Manifest: exactly what each tick dragged along, grouped by the tick that
  // caused it. "Loud" auto-include — the operator reads the full consequence
  // of a checkbox rather than discovering it in the patch.
  const manifest = document.getElementById("dep-manifest");
  if (manifest) {{
    if (!autoItems.length) {{
      manifest.style.display = "none";
      manifest.innerHTML = "";
    }} else {{
      const groups = {{}};
      for (const it of autoItems) {{
        const root = rootCause(it.key, lastClosure.cause) || "(unknown)";
        (groups[root] = groups[root] || []).push(it.key);
      }}
      const parts = Object.keys(groups).sort().map(root =>
        "<strong>" + esc(labelKey(root)) + "</strong> pulled in " +
        groups[root].length + ": " +
        groups[root].sort().map(k => esc(labelKey(k))).join(", "));
      manifest.innerHTML = "Auto-included &mdash; " + parts.join(" &nbsp;·&nbsp; ");
      manifest.style.display = "";
    }}
  }}

  const warningEl = document.getElementById("footer-warning");
  warningEl.classList.toggle("visible", cautionCount > 0);
  warningEl.textContent = autoCaution
    ? "⚠ " + autoCaution + " caution item(s) auto-included as dependencies; these need --allow-caution. The applier validates and smoke-applies on a copy first; always run the verify step after."
    : "⚠ caution items require --allow-caution. The applier validates and smoke-applies on a copy first; always run the verify step after.";
}}

function buildSelectionPayload() {{
  const selected = getSelectedItems();
  return {{
    source_diff: DIFF.meta,
    selected: selected.map(i => i.key)
  }};
}}

function downloadSelection() {{
  const payload = buildSelectionPayload();
  const json = JSON.stringify(payload, null, 2);
  const blob = new Blob([json], {{type: "application/json"}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "selection.json";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}}

function copySelection() {{
  const payload = buildSelectionPayload();
  const json = JSON.stringify(payload, null, 2);
  const feedback = document.getElementById("copy-feedback");
  navigator.clipboard.writeText(json).then(() => {{
    feedback.textContent = "copied ✓";
    setTimeout(() => {{ feedback.textContent = ""; }}, 2000);
  }}).catch(() => {{
    feedback.textContent = "copy failed";
    setTimeout(() => {{ feedback.textContent = ""; }}, 2000);
  }});
}}

// ── Init ──────────────────────────────────────────────────────────────────────

function init() {{
  buildHeader();
  buildFilterBar();
  buildSections();
  applyFilter();
  updateFooter();
}}

document.addEventListener("DOMContentLoaded", init);
</script>
</body>
</html>"""

    return html


# ── CLI ───────────────────────────────────────────────────────────────────────

def _compute_deps(diff: dict, direction: str = "push") -> dict:
    """Best-effort dependency analysis from the exports named in diff.meta.

    Returns {"deps": {}, "blockers": {}} (with a stderr note) if the exports
    aren't available or anything fails — the review page still works, just
    without dependency auto-include.
    """
    empty = {"deps": {}, "blockers": {}}
    meta = diff.get("meta", {})
    dev_export, prod_export = meta.get("dev_export"), meta.get("prod_export")
    if not (dev_export and prod_export
            and Path(dev_export).exists() and Path(prod_export).exists()):
        print("note: dev/prod exports not available; dependency auto-include disabled",
              file=sys.stderr)
        return empty
    try:
        from lxml import etree
        import saxml_parser as P
        import gen_patch
        dev_root = etree.parse(P.open_fmsavexml(dev_export)).getroot()
        prod_root = etree.parse(P.open_fmsavexml(prod_export)).getroot()
        return gen_patch.dependency_analysis(dev_root, prod_root, diff,
                                             direction=direction)
    except Exception as exc:  # noqa: BLE001 — never block the review artifact
        print(f"warning: dependency graph unavailable ({exc})", file=sys.stderr)
        return empty


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a self-contained HTML diff-review artifact."
    )
    parser.add_argument("diff_json", help="Path to diff.json produced by saxml_diff.py")
    parser.add_argument("-o", "--output", default="-", help="Output file (default: stdout)")
    parser.add_argument("--no-deps", action="store_true",
                        help="skip the dependency graph (no auto-include on tick)")
    parser.add_argument("--direction", choices=("push", "sync"), default="push",
                        help="push (default): dev is the source and prod-only "
                             "objects are preserved, never selectable — the "
                             "patch cannot delete the target's own work. "
                             "sync: prod-only objects are selectable and "
                             "compile to DeleteAction.")
    args = parser.parse_args()

    with open(args.diff_json, encoding="utf-8") as f:
        diff = json.load(f)

    analysis = {"deps": {}, "blockers": {}} if args.no_deps \
        else _compute_deps(diff, args.direction)
    html = build_html(diff, analysis.get("deps"), analysis.get("blockers"),
                      direction=args.direction)

    if args.output == "-":
        sys.stdout.write(html)
    else:
        Path(args.output).write_text(html, encoding="utf-8")
        size = Path(args.output).stat().st_size
        print(f"wrote {args.output} ({size:,} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
