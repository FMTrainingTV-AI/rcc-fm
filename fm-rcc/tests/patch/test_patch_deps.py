"""Dependency-aware patch-review selection.

gen_patch.dependency_graph derives, for each selectable 'added' diff item, the
other added items it references (so the review UI can auto-include them on tick).
make_review embeds that graph and closes the selection in the browser.
"""
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))
import gen_patch as G
import make_review as M

# DEV/PROD covering the dependency shapes that matter:
#  - a new SCRIPT whose step references a new FIELD          (script -> field)
#  - a new FIELD on a table that already exists in prod      (no dep)
#  - a new FIELD on a NEW table                              (field -> base_table)
#  - a new TABLE OCCURRENCE on a new base table              (TO -> base_table)
#  - the new base table itself                               (no dep)
DEV = '''<?xml version="1.0" encoding="UTF-8"?>
<FMSaveAsXML version="2.3.0.0" Source="26.0.1" File="dev"><Structure><AddAction>
 <BaseTableCatalog membercount="2"><UUID>CAT-BT</UUID>
  <BaseTable id="10" name="T"><UUID>DEV-T</UUID><TagList/></BaseTable>
  <BaseTable id="11" name="N"><UUID>DEV-N</UUID><TagList/></BaseTable>
 </BaseTableCatalog>
 <FieldsForTables>
  <FieldCatalog><UUID>CAT-F-T</UUID>
   <BaseTableReference id="10" name="T" UUID="DEV-T"/>
   <ObjectList membercount="2">
    <Field id="1" name="Existing" fieldtype="Normal" datatype="Text"><UUID>DEV-F-EX</UUID></Field>
    <Field id="2" name="NewField" fieldtype="Normal" datatype="Text"><UUID>DEV-F-NEW</UUID></Field>
   </ObjectList></FieldCatalog>
  <FieldCatalog><UUID>CAT-F-N</UUID>
   <BaseTableReference id="11" name="N" UUID="DEV-N"/>
   <ObjectList membercount="1">
    <Field id="1" name="NField" fieldtype="Normal" datatype="Text"><UUID>DEV-F-NF</UUID></Field>
   </ObjectList></FieldCatalog>
 </FieldsForTables>
 <TableOccurrenceCatalog membercount="1"><UUID>CAT-TO</UUID>
  <TableOccurrence id="50" name="N_occ" type="Local"><UUID>DEV-TO-N</UUID>
   <BaseTableSourceReference><BaseTableReference id="11" name="N" UUID="DEV-N"/></BaseTableSourceReference>
  </TableOccurrence>
 </TableOccurrenceCatalog>
 <ScriptCatalog membercount="2"><UUID>CAT-S</UUID>
  <Script id="3" name="Other"><UUID>DEV-S-OTHER</UUID><Options hidden="False">2</Options><TagList/></Script>
  <Script id="4" name="Doer"><UUID>DEV-S-DOER</UUID><Options hidden="False">2</Options><TagList/></Script>
 </ScriptCatalog>
 <StepsForScripts>
  <Script><ScriptReference id="4" name="Doer" UUID="DEV-S-DOER"/>
   <ObjectList membercount="1">
    <Step index="1" name="Set Field">
     <FieldReference id="2" name="NewField" UUID="DEV-F-NEW"/>
    </Step>
   </ObjectList></Script>
 </StepsForScripts>
</AddAction></Structure></FMSaveAsXML>'''

PROD = '''<?xml version="1.0" encoding="UTF-8"?>
<FMSaveAsXML version="2.3.0.0" Source="26.0.1" File="prod"><Structure><AddAction>
 <BaseTableCatalog membercount="1"><UUID>P-CAT-BT</UUID>
  <BaseTable id="200" name="T"><UUID>PROD-T</UUID><TagList/></BaseTable>
 </BaseTableCatalog>
 <FieldsForTables>
  <FieldCatalog><UUID>P-CAT-F</UUID>
   <BaseTableReference id="200" name="T" UUID="PROD-T"/>
   <ObjectList membercount="1">
    <Field id="1" name="Existing" fieldtype="Normal" datatype="Text"><UUID>PROD-F-EX</UUID></Field>
   </ObjectList></FieldCatalog>
 </FieldsForTables>
 <ScriptCatalog membercount="1"><UUID>P-CAT-S</UUID>
  <Script id="9" name="Other"><UUID>PROD-S-OTHER</UUID><Options hidden="False">2</Options><TagList/></Script>
 </ScriptCatalog>
</AddAction></Structure></FMSaveAsXML>'''

DIFF = {"meta": {}, "items": [
    {"key": "base_table:N", "kind": "base_table", "change": "added", "patchability": "proven"},
    {"key": "field:T::NewField", "kind": "field", "change": "added", "patchability": "proven"},
    {"key": "field:N::NField", "kind": "field", "change": "added", "patchability": "proven"},
    {"key": "table_occurrence:N_occ", "kind": "table_occurrence", "change": "added", "patchability": "proven"},
    {"key": "script:Doer", "kind": "script", "change": "added", "patchability": "caution"},
]}


def _graph():
    dev = etree.fromstring(DEV.encode())
    prod = etree.fromstring(PROD.encode())
    return G.dependency_graph(dev, prod, DIFF)


def test_script_pulls_in_the_field_it_calls():
    # The headline case: tick a script, the new field its step references comes too.
    assert _graph()["script:Doer"] == ["field:T::NewField"]


def test_field_on_existing_table_has_no_deps():
    assert _graph()["field:T::NewField"] == []


def test_field_on_new_table_depends_on_that_table():
    assert _graph()["field:N::NField"] == ["base_table:N"]


def test_table_occurrence_depends_on_its_base_table():
    assert _graph()["table_occurrence:N_occ"] == ["base_table:N"]


def test_base_table_has_no_deps():
    assert _graph()["base_table:N"] == []


def test_graph_only_points_at_selectable_added_items():
    g = _graph()
    keys = {i["key"] for i in DIFF["items"]}
    for src, targets in g.items():
        for t in targets:
            assert t in keys and t != src


def test_manual_items_excluded_from_graph():
    # A manual-tier or ignored added item never appears as a graph node.
    diff = {"meta": {}, "items": DIFF["items"] + [
        {"key": "script:Hand", "kind": "script", "change": "added", "patchability": "manual"},
        {"key": "script:Ign", "kind": "script", "change": "added", "patchability": "caution", "ignored": True},
    ]}
    dev = etree.fromstring(DEV.encode())
    prod = etree.fromstring(PROD.encode())
    g = G.dependency_graph(dev, prod, diff)
    assert "script:Hand" not in g
    assert "script:Ign" not in g


# ── make_review wiring ────────────────────────────────────────────────────────

def test_make_review_embeds_the_dependency_graph():
    html = M.build_html(DIFF, {"script:Doer": ["field:T::NewField"]})
    assert '"script:Doer"' in html and '"field:T::NewField"' in html
    assert "const DEPS = {" in html
    # the closure machinery is present
    assert "depClosure" in html and "auto-dep" in html and "manualSel" in html


def test_make_review_deps_default_to_empty():
    html = M.build_html({"meta": {}, "items": []})
    assert "const DEPS = {};" in html
