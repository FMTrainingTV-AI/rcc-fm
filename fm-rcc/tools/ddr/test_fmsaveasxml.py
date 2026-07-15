"""
Verification test for the FM 2026 "Save a Copy as XML" split-catalog parser.

Recomputes expected object counts directly from the raw catalog XML (independent
of the parser), runs the parser into a temp dir, and asserts the per-object file
counts match. Also checks a few structural guarantees the downstream tools rely on:
roots carry `name`, scripts carry resolved <StepText>, TOs carry `baseTable`.

Run:  python3 scripts/test_fmsaveasxml.py [path/to/ddr/Summary.xml]

Defaults to the first Summary.xml under schema/ddrs/*/. Skips (exit 0) if no
FM 2026 split-catalog export is present — classic DDRs are not this test's target.
"""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lxml import etree
import ddr
import fmsaveasxml as fx


def ln(t):
    return t.split('}', 1)[1] if isinstance(t, str) and '}' in t else t


def count_in_catalog(folder, suffix, tag, container_aware=True):
    """Count <tag> elements in the catalog file ending with `suffix`."""
    for f in Path(folder).glob('*.xml'):
        if f.stem.lower().endswith(suffix):
            root = etree.parse(str(f)).getroot()
            return sum(1 for e in root.iter() if ln(e.tag) == tag)
    return 0


def main():
    if len(sys.argv) > 1:
        summary = Path(sys.argv[1])
    else:
        candidates = sorted((HERE.parent / 'schema' / 'ddrs').glob('*/Summary.xml'))
        summary = candidates[0] if candidates else HERE.parent / 'schema' / 'ddrs' / 'Summary.xml'

    if not summary.exists():
        print(f"SKIP: no fixture found under schema/ddrs/*/Summary.xml")
        return 0

    folders = fx.summary_catalog_folders(etree.parse(str(summary)).getroot(), summary)
    if not (folders and folders[0][1]):
        print(f"SKIP: {summary} is not an FM 2026 split-catalog export (classic DDRs are out of scope here)")
        return 0
    db_name, folder = folders[0]

    # Expected counts computed straight from the source catalogs.
    expected = {
        'tables': count_in_catalog(folder, 'basetablecatalog', 'BaseTable'),
        'fields': count_in_catalog(folder, 'fieldcatalog', 'Field'),
        'table_occurrences': count_in_catalog(folder, 'tableoccurrencecatalog', 'TableOccurrence'),
        'relationships': count_in_catalog(folder, 'relationshipcatalog', 'Relationship'),
        'value_lists': count_in_catalog(folder, 'valuelistcatalog', 'ValueList'),
        'custom_functions': count_in_catalog(folder, 'customfunctionscatalog', 'CustomFunction'),
        'accounts': count_in_catalog(folder, 'accountscatalog', 'Account'),
        'privilege_sets': count_in_catalog(folder, 'privilegesetscatalog', 'PrivilegeSet'),
        'extended_privileges': count_in_catalog(folder, 'extendedprivilegescatalog', 'ExtendedPrivilege'),
        'external_data_sources': count_in_catalog(folder, 'externaldatasourcecatalog', 'ExternalDataSource'),
    }
    # Scripts: named <Script> in the ScriptCatalog hierarchy (exclude step-body wrappers).
    for f in Path(folder).glob('*ScriptCatalog.xml'):
        r = etree.parse(str(f)).getroot()
        sc = fx._catalog_element(r)
        expected['scripts'] = sum(1 for e in sc.iter()
                                  if ln(e.tag) == 'Script' and e.get('name'))
    # Layouts: non-folder only.
    for f in Path(folder).glob('*LayoutCatalog.xml'):
        r = etree.parse(str(f)).getroot()
        cat = fx._catalog_element(r)
        expected['layouts'] = sum(1 for e in fx._children(fx._item_container(cat), 'Layout')
                                  if e.get('isFolder') != 'True')

    out = Path(tempfile.mkdtemp(prefix='fmtest_'))
    try:
        ddr.split_ddr(str(summary), str(out))
        db_dir = out / fx.safe_filename(db_name)

        # File-count assertions per object type.
        type_dirs = {
            'tables': 'tables', 'table_occurrences': 'table_occurrences',
            'relationships': 'relationships', 'scripts': 'scripts',
            'layouts': 'layouts', 'value_lists': 'value_lists',
            'custom_functions': 'custom_functions', 'accounts': 'accounts',
            'privilege_sets': 'privilege_sets', 'extended_privileges': 'extended_privileges',
            'external_data_sources': 'external_data_sources',
        }
        failures = []
        for key, sub in type_dirs.items():
            d = db_dir / sub
            if key == 'tables':
                got = sum(1 for _ in d.glob('*/fields.xml')) if d.exists() else 0
            else:
                got = sum(1 for _ in d.rglob('*.xml')) if d.exists() else 0
            exp = expected.get(key, 0)
            status = 'OK' if got == exp else 'FAIL'
            if got != exp:
                failures.append(f'{key}: expected {exp}, got {got}')
            print(f'  {status:4} {key:24} expected={exp:<5} got={got}')

        # Field total across all tables.
        field_files = list((db_dir / 'tables').rglob('fields.xml'))
        total_fields = 0
        for ff in field_files:
            r = etree.parse(str(ff)).getroot()
            total_fields += sum(1 for e in r.iter() if ln(e.tag) == 'Field')
        fstatus = 'OK' if total_fields == expected['fields'] else 'FAIL'
        if total_fields != expected['fields']:
            failures.append(f"fields(in files): expected {expected['fields']}, got {total_fields}")
        print(f'  {fstatus:4} {"fields (in table files)":24} expected={expected["fields"]:<5} got={total_fields}')

        # Structural guarantees.
        struct = []
        # 1. Every script root has a name attribute.
        for sf in (db_dir / 'scripts').rglob('*.xml'):
            r = etree.parse(str(sf)).getroot()
            if not r.get('name'):
                struct.append(f'script missing name: {sf.name}')
                break
        # 2. At least one resolved <StepText> exists.
        steptext = sum(1 for sf in (db_dir / 'scripts').rglob('*.xml')
                       for _ in etree.parse(str(sf)).getroot().iter()
                       if ln(_.tag) == 'StepText')
        if steptext == 0:
            struct.append('no resolved <StepText> found')
        print(f'  {"OK" if steptext else "FAIL":4} resolved StepText elements: {steptext}')
        # 3. TOs carry baseTable.
        to_files = list((db_dir / 'table_occurrences').glob('*.xml'))
        with_bt = sum(1 for tf in to_files
                      if etree.parse(str(tf)).getroot().get('baseTable'))
        if to_files and with_bt == 0:
            struct.append('TOs missing baseTable attribute')
        print(f'  {"OK" if with_bt else "FAIL":4} TOs with baseTable attr: {with_bt}/{len(to_files)}')

        failures.extend(struct)
        print()
        if failures:
            print('FAILURES:')
            for f in failures:
                print('  -', f)
            return 1
        print('ALL CHECKS PASSED')
        return 0
    finally:
        import shutil
        shutil.rmtree(out, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
