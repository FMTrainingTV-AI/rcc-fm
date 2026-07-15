"""
FileMaker 2026 "Save a Copy as XML" (split-catalog) parser.

FileMaker 2026 (Source 26.x) can export a database as a *folder* of per-catalog
XML files instead of the classic single DDR document. Each catalog file looks like:

    <FMSaveAsXML version="2.3.0.0" Source="26.0.1" File="X.fmp12"
                 Has_DDR_INFO="True" split_catalogs="True">
      <Structure><AddAction><XxxCatalog>…</XxxCatalog></AddAction></Structure>
      <DDR_INFO>…</DDR_INFO>
    </FMSaveAsXML>

Two important differences from the classic <FMPReport> DDR:

  1. **Richer, pre-resolved structure.** Calculations and script steps carry
     inline <TableOccurrenceReference>, <FieldReference>, <ScriptReference>
     elements (id + name + UUID) alongside the raw calc <Text>. Dependencies are
     resolved in place rather than left as TO::Field strings.

  2. **Two-branch layout.** `Structure/AddAction/<Catalog>` holds the definitions;
     `DDR_INFO` holds a content-addressable text store (calc/step text broken into
     hashed <Chunk>s, referenced from the structure via <DDRREF hash=…>). The
     inline <Text> already contains the full text, so DDR_INFO is supplementary —
     we use it only to recover the human-readable one-line step text (StepText).

This module emits the SAME parsed/<db>/<type>/ per-object layout that the classic-DDR path
produces for the legacy format, so summary.py / search.py / refs.py / orphans.py /
compare.py keep working unchanged.

It is invoked from ddr.py split when that format is detected; it is not a CLI entry
point on its own.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ddr_xml_utils import safe_filename, write_metadata

try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    USING_LXML = False


# Map catalog-file suffix -> output object-type directory (the parsed/ contract).
# Suffix is matched case-insensitively against the file stem.
CATALOG_FILE_TYPES = {
    'basetablecatalog': 'tables',            # handled specially (merged with fields)
    'fieldcatalog': 'tables',                # handled specially
    'tableoccurrencecatalog': 'table_occurrences',
    'relationshipcatalog': 'relationships',
    'scriptcatalog': 'scripts',              # handled specially
    'layoutcatalog': 'layouts',              # handled specially
    'valuelistcatalog': 'value_lists',
    'customfunctionscatalog': 'custom_functions',
    'custommenucatalog': 'custom_menus',
    'custommenusetcatalog': 'custom_menu_sets',
    'accountscatalog': 'accounts',
    'privilegesetscatalog': 'privilege_sets',
    'extendedprivilegescatalog': 'extended_privileges',
    'externaldatasourcecatalog': 'external_data_sources',
    'basedirectorycatalog': 'base_directory',
    'persistentstorecatalog': 'persistent_store',
    'fileaccesscatalog': 'file_access',
    'themecatalog': 'themes',
}


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

def localname(tag):
    if isinstance(tag, str) and '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def is_fmsaveasxml_root(root):
    """True if this XML document is an FMSaveAsXML catalog file."""
    return localname(root.tag) == 'FMSaveAsXML'


def summary_catalog_folders(summary_root, summary_path):
    """For an <FMPReport type="Summary"> that points at split-catalog folders,
    return a list of (db_name, folder_path). Empty if this isn't that format.

    FM 2026 Summary.xml:
        <File name="X.fmp12" path="host"><XML path="/abs/path/to/X/"/></File>
    """
    out = []
    base = Path(summary_path).parent
    for file_elem in summary_root.findall('File'):
        db_name = file_elem.get('name', 'Unknown')
        xml_elem = file_elem.find('XML')
        if xml_elem is None:
            continue
        raw = (xml_elem.get('path') or xml_elem.text or '').strip()
        if not raw:
            continue
        folder = Path(raw)
        # The absolute path in the DDR is from the export machine; prefer a
        # sibling folder next to Summary.xml named after the file/db.
        candidates = [
            base / Path(raw).name,                       # sibling folder by name
            base / safe_filename(db_name.replace('.fmp12', '')),
            folder,                                       # absolute path as-is
        ]
        for c in candidates:
            if c.is_dir():
                out.append((db_name, c))
                break
        else:
            out.append((db_name, None))
    return out


def is_split_catalog_folder(folder):
    """True if a folder contains FMSaveAsXML split-catalog files."""
    folder = Path(folder)
    if not folder.is_dir():
        return False
    for f in folder.glob('*.xml'):
        try:
            root = etree.parse(str(f)).getroot()
        except Exception:
            continue
        if is_fmsaveasxml_root(root):
            return True
    return False


# ---------------------------------------------------------------------------
# Per-file helpers
# ---------------------------------------------------------------------------

def _catalog_element(file_root):
    """Return the catalog element (the single child of Structure/AddAction)."""
    structure = None
    for child in file_root:
        if localname(child.tag) == 'Structure':
            structure = child
            break
    if structure is None:
        return None
    for add in structure:
        if localname(add.tag) == 'AddAction':
            for cat in add:
                if isinstance(cat.tag, str):
                    return cat
    return None


def _ddr_info_element(file_root):
    for child in file_root:
        if localname(child.tag) == 'DDR_INFO':
            return child
    return None


def _iter(parent, tag):
    """Direct-or-descendant children with a given local tag name."""
    for e in parent.iter():
        if localname(e.tag) == tag:
            yield e


def _child(parent, tag):
    for c in parent:
        if localname(c.tag) == tag:
            return c
    return None


def _children(parent, tag):
    return [c for c in parent if localname(c.tag) == tag]


def _item_container(catalog):
    """Some catalogs nest their items in an <ObjectList> wrapper, others list
    them directly. Return whichever holds the actual objects."""
    ol = _child(catalog, 'ObjectList')
    return ol if ol is not None else catalog


def _uuid_text(elem):
    u = _child(elem, 'UUID')
    return (u.text or '').strip() if u is not None else ''


def _write(elem, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if USING_LXML:
        data = etree.tostring(elem, pretty_print=True, xml_declaration=True, encoding='utf-8')
    else:
        body = etree.tostring(elem, encoding='unicode')
        data = ('<?xml version="1.0" encoding="utf-8"?>\n' + body).encode('utf-8')
    with open(path, 'wb') as f:
        f.write(data)


def _unique(directory, name, fm_id=''):
    safe = safe_filename(name) or 'unnamed'
    p = Path(directory) / f'{safe}.xml'
    if p.exists() and fm_id:
        p = Path(directory) / f'{safe}_{fm_id}.xml'
    return p


def _el(tag, attrib=None):
    if USING_LXML:
        e = etree.Element(tag)
    else:
        e = etree.Element(tag)
    for k, v in (attrib or {}).items():
        e.set(k, v)
    return e


# ---------------------------------------------------------------------------
# DDR_INFO text store (for recovering readable step text)
# ---------------------------------------------------------------------------

def _build_text_store(file_root):
    """Map DDR_INFO object keys -> reconstructed text.

    DDR_INFO holds the content-addressable text store as elements named after
    the object key, e.g. <_BDEE15BC-…-…> or <_7BBC5499-…_1>, each containing the
    readable text (step text, calc text) as descendant text/Chunks. A <DDRREF>
    in the structure references one of these by its *text content* (the key).
    """
    store = {}
    ddr = _ddr_info_element(file_root)
    if ddr is None:
        return store
    for e in ddr.iter():
        tag = localname(e.tag)
        if tag.startswith('_'):
            text = ''.join(e.itertext())
            if text:
                store[tag] = text
    return store


def _resolve_step_text(step, store):
    """Attach a readable <StepText> to a step from DDR_INFO, if available."""
    for ref in _children(step, 'DDRREF'):
        if ref.get('kind') == 'StepText':
            key = (ref.text or '').strip()
            text = store.get(key)
            if text:
                st = _el('StepText')
                st.text = text
                step.insert(0, st)
            break


# ---------------------------------------------------------------------------
# Extractors (each returns the number of objects written)
# ---------------------------------------------------------------------------

def _extract_tables(basetable_root, field_root, out_dir):
    """Merge BaseTableCatalog (table list) with the FieldCatalog (per-table fields).

    The per-table <FieldCatalog> blocks have no name/id attribute; FileMaker emits
    them in the same document order as the base tables, so we zip positionally.
    Output: tables/<TableName>/fields.xml with root <BaseTable id name> wrapping
    the table's FieldCatalog.
    """
    bt_cat = _catalog_element(basetable_root) if basetable_root is not None else None
    base_tables = _children(bt_cat, 'BaseTable') if bt_cat is not None else []

    per_table_fields = []
    if field_root is not None:
        fld_cat = _catalog_element(field_root)  # <FieldsForTables>
        if fld_cat is not None:
            per_table_fields = _children(fld_cat, 'FieldCatalog')

    count = 0
    n = max(len(base_tables), len(per_table_fields))
    for i in range(n):
        bt = base_tables[i] if i < len(base_tables) else None
        fc = per_table_fields[i] if i < len(per_table_fields) else None
        if bt is not None:
            name = bt.get('name', f'table_{i}')
            tid = bt.get('id', '')
            comment = bt.get('comment', '')
        else:
            name = f'table_{i}'
            tid = ''
            comment = ''
        wrapper = _el('BaseTable', {'id': tid, 'name': name, 'comment': comment})
        if bt is not None:
            u = _child(bt, 'UUID')
            if u is not None:
                wrapper.append(u)
        if fc is not None:
            wrapper.append(fc)
        table_dir = Path(out_dir) / safe_filename(name)
        _write(wrapper, table_dir / 'fields.xml')
        count += 1
    return count


def _extract_table_occurrences(catalog, out_dir):
    count = 0
    for to in _children(_item_container(catalog), 'TableOccurrence'):
        # Surface the base table name as a `baseTable` attr for downstream tools.
        bt_ref = None
        for e in to.iter():
            if localname(e.tag) == 'BaseTableReference':
                bt_ref = e
                break
        if bt_ref is not None and not to.get('baseTable'):
            to.set('baseTable', bt_ref.get('name', ''))
        _write(to, _unique(out_dir, to.get('name', 'to'), to.get('id', '')))
        count += 1
    return count


def _extract_relationships(catalog, out_dir):
    count = 0
    for rel in _children(_item_container(catalog), 'Relationship'):
        left = right = None
        for side_tag, store in (('LeftTable', 'l'), ('RightTable', 'r')):
            side = _child(rel, side_tag)
            if side is not None:
                ref = _child(side, 'TableOccurrenceReference')
                if ref is not None:
                    if side_tag == 'LeftTable':
                        left = ref.get('name', '')
                    else:
                        right = ref.get('name', '')
        if left or right:
            name = f'{left or "?"}___{right or "?"}'
        else:
            name = rel.get('id', f'relationship_{count}')
        _write(rel, _unique(out_dir, name, rel.get('id', '')))
        count += 1
    return count


def _extract_scripts(catalog_root, out_dir):
    """Scripts live in two sibling sections of the ScriptCatalog file:
       <ScriptCatalog>  — Group/Script hierarchy (folders, names, ids, options)
       <StepsForScripts> — <Script><ScriptReference/><ObjectList>{Step}</ObjectList>
    We join them by script id and write scripts/<folder>/<name>.xml with a
    <Script id name><StepList>…</StepList></Script> root.
    """
    structure = None
    for child in catalog_root:
        if localname(child.tag) == 'Structure':
            structure = child
            break
    if structure is None:
        return 0
    add = _child(structure, 'AddAction')
    if add is None:
        return 0

    script_catalog = _child(add, 'ScriptCatalog')
    steps_for = _child(add, 'StepsForScripts')

    # id -> ObjectList of steps
    steps_by_id = {}
    store = _build_text_store(catalog_root)
    if steps_for is not None:
        for s in _children(steps_for, 'Script'):
            ref = _child(s, 'ScriptReference')
            obj_list = _child(s, 'ObjectList')
            if ref is not None and obj_list is not None:
                for step in _children(obj_list, 'Step'):
                    _resolve_step_text(step, store)
                steps_by_id[ref.get('id', '')] = obj_list

    count = 0

    def walk(parent, folder_parts):
        nonlocal count
        for item in parent:
            tag = localname(item.tag)
            if tag == 'Group':
                gname = item.get('name', 'Unnamed Folder')
                walk(item, folder_parts + [safe_filename(gname)])
            elif tag == 'Script':
                sid = item.get('id', '')
                name = item.get('name', f'script_{count}')
                script_el = _el('Script', {'id': sid, 'name': name})
                opts = _child(item, 'Options')
                if opts is not None:
                    script_el.append(opts)
                u = _child(item, 'UUID')
                if u is not None:
                    script_el.append(u)
                step_list = _el('StepList')
                obj_list = steps_by_id.get(sid)
                if obj_list is not None:
                    for step in _children(obj_list, 'Step'):
                        step_list.append(step)
                script_el.append(step_list)
                target = Path(out_dir).joinpath(*folder_parts) if folder_parts else Path(out_dir)
                _write(script_el, _unique(target, name, sid))
                count += 1

    if script_catalog is not None:
        walk(script_catalog, [])
    return count


def _extract_layouts(catalog, out_dir):
    """Layouts are a flat list; folders appear as <Layout isFolder="True">.
    Write each real layout as layouts/<name>.xml; skip folder markers."""
    count = 0
    for lay in _children(_item_container(catalog), 'Layout'):
        if lay.get('isFolder') == 'True':
            continue
        _write(lay, _unique(out_dir, lay.get('name', 'layout'), lay.get('id', '')))
        count += 1
    return count


def _extract_named(catalog, out_dir, child_tag):
    """Generic: write each <child_tag name=…> item of the catalog as a file."""
    count = 0
    for item in _children(_item_container(catalog), child_tag):
        _write(item, _unique(out_dir, item.get('name', f'{child_tag}_{count}'), item.get('id', '')))
        count += 1
    return count


# Generic catalog -> (child element tag) for the simple "named list" catalogs.
SIMPLE_CATALOGS = {
    'value_lists': ('ValueListCatalog', 'ValueList'),
    'custom_functions': ('CustomFunctionCatalog', 'CustomFunction'),
    'custom_menus': ('CustomMenuCatalog', 'CustomMenu'),
    'custom_menu_sets': ('CustomMenuSetCatalog', 'CustomMenuSet'),
    'accounts': ('AccountsCatalog', 'Account'),
    'privilege_sets': ('PrivilegeSetsCatalog', 'PrivilegeSet'),
    'extended_privileges': ('ExtendedPrivilegesCatalog', 'ExtendedPrivilege'),
    'external_data_sources': ('ExternalDataSourceCatalog', 'ExternalDataSource'),
    'themes': ('ThemeCatalog', 'Theme'),
}


# ---------------------------------------------------------------------------
# Folder driver
# ---------------------------------------------------------------------------

def parse_catalog_folder(folder, output_dir, db_name=None, called_from_summary=False):
    """Parse one split-catalog folder into output_dir/<safe_db_name>/…

    Returns a metadata dict (single-db shape) for _metadata.json.
    """
    folder = Path(folder)
    output_dir = Path(output_dir)

    # Index catalog files by their type suffix.
    files_by_type = {}
    fm_version = ''
    file_attr = ''
    for f in sorted(folder.glob('*.xml')):
        stem = f.stem.lower()
        for suffix, otype in CATALOG_FILE_TYPES.items():
            if stem.endswith(suffix):
                files_by_type.setdefault(suffix, f)
                break
        # Capture version / file name from any catalog file root.
        if not fm_version:
            try:
                r = etree.parse(str(f)).getroot()
                if is_fmsaveasxml_root(r):
                    fm_version = r.get('version', '')
                    file_attr = r.get('File', '')
            except Exception:
                pass

    if db_name is None:
        db_name = file_attr or folder.name
    # Match the legacy splitter convention: directory == safe_filename(db_name),
    # keyed identically in _metadata.json so downstream tools resolve it.
    safe_db = safe_filename(db_name)
    db_dir = output_dir / safe_db

    counts = {}
    warnings = []

    def load(suffix):
        f = files_by_type.get(suffix)
        if not f:
            return None
        try:
            return etree.parse(str(f)).getroot()
        except Exception as e:
            warnings.append(f'Could not parse {f.name}: {e}')
            return None

    # --- tables (BaseTable + Field merge) ---
    bt_root = load('basetablecatalog')
    fld_root = load('fieldcatalog')
    if bt_root is not None or fld_root is not None:
        # Count fields BEFORE extraction — _extract_tables reparents the
        # FieldCatalog elements out of fld_root (lxml append moves nodes).
        if fld_root is not None:
            fld_cat = _catalog_element(fld_root)
            if fld_cat is not None:
                counts['fields'] = sum(1 for _ in _iter(fld_cat, 'Field'))
        counts['tables'] = _extract_tables(bt_root, fld_root, db_dir / 'tables')

    # --- table occurrences ---
    to_root = load('tableoccurrencecatalog')
    if to_root is not None:
        cat = _catalog_element(to_root)
        if cat is not None:
            counts['table_occurrences'] = _extract_table_occurrences(cat, db_dir / 'table_occurrences')

    # --- relationships ---
    rel_root = load('relationshipcatalog')
    if rel_root is not None:
        cat = _catalog_element(rel_root)
        if cat is not None:
            counts['relationships'] = _extract_relationships(cat, db_dir / 'relationships')

    # --- scripts ---
    script_root = load('scriptcatalog')
    if script_root is not None:
        counts['scripts'] = _extract_scripts(script_root, db_dir / 'scripts')

    # --- layouts ---
    layout_root = load('layoutcatalog')
    if layout_root is not None:
        cat = _catalog_element(layout_root)
        if cat is not None:
            counts['layouts'] = _extract_layouts(cat, db_dir / 'layouts')

    # --- simple named catalogs ---
    for otype, (cat_tag, child_tag) in SIMPLE_CATALOGS.items():
        # find the file whose suffix maps to this otype
        suffix = next((s for s, t in CATALOG_FILE_TYPES.items() if t == otype), None)
        if not suffix:
            continue
        root = load(suffix)
        if root is None:
            continue
        cat = _catalog_element(root)
        if cat is None:
            continue
        counts[otype] = _extract_named(cat, db_dir / otype, child_tag)

    metadata = {
        'name': db_name,
        'source': str(folder),
        'parsed_at': datetime.now().isoformat(),
        'fm_version': fm_version,
        'format': 'fmsaveasxml-split',
        'counts': counts,
        'warnings': warnings,
    }

    if not called_from_summary:
        full = {
            'type': 'single-file',
            'source': str(folder),
            'parsed_at': metadata['parsed_at'],
            'fm_version': fm_version,
            'format': 'fmsaveasxml-split',
            'databases': {db_name: metadata},
            'warnings': warnings,
        }
        write_metadata(output_dir, full)

    return metadata
