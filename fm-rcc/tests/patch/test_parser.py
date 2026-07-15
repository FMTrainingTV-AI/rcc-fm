import json, subprocess, sys
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import saxml_parser as P
from lxml import etree

SP_EXPORT = Path(__file__).parent / "fixtures" / "parser-fixture.xml"  # FM 2026 export, tracked in-repo

def _root():
    return etree.parse(P.open_fmsavexml(SP_EXPORT)).getroot()

def test_header():
    h = P.parse_file_header(_root())
    assert h["fmsavexml_version"] == "2.3.0.0"
    # Actual fixture: File="pk-fmsp.fmp12" (includes extension)
    assert h["filename"] == "pk-fmsp.fmp12"

def test_base_tables_have_accounts_and_hashes():
    bts = P.parse_base_tables(_root())
    names = {b["name"] for b in bts}
    # Actual fixture base tables: BASE and ProofKitApps
    assert "BASE" in names
    assert all(len(b["_hash"]) == 32 for b in bts)

def test_fields_nonempty_with_table_scope():
    fs = P.parse_fields(_root())
    # Actual fixture fields are scoped to BASE table
    assert any(f["table_name"] == "BASE" for f in fs)

def test_catalog_uuids():
    cats = P.parse_catalog_uuids(_root())
    assert cats["BaseTableCatalog"]  # exists in this export
    assert cats["FieldsForTables"] is None  # container element, not a UUID-bearing catalog

def test_encoding_detection():
    assert P._detect_encoding(b"\xff\xfe<\x00?\x00") == "utf-16"
    assert P._detect_encoding(b"<?xml version") == "utf-8"

def test_hash_ignores_uuid_and_id():
    a = etree.fromstring('<BaseTable id="1" name="T"><UUID>AAA</UUID></BaseTable>')
    b = etree.fromstring('<BaseTable id="9" name="T"><UUID>BBB</UUID></BaseTable>')
    c = etree.fromstring('<BaseTable id="1" name="OTHER"><UUID>AAA</UUID></BaseTable>')
    assert P.compute_hash(a) == P.compute_hash(b)
    assert P.compute_hash(a) != P.compute_hash(c)

def test_snapshot_cli(tmp_path):
    subprocess.run([sys.executable, "tools/patch/saxml_parser.py", str(SP_EXPORT), "-o", str(tmp_path)],
                   check=True, cwd=Path(__file__).parent.parent.parent)
    assert json.loads((tmp_path / "base_tables.json").read_text())

def test_hash_strips_child_ids():
    a = etree.fromstring('<Script id="1" name="S"><Step id="5" name="If"/></Script>')
    b = etree.fromstring('<Script id="1" name="S"><Step id="9" name="If"/></Script>')
    c = etree.fromstring('<Script id="1" name="S"><Step id="5" name="Loop"/></Script>')
    assert P.compute_hash(a) == P.compute_hash(b)
    assert P.compute_hash(a) != P.compute_hash(c)


def test_hash_ignores_sourceuuid():
    a = etree.fromstring('<BaseTable id="1" name="T"><UUID>AAA</UUID></BaseTable>')
    b = etree.fromstring('<BaseTable id="1" name="T"><UUID>BBB</UUID><SourceUUID>CCC</SourceUUID></BaseTable>')
    assert P.compute_hash(a) == P.compute_hash(b)


def test_inline_calc_extracted():
    # Matches the real FMDeveloperTool 22.0.5 inline shape observed in sandbox/dev.xml:
    # Calculation is a direct child of the named Field element, with a Text child.
    xml = (
        '<Field id="13" name="LineTotal" fieldtype="Calculated" datatype="Number">'
        '<UUID>AAA</UUID>'
        '<SourceUUID>BBB</SourceUUID>'
        '<AutoEnter alwaysEvaluate="False"/>'
        '<Storage storeCalculationResults="True" autoIndex="True" global="False" maxRepetitions="1"/>'
        '<Calculation>'
        '<TableOccurrenceReference id="1" name="EstimateLines"/>'
        '<Text>Quantity * UnitPrice</Text>'
        '</Calculation>'
        '</Field>'
    )
    ol_xml = '<ObjectList>' + xml + '</ObjectList>'
    fc_xml = (
        '<FieldCatalog>'
        '<BaseTableReference id="136" name="EstimateLines"/>'
        + ol_xml +
        '</FieldCatalog>'
    )
    ffts = etree.fromstring('<FieldsForTables>' + fc_xml + '</FieldsForTables>')
    # Wrap in a minimal root so parse_fields can find FieldsForTables
    root = etree.fromstring('<FMSaveAsXML>' + etree.tostring(ffts).decode() + '</FMSaveAsXML>')
    fields = P.parse_fields(root)
    assert len(fields) == 1
    assert fields[0]["name"] == "LineTotal"
    assert fields[0]["calc_text"] == "Quantity * UnitPrice"


def test_inline_calc_extracted_from_sandbox():
    SB = Path(__file__).parent.parent.parent / "sandbox"
    if not (SB / "dev.xml").exists():
        pytest.skip("sandbox not built")
    root = etree.parse(P.open_fmsavexml(SB / "dev.xml")).getroot()
    fields = {(f["table_name"], f["name"]): f for f in P.parse_fields(root)}
    lt = fields[("EstimateLines", "LineTotal")]
    assert lt["calc_text"] and "Quantity" in lt["calc_text"]


# --- Task 6.5: script step bodies in the script hash --------------------------

_STEPS_DOC = '''<FMSaveAsXML version="2.3.0.0"><Structure><AddAction>
 <ScriptCatalog membercount="1"><UUID>CAT-S</UUID>
  <Script id="7" name="Doer"><UUID>S-DOER</UUID>
   <Options hidden="False" runwithfullaccess="False">2</Options><TagList/></Script>
 </ScriptCatalog>
 <StepsForScripts membercount="1">
  <Script>
   <ScriptReference id="7" name="Doer" UUID="S-DOER"/>
   <ObjectList membercount="2">
    <Step hash="AAA" index="0" id="89" name="# (comment)" enable="True"><UUID>ST-1</UUID>
     <Options>0</Options></Step>
    <Step hash="BBB" index="1" id="103" name="Set Variable" enable="True"><UUID>ST-2</UUID>
     <Options>0</Options><Name>$x</Name><Calculation><Text>{calc}</Text></Calculation></Step>
   </ObjectList>
  </Script>
 </StepsForScripts>
</AddAction></Structure></FMSaveAsXML>'''


def _scripts_for(calc):
    root = etree.fromstring(_STEPS_DOC.format(calc=calc).encode())
    return P.parse_scripts(root)


def test_script_hash_includes_step_bodies():
    a = _scripts_for("1 + 1")[0]
    b = _scripts_for("2 + 2")[0]  # ONLY a step's calc text differs
    assert a["step_count"] == b["step_count"] == 2
    assert a["_hash"] != b["_hash"]
    # deterministic: same content -> same hash
    assert a["_hash"] == _scripts_for("1 + 1")[0]["_hash"]


def test_script_hash_ignores_step_uuids_and_hash_attrs():
    a = _scripts_for("1 + 1")
    doc = _STEPS_DOC.format(calc="1 + 1")
    doc = doc.replace("ST-1", "ST-9").replace('hash="AAA"', 'hash="ZZZ"')
    b = P.parse_scripts(etree.fromstring(doc.encode()))
    assert a[0]["_hash"] == b[0]["_hash"]


def test_script_without_steps_keeps_catalog_hash():
    doc = _STEPS_DOC.format(calc="1")
    root = etree.fromstring(doc.encode())
    sfs = root.find("Structure/AddAction/StepsForScripts")
    sfs.getparent().remove(sfs)
    s = P.parse_scripts(root)[0]
    assert s["step_count"] is None
    assert s["_hash"] == P.compute_hash(root.find(".//ScriptCatalog/Script"))


def test_script_steps_from_sandbox():
    SB = Path(__file__).parent.parent.parent / "sandbox"
    if not (SB / "dev.xml").exists():
        pytest.skip("sandbox not built")
    root = etree.parse(P.open_fmsavexml(SB / "dev.xml")).getroot()
    scripts = {s["name"]: s for s in P.parse_scripts(root)}
    assert scripts["get_script_names"]["step_count"] == 22
    assert scripts["ProofKit"]["step_count"] is None  # folder: no steps entry


def test_hash_ignores_ownerid():
    # FMUpgradeTool stamps <OwnerID/> (often empty) onto objects it patches in;
    # without stripping it, a perfectly applied patch re-diffs as modified.
    a = etree.fromstring('<Script id="1" name="S"><UUID>AAA</UUID></Script>')
    b = etree.fromstring('<Script id="1" name="S"><UUID>AAA</UUID><OwnerID/></Script>')
    c = etree.fromstring('<Script id="1" name="S"><UUID>AAA</UUID><OwnerID>X-1</OwnerID></Script>')
    assert P.compute_hash(a) == P.compute_hash(b) == P.compute_hash(c)


def test_hash_ignores_nextvalue():
    # Serial counters advance with normal data entry — instance state, not schema.
    a = etree.fromstring('<Field name="F"><AutoEnter><SerialNumber nextvalue="5"/></AutoEnter></Field>')
    b = etree.fromstring('<Field name="F"><AutoEnter><SerialNumber nextvalue="999"/></AutoEnter></Field>')
    c = etree.fromstring('<Field name="F"><AutoEnter><SerialNumber nextvalue="5" increment="2"/></AutoEnter></Field>')
    assert P.compute_hash(a) == P.compute_hash(b)
    assert P.compute_hash(a) != P.compute_hash(c)


# --- Layout hash: per-instance state from FMUpgradeTool layout apply ----------

_LAYOUT_DOC = '''<FMSaveAsXML version="2.3.0.0"><Structure><AddAction>
 <LayoutCatalog membercount="1">
  <Layout id="15" name="Products" width="1024">
   <Options hidden="False">{options}</Options>
   <TableOccurrenceReference id="139" name="Products"/>
   <ObjectList membercount="1">
    <LayoutObject type="Edit Box" name="" kind="1">
     <Options>{obj_options}</Options>
     <Accessibility><Label>{label}</Label></Accessibility>
    </LayoutObject>
   </ObjectList>
  </Layout>
 </LayoutCatalog>
</AddAction></Structure></FMSaveAsXML>'''


def _layout_hash(options="64440436737", label="18", obj_options="805306368"):
    root = etree.fromstring(_LAYOUT_DOC.format(
        options=options, label=label, obj_options=obj_options).encode())
    return P.parse_layouts(root)[0]["_hash"]


def test_layout_hash_ignores_accessibility_label_renumber():
    # FMUpgradeTool renumbers internal object ids on layout AddAction; ids are
    # already hash-stripped, but <Accessibility><Label> holds a reference to
    # them (18 -> 16 in the 2026-06-12 dry run) and must be stripped too.
    assert _layout_hash(label="18") == _layout_hash(label="16")


def test_layout_hash_ignores_layout_options_bit26():
    # Engine-managed state bit: set by FMUpgradeTool on layout insert, and
    # varies across normally-created layouts within one file — instance state,
    # not schema (same class as serial nextvalue).
    base = 64440436737
    assert _layout_hash(options=str(base)) == _layout_hash(options=str(base | (1 << 26)))
    # any other Options bit is a real layout option and MUST still be detected
    assert _layout_hash(options=str(base)) != _layout_hash(options=str(base | 2))


def test_layout_hash_keeps_object_level_options():
    # the state-bit mask applies to the layout-level Options only; a
    # LayoutObject's own Options are real content at full fidelity
    obj = 805306368
    assert _layout_hash(obj_options=str(obj)) != _layout_hash(obj_options=str(obj | (1 << 26)))
