#!/usr/bin/env python3
"""
FileMaker DDR Analyzer — Unified CLI
=====================================
Reliability: STABLE
Last validated: 2026-02-20
Known limitations:
- Files > 100MB use streaming parse (no full tree, some features limited)
- lxml recommended for XPath; falls back to xml.etree (limited)
- UTF-16 LE DDR files handled automatically via lxml BOM detection

Dependencies:
- lxml (recommended, optional)

Analyzes FileMaker Database Design Report (DDR) XML exports. Supports
splitting, reference tracing, orphan detection, comparison, search, and
summary generation. Read-only — never modifies FileMaker files.

Usage:
    python3 scripts/ddr.py split <input_xml> <output_dir>
    python3 scripts/ddr.py refs <parsed_dir> <target> [--type auto|eds|to|field|script|layout|valuelist]
    python3 scripts/ddr.py orphans <parsed_dir>
    python3 scripts/ddr.py compare <before_dir> <after_dir>
    python3 scripts/ddr.py search <parsed_dir> <term> [--regex] [--case-sensitive] [--type ...]
    python3 scripts/ddr.py summary <parsed_dir>

All commands support:
    --output <path>     Write report to file
    --json              Output structured JSON
    --project <name>    Shorthand: resolves to projects/<name>/parsed/
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ddr_xml_utils import (
    parse_xml, get_ddr_version, get_database_name, safe_filename,
    find_all_elements, extract_text_content, find_to_field_references,
    write_metadata, read_metadata, iter_parsed_files, USING_LXML,
)

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree


# ============================================================================
# Utility: output formatting
# ============================================================================

def output_result(data, fmt='markdown', output_path=None):
    """Write result to stdout or file, in markdown or JSON format."""
    if fmt == 'json':
        text = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    else:
        text = data if isinstance(data, str) else json.dumps(data, indent=2, default=str)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Report written to {output_path}")
    else:
        print(text)


def resolve_parsed_dir(args):
    """Resolve parsed_dir from --project shorthand or direct path."""
    if hasattr(args, 'project') and args.project:
        return Path('projects') / args.project / 'parsed'
    return Path(args.parsed_dir)


# ============================================================================
# SPLIT command
# ============================================================================

def cmd_split(args):
    """Parse a DDR XML and split into component files."""
    input_path = Path(args.input_xml)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        return {"status": "fatal", "error": {"type": "not_found", "message": f"Input file not found: {input_path}"}}

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = split_ddr(input_path, output_dir)

    if args.json:
        return {"status": "success", "data": metadata}
    return metadata


def split_ddr(input_path, output_dir):
    """Main entry point: parse a DDR export and split into component files.

    Auto-detects classic <FMPReport> DDR (FM 12-22) and FileMaker 2026
    "Save a Copy as XML" split-catalog folders (<FMSaveAsXML split_catalogs>).
    """
    from fmsaveasxml import is_fmsaveasxml_root, summary_catalog_folders

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # FM 2026: a split-catalog folder passed directly.
    if input_path.is_dir():
        print(f"Parsing split-catalog folder {input_path.name}/ ...")
        return _split_catalog_folders([(input_path.name, input_path)], input_path, output_dir)

    print(f"Parsing {input_path.name}...")
    root, tree = parse_xml(input_path)

    # FM 2026: a single <FMSaveAsXML> catalog file — parse its whole folder.
    if is_fmsaveasxml_root(root):
        folder = input_path.parent
        return _split_catalog_folders([(root.get('File', folder.name), folder)], input_path, output_dir)

    if _is_summary_file(root):
        # FM 2026 Summary.xml points at split-catalog folders via <XML path>.
        folders = summary_catalog_folders(root, input_path)
        if folders and any(f for _, f in folders):
            return _split_catalog_folders(folders, input_path, output_dir)
        return _split_summary(root, input_path, output_dir)
    else:
        return _split_database(root, input_path, output_dir)


def _split_catalog_folders(folders, source_path, output_dir):
    """Drive the FM 2026 split-catalog parser over one or more database folders."""
    from fmsaveasxml import parse_catalog_folder

    metadata = {
        'type': 'multi-file' if len(folders) > 1 else 'single-file',
        'source': str(source_path),
        'parsed_at': datetime.now().isoformat(),
        'fm_version': '',
        'format': 'fmsaveasxml-split',
        'databases': {},
        'warnings': [],
    }
    for db_name, folder in folders:
        if folder is None:
            warning = f"Split-catalog folder not found for '{db_name}'"
            metadata['warnings'].append(warning)
            print(f"  WARNING: {warning}")
            continue
        print(f"  Processing database: {db_name} ({folder.name}/)")
        db_meta = parse_catalog_folder(folder, output_dir, db_name=db_name, called_from_summary=True)
        metadata['databases'][db_name] = db_meta
        metadata['fm_version'] = metadata['fm_version'] or db_meta.get('fm_version', '')
        metadata['warnings'].extend(db_meta.get('warnings', []))

    write_metadata(output_dir, metadata)
    return metadata


def _is_summary_file(root):
    """Detect if this is a Summary.xml or a database report file."""
    report_type = root.get('type', '')
    if report_type == 'Summary':
        return True
    if report_type == 'Report':
        return False

    file_catalog = root.find('.//FileCatalog')
    if file_catalog is not None:
        files = file_catalog.findall('File')
        if files:
            return True

    for file_elem in root.findall('File'):
        if file_elem.get('link'):
            return True

    return False


def _split_summary(root, input_path, output_dir):
    """Split a Summary.xml that references database files."""
    metadata = {
        'type': 'multi-file' if len(root.findall('File')) > 1 else 'single-file',
        'source': str(input_path),
        'parsed_at': datetime.now().isoformat(),
        'fm_version': get_ddr_version(root),
        'databases': {},
        'warnings': []
    }

    input_dir = input_path.parent

    file_elems = root.findall('File')
    if not file_elems:
        file_catalog = root.find('.//FileCatalog')
        if file_catalog is not None:
            file_elems = file_catalog.findall('File')

    for file_elem in file_elems:
        db_name = file_elem.get('name', 'Unknown')
        link = file_elem.get('link', '')
        filename = file_elem.get('filename', '')

        db_path = None
        if link:
            link_clean = link.lstrip('.').lstrip('/')
            db_path = input_dir / link_clean
            if not db_path.exists():
                db_path = input_dir / link

        if (db_path is None or not db_path.exists()) and filename:
            db_path = input_dir / filename

        if db_path is None or not db_path.exists():
            for candidate in [
                f'{safe_filename(db_name)}.xml',
                f'{db_name}.xml',
                f'{db_name.replace(".fmp12", "_fmp12")}.xml',
            ]:
                candidate_path = input_dir / candidate
                if candidate_path.exists():
                    db_path = candidate_path
                    break

        if db_path is not None and db_path.exists():
            print(f"  Processing database: {db_name} ({db_path.name})")
            db_root, _ = parse_xml(db_path)
            db_meta = _split_database(db_root, db_path, output_dir, called_from_summary=True)
            metadata['databases'][db_name] = db_meta

            expected = _extract_summary_counts(file_elem)
            if expected:
                db_meta['expected_counts'] = expected
        else:
            warning = f"Referenced file not found for '{db_name}' (link='{link}')"
            metadata['warnings'].append(warning)
            print(f"  WARNING: {warning}")

    write_metadata(output_dir, metadata)
    _print_split_summary(metadata)
    return metadata


def _extract_summary_counts(file_elem):
    """Extract expected counts from a Summary.xml File element."""
    counts = {}
    count_map = {
        'BaseTables': 'tables',
        'Tables': 'table_occurrences',
        'Relationships': 'relationships',
        'Accounts': 'accounts',
        'Privileges': 'privilege_sets',
        'ExtendedPrivileges': 'extended_privileges',
        'FileAccess': 'file_access',
        'Layouts': 'layouts',
        'Scripts': 'scripts',
        'ValueLists': 'value_lists',
        'CustomFunctions': 'custom_functions',
        'FileReferences': 'external_data_sources',
        'CustomMenuSets': 'custom_menu_sets',
        'CustomMenus': 'custom_menus',
    }
    for child in file_elem:
        tag = child.tag
        if tag in count_map:
            count_str = child.get('count', '0')
            try:
                counts[count_map[tag]] = int(count_str)
            except ValueError:
                pass
    return counts


def _split_database(root, input_path, output_dir, called_from_summary=False):
    """Split a single database DDR XML into component files."""
    db_name = get_database_name(root)
    safe_db_name = safe_filename(db_name)
    db_dir = Path(output_dir) / safe_db_name

    metadata = {
        'name': db_name,
        'source': str(input_path),
        'parsed_at': datetime.now().isoformat(),
        'fm_version': get_ddr_version(root),
        'counts': {},
        'warnings': []
    }

    extractors = [
        ('external_data_sources', _extract_external_data_sources),
        ('table_occurrences', _extract_table_occurrences),
        ('tables', _extract_tables),
        ('relationships', _extract_relationships),
        ('scripts', _extract_scripts),
        ('layouts', _extract_layouts),
        ('value_lists', _extract_value_lists),
        ('custom_functions', _extract_custom_functions),
        ('custom_menus', _extract_custom_menus),
        ('accounts', _extract_accounts),
        ('privilege_sets', _extract_privilege_sets),
    ]

    for obj_type, extractor in extractors:
        type_dir = db_dir / obj_type
        try:
            count = extractor(root, type_dir)
            metadata['counts'][obj_type] = count
        except Exception as e:
            warning = f"Error extracting {obj_type}: {e}"
            metadata['warnings'].append(warning)
            metadata['counts'][obj_type] = 0
            print(f"  WARNING: {warning}")

    if not called_from_summary:
        full_meta = {
            'type': 'single-file',
            'source': str(input_path),
            'parsed_at': datetime.now().isoformat(),
            'fm_version': metadata['fm_version'],
            'databases': {db_name: metadata},
            'warnings': metadata['warnings']
        }
        write_metadata(output_dir, full_meta)
        _print_split_summary(full_meta)

    return metadata


def _write_element(element, output_path):
    """Write an XML element to a file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if USING_LXML:
        xml_bytes = etree.tostring(element, pretty_print=True, xml_declaration=True, encoding='utf-8')
    else:
        xml_bytes = etree.tostring(element, encoding='unicode')
        xml_bytes = f'<?xml version="1.0" encoding="utf-8"?>\n{xml_bytes}'.encode('utf-8')

    with open(output_path, 'wb') as f:
        f.write(xml_bytes)


def _get_unique_filename(directory, name, fm_id=None):
    """Get a unique filename, appending FM ID if there's a collision."""
    safe_name = safe_filename(name)
    path = Path(directory) / f'{safe_name}.xml'
    if path.exists() and fm_id:
        path = Path(directory) / f'{safe_name}_{fm_id}.xml'
    return path


# --- Extractors for each DDR catalog type ---

def _extract_external_data_sources(root, output_dir):
    count = 0
    catalog_searches = [
        'ExternalDataSourcesCatalog',
        'ExternalDataSourceCatalog',
        'FileReferenceCatalog',
    ]
    for catalog_tag in catalog_searches:
        catalog = root.find(f'.//{catalog_tag}')
        if catalog is None:
            continue
        for item in catalog:
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            out_path = _get_unique_filename(output_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
        if count > 0:
            break
    return count


def _extract_table_occurrences(root, output_dir):
    count = 0
    catalog = root.find('.//TableOccurrenceCatalog')
    if catalog is not None:
        for item in catalog.findall('TableOccurrence'):
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            out_path = _get_unique_filename(output_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
        return count

    rel_graph = root.find('.//RelationshipGraph')
    if rel_graph is not None:
        table_list = rel_graph.find('TableList')
        if table_list is not None:
            for item in table_list.findall('Table'):
                name = item.get('name', f'unnamed_{count}')
                fm_id = item.get('id', '')
                out_path = _get_unique_filename(output_dir, name, fm_id)
                _write_element(item, out_path)
                count += 1
    return count


def _extract_tables(root, output_dir):
    count = 0
    catalog = root.find('.//BaseTableCatalog')
    if catalog is None:
        return 0
    for table in catalog.findall('BaseTable'):
        name = table.get('name', f'unnamed_{count}')
        table_dir = Path(output_dir) / safe_filename(name)
        _write_element(table, table_dir / 'fields.xml')
        count += 1
    return count


def _extract_relationships(root, output_dir):
    count = 0
    catalog = root.find('.//RelationshipCatalog')
    if catalog is not None:
        for item in catalog.findall('Relationship'):
            name = _relationship_name(item, count)
            fm_id = item.get('id', '')
            out_path = _get_unique_filename(output_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
        return count

    rel_graph = root.find('.//RelationshipGraph')
    if rel_graph is not None:
        rel_list = rel_graph.find('RelationshipList')
        if rel_list is not None:
            for item in rel_list.findall('Relationship'):
                name = _relationship_name(item, count)
                fm_id = item.get('id', '')
                out_path = _get_unique_filename(output_dir, name, fm_id)
                _write_element(item, out_path)
                count += 1
    return count


def _relationship_name(item, index):
    """Build a filename for a relationship from its left and right table names."""
    left = item.find('.//LeftTable')
    right = item.find('.//RightTable')
    if left is not None and right is not None:
        left_name = left.get('name', 'unknown')
        right_name = right.get('name', 'unknown')
        return f'{left_name}___{right_name}'
    return item.get('name', f'relationship_{index}')


def _extract_scripts(root, output_dir):
    catalog = root.find('.//ScriptCatalog')
    if catalog is None:
        return 0
    return _extract_scripts_recursive(catalog, output_dir, [])


def _extract_scripts_recursive(parent, output_dir, folder_path):
    count = 0
    for item in parent:
        tag = item.tag if not USING_LXML else etree.QName(item.tag).localname if '}' in item.tag else item.tag

        if tag == 'Group':
            group_name = item.get('name', 'Unnamed Folder')
            new_path = folder_path + [safe_filename(group_name)]
            count += _extract_scripts_recursive(item, output_dir, new_path)
        elif tag == 'Script':
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            if folder_path:
                script_dir = Path(output_dir).joinpath(*folder_path)
            else:
                script_dir = Path(output_dir)
            out_path = _get_unique_filename(script_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
    return count


def _extract_layouts(root, output_dir):
    catalog = root.find('.//LayoutCatalog')
    if catalog is None:
        return 0
    return _extract_layouts_recursive(catalog, output_dir, [])


def _extract_layouts_recursive(parent, output_dir, folder_path):
    count = 0
    for item in parent:
        tag = item.tag if not USING_LXML else etree.QName(item.tag).localname if '}' in item.tag else item.tag

        if tag == 'Group':
            group_name = item.get('name', 'Unnamed Folder')
            new_path = folder_path + [safe_filename(group_name)]
            count += _extract_layouts_recursive(item, output_dir, new_path)
        elif tag == 'Layout':
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            if folder_path:
                layout_dir = Path(output_dir).joinpath(*folder_path)
            else:
                layout_dir = Path(output_dir)
            out_path = _get_unique_filename(layout_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
    return count


def _extract_value_lists(root, output_dir):
    count = 0
    catalog = root.find('.//ValueListCatalog')
    if catalog is None:
        return 0
    for item in catalog.findall('ValueList'):
        name = item.get('name', f'unnamed_{count}')
        fm_id = item.get('id', '')
        out_path = _get_unique_filename(output_dir, name, fm_id)
        _write_element(item, out_path)
        count += 1
    return count


def _extract_custom_functions(root, output_dir):
    count = 0
    catalog = root.find('.//CustomFunctionCatalog')
    if catalog is None:
        return 0
    for item in catalog.findall('CustomFunction'):
        name = item.get('name', f'unnamed_{count}')
        fm_id = item.get('id', '')
        out_path = _get_unique_filename(output_dir, name, fm_id)
        _write_element(item, out_path)
        count += 1
    return count


def _extract_custom_menus(root, output_dir):
    count = 0
    for catalog_tag in ['CustomMenuCatalog', 'CustomMenuSetCatalog']:
        catalog = root.find(f'.//{catalog_tag}')
        if catalog is None:
            continue
        for item in catalog:
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            out_path = _get_unique_filename(output_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
    return count


def _extract_accounts(root, output_dir):
    count = 0
    catalog = root.find('.//AccountCatalog')
    if catalog is None:
        return 0
    for item in catalog.findall('Account'):
        name = item.get('name', f'unnamed_{count}')
        fm_id = item.get('id', '')
        out_path = _get_unique_filename(output_dir, name, fm_id)
        _write_element(item, out_path)
        count += 1
    return count


def _extract_privilege_sets(root, output_dir):
    count = 0
    for catalog_tag in ['PrivilegesCatalog', 'PrivilegeSetCatalog']:
        catalog = root.find(f'.//{catalog_tag}')
        if catalog is None:
            continue
        for item in catalog.findall('PrivilegeSet'):
            name = item.get('name', f'unnamed_{count}')
            fm_id = item.get('id', '')
            out_path = _get_unique_filename(output_dir, name, fm_id)
            _write_element(item, out_path)
            count += 1
        if count > 0:
            break
    return count


def _print_split_summary(metadata):
    """Print a human-readable summary of what was parsed."""
    print("\n--- Parse Complete ---")
    fm_version = metadata.get('fm_version', 'Unknown')
    if fm_version:
        print(f"FileMaker Version: {fm_version}")

    for db_name, db_meta in metadata.get('databases', {}).items():
        counts = db_meta.get('counts', {})
        print(f"\n  {db_name}:")
        for obj_type, count in counts.items():
            expected = db_meta.get('expected_counts', {}).get(obj_type)
            if expected is not None:
                match = "OK" if count == expected else f"MISMATCH (expected {expected})"
                print(f"    {obj_type}: {count}  [{match}]")
            elif count > 0:
                print(f"    {obj_type}: {count}")

    warnings = metadata.get('warnings', [])
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")


# ============================================================================
# REFS command
# ============================================================================

def cmd_refs(args):
    """Find all references to a target across the parsed DDR."""
    parsed_dir = resolve_parsed_dir(args)
    results = find_references(parsed_dir, args.target, args.type)

    if args.json:
        output_result({"status": "success", "data": results}, 'json', args.output)
    else:
        report = format_refs_report(results)
        output_result(report, 'markdown', args.output)


def find_references(parsed_dir, target, target_type='auto'):
    """Find all references to a target across the parsed DDR."""
    parsed_dir = Path(parsed_dir)
    read_metadata(parsed_dir)  # Validate parsed dir

    results = {
        'target': target,
        'target_type': target_type,
        'external_data_sources': [],
        'table_occurrences': [],
        'calculations': [],
        'script_steps': [],
        'layout_objects': [],
        'value_lists': [],
        'relationships': [],
        'custom_functions': [],
        'summary': {}
    }

    if target_type in ('auto', 'eds'):
        _find_eds_references(parsed_dir, target, results)

    to_names = [ref['name'] for ref in results['table_occurrences']]
    if target_type in ('auto', 'to') and not to_names:
        to_names = [target]

    if to_names:
        _find_to_references(parsed_dir, to_names, target, results)

    if target_type == 'field' or (target_type == 'auto' and '::' in target):
        _find_field_references(parsed_dir, target, results)

    if target_type in ('script', 'auto'):
        _find_script_references(parsed_dir, target, results)

    if target_type in ('layout', 'auto'):
        _find_layout_references(parsed_dir, target, results)

    results['summary'] = {
        'total': sum(len(v) for k, v in results.items() if isinstance(v, list)),
        'external_data_sources': len(results['external_data_sources']),
        'table_occurrences': len(results['table_occurrences']),
        'calculations': len(results['calculations']),
        'script_steps': len(results['script_steps']),
        'layout_objects': len(results['layout_objects']),
        'value_lists': len(results['value_lists']),
        'relationships': len(results['relationships']),
        'custom_functions': len(results['custom_functions']),
    }

    return results


def _find_eds_references(parsed_dir, target, results):
    """Find external data source references and TOs pointing to them."""
    for filepath, root in iter_parsed_files(parsed_dir, 'external_data_sources'):
        name = root.get('name', '')
        if target.lower() in name.lower():
            results['external_data_sources'].append({
                'file': str(filepath),
                'name': name,
                'paths': extract_text_content(root.find('.//PathList') or root.find('.//FilePathList')),
            })

    for filepath, root in iter_parsed_files(parsed_dir, 'table_occurrences'):
        to_name = root.get('name', '')
        source_elem = root.find('.//FileReference') or root.find('.//SourceFile')
        if source_elem is not None:
            source_name = source_elem.get('name', '')
            if target.lower() in source_name.lower():
                base_table = root.get('baseTable', '')
                results['table_occurrences'].append({
                    'file': str(filepath),
                    'name': to_name,
                    'base_table': base_table,
                    'source_file': source_name,
                })


def _find_to_references(parsed_dir, to_names, original_target, results):
    """Find all references to specific table occurrence names."""
    # Search calculations
    for filepath, root in iter_parsed_files(parsed_dir, 'tables'):
        table_name = root.get('name', filepath.parent.name)
        field_catalog = root.find('.//FieldCatalog') or root
        for field in find_all_elements(field_catalog, 'Field'):
            field_name = field.get('name', '')
            calc_elem = field.find('.//Calculation')
            if calc_elem is not None:
                calc_text = extract_text_content(calc_elem)
                refs_found = find_to_field_references(calc_text)
                for to_name, ref_field in refs_found:
                    if to_name in to_names or original_target.lower() in to_name.lower():
                        results['calculations'].append({
                            'file': str(filepath),
                            'table': table_name,
                            'field': field_name,
                            'reference': f'{to_name}::{ref_field}',
                            'context': _truncate_context(calc_text, to_name),
                        })

    # Search script steps
    for filepath, root in iter_parsed_files(parsed_dir, 'scripts'):
        script_name = root.get('name', filepath.stem)
        step_list = root.find('.//StepList') or root
        for step in find_all_elements(step_list, 'Step'):
            step_id = step.get('id', '')
            step_name = step.get('name', '')
            step_text = extract_text_content(step)
            for to_name in to_names:
                if to_name in step_text:
                    results['script_steps'].append({
                        'file': str(filepath),
                        'script': script_name,
                        'step_id': step_id,
                        'step_type': step_name,
                        'context': _truncate_context(step_text, to_name),
                    })
                    break

    # Search layout objects
    for filepath, root in iter_parsed_files(parsed_dir, 'layouts'):
        layout_name = root.get('name', filepath.stem)
        layout_text = extract_text_content(root)
        for to_name in to_names:
            if to_name in layout_text:
                for obj in find_all_elements(root, 'Object') + find_all_elements(root, 'FieldObj'):
                    obj_text = extract_text_content(obj)
                    if to_name in obj_text:
                        obj_type = obj.get('type', obj.tag)
                        field_ref = _extract_field_ref(obj, to_name)
                        results['layout_objects'].append({
                            'file': str(filepath),
                            'layout': layout_name,
                            'object_type': obj_type,
                            'reference': field_ref or to_name,
                        })

    # Search value lists
    for filepath, root in iter_parsed_files(parsed_dir, 'value_lists'):
        vl_name = root.get('name', filepath.stem)
        vl_text = extract_text_content(root)
        for to_name in to_names:
            if to_name in vl_text:
                results['value_lists'].append({
                    'file': str(filepath),
                    'name': vl_name,
                    'reference': to_name,
                })

    # Search relationships
    for filepath, root in iter_parsed_files(parsed_dir, 'relationships'):
        rel_text = extract_text_content(root)
        for to_name in to_names:
            if to_name in rel_text:
                results['relationships'].append({
                    'file': str(filepath),
                    'name': filepath.stem,
                    'reference': to_name,
                })

    # Search custom functions
    for filepath, root in iter_parsed_files(parsed_dir, 'custom_functions'):
        cf_name = root.get('name', filepath.stem)
        cf_text = extract_text_content(root)
        for to_name in to_names:
            if to_name in cf_text:
                results['custom_functions'].append({
                    'file': str(filepath),
                    'name': cf_name,
                    'reference': to_name,
                    'context': _truncate_context(cf_text, to_name),
                })


def _find_field_references(parsed_dir, target, results):
    """Find references to a specific field (TO::FieldName pattern)."""
    for filepath, root in iter_parsed_files(parsed_dir):
        text = extract_text_content(root)
        if target in text:
            rel_path = str(filepath)
            obj_name = root.get('name', filepath.stem)
            if '/scripts/' in rel_path:
                results['script_steps'].append({
                    'file': rel_path,
                    'script': obj_name,
                    'step_id': '',
                    'step_type': '(field reference)',
                    'context': _truncate_context(text, target),
                })
            elif '/tables/' in rel_path:
                results['calculations'].append({
                    'file': rel_path,
                    'table': filepath.parent.name,
                    'field': obj_name,
                    'reference': target,
                    'context': _truncate_context(text, target),
                })
            elif '/layouts/' in rel_path:
                results['layout_objects'].append({
                    'file': rel_path,
                    'layout': obj_name,
                    'object_type': 'field reference',
                    'reference': target,
                })


def _find_script_references(parsed_dir, target, results):
    """Find references to a script name (called by other scripts)."""
    for filepath, root in iter_parsed_files(parsed_dir, 'scripts'):
        script_name = root.get('name', filepath.stem)
        if script_name == target:
            continue
        text = extract_text_content(root)
        if target in text:
            for step in find_all_elements(root, 'Step'):
                step_text = extract_text_content(step)
                if target in step_text and step.get('name', '') in ('Perform Script', 'Perform Script on Server'):
                    results['script_steps'].append({
                        'file': str(filepath),
                        'script': script_name,
                        'step_id': step.get('id', ''),
                        'step_type': step.get('name', ''),
                        'context': f'Calls script: "{target}"',
                    })


def _find_layout_references(parsed_dir, target, results):
    """Find references to a layout name (Go to Layout steps)."""
    for filepath, root in iter_parsed_files(parsed_dir, 'scripts'):
        script_name = root.get('name', filepath.stem)
        for step in find_all_elements(root, 'Step'):
            step_name = step.get('name', '')
            if 'Layout' in step_name:
                step_text = extract_text_content(step)
                if target in step_text:
                    results['script_steps'].append({
                        'file': str(filepath),
                        'script': script_name,
                        'step_id': step.get('id', ''),
                        'step_type': step_name,
                        'context': f'References layout: "{target}"',
                    })


def _truncate_context(text, target, max_len=120):
    """Extract a context snippet around the target match."""
    idx = text.find(target)
    if idx == -1:
        return text[:max_len]
    start = max(0, idx - 40)
    end = min(len(text), idx + len(target) + 40)
    snippet = text[start:end].replace('\n', ' ').replace('\r', '').strip()
    if start > 0:
        snippet = '...' + snippet
    if end < len(text):
        snippet = snippet + '...'
    return snippet


def _extract_field_ref(obj_elem, to_name):
    """Try to extract a TO::Field reference from a layout object element."""
    text = extract_text_content(obj_elem)
    refs = find_to_field_references(text)
    for to, field in refs:
        if to == to_name:
            return f'{to}::{field}'
    return None


def format_refs_report(results):
    """Format reference results as a markdown report."""
    target = results['target']
    summary = results['summary']

    lines = []
    lines.append(f'# Reference Report: "{target}"')
    lines.append('')
    lines.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('')

    lines.append('## Summary')
    lines.append(f'- **Total references found:** {summary["total"]}')
    for key, count in summary.items():
        if key != 'total' and count > 0:
            label = key.replace('_', ' ').title()
            lines.append(f'- **{label}:** {count}')
    lines.append('')

    if results['external_data_sources']:
        lines.append(f'## External Data Sources ({len(results["external_data_sources"])})')
        for ref in results['external_data_sources']:
            lines.append(f'- [ ] `{ref["name"]}` — {ref.get("paths", "no paths listed")}')
        lines.append('')

    if results['table_occurrences']:
        lines.append(f'## Table Occurrences ({len(results["table_occurrences"])})')
        lines.append(f'TOs pointing to "{target}":')
        for ref in results['table_occurrences']:
            lines.append(f'- [ ] `{ref["name"]}` -> {ref.get("source_file", "")}::{ref.get("base_table", "")}')
        lines.append('')

    if results['calculations']:
        lines.append(f'## Calculations ({len(results["calculations"])})')
        for ref in results['calculations']:
            lines.append(f'- [ ] `{ref["table"]}::{ref["field"]}` uses `{ref["reference"]}`')
            if ref.get('context'):
                lines.append(f'  > `{ref["context"]}`')
        lines.append('')

    if results['script_steps']:
        lines.append(f'## Script Steps ({len(results["script_steps"])})')
        for ref in results['script_steps']:
            step_info = f'Step {ref["step_id"]}' if ref['step_id'] else ''
            lines.append(f'- [ ] `{ref["script"]}` -> {step_info}: {ref["step_type"]}')
            if ref.get('context'):
                lines.append(f'  > `{ref["context"]}`')
        lines.append('')

    if results['layout_objects']:
        lines.append(f'## Layout Objects ({len(results["layout_objects"])})')
        for ref in results['layout_objects']:
            lines.append(f'- [ ] `{ref["layout"]}` -> {ref["object_type"]}: {ref["reference"]}')
        lines.append('')

    if results['value_lists']:
        lines.append(f'## Value Lists ({len(results["value_lists"])})')
        for ref in results['value_lists']:
            lines.append(f'- [ ] `{ref["name"]}` references `{ref["reference"]}`')
        lines.append('')

    if results['relationships']:
        lines.append(f'## Relationships ({len(results["relationships"])})')
        for ref in results['relationships']:
            lines.append(f'- [ ] `{ref["name"]}` involves `{ref["reference"]}`')
        lines.append('')

    if results['custom_functions']:
        lines.append(f'## Custom Functions ({len(results["custom_functions"])})')
        for ref in results['custom_functions']:
            lines.append(f'- [ ] `{ref["name"]}` references `{ref["reference"]}`')
            if ref.get('context'):
                lines.append(f'  > `{ref["context"]}`')
        lines.append('')

    return '\n'.join(lines)


# ============================================================================
# ORPHANS command
# ============================================================================

def cmd_orphans(args):
    """Find unreferenced objects in the parsed DDR."""
    parsed_dir = resolve_parsed_dir(args)
    orphans = find_orphans(parsed_dir)

    if args.json:
        output_result({"status": "success", "data": orphans}, 'json', args.output)
    else:
        report = format_orphans_report(orphans)
        output_result(report, 'markdown', args.output)


def find_orphans(parsed_dir):
    """Find all unreferenced objects in the parsed DDR."""
    parsed_dir = Path(parsed_dir)
    read_metadata(parsed_dir)

    defined = _collect_defined_objects(parsed_dir)
    referenced = _collect_all_references(parsed_dir)

    orphans = {
        'table_occurrences': [],
        'fields': defaultdict(list),
        'scripts': [],
        'layouts': [],
        'custom_functions': [],
        'value_lists': [],
        'external_data_sources': [],
        'summary': {}
    }

    for to_name, to_info in defined['table_occurrences'].items():
        if to_name not in referenced['table_occurrences']:
            orphans['table_occurrences'].append({
                'name': to_name,
                'base_table': to_info.get('base_table', ''),
                'file': to_info.get('file', ''),
                'likely_safe': True,
            })

    for table_name, fields in defined['fields'].items():
        for field_name, field_info in fields.items():
            is_referenced = False
            for to_name, to_info in defined['table_occurrences'].items():
                if to_info.get('base_table') == table_name:
                    to_field_ref = f'{to_name}::{field_name}'
                    if to_field_ref in referenced['fields'] or field_name in referenced['field_names_only']:
                        is_referenced = True
                        break
            if not is_referenced:
                orphans['fields'][table_name].append({
                    'name': field_name,
                    'type': field_info.get('type', ''),
                    'is_calculated': field_info.get('is_calculated', False),
                    'file': field_info.get('file', ''),
                })

    for script_name, script_info in defined['scripts'].items():
        if script_name not in referenced['scripts']:
            is_entry_point = _might_be_entry_point(script_name)
            orphans['scripts'].append({
                'name': script_name,
                'file': script_info.get('file', ''),
                'folder': script_info.get('folder', ''),
                'likely_safe': not is_entry_point,
                'note': 'May be entry point (button/trigger/API)' if is_entry_point else '',
            })

    for layout_name, layout_info in defined['layouts'].items():
        if layout_name not in referenced['layouts']:
            orphans['layouts'].append({
                'name': layout_name,
                'file': layout_info.get('file', ''),
                'folder': layout_info.get('folder', ''),
            })

    for cf_name, cf_info in defined['custom_functions'].items():
        if cf_name not in referenced['custom_functions']:
            orphans['custom_functions'].append({
                'name': cf_name,
                'file': cf_info.get('file', ''),
            })

    for vl_name, vl_info in defined['value_lists'].items():
        if vl_name not in referenced['value_lists']:
            orphans['value_lists'].append({
                'name': vl_name,
                'file': vl_info.get('file', ''),
            })

    for eds_name, eds_info in defined['external_data_sources'].items():
        if eds_name not in referenced['external_data_sources']:
            orphans['external_data_sources'].append({
                'name': eds_name,
                'file': eds_info.get('file', ''),
            })

    orphans['summary'] = {
        'table_occurrences': len(orphans['table_occurrences']),
        'fields': sum(len(fields) for fields in orphans['fields'].values()),
        'scripts': len(orphans['scripts']),
        'layouts': len(orphans['layouts']),
        'custom_functions': len(orphans['custom_functions']),
        'value_lists': len(orphans['value_lists']),
        'external_data_sources': len(orphans['external_data_sources']),
    }
    orphans['summary']['total'] = sum(orphans['summary'].values())

    return orphans


def _collect_defined_objects(parsed_dir):
    """Collect all objects defined in the DDR."""
    defined = {
        'table_occurrences': {},
        'fields': defaultdict(dict),
        'scripts': {},
        'layouts': {},
        'custom_functions': {},
        'value_lists': {},
        'external_data_sources': {},
    }

    for filepath, root in iter_parsed_files(parsed_dir, 'table_occurrences'):
        name = root.get('name', filepath.stem)
        defined['table_occurrences'][name] = {
            'base_table': root.get('baseTable', ''),
            'file': str(filepath),
        }

    for filepath, root in iter_parsed_files(parsed_dir, 'tables'):
        table_name = root.get('name', filepath.parent.name)
        for field in find_all_elements(root, 'Field'):
            field_name = field.get('name', '')
            field_type = (field.get('fieldType') or field.get('fieldtype') or field.get('type') or '')
            has_calc = field.find('.//Calculation') is not None
            defined['fields'][table_name][field_name] = {
                'type': field_type,
                'is_calculated': has_calc,
                'file': str(filepath),
            }

    for filepath, root in iter_parsed_files(parsed_dir, 'scripts'):
        name = root.get('name', filepath.stem)
        folder = str(filepath.parent.relative_to(parsed_dir)) if filepath.parent != parsed_dir else ''
        defined['scripts'][name] = {
            'file': str(filepath),
            'folder': folder,
        }

    for filepath, root in iter_parsed_files(parsed_dir, 'layouts'):
        name = root.get('name', filepath.stem)
        folder = str(filepath.parent.relative_to(parsed_dir)) if filepath.parent != parsed_dir else ''
        defined['layouts'][name] = {
            'file': str(filepath),
            'folder': folder,
        }

    for filepath, root in iter_parsed_files(parsed_dir, 'custom_functions'):
        name = root.get('name', filepath.stem)
        defined['custom_functions'][name] = {'file': str(filepath)}

    for filepath, root in iter_parsed_files(parsed_dir, 'value_lists'):
        name = root.get('name', filepath.stem)
        defined['value_lists'][name] = {'file': str(filepath)}

    for filepath, root in iter_parsed_files(parsed_dir, 'external_data_sources'):
        name = root.get('name', filepath.stem)
        defined['external_data_sources'][name] = {'file': str(filepath)}

    return defined


def _collect_all_references(parsed_dir):
    """Scan all parsed files and collect every reference to every object."""
    referenced = {
        'table_occurrences': set(),
        'fields': set(),
        'field_names_only': set(),
        'scripts': set(),
        'layouts': set(),
        'custom_functions': set(),
        'value_lists': set(),
        'external_data_sources': set(),
    }

    for filepath, root in iter_parsed_files(parsed_dir):
        text = extract_text_content(root)
        to_field_refs = find_to_field_references(text)
        for to_name, field_name in to_field_refs:
            referenced['table_occurrences'].add(to_name)
            referenced['fields'].add(f'{to_name}::{field_name}')
            referenced['field_names_only'].add(field_name)

    for filepath, root in iter_parsed_files(parsed_dir, 'scripts'):
        for step in find_all_elements(root, 'Step'):
            step_name = step.get('name', '')
            # Classic DDR nests <Script>/<Layout>; FM 2026 uses <ScriptReference>/<LayoutReference>.
            if 'Perform Script' in step_name:
                for ref in find_all_elements(step, 'Script') + find_all_elements(step, 'ScriptReference'):
                    if ref.get('name'):
                        referenced['scripts'].add(ref.get('name'))
            if 'Layout' in step_name:
                for ref in find_all_elements(step, 'Layout') + find_all_elements(step, 'LayoutReference'):
                    if ref.get('name'):
                        referenced['layouts'].add(ref.get('name'))

    for filepath, root in iter_parsed_files(parsed_dir, 'layouts'):
        for vl_elem in find_all_elements(root, 'ValueList') + find_all_elements(root, 'ValueListReference'):
            referenced['value_lists'].add(vl_elem.get('name', ''))
        for trigger in find_all_elements(root, 'Script') + find_all_elements(root, 'ScriptReference'):
            referenced['scripts'].add(trigger.get('name', ''))

    for filepath, root in iter_parsed_files(parsed_dir, 'tables'):
        for calc in find_all_elements(root, 'Calculation'):
            calc_text = extract_text_content(calc)
            referenced['custom_functions'].update(
                _extract_function_calls(calc_text)
            )

    for filepath, root in iter_parsed_files(parsed_dir, 'table_occurrences'):
        source = root.find('.//FileReference') or root.find('.//SourceFile')
        if source is not None:
            referenced['external_data_sources'].add(source.get('name', ''))

    return referenced


def _might_be_entry_point(script_name):
    """Heuristic: might this script be called externally?"""
    entry_patterns = ['startup', 'shutdown', 'init', 'on open', 'on close',
                      'trigger', 'api', 'webhook', 'button', 'onrecord',
                      'onfirst', 'onlast', 'ontimer']
    name_lower = script_name.lower()
    return any(p in name_lower for p in entry_patterns)


def _extract_function_calls(calc_text):
    """Extract function names from a calculation text."""
    matches = re.findall(r'\b([A-Za-z_]\w+)\s*\(', calc_text)
    return set(matches)


def format_orphans_report(orphans):
    """Format orphan results as a markdown report."""
    summary = orphans['summary']

    lines = []
    lines.append('# Orphan Report')
    lines.append('')
    lines.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('')

    lines.append('## Summary')
    lines.append(f'- **Total orphaned objects:** {summary["total"]}')
    for key, count in summary.items():
        if key != 'total' and count > 0:
            label = key.replace('_', ' ').title()
            lines.append(f'- **{label}:** {count}')
    lines.append('')

    if orphans['table_occurrences']:
        lines.append(f'## Orphaned Table Occurrences ({len(orphans["table_occurrences"])})')
        safe = [o for o in orphans['table_occurrences'] if o.get('likely_safe')]
        review = [o for o in orphans['table_occurrences'] if not o.get('likely_safe')]
        if safe:
            lines.append('### Likely Safe to Remove')
            for o in safe:
                lines.append(f'- [ ] `{o["name"]}` — base table: {o["base_table"]}')
        if review:
            lines.append('### Review Before Removing')
            for o in review:
                lines.append(f'- [ ] `{o["name"]}` — base table: {o["base_table"]}')
        lines.append('')

    if orphans['fields']:
        total_fields = sum(len(f) for f in orphans['fields'].values())
        lines.append(f'## Orphaned Fields ({total_fields})')
        for table_name, fields in sorted(orphans['fields'].items()):
            lines.append(f'### Table: {table_name}')
            for f in fields:
                calc_note = ' (calculated)' if f['is_calculated'] else ''
                lines.append(f'- [ ] `{f["name"]}` — {f["type"]}{calc_note}')
        lines.append('')

    if orphans['scripts']:
        lines.append(f'## Orphaned Scripts ({len(orphans["scripts"])})')
        safe = [o for o in orphans['scripts'] if o.get('likely_safe')]
        review = [o for o in orphans['scripts'] if not o.get('likely_safe')]
        if safe:
            lines.append('### Likely Safe to Remove')
            for o in safe:
                lines.append(f'- [ ] `{o["folder"]}/{o["name"]}`' if o['folder'] else f'- [ ] `{o["name"]}`')
        if review:
            lines.append('### Review Before Removing (may be entry points)')
            for o in review:
                note = f' — {o["note"]}' if o.get('note') else ''
                lines.append(f'- [ ] `{o["name"]}`{note}')
        lines.append('')

    if orphans['layouts']:
        lines.append(f'## Orphaned Layouts ({len(orphans["layouts"])})')
        for o in orphans['layouts']:
            lines.append(f'- [ ] `{o["name"]}`')
        lines.append('')

    if orphans['custom_functions']:
        lines.append(f'## Orphaned Custom Functions ({len(orphans["custom_functions"])})')
        for o in orphans['custom_functions']:
            lines.append(f'- [ ] `{o["name"]}`')
        lines.append('')

    if orphans['value_lists']:
        lines.append(f'## Orphaned Value Lists ({len(orphans["value_lists"])})')
        for o in orphans['value_lists']:
            lines.append(f'- [ ] `{o["name"]}`')
        lines.append('')

    if orphans['external_data_sources']:
        lines.append(f'## Orphaned External Data Sources ({len(orphans["external_data_sources"])})')
        for o in orphans['external_data_sources']:
            lines.append(f'- [ ] `{o["name"]}`')
        lines.append('')

    return '\n'.join(lines)


# ============================================================================
# COMPARE command
# ============================================================================

def cmd_compare(args):
    """Compare two parsed DDR exports."""
    before_dir = Path(args.before_dir)
    after_dir = Path(args.after_dir)
    changes = compare_ddrs(before_dir, after_dir)

    if args.json:
        output_result({"status": "success", "data": changes}, 'json', args.output)
    else:
        report = format_compare_report(changes)
        output_result(report, 'markdown', args.output)


def compare_ddrs(before_dir, after_dir):
    """Compare two parsed DDR directories."""
    before_dir = Path(before_dir)
    after_dir = Path(after_dir)

    before_meta = read_metadata(before_dir)
    after_meta = read_metadata(after_dir)

    changes = {
        'before': {
            'source': before_meta.get('source', ''),
            'parsed_at': before_meta.get('parsed_at', ''),
            'fm_version': before_meta.get('fm_version', ''),
        },
        'after': {
            'source': after_meta.get('source', ''),
            'parsed_at': after_meta.get('parsed_at', ''),
            'fm_version': after_meta.get('fm_version', ''),
        },
        'databases': {},
        'summary': defaultdict(lambda: {'added': 0, 'removed': 0, 'modified': 0}),
    }

    before_dbs = set(before_meta.get('databases', {}).keys())
    after_dbs = set(after_meta.get('databases', {}).keys())
    all_dbs = before_dbs | after_dbs

    for db_name in sorted(all_dbs):
        if db_name in before_dbs and db_name not in after_dbs:
            changes['databases'][db_name] = {'status': 'removed'}
            changes['summary']['databases']['removed'] += 1
        elif db_name not in before_dbs and db_name in after_dbs:
            changes['databases'][db_name] = {'status': 'added'}
            changes['summary']['databases']['added'] += 1
        else:
            safe_name = safe_filename(db_name)
            db_changes = _compare_database(
                before_dir / safe_name,
                after_dir / safe_name,
                db_name
            )
            changes['databases'][db_name] = db_changes

            for obj_type, type_changes in db_changes.items():
                if isinstance(type_changes, dict) and 'added' in type_changes:
                    changes['summary'][obj_type]['added'] += len(type_changes.get('added', []))
                    changes['summary'][obj_type]['removed'] += len(type_changes.get('removed', []))
                    changes['summary'][obj_type]['modified'] += len(type_changes.get('modified', []))

    return changes


def _compare_database(before_db_dir, after_db_dir, db_name):
    """Compare a single database between two DDR versions."""
    db_changes = {'name': db_name}

    object_types = [
        ('tables', _compare_tables),
        ('table_occurrences', _compare_simple_objects),
        ('scripts', _compare_scripts),
        ('layouts', _compare_simple_objects),
        ('relationships', _compare_simple_objects),
        ('value_lists', _compare_simple_objects),
        ('custom_functions', _compare_simple_objects),
        ('external_data_sources', _compare_simple_objects),
        ('accounts', _compare_simple_objects),
        ('privilege_sets', _compare_simple_objects),
        ('custom_menus', _compare_simple_objects),
    ]

    for obj_type, compare_func in object_types:
        before_type_dir = before_db_dir / obj_type
        after_type_dir = after_db_dir / obj_type

        if not before_type_dir.exists() and not after_type_dir.exists():
            continue

        try:
            type_changes = compare_func(before_type_dir, after_type_dir)
            if type_changes['added'] or type_changes['removed'] or type_changes['modified']:
                db_changes[obj_type] = type_changes
        except Exception as e:
            db_changes[obj_type] = {'error': str(e)}

    return db_changes


def _compare_simple_objects(before_dir, after_dir):
    """Compare objects by name — detect added, removed, and content changes."""
    result = {'added': [], 'removed': [], 'modified': []}

    before_files = {}
    after_files = {}

    if before_dir.exists():
        for f in before_dir.rglob('*.xml'):
            try:
                root, _ = parse_xml(f)
                name = root.get('name', f.stem)
                content = extract_text_content(root)
                before_files[name] = {'file': f, 'content': content}
            except Exception:
                before_files[f.stem] = {'file': f, 'content': ''}

    if after_dir.exists():
        for f in after_dir.rglob('*.xml'):
            try:
                root, _ = parse_xml(f)
                name = root.get('name', f.stem)
                content = extract_text_content(root)
                after_files[name] = {'file': f, 'content': content}
            except Exception:
                after_files[f.stem] = {'file': f, 'content': ''}

    all_names = set(before_files.keys()) | set(after_files.keys())

    for name in sorted(all_names):
        if name in before_files and name not in after_files:
            result['removed'].append({'name': name})
        elif name not in before_files and name in after_files:
            result['added'].append({'name': name})
        else:
            before_content = _normalize(before_files[name]['content'])
            after_content = _normalize(after_files[name]['content'])
            if before_content != after_content:
                result['modified'].append({
                    'name': name,
                    'details': _diff_summary(before_files[name]['content'], after_files[name]['content']),
                })

    return result


def _compare_tables(before_dir, after_dir):
    """Compare tables with field-level detail."""
    result = {'added': [], 'removed': [], 'modified': []}

    before_tables = _load_tables(before_dir)
    after_tables = _load_tables(after_dir)

    all_names = set(before_tables.keys()) | set(after_tables.keys())

    for name in sorted(all_names):
        if name in before_tables and name not in after_tables:
            result['removed'].append({'name': name, 'field_count': len(before_tables[name]['fields'])})
        elif name not in before_tables and name in after_tables:
            result['added'].append({'name': name, 'field_count': len(after_tables[name]['fields']),
                                    'fields': list(after_tables[name]['fields'].keys())})
        else:
            field_changes = _compare_fields(before_tables[name]['fields'], after_tables[name]['fields'])
            if field_changes['added'] or field_changes['removed'] or field_changes['modified']:
                result['modified'].append({
                    'name': name,
                    'field_changes': field_changes,
                })

    return result


def _compare_scripts(before_dir, after_dir):
    """Compare scripts with step-level detail."""
    result = {'added': [], 'removed': [], 'modified': []}

    before_scripts = _load_scripts(before_dir)
    after_scripts = _load_scripts(after_dir)

    all_names = set(before_scripts.keys()) | set(after_scripts.keys())

    for name in sorted(all_names):
        if name in before_scripts and name not in after_scripts:
            result['removed'].append({'name': name, 'steps': before_scripts[name]['step_count']})
        elif name not in before_scripts and name in after_scripts:
            result['added'].append({'name': name, 'steps': after_scripts[name]['step_count']})
        else:
            before_content = _normalize(before_scripts[name]['content'])
            after_content = _normalize(after_scripts[name]['content'])
            if before_content != after_content:
                result['modified'].append({
                    'name': name,
                    'before_steps': before_scripts[name]['step_count'],
                    'after_steps': after_scripts[name]['step_count'],
                    'details': _diff_summary(before_scripts[name]['content'], after_scripts[name]['content']),
                })

    return result


def _load_tables(tables_dir):
    """Load all tables and their fields from a parsed tables directory."""
    tables = {}
    if not tables_dir.exists():
        return tables

    for table_dir in tables_dir.iterdir():
        if table_dir.is_dir():
            fields_file = table_dir / 'fields.xml'
            if fields_file.exists():
                try:
                    root, _ = parse_xml(fields_file)
                    table_name = root.get('name', table_dir.name)
                    fields = {}
                    for field in find_all_elements(root, 'Field'):
                        field_name = field.get('name', '')
                        field_type = (field.get('fieldType') or field.get('fieldtype') or field.get('type') or '')
                        calc_elem = field.find('.//Calculation')
                        calc_text = extract_text_content(calc_elem) if calc_elem is not None else ''
                        fields[field_name] = {
                            'type': field_type,
                            'calculation': calc_text,
                        }
                    tables[table_name] = {'fields': fields}
                except Exception:
                    pass
    return tables


def _load_scripts(scripts_dir):
    """Load all scripts and their content from a parsed scripts directory."""
    scripts = {}
    if not scripts_dir.exists():
        return scripts

    for xml_file in scripts_dir.rglob('*.xml'):
        try:
            root, _ = parse_xml(xml_file)
            name = root.get('name', xml_file.stem)
            steps = find_all_elements(root, 'Step')
            content = extract_text_content(root)
            scripts[name] = {
                'step_count': len(steps),
                'content': content,
            }
        except Exception:
            pass
    return scripts


def _compare_fields(before_fields, after_fields):
    """Compare field sets between two versions of a table."""
    result = {'added': [], 'removed': [], 'modified': []}

    all_names = set(before_fields.keys()) | set(after_fields.keys())

    for name in sorted(all_names):
        if name in before_fields and name not in after_fields:
            result['removed'].append({'name': name, 'type': before_fields[name]['type']})
        elif name not in before_fields and name in after_fields:
            result['added'].append({'name': name, 'type': after_fields[name]['type']})
        else:
            bf = before_fields[name]
            af = after_fields[name]
            changes = []
            if bf['type'] != af['type']:
                changes.append(f'type: {bf["type"]} -> {af["type"]}')
            if _normalize(bf['calculation']) != _normalize(af['calculation']):
                changes.append('calculation changed')
            if changes:
                result['modified'].append({'name': name, 'changes': changes})

    return result


def _normalize(text):
    """Normalize text for comparison."""
    return ' '.join(text.split())


def _diff_summary(before_text, after_text):
    """Generate a brief summary of what changed between two texts."""
    before_len = len(before_text)
    after_len = len(after_text)
    if after_len > before_len:
        return f'Content expanded ({before_len} -> {after_len} chars)'
    elif after_len < before_len:
        return f'Content reduced ({before_len} -> {after_len} chars)'
    else:
        return 'Content modified (same length)'


def format_compare_report(changes):
    """Format comparison results as a markdown report."""
    lines = []
    lines.append('# DDR Comparison Report')
    lines.append('')
    lines.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append(f'**Before:** {changes["before"].get("source", "unknown")} (FM {changes["before"].get("fm_version", "?")})')
    lines.append(f'**After:** {changes["after"].get("source", "unknown")} (FM {changes["after"].get("fm_version", "?")})')
    lines.append('')

    lines.append('## Summary of Changes')
    lines.append('')
    lines.append('| Type | Added | Removed | Modified |')
    lines.append('|---|---|---|---|')
    for obj_type, counts in sorted(changes['summary'].items()):
        label = obj_type.replace('_', ' ').title()
        lines.append(f'| {label} | {counts["added"]} | {counts["removed"]} | {counts["modified"]} |')
    lines.append('')

    for db_name, db_changes in sorted(changes['databases'].items()):
        if db_changes.get('status') == 'added':
            lines.append(f'## {db_name} (NEW DATABASE)')
            lines.append('')
            continue
        elif db_changes.get('status') == 'removed':
            lines.append(f'## {db_name} (REMOVED)')
            lines.append('')
            continue

        has_changes = any(
            isinstance(v, dict) and ('added' in v or 'error' in v)
            for k, v in db_changes.items() if k != 'name'
        )
        if not has_changes:
            continue

        lines.append(f'## {db_name}')
        lines.append('')

        for obj_type, type_changes in sorted(db_changes.items()):
            if obj_type == 'name' or not isinstance(type_changes, dict):
                continue
            if 'error' in type_changes:
                lines.append(f'### {obj_type.replace("_", " ").title()} (Error: {type_changes["error"]})')
                continue

            added = type_changes.get('added', [])
            removed = type_changes.get('removed', [])
            modified = type_changes.get('modified', [])

            if not added and not removed and not modified:
                continue

            label = obj_type.replace('_', ' ').title()
            lines.append(f'### {label}')
            lines.append('')

            if added:
                lines.append(f'**Added ({len(added)}):**')
                for item in added:
                    detail = ''
                    if 'field_count' in item:
                        detail = f' — {item["field_count"]} fields'
                    elif 'steps' in item:
                        detail = f' — {item["steps"]} steps'
                    lines.append(f'- [ ] `{item["name"]}`{detail}')
                lines.append('')

            if removed:
                lines.append(f'**Removed ({len(removed)}):**')
                for item in removed:
                    lines.append(f'- [ ] `{item["name"]}`')
                lines.append('')

            if modified:
                lines.append(f'**Modified ({len(modified)}):**')
                for item in modified:
                    lines.append(f'- [ ] `{item["name"]}`')
                    if 'field_changes' in item:
                        fc = item['field_changes']
                        for f in fc.get('added', []):
                            lines.append(f'  - Added field: `{f["name"]}` ({f["type"]})')
                        for f in fc.get('removed', []):
                            lines.append(f'  - Removed field: `{f["name"]}` ({f["type"]})')
                        for f in fc.get('modified', []):
                            lines.append(f'  - Modified field: `{f["name"]}` — {", ".join(f["changes"])}')
                    elif 'details' in item:
                        lines.append(f'  - {item["details"]}')
                lines.append('')

    return '\n'.join(lines)


# ============================================================================
# SEARCH command
# ============================================================================

def cmd_search(args):
    """Search across all parsed DDR files."""
    parsed_dir = resolve_parsed_dir(args)
    results = search_ddr(
        parsed_dir, args.term,
        case_sensitive=args.case_sensitive,
        use_regex=args.regex,
        object_type=args.type
    )

    if args.json:
        output_result({"status": "success", "data": results}, 'json', args.output)
    else:
        report = format_search_report(results)
        output_result(report, 'markdown', args.output)


def search_ddr(parsed_dir, term, case_sensitive=False, use_regex=False, object_type='all'):
    """Search for a term across all parsed DDR files."""
    parsed_dir = Path(parsed_dir)

    if use_regex:
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(term, flags)
        except re.error as e:
            return {"status": "fatal", "error": {"type": "validation", "message": f"Invalid regex: {e}"}}
        match_func = lambda text: bool(pattern.search(text))
    else:
        if case_sensitive:
            match_func = lambda text: term in text
        else:
            term_lower = term.lower()
            match_func = lambda text: term_lower in text.lower()

    results = {
        'term': term,
        'case_sensitive': case_sensitive,
        'regex': use_regex,
        'matches': defaultdict(list),
        'files_searched': 0,
        'files_matched': 0,
    }

    type_map = {
        'all': None,
        'calcs': 'tables',
        'scripts': 'scripts',
        'layouts': 'layouts',
        'valuelists': 'value_lists',
        'customfunctions': 'custom_functions',
    }
    search_type = type_map.get(object_type.lower(), None)

    files_with_matches = set()

    for filepath, root in iter_parsed_files(parsed_dir, search_type):
        results['files_searched'] += 1

        rel_path = str(filepath)
        category = _categorize_file(rel_path)

        text = extract_text_content(root)

        if match_func(text):
            files_with_matches.add(str(filepath))
            matches = _find_matches_with_context(root, filepath, term, match_func, category)
            results['matches'][category].extend(matches)

    results['files_matched'] = len(files_with_matches)
    return results


def _categorize_file(filepath):
    """Determine the DDR category from a file path."""
    parts = filepath.lower()
    if '/tables/' in parts:
        return 'calculations'
    elif '/scripts/' in parts:
        return 'scripts'
    elif '/layouts/' in parts:
        return 'layouts'
    elif '/value_lists/' in parts:
        return 'value_lists'
    elif '/custom_functions/' in parts:
        return 'custom_functions'
    elif '/table_occurrences/' in parts:
        return 'table_occurrences'
    elif '/relationships/' in parts:
        return 'relationships'
    elif '/external_data_sources/' in parts:
        return 'external_data_sources'
    elif '/accounts/' in parts:
        return 'accounts'
    elif '/privilege_sets/' in parts:
        return 'privilege_sets'
    elif '/custom_menus/' in parts:
        return 'custom_menus'
    return 'other'


def _find_matches_with_context(root, filepath, term, match_func, category):
    """Find specific match locations within an element, with context."""
    matches = []
    obj_name = root.get('name', filepath.stem)

    if category == 'calculations':
        table_name = root.get('name', filepath.parent.name)
        for field in find_all_elements(root, 'Field'):
            field_name = field.get('name', '')
            calc = field.find('.//Calculation')
            if calc is not None:
                calc_text = extract_text_content(calc)
                if match_func(calc_text):
                    matches.append({
                        'file': str(filepath),
                        'object': f'{table_name}::{field_name}',
                        'type': 'field calculation',
                        'context': _get_search_context(calc_text, term),
                    })

    elif category == 'scripts':
        script_name = obj_name
        for step in find_all_elements(root, 'Step'):
            step_text = extract_text_content(step)
            if match_func(step_text):
                step_id = step.get('id', '?')
                step_type = step.get('name', 'Unknown')
                matches.append({
                    'file': str(filepath),
                    'object': script_name,
                    'type': f'Step {step_id} ({step_type})',
                    'context': _get_search_context(step_text, term),
                })

    else:
        text = extract_text_content(root)
        if match_func(text):
            matches.append({
                'file': str(filepath),
                'object': obj_name,
                'type': category,
                'context': _get_search_context(text, term),
            })

    return matches


def _get_search_context(text, term, max_len=120):
    """Extract a context snippet around the search term."""
    idx = text.lower().find(term.lower())
    if idx == -1:
        return text[:max_len].replace('\n', ' ').strip()

    start = max(0, idx - 40)
    end = min(len(text), idx + len(term) + 40)
    snippet = text[start:end].replace('\n', ' ').replace('\r', '').strip()

    if start > 0:
        snippet = '...' + snippet
    if end < len(text):
        snippet = snippet + '...'

    return snippet


def format_search_report(results):
    """Format search results as a markdown report."""
    term = results['term']
    total_matches = sum(len(m) for m in results['matches'].values())

    lines = []
    lines.append(f'# Search Report: "{term}"')
    lines.append('')
    lines.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    if results['regex']:
        lines.append('**Pattern type:** regex')
    if results['case_sensitive']:
        lines.append('**Case sensitive:** yes')
    lines.append('')

    lines.append('## Summary')
    lines.append(f'- **Total matches:** {total_matches}')
    lines.append(f'- **Files searched:** {results["files_searched"]}')
    lines.append(f'- **Files with matches:** {results["files_matched"]}')
    lines.append('')

    for category, matches in sorted(results['matches'].items()):
        if not matches:
            continue
        label = category.replace('_', ' ').title()
        lines.append(f'## {label} ({len(matches)} matches)')
        for m in matches:
            lines.append(f'- [ ] `{m["object"]}` — {m["type"]}')
            if m.get('context'):
                lines.append(f'  > `{m["context"]}`')
        lines.append('')

    return '\n'.join(lines)


# ============================================================================
# SUMMARY command
# ============================================================================

def cmd_summary(args):
    """Generate a high-level DDR summary."""
    parsed_dir = resolve_parsed_dir(args)
    summary = summarize_ddr(parsed_dir)

    if args.json:
        output_result({"status": "success", "data": summary}, 'json', args.output)
    else:
        report = format_summary_report(summary)
        output_result(report, 'markdown', args.output)


def summarize_ddr(parsed_dir):
    """Generate a comprehensive summary of the parsed DDR."""
    parsed_dir = Path(parsed_dir)
    metadata = read_metadata(parsed_dir)

    summary = {
        'fm_version': metadata.get('fm_version', 'Unknown'),
        'parsed_at': metadata.get('parsed_at', ''),
        'type': metadata.get('type', 'unknown'),
        'databases': {},
        'totals': defaultdict(int),
        'concerns': [],
    }

    for db_name in metadata.get('databases', {}):
        db_summary = _summarize_database(parsed_dir, db_name)
        summary['databases'][db_name] = db_summary

        for key, value in db_summary.get('counts', {}).items():
            summary['totals'][key] += value

    summary['concerns'] = _identify_concerns(summary)

    return summary


def _summarize_database(parsed_dir, db_name):
    """Summarize a single database within the parsed DDR."""
    db_dir = parsed_dir / safe_filename(db_name)

    if not db_dir.exists():
        return {'name': db_name, 'counts': {}, 'error': 'Directory not found'}

    db_summary = {
        'name': db_name,
        'counts': {},
        'tables': [],
        'scripts_by_folder': defaultdict(int),
        'layouts_by_folder': defaultdict(int),
        'external_deps': [],
        'script_complexity': [],
    }

    # Count and detail tables
    tables_dir = db_dir / 'tables'
    if tables_dir.exists():
        table_count = 0
        for table_dir in sorted(tables_dir.iterdir()):
            if table_dir.is_dir():
                fields_file = table_dir / 'fields.xml'
                if fields_file.exists():
                    table_count += 1
                    table_info = _analyze_table(fields_file, table_dir.name)
                    db_summary['tables'].append(table_info)
        db_summary['counts']['tables'] = table_count
        db_summary['counts']['fields'] = sum(t['total_fields'] for t in db_summary['tables'])

    # Count scripts and analyze complexity
    scripts_dir = db_dir / 'scripts'
    if scripts_dir.exists():
        script_count = 0
        for xml_file in scripts_dir.rglob('*.xml'):
            script_count += 1
            folder = str(xml_file.parent.relative_to(scripts_dir)) if xml_file.parent != scripts_dir else '(root)'
            db_summary['scripts_by_folder'][folder] += 1
            try:
                root, _ = parse_xml(xml_file)
                steps = find_all_elements(root, 'Step')
                step_count = len(steps)
                db_summary['script_complexity'].append({
                    'name': root.get('name', xml_file.stem),
                    'folder': folder,
                    'steps': step_count,
                })
            except Exception:
                pass
        db_summary['counts']['scripts'] = script_count

    # Count layouts
    layouts_dir = db_dir / 'layouts'
    if layouts_dir.exists():
        layout_count = 0
        for xml_file in layouts_dir.rglob('*.xml'):
            layout_count += 1
            folder = str(xml_file.parent.relative_to(layouts_dir)) if xml_file.parent != layouts_dir else '(root)'
            db_summary['layouts_by_folder'][folder] += 1
        db_summary['counts']['layouts'] = layout_count

    # Count simple items
    for obj_type in ['table_occurrences', 'relationships', 'value_lists',
                     'custom_functions', 'external_data_sources', 'custom_menus',
                     'accounts', 'privilege_sets']:
        type_dir = db_dir / obj_type
        if type_dir.exists():
            count = sum(1 for f in type_dir.rglob('*.xml'))
            db_summary['counts'][obj_type] = count

    # Detail external data sources
    eds_dir = db_dir / 'external_data_sources'
    if eds_dir.exists():
        for xml_file in eds_dir.rglob('*.xml'):
            try:
                root, _ = parse_xml(xml_file)
                name = root.get('name', xml_file.stem)
                paths = extract_text_content(root.find('.//PathList') or root.find('.//FilePathList') or root)
                db_summary['external_deps'].append({
                    'name': name,
                    'paths': paths[:200],
                })
            except Exception:
                pass

    return db_summary


def _analyze_table(fields_file, table_name):
    """Analyze a table's field definitions."""
    info = {
        'name': table_name,
        'total_fields': 0,
        'calculated': 0,
        'summary_fields': 0,
        'global_fields': 0,
        'stored': 0,
    }
    try:
        root, _ = parse_xml(fields_file)
        for field in find_all_elements(root, 'Field'):
            info['total_fields'] += 1
            field_type = (field.get('fieldType') or field.get('fieldtype') or field.get('type') or '').lower()
            if 'calc' in field_type:
                info['calculated'] += 1
            elif 'summary' in field_type:
                info['summary_fields'] += 1
            else:
                info['stored'] += 1
            storage = field.find('.//Storage')
            if storage is not None and storage.get('global', '').lower() == 'true':
                info['global_fields'] += 1
    except Exception:
        pass
    return info


def _identify_concerns(summary):
    """Identify potential issues or notable patterns."""
    concerns = []

    for db_name, db in summary['databases'].items():
        for table in db.get('tables', []):
            if table['total_fields'] > 100:
                concerns.append(f'{db_name}: Table "{table["name"]}" has {table["total_fields"]} fields (consider splitting)')

        for script in db.get('script_complexity', []):
            if script['steps'] > 100:
                concerns.append(f'{db_name}: Script "{script["name"]}" has {script["steps"]} steps (consider refactoring)')

        eds_count = db.get('counts', {}).get('external_data_sources', 0)
        if eds_count > 5:
            concerns.append(f'{db_name}: {eds_count} external data sources (high coupling)')

        to_count = db.get('counts', {}).get('table_occurrences', 0)
        table_count = db.get('counts', {}).get('tables', 0)
        if table_count > 0 and to_count > table_count * 5:
            concerns.append(f'{db_name}: {to_count} TOs for {table_count} tables (high TO/table ratio)')

    return concerns


def format_summary_report(summary):
    """Format summary as a markdown report."""
    lines = []
    lines.append('# DDR Summary')
    lines.append('')
    lines.append(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append(f'**FileMaker Version:** {summary["fm_version"]}')
    lines.append(f'**Files in Solution:** {len(summary["databases"])}')
    lines.append('')

    lines.append('## Database Files')
    lines.append('')
    lines.append('| File | Tables | Fields | Scripts | Layouts | TOs | Relationships | External DS |')
    lines.append('|---|---|---|---|---|---|---|---|')
    for db_name, db in sorted(summary['databases'].items()):
        c = db.get('counts', {})
        lines.append(f'| {db_name} | {c.get("tables", 0)} | {c.get("fields", 0)} | {c.get("scripts", 0)} | {c.get("layouts", 0)} | {c.get("table_occurrences", 0)} | {c.get("relationships", 0)} | {c.get("external_data_sources", 0)} |')
    if len(summary['databases']) > 1:
        t = summary['totals']
        lines.append(f'| **Total** | **{t.get("tables", 0)}** | **{t.get("fields", 0)}** | **{t.get("scripts", 0)}** | **{t.get("layouts", 0)}** | **{t.get("table_occurrences", 0)}** | **{t.get("relationships", 0)}** | **{t.get("external_data_sources", 0)}** |')
    lines.append('')

    for db_name, db in sorted(summary['databases'].items()):
        lines.append(f'## {db_name}')
        lines.append('')

        if db.get('tables'):
            lines.append('### Tables')
            lines.append('')
            lines.append('| Table | Fields | Calculated | Summary | Global |')
            lines.append('|---|---|---|---|---|')
            for t in sorted(db['tables'], key=lambda x: -x['total_fields']):
                lines.append(f'| {t["name"]} | {t["total_fields"]} | {t["calculated"]} | {t["summary_fields"]} | {t["global_fields"]} |')
            lines.append('')

        if db.get('scripts_by_folder'):
            lines.append('### Scripts by Folder')
            lines.append('')
            lines.append('| Folder | Count |')
            lines.append('|---|---|')
            for folder, count in sorted(db['scripts_by_folder'].items()):
                lines.append(f'| {folder} | {count} |')
            lines.append('')

        if db.get('script_complexity'):
            top_scripts = sorted(db['script_complexity'], key=lambda x: -x['steps'])[:10]
            lines.append('### Most Complex Scripts (Top 10)')
            lines.append('')
            lines.append('| Script | Folder | Steps |')
            lines.append('|---|---|---|')
            for s in top_scripts:
                lines.append(f'| {s["name"]} | {s["folder"]} | {s["steps"]} |')
            lines.append('')

        if db.get('external_deps'):
            lines.append('### External Data Sources')
            lines.append('')
            for dep in db['external_deps']:
                lines.append(f'- **{dep["name"]}**: `{dep["paths"]}`')
            lines.append('')

    if summary['concerns']:
        lines.append('## Potential Concerns')
        lines.append('')
        for concern in summary['concerns']:
            lines.append(f'- {concern}')
        lines.append('')

    return '\n'.join(lines)


def cmd_readable(args):
    """Export an agent-facing readable knowledge base (Markdown) from a parsed DDR."""
    import readable as _readable
    parsed_dir = resolve_parsed_dir(args)
    metadata = read_metadata(parsed_dir)
    output_dir = Path(args.output_dir) if args.output_dir else parsed_dir.parent / 'readable'
    print(f"Exporting readable knowledge base → {output_dir}")
    dbs = [args.db] if args.db else list(metadata.get('databases', {}))
    for db_name in dbs:
        _readable.export_db(parsed_dir, db_name, output_dir)
    return {"status": "success", "data": {"output_dir": str(output_dir), "databases": dbs}}


# ============================================================================
# CLI entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='FileMaker DDR Analyzer — parse, search, compare, and audit DDR XML exports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  split     Parse DDR XML and split into component files
  refs      Trace all references to a target object
  orphans   Find unreferenced (dead) objects
  compare   Compare two parsed DDR versions
  search    Free-text search across all DDR content
  summary   Generate high-level database overview

Examples:
  python3 scripts/ddr.py split projects/mydb/ddr/Summary.xml projects/mydb/parsed/
  python3 scripts/ddr.py refs projects/mydb/parsed/ "OldDatabase" --type eds
  python3 scripts/ddr.py orphans projects/mydb/parsed/ --output report.md
  python3 scripts/ddr.py summary --project mydb
        """
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # --- split ---
    sp_split = subparsers.add_parser('split', help='Parse DDR XML and split into component files')
    sp_split.add_argument('input_xml', help='Path to Summary.xml or database XML file')
    sp_split.add_argument('output_dir', help='Directory to write parsed output')
    sp_split.add_argument('--json', action='store_true', help='Output as JSON')
    sp_split.add_argument('--output', help='Write report to file')
    sp_split.set_defaults(func=cmd_split)

    # --- refs ---
    sp_refs = subparsers.add_parser('refs', help='Trace all references to a target')
    sp_refs.add_argument('parsed_dir', nargs='?', help='Path to parsed DDR directory')
    sp_refs.add_argument('target', help='Target name to search for')
    sp_refs.add_argument('--type', default='auto',
                         choices=['auto', 'eds', 'to', 'field', 'script', 'layout', 'valuelist'],
                         help='Type of target (default: auto-detect)')
    sp_refs.add_argument('--project', help='Project name (shorthand for projects/<name>/parsed/)')
    sp_refs.add_argument('--json', action='store_true', help='Output as JSON')
    sp_refs.add_argument('--output', help='Write report to file')
    sp_refs.set_defaults(func=cmd_refs)

    # --- orphans ---
    sp_orphans = subparsers.add_parser('orphans', help='Find unreferenced objects')
    sp_orphans.add_argument('parsed_dir', nargs='?', help='Path to parsed DDR directory')
    sp_orphans.add_argument('--project', help='Project name (shorthand for projects/<name>/parsed/)')
    sp_orphans.add_argument('--json', action='store_true', help='Output as JSON')
    sp_orphans.add_argument('--output', help='Write report to file')
    sp_orphans.set_defaults(func=cmd_orphans)

    # --- compare ---
    sp_compare = subparsers.add_parser('compare', help='Compare two parsed DDR versions')
    sp_compare.add_argument('before_dir', help='Path to "before" parsed DDR')
    sp_compare.add_argument('after_dir', help='Path to "after" parsed DDR')
    sp_compare.add_argument('--json', action='store_true', help='Output as JSON')
    sp_compare.add_argument('--output', help='Write report to file')
    sp_compare.set_defaults(func=cmd_compare)

    # --- search ---
    sp_search = subparsers.add_parser('search', help='Free-text search across DDR')
    sp_search.add_argument('parsed_dir', nargs='?', help='Path to parsed DDR directory')
    sp_search.add_argument('term', help='Search term or regex pattern')
    sp_search.add_argument('--case-sensitive', action='store_true', help='Match case exactly')
    sp_search.add_argument('--regex', action='store_true', help='Treat term as regex')
    sp_search.add_argument('--type', default='all',
                           choices=['all', 'calcs', 'scripts', 'layouts', 'valuelists', 'customfunctions'],
                           help='Limit search to specific object types')
    sp_search.add_argument('--project', help='Project name (shorthand for projects/<name>/parsed/)')
    sp_search.add_argument('--json', action='store_true', help='Output as JSON')
    sp_search.add_argument('--output', help='Write report to file')
    sp_search.set_defaults(func=cmd_search)

    # --- summary ---
    sp_summary = subparsers.add_parser('summary', help='Generate database overview')
    sp_summary.add_argument('parsed_dir', nargs='?', help='Path to parsed DDR directory')
    sp_summary.add_argument('--project', help='Project name (shorthand for projects/<name>/parsed/)')
    sp_summary.add_argument('--json', action='store_true', help='Output as JSON')
    sp_summary.add_argument('--output', help='Write report to file')
    sp_summary.set_defaults(func=cmd_summary)

    # --- readable (agent knowledge base) ---
    sp_readable = subparsers.add_parser('readable', help='Export an agent-facing Markdown knowledge base for the script-XML round-trip')
    sp_readable.add_argument('parsed_dir', nargs='?', help='Path to parsed DDR directory')
    sp_readable.add_argument('--project', help='Project name (shorthand for projects/<name>/parsed/)')
    sp_readable.add_argument('--output-dir', help='Output dir (default: <parsed>/../readable)')
    sp_readable.add_argument('--db', help='Only export this database (name as in _metadata.json)')
    sp_readable.add_argument('--json', action='store_true', help='Output as JSON')
    sp_readable.set_defaults(func=cmd_readable)

    args = parser.parse_args()

    try:
        result = args.func(args)
        if args.json and isinstance(result, dict):
            output_result(result, 'json', getattr(args, 'output', None))
    except FileNotFoundError as e:
        error = {"status": "fatal", "error": {"type": "not_found", "message": str(e)}}
        print(json.dumps(error, indent=2))
        sys.exit(1)
    except Exception as e:
        error = {"status": "fatal", "error": {"type": "unexpected", "message": str(e)}}
        print(json.dumps(error, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
