"""
Readable knowledge-base exporter — turns a parsed DDR into agent-facing Markdown.

This is NOT a human reading doc. It's the context an AI agent loads to read and
*write* FileMaker script/calc XML against a specific database: resolve any
`TO::Field` reference, pick the right table occurrence + field id for a Set Field
step, know custom-function signatures, and read existing scripts as pseudo-code so
new/edited steps match the solution's conventions.

The intended loop:
  1. You copy script steps in FileMaker → clipboard holds `fmxmlsnippet` XML.
  2. You paste that XML into a chat with the agent.
  3. The agent, having loaded this knowledge base, returns corrected/updated
     `fmxmlsnippet` XML you paste straight back into FileMaker.

Reads the normalized parsed/ tree (works for both classic DDR and FM 2026
split-catalog exports). Output layout under <output-dir>/<db>/:
  _schema.md            — TOs + relationship graph, tables/fields (with ids),
                          custom-function signatures, value lists, script index,
                          layout index. The file to load first.
  custom_functions.md   — full custom-function bodies (loaded on demand).
  scripts/<folder>/<name>.md — each script as indented pseudo-code.
  _overview.md          — counts + how-to-use.

Usage:
    python3 readable.py <parsed_dir> [--output-dir schema/readable] [--db NAME]
"""

import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ddr_xml_utils import parse_xml, read_metadata, safe_filename

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


def ln(t):
    return t.split('}', 1)[1] if isinstance(t, str) and '}' in t else t


def child(parent, tag):
    for c in parent:
        if ln(c.tag) == tag:
            return c
    return None


def descend(parent, tag):
    for e in parent.iter():
        if ln(e.tag) == tag:
            return e
    return None


def all_desc(parent, tag):
    return [e for e in parent.iter() if ln(e.tag) == tag]


def _md_cell(text, limit=70):
    """Sanitize text for a one-line Markdown table cell."""
    if not text:
        return ''
    s = ' '.join(str(text).split())          # collapse whitespace/newlines
    s = s.replace('|', '\\|')
    if len(s) > limit:
        s = s[:limit - 1] + '…'
    return s


# --- relationship operators -> symbols ---
OP_SYMBOL = {
    'Equal': '=', 'NotEqual': '≠', 'LessThan': '<', 'GreaterThan': '>',
    'LessThanEqual': '≤', 'GreaterThanEqual': '≥', 'Less': '<', 'Greater': '>',
    'LessEqual': '≤', 'GreaterEqual': '≥', 'Cartesian': '×',
    'CartesianProduct': '×',
}

# --- script control-flow indentation ---
INDENT_AFTER = {'If', 'Loop', 'Else', 'Else If'}
OUTDENT_BEFORE = {'End If', 'End Loop', 'Else', 'Else If'}


# ---------------------------------------------------------------------------
# Loaders (read the normalized parsed/ tree)
# ---------------------------------------------------------------------------

def load_tables(db_dir):
    """[(name, comment, [field dicts], [to names])] — to names filled in later."""
    tables = []
    tdir = db_dir / 'tables'
    if not tdir.exists():
        return tables
    for table_dir in sorted(tdir.iterdir()):
        ff = table_dir / 'fields.xml'
        if not ff.exists():
            continue
        root, _ = parse_xml(ff)
        name = root.get('name', table_dir.name)
        comment = root.get('comment', '')
        fields = []
        for fld in all_desc(root, 'Field'):
            calc_el = None
            # first <Text> under the field is the calc / auto-enter text
            for t in fld.iter():
                if ln(t.tag) == 'Text' and (t.text or '').strip():
                    calc_el = t
                    break
            fields.append({
                'name': fld.get('name', ''),
                'id': fld.get('id', ''),
                'type': fld.get('fieldtype') or fld.get('fieldType') or 'Normal',
                'datatype': fld.get('datatype') or fld.get('dataType') or '',
                'calc': (calc_el.text or '').strip() if calc_el is not None else '',
                'comment': fld.get('comment', ''),
            })
        tables.append({'name': name, 'comment': comment, 'fields': fields, 'tos': []})
    return tables


def load_tos(db_dir):
    """[(to_name, base_table)]"""
    tos = []
    d = db_dir / 'table_occurrences'
    if not d.exists():
        return tos
    for f in sorted(d.glob('*.xml')):
        root, _ = parse_xml(f)
        base = root.get('baseTable', '')
        if not base:
            br = descend(root, 'BaseTableReference')
            base = br.get('name', '') if br is not None else ''
        tos.append({'name': root.get('name', f.stem), 'base': base, 'id': root.get('id', '')})
    return tos


def load_relationships(db_dir):
    rels = []
    d = db_dir / 'relationships'
    if not d.exists():
        return rels
    for f in sorted(d.glob('*.xml')):
        root, _ = parse_xml(f)
        lt = child(root, 'LeftTable')
        rt = child(root, 'RightTable')
        left = descend(lt, 'TableOccurrenceReference') if lt is not None else None
        right = descend(rt, 'TableOccurrenceReference') if rt is not None else None
        preds = []
        for jp in all_desc(root, 'JoinPredicate'):
            op = jp.get('type', '=')
            lf = descend(child(jp, 'LeftField'), 'FieldReference') if child(jp, 'LeftField') is not None else None
            rf = descend(child(jp, 'RightField'), 'FieldReference') if child(jp, 'RightField') is not None else None
            preds.append({
                'op': OP_SYMBOL.get(op, op),
                'left': lf.get('name') if lf is not None else '?',
                'right': rf.get('name') if rf is not None else '?',
            })
        rels.append({
            'left': left.get('name') if left is not None else '?',
            'right': right.get('name') if right is not None else '?',
            'preds': preds,
        })
    return rels


def load_custom_functions(db_dir):
    cfs = []
    d = db_dir / 'custom_functions'
    if not d.exists():
        return cfs
    for f in sorted(d.glob('*.xml')):
        root, _ = parse_xml(f)
        params = [p.get('name', '') for p in all_desc(root, 'Parameter')]
        body_el = None
        for t in root.iter():
            if ln(t.tag) == 'Text' and (t.text or '').strip():
                body_el = t
                break
        body = (body_el.text or '').strip() if body_el is not None else ''
        cfs.append({
            'name': root.get('name', f.stem),
            'params': params,
            'body': body,
        })
    return cfs


def load_value_lists(db_dir):
    vls = []
    d = db_dir / 'value_lists'
    if not d.exists():
        return vls
    for f in sorted(d.glob('*.xml')):
        root, _ = parse_xml(f)
        src = descend(root, 'Source')
        source = src.get('value', '') if src is not None else ''
        detail = ''
        if source == 'FromField':
            fr = descend(root, 'FieldReference')
            to = descend(root, 'TableOccurrenceReference')
            if fr is not None:
                detail = f"{to.get('name') + '::' if to is not None else ''}{fr.get('name', '')}"
        else:
            cv = descend(root, 'CustomValues')
            if cv is not None:
                vals = [(_md_cell(v.text, 30)) for v in all_desc(cv, 'Value') if (v.text or '').strip()]
                detail = ', '.join(vals[:8])
        vls.append({'name': root.get('name', f.stem), 'source': source, 'detail': detail})
    return vls


def load_scripts(db_dir):
    """[(name, id, folder, steps, path)] sorted by folder/name."""
    scripts = []
    d = db_dir / 'scripts'
    if not d.exists():
        return scripts
    for f in sorted(d.rglob('*.xml')):
        root, _ = parse_xml(f)
        folder = str(f.parent.relative_to(d)) if f.parent != d else ''
        steps = all_desc(root, 'Step')
        scripts.append({
            'name': root.get('name', f.stem),
            'id': root.get('id', ''),
            'folder': folder if folder != '.' else '',
            'step_count': len(steps),
            'path': f,
        })
    return scripts


def load_layouts(db_dir):
    lays = []
    d = db_dir / 'layouts'
    if not d.exists():
        return lays
    for f in sorted(d.rglob('*.xml')):
        root, _ = parse_xml(f)
        to = descend(root, 'TableOccurrenceReference')
        lays.append({'name': root.get('name', f.stem), 'to': to.get('name') if to is not None else ''})
    return lays


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def extract_script_deps(root, cf_names):
    """Exact dependency manifest from a parsed script's resolved references.

    Returns sets: table occurrences, TO::field references, scripts called,
    layouts used, custom functions used.
    """
    tos, fields, calls, layouts, cfs = set(), set(), set(), set(), set()
    for e in root.iter():
        t = ln(e.tag)
        if t == 'TableOccurrenceReference':
            if e.get('name'):
                tos.add(e.get('name'))
        elif t == 'ScriptReference':
            if e.get('name'):
                calls.add(e.get('name'))
        elif t == 'LayoutReference':
            if e.get('name'):
                layouts.add(e.get('name'))
        elif t == 'FieldReference':
            to = None
            for c in e:
                if ln(c.tag) == 'TableOccurrenceReference':
                    to = c.get('name')
            fields.add(f"{to + '::' if to else ''}{e.get('name', '')}")
        elif t == 'Text' and e.text and cf_names:
            for m in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', e.text):
                if m in cf_names:
                    cfs.add(m)
    return {'tos': tos, 'fields': fields, 'calls': calls, 'layouts': layouts, 'cfs': cfs}


def _dep_block(deps, callers, to_base):
    """Render the 'Connects to' / 'Called by' header for a script file."""
    L = []
    tables = sorted({to_base.get(to, to) for to in deps['tos']})
    L.append("## Connects to")
    L.append("")
    L.append(f"- **Tables/TOs:** " + (", ".join(f"`{t}`" for t in sorted(deps['tos'])) or "_none_"))
    if tables:
        L.append(f"- **Base tables:** " + ", ".join(tables))
    flds = sorted(deps['fields'])
    shown = ", ".join(f"`{f}`" for f in flds[:40]) + (f"  …(+{len(flds)-40})" if len(flds) > 40 else "")
    L.append(f"- **Fields:** " + (shown or "_none_"))
    L.append(f"- **Scripts called:** " + (", ".join(f"`{c}`" for c in sorted(deps['calls'])) or "_none_"))
    L.append(f"- **Layouts:** " + (", ".join(f"`{l}`" for l in sorted(deps['layouts'])) or "_none_"))
    L.append(f"- **Custom functions:** " + (", ".join(f"`{c}`" for c in sorted(deps['cfs'])) or "_none_"))
    L.append("")
    L.append("## Called by")
    L.append("")
    L.append("- " + (", ".join(f"`{c}`" for c in sorted(callers)) if callers
                     else "_no callers found — entry point (trigger / button / API / scheduled)_"))
    L.append("")
    return L


def render_script_pseudocode(path, deps=None, callers=None, to_base=None):
    root, _ = parse_xml(path)
    lines = [f"# Script: {root.get('name')}", ""]
    if deps is not None:
        lines += _dep_block(deps, callers or set(), to_base or {})
    lines.append("## Steps")
    lines.append("")
    lines.append("```")
    depth = 0
    for step in all_desc(root, 'Step'):
        name = step.get('name', '')
        enabled = step.get('enable', 'True') == 'True'
        st = child(step, 'StepText')
        text = (st.text if st is not None and st.text else name)
        text = ' '.join(text.split()) if text else name
        if name in OUTDENT_BEFORE:
            depth = max(0, depth - 1)
        prefix = '    ' * depth
        lines.append(f"{prefix}{'// [disabled] ' if not enabled else ''}{text}")
        if name in INDENT_AFTER:
            depth += 1
    lines.append("```")
    return '\n'.join(lines) + '\n'


def render_schema_md(db_name, tables, tos, rels, cfs, vls, scripts, layouts):
    # base table -> [to names]
    by_base = {}
    for to in tos:
        by_base.setdefault(to['base'], []).append(to['name'])
    for t in tables:
        t['tos'] = by_base.get(t['name'], [])

    L = []
    L.append(f"# {db_name} — Schema Reference (agent context)")
    L.append("")
    L.append("> Knowledge base for reading and **writing** FileMaker script/calc XML against "
             "this database. Field references use `TO::Field`. A Set Field snippet needs "
             "`<Field table=\"<TO>\" id=\"<fieldId>\" name=\"<Field>\"/>` — use the field `id` "
             "from the tables below and a TO whose base table owns the field. Full custom-function "
             "bodies are in `custom_functions.md`; each script's steps are in `scripts/`.")
    L.append("")
    L.append(f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}.*")
    L.append("")
    L.append(f"**Totals:** {len(tables)} tables · "
             f"{sum(len(t['fields']) for t in tables)} fields · {len(tos)} TOs · "
             f"{len(rels)} relationships · {len(scripts)} scripts · {len(layouts)} layouts · "
             f"{len(cfs)} custom functions · {len(vls)} value lists")
    L.append("")

    # Relationship graph
    L.append("## Table Occurrences & Relationships")
    L.append("")
    L.append("Table occurrence → base table:")
    L.append("")
    L.append("| Table Occurrence | Base table |")
    L.append("|---|---|")
    for to in sorted(tos, key=lambda x: x['name'].lower()):
        L.append(f"| `{to['name']}` | {to['base']} |")
    L.append("")
    if rels:
        L.append("Relationships (left TO → right TO · predicates):")
        L.append("")
        for r in rels:
            preds = "  AND  ".join(f"{p['left']} {p['op']} {p['right']}" for p in r['preds'])
            L.append(f"- `{r['left']}` → `{r['right']}` · {preds}")
        L.append("")

    # Tables & fields
    L.append("## Tables & Fields")
    L.append("")
    for t in sorted(tables, key=lambda x: x['name'].lower()):
        L.append(f"### {t['name']}")
        if t['comment']:
            L.append(f"_{_md_cell(t['comment'], 200)}_")
        tos_here = ', '.join(f"`{n}`" for n in t['tos']) or '_(no table occurrence)_'
        L.append(f"TOs: {tos_here}")
        L.append("")
        L.append("| Field | id | Type | Calc / auto-enter | Comment |")
        L.append("|---|---|---|---|---|")
        for fld in t['fields']:
            typ = fld['datatype'] + (f" ({fld['type']})" if fld['type'] and fld['type'] != 'Normal' else '')
            L.append(f"| {_md_cell(fld['name'],40)} | {fld['id']} | {typ} | "
                     f"{_md_cell(fld['calc'],60)} | {_md_cell(fld['comment'],45)} |")
        L.append("")

    # Custom function signatures
    if cfs:
        L.append("## Custom Functions")
        L.append("")
        L.append("Signatures (full bodies in `custom_functions.md`):")
        L.append("")
        L.append("| Function | Parameters |")
        L.append("|---|---|")
        for cf in sorted(cfs, key=lambda x: x['name'].lower()):
            params = '; '.join(cf['params'])
            L.append(f"| `{cf['name']}` | {_md_cell(params, 80)} |")
        L.append("")

    # Value lists
    if vls:
        L.append("## Value Lists")
        L.append("")
        L.append("| Value List | Source | Detail |")
        L.append("|---|---|---|")
        for vl in sorted(vls, key=lambda x: x['name'].lower()):
            L.append(f"| `{vl['name']}` | {vl['source']} | {_md_cell(vl['detail'],60)} |")
        L.append("")

    # Scripts index
    if scripts:
        L.append("## Scripts")
        L.append("")
        L.append("Pseudo-code for each is in `scripts/<folder>/<name>.md`.")
        L.append("")
        L.append("| Script | id | Folder | Steps |")
        L.append("|---|---|---|---|")
        for s in sorted(scripts, key=lambda x: (x['folder'].lower(), x['name'].lower())):
            L.append(f"| {_md_cell(s['name'],50)} | {s['id']} | {_md_cell(s['folder'],30)} | {s['step_count']} |")
        L.append("")

    # Layouts index
    if layouts:
        L.append("## Layouts")
        L.append("")
        L.append("| Layout | Based on TO |")
        L.append("|---|---|")
        for lay in sorted(layouts, key=lambda x: x['name'].lower()):
            L.append(f"| {_md_cell(lay['name'],50)} | {lay['to']} |")
        L.append("")

    return '\n'.join(L)


def render_custom_functions_md(db_name, cfs):
    L = [f"# {db_name} — Custom Functions", ""]
    L.append("Full bodies. Signatures and the rest of the schema are in `_schema.md`.")
    L.append("")
    for cf in sorted(cfs, key=lambda x: x['name'].lower()):
        sig = f"{cf['name']} ( {' ; '.join(cf['params'])} )" if cf['params'] else f"{cf['name']} ( )"
        L.append(f"## {sig}")
        L.append("")
        L.append("```")
        L.append(cf['body'] or '(empty)')
        L.append("```")
        L.append("")
    return '\n'.join(L)


def _is_separator(name):
    """FileMaker menu separators are scripts named only with dashes/spaces."""
    return not name.strip(' -')


def render_xref_md(db_name, scripts, deps_by_script, called_by, table_to_scripts, to_base):
    real = [s for s in scripts if not _is_separator(s['name'])]
    L = [f"# {db_name} — Cross-Reference Index", ""]
    L.append("Reverse lookups for *backtracking what connects to what*. Per-script forward "
             "dependencies are in each `scripts/<name>.md`. (Menu-separator scripts omitted.)")
    L.append("")

    # Entry points (called by nobody), excluding separators.
    entry = sorted(s['name'] for s in real if not called_by.get(s['name']))
    L.append(f"## Entry-point scripts (no internal callers) — {len(entry)}")
    L.append("")
    L.append("_Called by a trigger, button, schedule, or API — or dead. Verify before removing._")
    L.append("")
    for name in entry:
        L.append(f"- `{name}`")
    L.append("")

    # Table -> scripts that touch it.
    L.append("## Table → scripts that touch it")
    L.append("")
    for base in sorted(table_to_scripts):
        users = sorted(table_to_scripts[base])
        L.append(f"### {base}  ({len(users)})")
        L.append(", ".join(f"`{u}`" for u in users))
        L.append("")

    # Script call graph (who calls whom).
    L.append("## Script call graph")
    L.append("")
    L.append("| Script | Calls | Called by |")
    L.append("|---|---|---|")
    for s in sorted(real, key=lambda x: x['name'].lower()):
        d = deps_by_script.get(s['name'], {})
        calls = ", ".join(sorted(d.get('calls', set())))
        callers = ", ".join(sorted(called_by.get(s['name'], set())))
        L.append(f"| {_md_cell(s['name'],40)} | {_md_cell(calls,60)} | {_md_cell(callers,60)} |")
    L.append("")
    return '\n'.join(L)


def render_overview_md(db_name, tables, tos, rels, cfs, vls, scripts, layouts):
    L = [f"# {db_name} — Readable Knowledge Base", ""]
    L.append("Agent-facing context generated from the parsed DDR. **Load `_schema.md` first.**")
    L.append("")
    L.append("## Files")
    L.append("- `_schema.md` — tables/fields (with ids), TOs + relationship graph, "
             "custom-function signatures, value lists, script & layout indexes. **Load first.**")
    L.append("- `_xref.md` — reverse lookups: entry-point scripts, table → scripts that touch it, "
             "and the script call graph. For *backtracking what connects to what*.")
    L.append("- `custom_functions.md` — full custom-function bodies.")
    L.append("- `scripts/<folder>/<name>.md` — each script: a **Connects to** / **Called by** "
             "header (exact dependencies) then indented pseudo-code.")
    L.append("")
    L.append("## Supports")
    L.append("- **Ask about scripts** — read `scripts/<name>.md` (deps + pseudo-code) and `_xref.md`.")
    L.append("- **Modify a pasted script** — resolve refs via `_schema.md`, return `fmxmlsnippet`.")
    L.append("- **Backtrack what a script connects to** — the script's `Connects to` block + `_xref.md`.")
    L.append("- **Write a script from scratch** — `_schema.md` + `custom_functions.md` + the snippet format.")
    L.append("")
    L.append("## Round-trip workflow")
    L.append("1. Copy script steps in FileMaker → clipboard holds `fmxmlsnippet` XML.")
    L.append("2. Paste that XML to the agent.")
    L.append("3. Agent resolves references against this knowledge base and returns updated "
             "`fmxmlsnippet` XML to paste back. (Validate with `scripts/validate_snippet.py`.)")
    L.append("")
    L.append("## Snapshot")
    L.append(f"- {len(tables)} tables, {sum(len(t['fields']) for t in tables)} fields")
    L.append(f"- {len(tos)} table occurrences, {len(rels)} relationships")
    L.append(f"- {len(scripts)} scripts, {len(layouts)} layouts")
    L.append(f"- {len(cfs)} custom functions, {len(vls)} value lists")
    L.append("")
    return '\n'.join(L)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def export_db(parsed_dir, db_name, output_dir):
    db_dir = parsed_dir / safe_filename(db_name)
    if not db_dir.exists():
        print(f"  SKIP {db_name}: {db_dir} not found")
        return
    out = output_dir / safe_filename(db_name.replace('.fmp12', ''))
    out.mkdir(parents=True, exist_ok=True)

    tables = load_tables(db_dir)
    tos = load_tos(db_dir)
    rels = load_relationships(db_dir)
    cfs = load_custom_functions(db_dir)
    vls = load_value_lists(db_dir)
    scripts = load_scripts(db_dir)
    layouts = load_layouts(db_dir)

    # Dependency manifests (exact, from resolved references) + reverse indexes.
    cf_names = {cf['name'] for cf in cfs}
    to_base = {to['name']: to['base'] for to in tos}
    deps_by_script = {}
    for s in scripts:
        root, _ = parse_xml(s['path'])
        deps_by_script[s['name']] = extract_script_deps(root, cf_names)
    called_by = defaultdict(set)
    table_to_scripts = defaultdict(set)
    for name, d in deps_by_script.items():
        for callee in d['calls']:
            called_by[callee].add(name)
        for to in d['tos']:
            table_to_scripts[to_base.get(to, to)].add(name)

    (out / '_schema.md').write_text(
        render_schema_md(db_name, tables, tos, rels, cfs, vls, scripts, layouts), encoding='utf-8')
    if cfs:
        (out / 'custom_functions.md').write_text(
            render_custom_functions_md(db_name, cfs), encoding='utf-8')
    (out / '_xref.md').write_text(
        render_xref_md(db_name, scripts, deps_by_script, called_by, table_to_scripts, to_base),
        encoding='utf-8')
    (out / '_overview.md').write_text(
        render_overview_md(db_name, tables, tos, rels, cfs, vls, scripts, layouts), encoding='utf-8')

    sdir = out / 'scripts'
    used = set()
    for s in scripts:
        rel = Path(s['folder']) if s['folder'] else Path('.')
        target = (sdir / rel)
        target.mkdir(parents=True, exist_ok=True)
        base = safe_filename(s['name']) or 'script'
        fname = f'{base}.md'
        # Avoid clobbering scripts whose names collapse to the same safe filename.
        if (target / fname) in used and s['id']:
            fname = f'{base}_{s["id"]}.md'
        used.add(target / fname)
        (target / fname).write_text(
            render_script_pseudocode(s['path'], deps_by_script[s['name']],
                                     called_by.get(s['name'], set()), to_base),
            encoding='utf-8')

    print(f"  {db_name}: _schema.md + _xref.md + {len(cfs)} CF bodies + {len(scripts)} script files → {out}")


def main():
    ap = argparse.ArgumentParser(description='Export an agent-facing readable knowledge base from a parsed DDR')
    ap.add_argument('parsed_dir', help='Path to the parsed DDR directory')
    ap.add_argument('--output-dir', default=None, help='Output dir (default: <repo>/schema/readable)')
    ap.add_argument('--db', help='Only export this database (name as in _metadata.json)')
    args = ap.parse_args()

    parsed_dir = Path(args.parsed_dir)
    metadata = read_metadata(parsed_dir)
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = parsed_dir.parent / 'readable'

    print(f"Exporting readable knowledge base → {output_dir}")
    dbs = [args.db] if args.db else list(metadata.get('databases', {}))
    for db_name in dbs:
        export_db(parsed_dir, db_name, output_dir)


if __name__ == '__main__':
    main()
