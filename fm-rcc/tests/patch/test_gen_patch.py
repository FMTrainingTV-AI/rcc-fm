import sys
from pathlib import Path
import pytest
from lxml import etree
sys.path.insert(0, str(Path(__file__).parent.parent))
import gen_patch as G

DEV = '''<?xml version="1.0" encoding="UTF-8"?>
<FMSaveAsXML version="9.8.7.0" Source="26.0.1" File="dev"><Structure><AddAction>
 <BaseTableCatalog membercount="2"><UUID>CAT-BT-DEV</UUID>
  <BaseTable id="129" name="Shared"><UUID>DEV-SHARED</UUID><TagList/></BaseTable>
  <BaseTable id="130" name="NewTable"><UUID>DEV-NEW</UUID><TagList/></BaseTable>
 </BaseTableCatalog>
 <FieldsForTables>
  <FieldCatalog><UUID>CAT-F-DEV-S</UUID>
   <BaseTableReference id="129" name="Shared" UUID="DEV-SHARED"/>
   <ObjectList membercount="1">
    <Field id="1" name="Old" fieldtype="Calculated" datatype="Text"><UUID>DEV-F-OLD</UUID>
     <Calculation><TableOccurrenceReference id="1065089" name="Shared" UUID="DEV-TO-SHARED"/>
      <Text>1 + 1</Text></Calculation></Field>
   </ObjectList></FieldCatalog>
  <FieldCatalog><UUID>CAT-F-DEV-N</UUID>
   <BaseTableReference id="130" name="NewTable" UUID="DEV-NEW"/>
   <ObjectList membercount="2">
    <Field id="1" name="Title" fieldtype="Normal" datatype="Text"><UUID>DEV-F-TITLE</UUID></Field>
    <Field id="2" name="AutoFull" fieldtype="Normal" datatype="Text"><UUID>DEV-F-AUTOFULL</UUID>
     <AutoEnter type="Calculated"><Calculated><Calculation>
      <TableOccurrenceReference id="1065090" name="NewTable" UUID="DEV-TO-NEW"/>
      <Text>Title &amp; "!"</Text></Calculation></Calculated></AutoEnter></Field>
   </ObjectList></FieldCatalog>
 </FieldsForTables>
 <TableOccurrenceCatalog membercount="2"><UUID>CAT-TO-DEV</UUID>
  <TableOccurrence id="1065089" name="Shared" type="Local"><UUID>DEV-TO-SHARED</UUID>
   <BaseTableSourceReference><BaseTableReference id="129" name="Shared" UUID="DEV-SHARED"/></BaseTableSourceReference>
  </TableOccurrence>
  <TableOccurrence id="1065090" name="NewTable" type="Local"><UUID>DEV-TO-NEW</UUID>
   <BaseTableSourceReference><BaseTableReference id="130" name="NewTable" UUID="DEV-NEW"/></BaseTableSourceReference>
   <DDRREF>cruft</DDRREF>
  </TableOccurrence>
 </TableOccurrenceCatalog>
 <ScriptCatalog membercount="1"><UUID>CAT-S-DEV</UUID>
  <Script id="3" name="Doer"><UUID>DEV-S-DOER</UUID><Options hidden="False">2</Options><TagList/></Script>
 </ScriptCatalog>
</AddAction></Structure></FMSaveAsXML>'''

PROD = '''<?xml version="1.0" encoding="UTF-8"?>
<FMSaveAsXML version="2.3.0.0" Source="26.0.1" File="prod"><Structure><AddAction>
 <BaseTableCatalog membercount="1"><UUID>CAT-BT-PROD</UUID>
  <BaseTable id="200" name="Shared"><UUID>PROD-SHARED</UUID><TagList/></BaseTable>
 </BaseTableCatalog>
 <FieldsForTables>
  <FieldCatalog><UUID>CAT-F-PROD-S</UUID>
   <BaseTableReference id="200" name="Shared" UUID="PROD-SHARED"/>
   <ObjectList membercount="2">
    <Field id="1" name="Old" fieldtype="Normal" datatype="Text"><UUID>PROD-F-OLD</UUID></Field>
    <Field id="2" name="Doomed" fieldtype="Normal" datatype="Text"><UUID>PROD-F-DOOMED</UUID></Field>
   </ObjectList></FieldCatalog>
 </FieldsForTables>
 <TableOccurrenceCatalog membercount="1"><UUID>CAT-TO-PROD</UUID>
  <TableOccurrence id="1065089" name="Shared" type="Local"><UUID>PROD-TO-SHARED</UUID>
   <BaseTableSourceReference><BaseTableReference id="200" name="Shared" UUID="PROD-SHARED"/></BaseTableSourceReference>
  </TableOccurrence>
 </TableOccurrenceCatalog>
 <ScriptCatalog membercount="2"><UUID>CAT-S-PROD</UUID>
  <Script id="9" name="Doer"><UUID>PROD-S-DOER</UUID><Options hidden="True">2</Options><TagList/></Script>
  <Script id="10" name="Gone"><UUID>PROD-S-GONE</UUID><Options hidden="False">2</Options><TagList/></Script>
 </ScriptCatalog>
</AddAction></Structure></FMSaveAsXML>'''

def _builder():
    dev = etree.fromstring(DEV.encode()); prod = etree.fromstring(PROD.encode())
    diff = {"items": [
        {"key": "base_table:NewTable", "kind": "base_table", "change": "added"},
        {"key": "field:NewTable::Title", "kind": "field", "change": "added"},
        {"key": "table_occurrence:NewTable", "kind": "table_occurrence", "change": "added"}]}
    return G.PatchBuilder(dev, prod, diff)

def test_addaction_table_with_fields_and_to():
    patch = _builder().build(["base_table:NewTable", "field:NewTable::Title",
                              "table_occurrence:NewTable"])
    # Sentinel version: proves the value is read from the dev export rather
    # than hardcoded (FMUpgradeTool accepts mismatched versions silently, so
    # only a unit assertion can catch a hardcode regression).
    assert patch.tag == "FMUpgradeToolPatch" and patch.get("version") == "9.8.7.0"
    xml = etree.tostring(patch).decode()
    assert "DDRREF" not in xml
    assert "DEV-NEW" not in xml and "DEV-TO-NEW" not in xml      # fresh UUIDs assigned
    bt = patch.find(".//BaseTableCatalog")
    assert bt.find("UUID").text == "CAT-BT-PROD"                  # prod catalog UUID reused
    new_bt = bt.find("BaseTable")
    assert new_bt.get("name") == "NewTable" and new_bt.get("id") == "201"  # prod max 200 + 1
    fc_ref = patch.find(".//FieldCatalog/BaseTableReference[@name='NewTable']")
    assert fc_ref.get("UUID") == new_bt.find("UUID").text
    add = patch.find(".//AddAction")
    tags = [c.tag for c in add]
    assert tags == ["BaseTableCatalog", "FieldsForTables", "TableOccurrenceCatalog"]

def test_dependency_error_when_to_selected_without_table():
    with pytest.raises(G.DependencyError) as e:
        _builder().build(["table_occurrence:NewTable"])
    assert any("NewTable" in p for p in e.value.problems)

def test_shared_reference_remapped_to_prod():
    patch = _builder().build(["base_table:NewTable", "field:NewTable::Title",
                              "table_occurrence:NewTable"])
    xml = etree.tostring(patch).decode()
    assert "DEV-SHARED" not in xml   # any shared refs must use PROD-SHARED

def test_caution_items_rejected_without_flag():
    b = _builder()
    b.diff["items"].append({"key": "field:Shared::Old", "kind": "field", "change": "modified"})
    with pytest.raises(ValueError):
        b.build(["field:Shared::Old"])

# --- Task 6: ReplaceAction / DeleteAction behind allow_caution ----------------

def _builder_caution():
    b = _builder()
    b.diff["items"] += [
        {"key": "field:Shared::Old", "kind": "field", "change": "modified"},
        {"key": "script:Doer", "kind": "script", "change": "modified"},
        {"key": "field:Shared::Doomed", "kind": "field", "change": "removed"},
        {"key": "script:Gone", "kind": "script", "change": "removed"}]
    return b

def test_replace_modified_field():
    patch = _builder_caution().build(["field:Shared::Old"], allow_caution=True)
    xml = etree.tostring(patch).decode()
    rep = patch.find("Structure/ReplaceAction/Replace")
    assert rep.get("type") == "Field" and rep.get("UUID") == "PROD-F-OLD"
    btref = rep.find("BaseTableReference")           # parent reference per official docs
    assert (btref.get("id"), btref.get("name"), btref.get("UUID")) == ("200", "Shared", "PROD-SHARED")
    fld = rep.find("Field")                          # full replacement object
    assert fld.get("name") == "Old" and fld.get("id") == "1"        # prod id
    assert fld.find("UUID").text == "PROD-F-OLD"                    # prod identity
    assert fld.get("fieldtype") == "Calculated"                     # dev content won
    tor = fld.find("Calculation/TableOccurrenceReference")
    assert tor.get("UUID") == "PROD-TO-SHARED"                      # internal refs remapped
    assert "DEV-" not in xml
    # calc field replaced -> ModifyAction re-apply stub, last in Structure
    structure = patch.find("Structure")
    assert [c.tag for c in structure] == ["ReplaceAction", "ModifyAction"]
    fr = structure.find("ModifyAction/FieldsForTables/FieldCatalog/ObjectList/Field/FieldReference")
    assert fr.get("name") == "Old" and fr.get("UUID") == "PROD-F-OLD" and fr.get("id") == "1"
    assert fr.find("Calculation/Text").text == "1 + 1"

def test_replace_modified_script():
    patch = _builder_caution().build(["script:Doer"], allow_caution=True)
    rep = patch.find("Structure/ReplaceAction/Replace")
    assert rep.get("type") == "Script" and rep.get("UUID") == "PROD-S-DOER"
    cat = rep.find("CatalogReference")               # parent of a Script is its catalog
    assert cat.get("catalogName") == "ScriptCatalog" and cat.get("uuid") == "CAT-S-PROD"
    s = rep.find("Script")
    assert s.get("name") == "Doer" and s.get("id") == "9"           # prod id
    assert s.find("UUID").text == "PROD-S-DOER"                     # prod identity
    assert s.find("Options").get("hidden") == "False"               # dev content won
    assert "DEV-" not in etree.tostring(patch).decode()

def test_delete_removed_items():
    patch = _builder_caution().build(["field:Shared::Doomed", "script:Gone"],
                                     allow_caution=True)
    irs = patch.findall("Structure/DeleteAction/ItemReference")
    assert len(irs) == 2
    fld_ir = next(i for i in irs if i.get("type") == "FieldReference")
    assert fld_ir.get("UUID") == "PROD-F-DOOMED"
    btref = fld_ir.find("BaseTableReference")        # FieldReference requires table parent
    assert (btref.get("id"), btref.get("UUID")) == ("200", "PROD-SHARED")
    s_ir = next(i for i in irs if i.get("type") == "ScriptReference")
    assert s_ir.get("UUID") == "PROD-S-GONE" and len(s_ir) == 0  # no parent child needed

def test_caution_without_flag_lists_offending_keys():
    b = _builder_caution()
    with pytest.raises(ValueError) as e:
        b.build(["field:Shared::Old", "field:Shared::Doomed"])
    assert "field:Shared::Old" in str(e.value) and "field:Shared::Doomed" in str(e.value)

def test_modified_unsupported_kind_rejected_even_with_flag():
    b = _builder_caution()
    b.diff["items"].append({"key": "layout:Main", "kind": "layout", "change": "modified"})
    with pytest.raises(ValueError) as e:
        b.build(["layout:Main"], allow_caution=True)
    assert "layout" in str(e.value)

def test_removed_unsupported_kind_rejected_even_with_flag():
    b = _builder_caution()
    b.diff["items"].append({"key": "relationship:A|B|x=y", "kind": "relationship",
                            "change": "removed"})
    with pytest.raises(ValueError) as e:
        b.build(["relationship:A|B|x=y"], allow_caution=True)
    assert "relationship" in str(e.value)

def test_mixed_selection_action_order():
    """Structure order: AddAction, ReplaceAction(s), DeleteAction(s), ModifyAction."""
    patch = _builder_caution().build(
        ["base_table:NewTable", "field:NewTable::Title", "table_occurrence:NewTable",
         "field:Shared::Old", "field:Shared::Doomed"], allow_caution=True)
    tags = [c.tag for c in patch.find("Structure")]
    assert tags == ["AddAction", "ReplaceAction", "DeleteAction", "ModifyAction"]

# --- additional coverage (beyond the spec-verbatim tests above) --------------

def test_calc_field_gets_modify_action_reapply_stub():
    """Calc formulas get a Structure/ModifyAction re-apply pass (FMUpgradeTool
    comments formulas out when their context TO is a forward reference)."""
    dev = DEV.replace(
        '<Field id="1" name="Title" fieldtype="Normal" datatype="Text"><UUID>DEV-F-TITLE</UUID></Field>',
        '<Field id="1" name="Title" fieldtype="Normal" datatype="Text"><UUID>DEV-F-TITLE</UUID></Field>'
        '<Field id="2" name="Total" fieldtype="Calculated" datatype="Number"><UUID>DEV-F-TOTAL</UUID>'
        '<Calculation><TableOccurrenceReference id="1065090" name="NewTable" UUID="DEV-TO-NEW"/>'
        '<Text>1 + 1</Text></Calculation></Field>')
    dev = dev.replace('<ObjectList membercount="1">\n    <Field id="1" name="Title"',
                      '<ObjectList membercount="2">\n    <Field id="1" name="Title"')
    diff = {"items": [
        {"key": "base_table:NewTable", "kind": "base_table", "change": "added"},
        {"key": "field:NewTable::Title", "kind": "field", "change": "added"},
        {"key": "field:NewTable::Total", "kind": "field", "change": "added"},
        {"key": "table_occurrence:NewTable", "kind": "table_occurrence", "change": "added"}]}
    b = G.PatchBuilder(etree.fromstring(dev.encode()), etree.fromstring(PROD.encode()), diff)
    patch = b.build([i["key"] for i in diff["items"]])
    ma = patch.find("Structure/ModifyAction")
    assert ma is not None
    fr = ma.find(".//FieldReference[@name='Total']")
    assert fr is not None and fr.get("id") == "2"
    new_to = patch.find(".//TableOccurrenceCatalog/TableOccurrence[@name='NewTable']")
    tor = fr.find("Calculation/TableOccurrenceReference")
    assert tor.get("UUID") == new_to.find("UUID").text       # remapped to fresh TO uuid
    assert fr.find("Calculation/Text").text == "1 + 1"
    assert "DEV-TO-NEW" not in etree.tostring(patch).decode()
    # AddAction without calc fields -> no ModifyAction at all
    p2 = _builder().build(["base_table:NewTable", "field:NewTable::Title",
                           "table_occurrence:NewTable"])
    assert p2.find("Structure/ModifyAction") is None


def test_unknown_and_ignored_selections_rejected():
    b = _builder()
    with pytest.raises(ValueError):
        b.build(["base_table:Nonexistent"])
    # Discriminating ignored case: the key EXISTS in the dev export, so only
    # the ignored guard itself can reject it (mutation-proof — a "not found"
    # error can't mask a deleted guard).
    b2 = _builder()
    for it in b2.diff["items"]:
        if it["key"] == "base_table:NewTable":
            it["ignored"] = True
    with pytest.raises(ValueError, match="ignored"):
        b2.build(["base_table:NewTable"])


def test_duplicate_name_and_manual_selections_rejected():
    b = _builder()
    for it in b.diff["items"]:
        if it["key"] == "base_table:NewTable":
            it["duplicate_name"] = True
    with pytest.raises(ValueError, match="duplicate"):
        b.build(["base_table:NewTable"])
    b2 = _builder()
    for it in b2.diff["items"]:
        if it["key"] == "base_table:NewTable":
            it["patchability"] = "manual"
    with pytest.raises(ValueError, match="manual"):
        b2.build(["base_table:NewTable"])


def test_auto_enter_calc_gets_modify_stub():
    """Auto-enter calc formulas referencing fields by name get silently
    commented out by FMUpgradeTool without a ModifyAction re-apply stub —
    the stub must carry the AutoEnter element (proven shape, 2026-06-12)."""
    b = _builder()
    b.diff["items"].append(
        {"key": "field:NewTable::AutoFull", "kind": "field", "change": "added"})
    patch = b.build(["base_table:NewTable", "field:NewTable::Title",
                     "field:NewTable::AutoFull", "table_occurrence:NewTable"])
    stubs = patch.findall(".//ModifyAction/FieldsForTables/FieldCatalog")
    autofull = [s for s in stubs
                if s.find("ObjectList/Field/FieldReference") is not None
                and s.find("ObjectList/Field/FieldReference").get("name") == "AutoFull"]
    assert autofull, "AutoFull needs a ModifyAction re-apply stub"
    assert autofull[0].find("ObjectList/Field/FieldReference/AutoEnter") is not None


def test_replace_preserves_prod_serial_counter():
    """A field Replace must keep PROD's serial nextvalue (per-instance state);
    shipping dev's stale counter mints duplicate serials and the hash strips
    nextvalue, so even the verify oracle can't see it."""
    dev = etree.fromstring(DEV.replace(
        '<Field id="1" name="Old" fieldtype="Calculated" datatype="Text"><UUID>DEV-F-OLD</UUID>\n'
        '     <Calculation><TableOccurrenceReference id="1065089" name="Shared" UUID="DEV-TO-SHARED"/>\n'
        '      <Text>1 + 1</Text></Calculation></Field>',
        '<Field id="1" name="Old" fieldtype="Normal" datatype="Number" comment="edited"><UUID>DEV-F-OLD</UUID>'
        '<AutoEnter type="SerialNumber"><SerialNumber nextvalue="5" increment="1"/></AutoEnter></Field>').encode())
    prod = etree.fromstring(PROD.replace(
        '<Field id="1" name="Old" fieldtype="Normal" datatype="Text"><UUID>PROD-F-OLD</UUID></Field>',
        '<Field id="1" name="Old" fieldtype="Normal" datatype="Number"><UUID>PROD-F-OLD</UUID>'
        '<AutoEnter type="SerialNumber"><SerialNumber nextvalue="100" increment="1"/></AutoEnter></Field>').encode())
    diff = {"items": [{"key": "field:Shared::Old", "kind": "field", "change": "modified"}]}
    patch = G.PatchBuilder(dev, prod, diff).build(["field:Shared::Old"], allow_caution=True)
    sn = patch.find(".//Replace/Field/AutoEnter/SerialNumber")
    assert sn is not None and sn.get("nextvalue") == "100"


def test_modifyaction_stubs_in_dev_export_do_not_shadow_real_catalogs():
    """Real exports carry Structure/ModifyAction calc-stub FieldCatalogs;
    indexing must scope to Structure/AddAction or the stubs shadow the real
    per-table catalogs and the patch ships empty field lists."""
    shadowed = DEV.replace(
        "</AddAction></Structure>",
        '</AddAction><ModifyAction><FieldsForTables membercount="1">'
        '<FieldCatalog><BaseTableReference id="130" name="NewTable" UUID="DEV-NEW"/>'
        '<ObjectList membercount="1"><Field><FieldReference id="1" name="Title"/>'
        "</Field></ObjectList></FieldCatalog></FieldsForTables></ModifyAction></Structure>")
    dev = etree.fromstring(shadowed.encode())
    prod = etree.fromstring(PROD.encode())
    diff = {"items": [
        {"key": "base_table:NewTable", "kind": "base_table", "change": "added"},
        {"key": "field:NewTable::Title", "kind": "field", "change": "added"},
        {"key": "table_occurrence:NewTable", "kind": "table_occurrence", "change": "added"}]}
    patch = G.PatchBuilder(dev, prod, diff).build(
        ["base_table:NewTable", "field:NewTable::Title", "table_occurrence:NewTable"])
    add_fields = [f for f in patch.findall(".//AddAction//FieldCatalog/ObjectList/Field")
                  if f.get("name") == "Title"]
    assert add_fields, "real (named) field definition must come from AddAction catalogs, not stubs"


def test_harvest_mismatch_guard_fires(monkeypatch):
    """The fields self-check must hard-fail when fewer definitions are
    harvested than selected ('Patch File Applied' prints even on no-ops)."""
    def gut(self, fc, tn, selected):
        ol = fc.find("ObjectList")
        if ol is not None:
            for ch in list(ol):
                ol.remove(ch)
    monkeypatch.setattr(G.PatchBuilder, "_prune_fieldcatalog", gut)
    with pytest.raises(RuntimeError, match="harvest mismatch"):
        _builder().build(["base_table:NewTable", "field:NewTable::Title",
                          "table_occurrence:NewTable"])


import shutil, subprocess, json
SB = Path(__file__).parent.parent.parent / "sandbox"

@pytest.mark.skipif(not ((SB / "prod.xml").exists() and (SB / "prod.fmp12").exists()),
                    reason="sandbox fixtures not built")
def test_real_replace_delete_patch_validates_and_applies(tmp_path):
    """Structural smoke for ReplaceAction/DeleteAction against the real tool.

    The sandbox diff is purely additive, so we synthesize caution items by
    treating prod as BOTH dev and prod: a self-identical Replace of
    Accounts::Name (plain), Accounts::RecordID (calc -> exercises the
    ModifyAction re-apply stub), and the get_script_names script (exercises
    the CatalogReference parent), plus a Delete of Accounts::Website.
    --validatePatch and --update both exiting 0 proves FMUpgradeTool accepts
    our Replace/Delete shapes and the Add->Replace->Delete->Modify ordering.
    This validates STRUCTURE, not semantics — a self-identical replace can't
    show a content change; real dev/prod divergence testing comes later.
    (The Delete WAS semantically verified by hand on 2026-06-11: re-export of
    the patched copy showed Accounts::Website gone.)"""
    diff = {"items": [
        {"key": "field:Accounts::Name", "kind": "field", "change": "modified"},
        {"key": "field:Accounts::RecordID", "kind": "field", "change": "modified"},
        {"key": "script:get_script_names", "kind": "script", "change": "modified"},
        {"key": "field:Accounts::Website", "kind": "field", "change": "removed"}]}
    diff_p = tmp_path / "diff.json"
    diff_p.write_text(json.dumps(diff))
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"selected": [i["key"] for i in diff["items"]]}))
    out = tmp_path / "patch.xml"
    G.generate(SB / "prod.xml", SB / "prod.xml", diff_p, sel, out, allow_caution=True)
    xml = out.read_text()
    assert "<ReplaceAction>" in xml and "<DeleteAction>" in xml and "<ModifyAction" in xml
    work = tmp_path / "prod-copy.fmp12"
    shutil.copy2(SB / "prod.fmp12", work)
    r = subprocess.run(["/usr/local/bin/FMUpgradeTool", "--validatePatch",
                        "-src_path", str(work), "-patch_path", str(out),
                        "-src_account", "Admin"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run(["/usr/local/bin/FMUpgradeTool", "--update",
                        "-src_path", str(work), "-patch_path", str(out),
                        "-src_account", "Admin",
                        "-dest_path", str(tmp_path / "patched.fmp12")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "patched.fmp12").exists()


# --- Task 6.5: script step bodies ---------------------------------------------

def _steps_dev():
    """DEV plus a StepsForScripts body for script Doer (and an added script
    Newby with steps referencing the shared prod script Doer)."""
    return DEV.replace(
        '<Script id="3" name="Doer"><UUID>DEV-S-DOER</UUID><Options hidden="False">2</Options><TagList/></Script>\n'
        ' </ScriptCatalog>',
        '<Script id="3" name="Doer"><UUID>DEV-S-DOER</UUID><Options hidden="False">2</Options><TagList/></Script>\n'
        '  <Script id="4" name="Newby"><UUID>DEV-S-NEWBY</UUID><Options hidden="False">2</Options><TagList/></Script>\n'
        ' </ScriptCatalog>\n'
        ' <StepsForScripts membercount="2">\n'
        '  <Script><ScriptReference id="3" name="Doer" UUID="DEV-S-DOER"/>\n'
        '   <ObjectList membercount="1">\n'
        '    <Step hash="H1" index="0" id="89" name="# (comment)" enable="True"><UUID>DEV-ST-1</UUID>\n'
        '     <Options>0</Options></Step>\n'
        '   </ObjectList></Script>\n'
        '  <Script><ScriptReference id="4" name="Newby" UUID="DEV-S-NEWBY"/>\n'
        '   <ObjectList membercount="2">\n'
        '    <Step hash="H2" index="0" id="89" name="# (comment)" enable="True"><UUID>DEV-ST-2</UUID>\n'
        '     <Options>0</Options></Step>\n'
        '    <Step hash="H3" index="1" id="1" name="Perform Script" enable="True"><UUID>DEV-ST-3</UUID>\n'
        '     <Options>16450</Options><ParameterValues membercount="1">\n'
        '      <Parameter type="List"><List name="From list" value="1">\n'
        '       <ScriptReference id="3" name="Doer" UUID="DEV-S-DOER"/></List></Parameter>\n'
        '     </ParameterValues></Step>\n'
        '   </ObjectList></Script>\n'
        ' </StepsForScripts>')


def test_added_script_carries_steps_fragment():
    dev = etree.fromstring(_steps_dev().encode())
    prod = etree.fromstring(PROD.encode())
    diff = {"items": [{"key": "script:Newby", "kind": "script", "change": "added"}]}
    patch = G.PatchBuilder(dev, prod, diff).build(["script:Newby"])
    add = patch.find("Structure/AddAction")
    assert [c.tag for c in add] == ["ScriptCatalog", "StepsForScripts"]  # steps LAST
    sfs = add.find("StepsForScripts")
    assert sfs.get("membercount") == "1" and sfs.find("UUID") is None  # no catalog UUID
    new_uuid = add.find("ScriptCatalog/Script[@name='Newby']/UUID").text
    ref = sfs.find("Script/ScriptReference")
    # linking reference remapped to the NEW script's fresh identity (id 11 = prod max 10 + 1)
    assert ref.get("UUID") == new_uuid and ref.get("id") == "11" and ref.get("name") == "Newby"
    steps = sfs.findall("Script/ObjectList/Step")
    assert len(steps) == 2
    xml = etree.tostring(patch).decode()
    assert "DEV-ST-" not in xml and 'hash=' not in xml      # fresh step UUIDs, hash attrs stripped
    # step's Perform Script reference resolved to the SHARED prod script
    inner = sfs.find(".//List/ScriptReference")
    assert inner.get("UUID") == "PROD-S-DOER"


def test_added_script_without_steps_emits_no_fragment():
    patch = _builder().build([])  # no scripts selected at all
    assert patch.find("Structure/AddAction/StepsForScripts") is None
    # script with no StepsForScripts entry in dev (folder-like): no fragment either
    dev = etree.fromstring(DEV.encode())  # DEV has no StepsForScripts at all
    prod = etree.fromstring(PROD.encode())
    diff = {"items": [{"key": "script:Doer", "kind": "script", "change": "added"}]}
    # Doer is shared in PROD, but build from a prod lacking it
    prod_no_doer = PROD.replace(
        '<Script id="9" name="Doer"><UUID>PROD-S-DOER</UUID><Options hidden="True">2</Options><TagList/></Script>\n', '')
    patch = G.PatchBuilder(dev, etree.fromstring(prod_no_doer.encode()), diff).build(["script:Doer"])
    assert patch.find("Structure/AddAction/ScriptCatalog/Script") is not None
    assert patch.find("Structure/AddAction/StepsForScripts") is None


def test_modified_script_with_step_divergence_rejected():
    """ReplaceAction can't carry step bodies (no ObjectList allowed) — a script
    whose steps changed must NOT silently replace only the catalog entry."""
    dev = etree.fromstring(_steps_dev().encode())
    prod = etree.fromstring(PROD.encode())  # prod has NO steps for Doer -> divergent
    diff = {"items": [{"key": "script:Doer", "kind": "script", "change": "modified"}]}
    with pytest.raises(ValueError) as e:
        G.PatchBuilder(dev, prod, diff).build(["script:Doer"], allow_caution=True)
    assert "step bodies differ" in str(e.value)
    # identical steps on both sides -> options-only replace still allowed
    prod_steps = PROD.replace(
        '</AddAction>',
        ' <StepsForScripts membercount="1">\n'
        '  <Script><ScriptReference id="9" name="Doer" UUID="PROD-S-DOER"/>\n'
        '   <ObjectList membercount="1">\n'
        '    <Step hash="HX" index="0" id="89" name="# (comment)" enable="True"><UUID>PROD-ST-1</UUID>\n'
        '     <Options>0</Options></Step>\n'
        '   </ObjectList></Script>\n'
        ' </StepsForScripts>\n</AddAction>')
    patch = G.PatchBuilder(dev, etree.fromstring(prod_steps.encode()), diff).build(
        ["script:Doer"], allow_caution=True)
    rep = patch.find("Structure/ReplaceAction/Replace")
    assert rep.get("type") == "Script" and rep.get("UUID") == "PROD-S-DOER"


FMUPG = "/usr/local/bin/FMUpgradeTool"
FMDEV = "/usr/local/bin/FMDeveloperTool"
_RT_READY = (SB / "dev.xml").exists() and (SB / "prod.xml").exists() and \
    (SB / "prod.fmp12").exists() and Path(FMUPG).exists() and Path(FMDEV).exists()


@pytest.mark.skipif(not _RT_READY, reason="sandbox fixtures or FM CLI tools missing")
def test_script_steps_round_trip(tmp_path):
    """The Task 6.5 acceptance bar, end to end against the real tools:
    delete script get_script_names from a prod copy (DeleteAction), verify it
    is gone from BOTH ScriptCatalog and StepsForScripts; diff dev vs the
    script-less file (empty ignore list — the specimen is on the default
    ignore list); generate an AddAction patch for the added script; apply;
    re-export; assert the catalog entry AND step bodies landed: same parser
    _hash and step_count as dev (~30s, two FMUpgradeTool runs + two exports).

    First run 2026-06-12 surfaced FMUpgradeTool stamping an empty <OwnerID/>
    onto every patched-in step — now stripped by compute_hash like
    UUID/SourceUUID, or every patched script would diff as modified forever."""
    import saxml_parser as P
    import saxml_diff as D

    def run(*cmd):
        r = subprocess.run(list(cmd), capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        return r

    def export(fmp12, xml):
        run(FMDEV, "--saveAsXML", str(fmp12), "Admin", "", "-t", str(xml), "-f")
        return etree.parse(P.open_fmsavexml(xml)).getroot()

    # 1. DeleteAction: remove the specimen from a working copy
    work = tmp_path / "work.fmp12"
    shutil.copy2(SB / "prod.fmp12", work)
    (tmp_path / "diff1.json").write_text(json.dumps({"items": [
        {"key": "script:get_script_names", "kind": "script", "change": "removed"}]}))
    (tmp_path / "sel.json").write_text(json.dumps(
        {"selected": ["script:get_script_names"]}))
    G.generate(SB / "prod.xml", SB / "prod.xml", tmp_path / "diff1.json",
               tmp_path / "sel.json", tmp_path / "patch1.xml", allow_caution=True)
    run(FMUPG, "--update", "-src_path", str(work), "-patch_path",
        str(tmp_path / "patch1.xml"), "-src_account", "Admin",
        "-dest_path", str(tmp_path / "step1.fmp12"))
    step1 = export(tmp_path / "step1.fmp12", tmp_path / "step1.xml")
    assert "get_script_names" not in {s["name"] for s in P.parse_scripts(step1)}
    by_uuid, _ = P.script_steps_index(step1)
    assert "get_script_names" not in {
        e.find("ScriptReference").get("name") for e in by_uuid.values()}

    # 2. diff dev vs the script-less file -> specimen is ADDED
    P.snapshot(SB / "dev.xml", tmp_path / "dev_parsed")
    P.snapshot(tmp_path / "step1.xml", tmp_path / "step1_parsed")
    diff2 = D.diff_snapshots(tmp_path / "dev_parsed", tmp_path / "step1_parsed", {})
    item = next(i for i in diff2["items"] if i["key"] == "script:get_script_names")
    assert item["change"] == "added"
    (tmp_path / "diff2.json").write_text(json.dumps(diff2))

    # 3. AddAction patch (no allow_caution needed) -> apply -> re-export -> compare
    out = G.generate(SB / "dev.xml", tmp_path / "step1.xml", tmp_path / "diff2.json",
                     tmp_path / "sel.json", tmp_path / "patch2.xml")
    assert "<StepsForScripts" in out.read_text()
    run(FMUPG, "--update", "-src_path", str(tmp_path / "step1.fmp12"),
        "-patch_path", str(tmp_path / "patch2.xml"), "-src_account", "Admin",
        "-dest_path", str(tmp_path / "step2.fmp12"))
    step2 = export(tmp_path / "step2.fmp12", tmp_path / "step2.xml")
    dev = etree.parse(P.open_fmsavexml(SB / "dev.xml")).getroot()
    d = {s["name"]: s for s in P.parse_scripts(dev)}["get_script_names"]
    o = {s["name"]: s for s in P.parse_scripts(step2)}["get_script_names"]
    assert o["step_count"] == d["step_count"] and d["step_count"] > 0
    assert o["_hash"] == d["_hash"]


@pytest.mark.skipif(not (SB / "diff.json").exists(), reason="sandbox diff not built")
def test_real_patch_validates(tmp_path):
    diff = json.loads((SB / "diff.json").read_text())
    keys = [i["key"] for i in diff["items"]
            if i["change"] == "added" and i["patchability"] == "proven" and not i["ignored"]]
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"source_diff": str(SB / "diff.json"), "selected": keys}))
    out = tmp_path / "patch.xml"
    G.generate(SB / "dev.xml", SB / "prod.xml", SB / "diff.json", sel, out)
    work = tmp_path / "prod-copy.fmp12"
    shutil.copy2(SB / "prod.fmp12", work)
    r = subprocess.run(["/usr/local/bin/FMUpgradeTool", "--validatePatch",
                        "-src_path", str(work), "-patch_path", str(out),
                        "-src_account", "Admin"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
