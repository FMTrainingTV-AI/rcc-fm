"""Unit tests for gen_scaffold (no Claris tools required)."""
import json, sys
from pathlib import Path
import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))
import gen_scaffold
import saxml_parser

FIX = Path(__file__).parent / "fixtures" / "fmbase.xml"


def _write_spec(tmp_path, spec):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    return p


GOOD_SPEC = {
    "file": "CRM",
    "tables": {
        "Accounts": {"Name": "text", "Phone": "text",
                     "Status": {"type": "text", "comment": "Active / Inactive"}},
        "Contacts": {"fk_Account_ID": "fk", "NameFirst": "text", "NameLast": "text",
                     "FullName": {"type": "calc", "result": "text",
                                  "formula": 'NameFirst & " " & NameLast'}},
        "EstimateLines": {"fk_Estimate_ID": {"type": "fk", "parent": "Estimates"},
                          "Quantity": "number", "UnitPrice": "number",
                          "LineTotal": {"type": "calc", "result": "number",
                                        "formula": "Quantity * UnitPrice"}},
        "Estimates": {"fk_Account_ID": "fk", "DateEstimate": "date"},
    },
}


def test_load_spec_normalizes(tmp_path):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, GOOD_SPEC))
    assert spec["file"] == "CRM"
    acc = {f["name"]: f for f in spec["tables"]["Accounts"]}
    assert acc["Name"] == {"name": "Name", "type": "text", "comment": "",
                           "datatype": "Text", "fieldtype": "Normal"}
    fk = {f["name"]: f for f in spec["tables"]["Contacts"]}["fk_Account_ID"]
    assert fk["parent"] == "Accounts"            # plural resolution: Account -> Accounts
    assert fk["datatype"] == "Number" and fk["comment"] == "-> Accounts.ID"
    fk2 = {f["name"]: f for f in spec["tables"]["EstimateLines"]}["fk_Estimate_ID"]
    assert fk2["parent"] == "Estimates"          # explicit parent wins
    calc = {f["name"]: f for f in spec["tables"]["Contacts"]}["FullName"]
    assert calc["fieldtype"] == "Calculated" and calc["datatype"] == "Text"
    assert calc["formula"] == 'NameFirst & " " & NameLast'


@pytest.mark.parametrize("mutate,fragment", [
    (lambda s: s.update(file="my crm"), "file"),
    (lambda s: s.update(tables={}), "tables"),
    (lambda s: s["tables"].update(BASE={"X": "text"}), "reserved"),
    (lambda s: s["tables"].update(ProofKitApps={"X": "text"}), "reserved"),
    (lambda s: s["tables"]["Accounts"].update({"Bad Name": "text"}), "identifier"),
    (lambda s: s["tables"]["Accounts"].update({"ID": "text"}), "BASE-7"),
    (lambda s: s["tables"]["Accounts"].update({"Blob": "blob"}), "unknown type"),
    (lambda s: s["tables"]["Accounts"].update({"fk_Nowhere_ID": "fk"}), "parent"),
    (lambda s: s["tables"]["Accounts"].update({"fk_Contact_ID": "text"}), "type 'fk'"),
    (lambda s: s["tables"]["Accounts"].update({"Total": {"type": "calc"}}), "formula"),
    (lambda s: s["tables"]["Accounts"].update({"fk_AccountID": "fk"}), "fk_<Parent>_ID"),
])
def test_load_spec_rejects(tmp_path, mutate, fragment):
    bad = json.loads(json.dumps(GOOD_SPEC))
    mutate(bad)
    with pytest.raises(gen_scaffold.SpecError) as e:
        gen_scaffold.load_spec(_write_spec(tmp_path, bad))
    assert fragment.lower() in str(e.value).lower()


def test_expand_spec_prepends_base7(tmp_path):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, GOOD_SPEC))
    exp = gen_scaffold.expand_spec(spec)
    names = [f["name"] for f in exp["Accounts"]]
    assert names == ["ID", "RecordID", "kTrue", "CreationTimestamp", "CreationAccount",
                     "ModifyTimestamp", "ModifyAccount", "Name", "Phone", "Status"]
    rid = exp["Accounts"][1]
    assert rid["datatype"] == "Text" and rid["fieldtype"] == "Calculated"


def test_expected_entries_match_diff_key_grammar(tmp_path):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, GOOD_SPEC))
    entries = gen_scaffold.expected_entries(gen_scaffold.expand_spec(spec))
    keys = {e["key"] for e in entries}
    assert "base_table:Accounts" in keys
    assert "field:Accounts::ID" in keys                  # BASE-7 expected too
    assert "field:Contacts::fk_Account_ID" in keys
    assert "table_occurrence:Accounts" in keys
    assert "layout:Accounts" in keys
    lay = next(e for e in entries if e["key"] == "layout:Accounts")
    assert lay["table"] == "Accounts"
    fld = next(e for e in entries if e["key"] == "field:Contacts::FullName")
    assert fld["datatype"] == "Text" and fld["fieldtype"] == "Calculated"


@pytest.fixture(scope="module")
def fmbase_ctx(tmp_path_factory):
    td = tmp_path_factory.mktemp("fmbase")
    parsed = saxml_parser.snapshot(FIX, td / "parsed")
    return gen_scaffold.harvest_context(FIX, parsed)


def test_harvest_ids_and_catalog_uuid(fmbase_ctx):
    assert fmbase_ctx["next_table_id"] == 132        # BASE=130, ProofKitApps=131
    assert fmbase_ctx["next_to_id"] == 1065092
    assert fmbase_ctx["next_layout_id"] == 8         # folders + separators count
    assert fmbase_ctx["layout_catalog_uuid"] == "159B0E23-F13E-4D89-BB0C-B756BD3FE08B"
    assert fmbase_ctx["tables"]["BASE"]["id"] == "130"
    assert fmbase_ctx["max_field_id"]["BASE"] == 13


def test_harvest_base7_fragments_and_theme(fmbase_ctx):
    frags = fmbase_ctx["base7_frags"]
    assert set(frags) == set(gen_scaffold.BASE7_TYPES)
    idf = frags["ID"]
    ae = idf.find("AutoEnter")
    assert ae.get("prohibitModification") == "True"   # convention preserved verbatim
    theme = fmbase_ctx["theme"]
    assert theme.get("name") == "com.filemaker.theme.apex_blue"
    assert theme.get("UUID")                          # harvested, file-specific


# ---------------------------------------------------------------------------
# Reconciler delta tests (Task 4)
# ---------------------------------------------------------------------------

def _delta(tmp_path, spec_dict, ctx):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, spec_dict))
    return gen_scaffold.compute_delta(gen_scaffold.expand_spec(spec), ctx)


def test_delta_virgin_base(tmp_path, fmbase_ctx):
    d = _delta(tmp_path, GOOD_SPEC, fmbase_ctx)
    assert d["new_tables"] == ["Accounts", "Contacts", "EstimateLines", "Estimates"]
    assert d["new_tos"] == d["new_tables"] and d["add_layouts"] == d["new_tables"]
    assert d["regen_layouts"] == [] and not d["noop"]
    assert d["drift"] == []          # BASE + ProofKitApps are reserved, not drift


def _fake_ctx(tables):
    """Minimal ctx for delta tests: {table: {field: (datatype, fieldtype)}}."""
    ctx = {"tables": {}, "tos": {}, "layouts": {}, "fields_by_table": {},
           "max_field_id": {}}
    for i, (tname, fields) in enumerate(tables.items()):
        ctx["tables"][tname] = {"id": str(200 + i), "name": tname, "uuid": f"T-{i}"}
        ctx["tos"][tname] = {"id": str(1065200 + i), "name": tname, "uuid": f"O-{i}",
                             "base_table_name": tname}
        ctx["layouts"][tname] = {"id": str(50 + i), "name": tname, "uuid": f"L-{i}",
                                 "table_occurrence": tname}
        ctx["fields_by_table"][tname] = {
            fn: {"table_name": tname, "id": str(j + 1), "name": fn,
                 "datatype": dt, "fieldtype": ft, "uuid": f"F-{i}-{j}"}
            for j, (fn, (dt, ft)) in enumerate(fields.items())}
        ctx["max_field_id"][tname] = len(fields)
    return ctx


def _built(spec_dict):
    """Fake ctx representing a file that already matches spec_dict —
    including live (uncommented) calc_text for spec-declared calc fields."""
    expanded = gen_scaffold.expand_spec(gen_scaffold.load_spec_dict(spec_dict))
    tables = {}
    for tname, fl in expanded.items():
        tables[tname] = {f["name"]: (f["datatype"], f["fieldtype"]) for f in fl}
    ctx = _fake_ctx(tables)
    for tname, fl in expanded.items():
        for f in fl:
            if f.get("formula"):
                ctx["fields_by_table"][tname][f["name"]]["calc_text"] = f["formula"]
    return ctx


def test_delta_noop_when_file_matches(tmp_path):
    ctx = _built(GOOD_SPEC)
    d = _delta(tmp_path, GOOD_SPEC, ctx)
    assert d["noop"] and d["new_tables"] == [] and d["new_fields"] == {}


def test_delta_partial_adds_fields_and_regenerates_layout(tmp_path):
    ctx = _built(GOOD_SPEC)
    spec2 = json.loads(json.dumps(GOOD_SPEC))
    spec2["tables"]["Accounts"]["Website"] = "text"
    spec2["tables"]["Projects"] = {"fk_Account_ID": "fk", "Name": "text"}
    d = _delta(tmp_path, spec2, ctx)
    assert d["new_tables"] == ["Projects"]
    assert [f["name"] for f in d["new_fields"]["Accounts"]] == ["Website"]
    assert d["regen_layouts"] == ["Accounts"]      # existing layout, new field
    assert "Projects" in d["add_layouts"] and "Accounts" not in d["add_layouts"]


def test_delta_reports_drift_not_changes(tmp_path):
    ctx = _built(GOOD_SPEC)
    ctx["tables"]["Legacy"] = {"id": "299", "name": "Legacy", "uuid": "T-X"}
    ctx["fields_by_table"]["Accounts"]["Phone"] = dict(
        ctx["fields_by_table"]["Accounts"]["Phone"], datatype="Number")
    d = _delta(tmp_path, GOOD_SPEC, ctx)
    assert d["noop"]                                # drift never produces a patch
    assert any("Legacy" in x for x in d["drift"])
    assert any("Accounts::Phone" in x for x in d["drift"])


# ---------------------------------------------------------------------------
# Patch synthesis tests (Task 5)
# ---------------------------------------------------------------------------

def _patch_root(tmp_path, spec_dict, ctx):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, spec_dict))
    expanded = gen_scaffold.expand_spec(spec)
    delta = gen_scaffold.compute_delta(expanded, ctx)
    xml = gen_scaffold.build_patch(expanded, delta, ctx)
    return etree.fromstring(xml.encode("utf-8"))


def test_patch_virgin_structure(tmp_path, fmbase_ctx):
    root = _patch_root(tmp_path, GOOD_SPEC, fmbase_ctx)
    assert root.tag == "FMUpgradeToolPatch" and root.get("version") == "2.3.0.0"
    add = root.find("Structure/AddAction")
    # proven catalog order — forward references fail, layouts last
    assert [c.tag for c in add] == ["BaseTableCatalog", "FieldsForTables",
                                    "TableOccurrenceCatalog", "LayoutCatalog"]
    assert root.find("Structure/DeleteAction") is None
    bts = add.findall("BaseTableCatalog/BaseTable")
    assert [b.get("name") for b in bts] == ["Accounts", "Contacts",
                                            "EstimateLines", "Estimates"]
    assert [b.get("id") for b in bts] == ["132", "133", "134", "135"]
    lc = add.find("LayoutCatalog")
    assert lc.find("UUID").text == fmbase_ctx["layout_catalog_uuid"]
    # every layout themed with the HARVESTED theme reference
    for lay in lc.findall("Layout"):
        th = lay.find("LayoutThemeReference")
        assert th.get("UUID") == fmbase_ctx["theme"].get("UUID")


def test_patch_field_shapes(tmp_path, fmbase_ctx):
    root = _patch_root(tmp_path, GOOD_SPEC, fmbase_ctx)
    add = root.find("Structure/AddAction")
    cats = {fc.find("BaseTableReference").get("name"): fc
            for fc in add.findall("FieldsForTables/FieldCatalog")}
    acc = cats["Accounts"]
    assert acc.find("SortOrder").text == "1"               # new-table shape
    assert len(acc.findall("CustomOrderList/key")) == 10   # BASE-7 + 3 domain
    fields = {f.get("name"): f for f in acc.findall("ObjectList/Field")}
    assert [int(f.get("id")) for f in acc.findall("ObjectList/Field")] == list(range(1, 11))
    # BASE-7 cloned from the base file, options intact, refs rewritten
    assert fields["ID"].find("AutoEnter").get("prohibitModification") == "True"
    for tor in fields["kTrue"].iter("TableOccurrenceReference"):
        assert tor.get("name") == "Accounts"
    # domain + fk + calc shapes
    assert fields["Status"].get("comment") == "Active / Inactive"
    con = {f.get("name"): f for f in cats["Contacts"].findall("ObjectList/Field")}
    assert con["fk_Account_ID"].get("datatype") == "Number"
    calc = con["FullName"]
    assert calc.get("fieldtype") == "Calculated" and calc.get("datatype") == "Text"
    assert calc.find("Calculation/Text").text == 'NameFirst & " " & NameLast'
    assert calc.find("Calculation/TableOccurrenceReference").get("name") == "Contacts"
    assert calc.find("Storage").get("storeCalculationResults") == "True"


def test_patch_layout_shape(tmp_path, fmbase_ctx):
    root = _patch_root(tmp_path, GOOD_SPEC, fmbase_ctx)
    lay = next(l for l in root.findall(".//LayoutCatalog/Layout")
               if l.get("name") == "Accounts")
    to_ref = lay.find("TableOccurrenceReference")
    assert to_ref.get("name") == "Accounts"
    objs = lay.findall("PartsList/Part/ObjectList/LayoutObject")
    assert len(objs) == 20                                  # label+edit per field
    edits = [o for o in objs if o.get("type") == "Edit Box"]
    assert len(edits) == 10
    # field refs carry the SAME UUIDs as the synthesized fields (scoped to Accounts)
    acc_cat = next(fc for fc in root.findall(".//FieldsForTables/FieldCatalog")
                   if fc.find("BaseTableReference").get("name") == "Accounts")
    field_uuids = {f.find("UUID").text
                   for f in acc_cat.findall("ObjectList/Field")}
    for e in edits:
        fr = e.find("Field/FieldReference")
        assert fr.get("UUID") in field_uuids
        # Accessibility/Label pairs each edit box to its label object id
        lbl_id = e.find("Accessibility/Label").text
        assert lay.find(f".//LayoutObject[@id='{lbl_id}']") is not None
    tv = lay.findall("TableView/ObjectList/TableViewLayoutObject")
    assert [t.get("name") for t in tv][:3] == ["ID", "RecordID", "kTrue"]


def _base7_frags_from_fixture():
    parsed_root = etree.parse(saxml_parser.open_fmsavexml(FIX)).getroot()
    add = parsed_root.find("Structure/AddAction")
    frags = {}
    for fc in add.iter("FieldCatalog"):
        bt = fc.find("BaseTableReference")
        if bt is not None and bt.get("name") == "BASE":
            for fe in fc.iter("Field"):
                if fe.get("name") in gen_scaffold.BASE7_TYPES:
                    frags[fe.get("name")] = fe
    return frags


def test_patch_delta_into_existing(tmp_path):
    ctx = _built(GOOD_SPEC)
    spec2 = json.loads(json.dumps(GOOD_SPEC))
    spec2["tables"]["Accounts"]["Website"] = "text"
    # fake ctx needs harvest-only keys for build_patch
    ctx.update(next_table_id=300, next_to_id=1065300, next_layout_id=60,
               layout_catalog_uuid="LC-UUID",
               theme=etree.fromstring('<LayoutThemeReference id="1" name="t" UUID="TH" Base="b"/>'),
               base7_frags=_base7_frags_from_fixture())
    root = _patch_root(tmp_path, spec2, ctx)
    add = root.find("Structure/AddAction")
    assert add.find("BaseTableCatalog") is None             # nothing new at table level
    fc = add.find("FieldsForTables/FieldCatalog")
    assert fc.find("SortOrder") is None                     # into-existing shape
    btref = fc.find("BaseTableReference")
    assert btref.get("name") == "Accounts" and btref.get("UUID") == ctx["tables"]["Accounts"]["uuid"]
    f = fc.find("ObjectList/Field")
    assert f.get("name") == "Website"
    assert int(f.get("id")) == ctx["max_field_id"]["Accounts"] + 1
    # regen: Delete OLD layout by UUID, AFTER AddAction (gen_patch's proven order)
    dels = root.findall("Structure/DeleteAction")
    assert len(dels) == 1
    ir = dels[0].find("ItemReference")
    assert ir.get("type") == "LayoutReference"
    assert ir.get("UUID") == ctx["layouts"]["Accounts"]["uuid"]
    kids = [c.tag for c in root.find("Structure")]
    assert kids == ["AddAction", "DeleteAction"]
    # the regenerated Accounts layout includes Website
    lay = next(l for l in root.findall(".//LayoutCatalog/Layout")
               if l.get("name") == "Accounts")
    names = [t.get("name") for t in lay.findall("TableView/ObjectList/TableViewLayoutObject")]
    assert "Website" in names and "ID" in names


def test_patch_self_check_raises_on_mismatch(tmp_path, fmbase_ctx):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, GOOD_SPEC))
    expanded = gen_scaffold.expand_spec(spec)
    delta = gen_scaffold.compute_delta(expanded, fmbase_ctx)
    delta["new_tables"] = delta["new_tables"][:-1]    # sabotage: drop a table
    with pytest.raises(ValueError, match="self-check"):
        gen_scaffold.build_patch(expanded, delta, fmbase_ctx)


def test_delta_rejects_to_name_collision(tmp_path):
    ctx = _built(GOOD_SPEC)
    spec2 = json.loads(json.dumps(GOOD_SPEC))
    spec2["tables"]["Projects"] = {"Name": "text"}
    # a TO named Projects already exists but points elsewhere
    ctx["tos"]["Projects"] = {"id": "1065999", "name": "Projects", "uuid": "O-X",
                              "base_table_name": "Accounts"}
    with pytest.raises(ValueError, match="TO name collision"):
        _delta(tmp_path, spec2, ctx)


def test_delta_rejects_layout_name_collision(tmp_path):
    ctx = _built(GOOD_SPEC)
    spec2 = json.loads(json.dumps(GOOD_SPEC))
    spec2["tables"]["Projects"] = {"Name": "text"}
    ctx["layouts"]["Projects"] = {"id": "99", "name": "Projects", "uuid": "L-X",
                                  "table_occurrence": "Accounts"}
    with pytest.raises(ValueError, match="layout name collision"):
        _delta(tmp_path, spec2, ctx)


def test_patch_self_check_counts_phantom_table(tmp_path, fmbase_ctx):
    spec = gen_scaffold.load_spec(_write_spec(tmp_path, GOOD_SPEC))
    expanded = gen_scaffold.expand_spec(spec)
    delta = gen_scaffold.compute_delta(expanded, fmbase_ctx)
    delta["new_tables"] = delta["new_tables"] + ["Phantom"]   # not in expanded
    with pytest.raises(ValueError, match="self-check"):
        gen_scaffold.build_patch(expanded, delta, fmbase_ctx)


# ---------------------------------------------------------------------------
# Coverage oracle, generate orchestration, CLI (Task 6)
# ---------------------------------------------------------------------------

def _parsed_from(tmp_path, name, base_tables=(), fields=(), tos=(), layouts=()):
    d = tmp_path / name
    d.mkdir()
    (d / "base_tables.json").write_text(json.dumps(list(base_tables)))
    (d / "fields.json").write_text(json.dumps(list(fields)))
    (d / "table_occurrences.json").write_text(json.dumps(list(tos)))
    (d / "layouts.json").write_text(json.dumps(list(layouts)))
    return d


def test_check_expected_pass_and_failures(tmp_path):
    expected = {"file": "X", "entries": [
        {"kind": "base_table", "key": "base_table:T", "name": "T"},
        {"kind": "field", "key": "field:T::Name", "table": "T", "name": "Name",
         "datatype": "Text", "fieldtype": "Normal"},
        {"kind": "table_occurrence", "key": "table_occurrence:T", "name": "T"},
        {"kind": "layout", "key": "layout:T", "name": "T", "table": "T"},
    ]}
    ok = _parsed_from(tmp_path, "ok",
        base_tables=[{"name": "T"}],
        fields=[{"table_name": "T", "name": "Name", "datatype": "Text",
                 "fieldtype": "Normal"}],
        tos=[{"name": "T"}],
        layouts=[{"name": "T", "is_folder": False, "table_occurrence": "T"}])
    r = gen_scaffold.check_expected(expected, ok)
    assert r["verified"] and r["missing"] == [] and r["mismatched"] == []

    missing_field = _parsed_from(tmp_path, "mf",
        base_tables=[{"name": "T"}], fields=[], tos=[{"name": "T"}],
        layouts=[{"name": "T", "is_folder": False, "table_occurrence": "T"}])
    r = gen_scaffold.check_expected(expected, missing_field)
    assert not r["verified"] and r["missing"] == ["field:T::Name"]

    wrong_type = _parsed_from(tmp_path, "wt",
        base_tables=[{"name": "T"}],
        fields=[{"table_name": "T", "name": "Name", "datatype": "Number",
                 "fieldtype": "Normal"}],
        tos=[{"name": "T"}],
        layouts=[{"name": "T", "is_folder": False, "table_occurrence": "T"}])
    r = gen_scaffold.check_expected(expected, wrong_type)
    assert not r["verified"] and "field:T::Name" in r["mismatched"][0]

    bad_layout = _parsed_from(tmp_path, "bl",
        base_tables=[{"name": "T"}],
        fields=[{"table_name": "T", "name": "Name", "datatype": "Text",
                 "fieldtype": "Normal"}],
        tos=[{"name": "T"}],
        layouts=[{"name": "T", "is_folder": False, "table_occurrence": "Other"}])
    r = gen_scaffold.check_expected(expected, bad_layout)
    assert not r["verified"] and "layout:T" in r["mismatched"][0]


def test_generate_virgin_writes_patch_and_expected(tmp_path):
    spec_p = _write_spec(tmp_path, GOOD_SPEC)
    out = tmp_path / "run1"
    summary = gen_scaffold.generate(spec_p, FIX, out)
    assert not summary["noop"]
    # 13 domain fields (3+4+4+2) + 4 new tables x 7 BASE-7 = 41
    assert summary["counts"] == {"new_tables": 4, "new_fields": 41,
                                 "new_tos": 4, "add_layouts": 4, "regen_layouts": 0}
    assert (out / "patch.xml").exists() and (out / "expected.json").exists()
    etree.parse(str(out / "patch.xml"))                  # well-formed
    exp = json.loads((out / "expected.json").read_text())
    assert exp["file"] == "CRM" and len(exp["entries"]) > 0
    # the patch satisfies its own expectations structurally (names line up)
    root = etree.parse(str(out / "patch.xml")).getroot()
    patched_tables = {b.get("name") for b in root.findall(".//BaseTable")}
    assert patched_tables == set(GOOD_SPEC["tables"])


def test_generate_noop_writes_expected_only(tmp_path):
    """generate() must gate on a noop delta: expected.json written, patch.xml not."""
    tiny = {"file": "T1", "tables": {"Things": {"Name": "text"}}}
    spec_p = _write_spec(tmp_path, tiny)
    flds = [{"table_name": "Things", "name": n, "datatype": dt, "fieldtype": ft,
             "id": str(i + 1), "uuid": f"F{i}"}
            for i, (n, (dt, ft)) in enumerate(
                {**gen_scaffold.BASE7_TYPES, "Name": ("Text", "Normal")}.items())]
    parsed = _parsed_from(tmp_path, "built",
        base_tables=[{"name": "Things", "id": "140", "uuid": "T0"}],
        fields=flds,
        tos=[{"name": "Things", "id": "1065100", "uuid": "O0",
              "base_table_name": "Things"}],
        layouts=[{"name": "Things", "id": "9", "is_folder": False, "uuid": "L0",
                  "table_occurrence": "Things"}])
    (parsed / "catalogs.json").write_text(json.dumps({"LayoutCatalog": "LC"}))
    summary = gen_scaffold.generate(spec_p, FIX, tmp_path / "run2",
                                    parsed_dir=parsed)
    assert summary["noop"]
    assert (tmp_path / "run2" / "expected.json").exists()
    assert not (tmp_path / "run2" / "patch.xml").exists()


def test_verify_built_uses_export(tmp_path, monkeypatch):
    """verify_built re-exports the target then runs check_expected — mirror
    the monkeypatch style of test_apply_patch.py."""
    expected = {"file": "X", "entries": [
        {"kind": "base_table", "key": "base_table:T", "name": "T"}]}
    exp_p = tmp_path / "expected.json"
    exp_p.write_text(json.dumps(expected))
    minimal = ('<FMSaveAsXML version="2.3.0.0" Has_DDR_INFO="False"><Structure>'
               '<AddAction membercount="1"><BaseTableCatalog membercount="1">'
               '<BaseTable id="130" name="T" comment=""></BaseTable>'
               '</BaseTableCatalog></AddAction></Structure></FMSaveAsXML>')
    def fake_export(fmp12, out_xml, account="Admin", pwd="", **kw):
        Path(out_xml).write_text(minimal)
        return Path(out_xml)
    monkeypatch.setattr(gen_scaffold.fm_export, "export_xml", fake_export)
    r = gen_scaffold.verify_built(exp_p, tmp_path / "fake.fmp12", tmp_path / "wd")
    assert r["verified"], r


def test_load_spec_bad_json_is_specerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(gen_scaffold.SpecError, match="not valid JSON"):
        gen_scaffold.load_spec(p)


# ---------------------------------------------------------------------------
# Fix 2(a) — extra fields/TOs/layouts reported as drift
# ---------------------------------------------------------------------------

def test_delta_reports_extra_field_to_layout_drift(tmp_path):
    ctx = _built(GOOD_SPEC)
    ctx["fields_by_table"]["Accounts"]["HandAdded"] = {
        "table_name": "Accounts", "id": "99", "name": "HandAdded",
        "datatype": "Text", "fieldtype": "Normal", "uuid": "F-X"}
    ctx["tos"]["Extra"] = {"id": "1065998", "name": "Extra", "uuid": "O-Y",
                           "base_table_name": "Accounts"}
    ctx["layouts"]["Scratch"] = {"id": "98", "name": "Scratch", "uuid": "L-Y",
                                 "table_occurrence": "Accounts"}
    d = _delta(tmp_path, GOOD_SPEC, ctx)
    assert d["noop"]
    assert any("Accounts::HandAdded" in x and "regenerated layout" in x
               for x in d["drift"])
    assert any("table occurrence Extra" in x for x in d["drift"])
    assert any("layout Scratch" in x for x in d["drift"])


# ---------------------------------------------------------------------------
# Fix 3(a) — duplicate JSON keys in spec
# ---------------------------------------------------------------------------

def test_load_spec_rejects_duplicate_keys(tmp_path):
    p = tmp_path / "dup.json"
    p.write_text('{"file":"X","tables":{"T":{"A":"text","A":"number"}}}')
    with pytest.raises(gen_scaffold.SpecError, match="duplicate"):
        gen_scaffold.load_spec(p)


# ---------------------------------------------------------------------------
# Fix 3(b) — duplicate names in target export
# ---------------------------------------------------------------------------

def test_harvest_rejects_duplicate_names(tmp_path):
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    (parsed / "base_tables.json").write_text(json.dumps(
        [{"name": "T", "id": "140", "uuid": "U1"}]))
    (parsed / "fields.json").write_text(json.dumps([]))
    (parsed / "table_occurrences.json").write_text(json.dumps(
        [{"name": "T", "id": "1", "uuid": "U2", "base_table_name": "T"}]))
    (parsed / "layouts.json").write_text(json.dumps(
        [{"name": "L", "id": "2", "is_folder": False, "uuid": "U3",
          "table_occurrence": "T"},
         {"name": "L", "id": "3", "is_folder": False, "uuid": "U4",
          "table_occurrence": "T"}]))
    (parsed / "catalogs.json").write_text(json.dumps({"LayoutCatalog": "LC"}))
    with pytest.raises(ValueError, match="duplicate"):
        gen_scaffold.harvest_context(FIX, parsed)


# -- calc re-apply pass (the silent /* … */ class, found live 2026-06-12) ----


def test_patch_emits_calc_reapply_modify_action(tmp_path, fmbase_ctx):
    root = _patch_root(tmp_path, GOOD_SPEC, fmbase_ctx)
    structure = root.find("Structure")
    assert [c.tag for c in structure][-1] == "ModifyAction"   # always last
    stubs = structure.findall("ModifyAction/FieldsForTables/FieldCatalog")
    stubbed = {(s.find("BaseTableReference").get("name"),
                s.find("ObjectList/Field/FieldReference").get("name"))
               for s in stubs}
    # synthesized calcs
    assert ("Contacts", "FullName") in stubbed
    assert ("EstimateLines", "LineTotal") in stubbed
    # cloned BASE-7 calc carriers (Calculation or auto-enter calc)
    assert ("Accounts", "RecordID") in stubbed
    assert ("Accounts", "kTrue") in stubbed
    assert ("Accounts", "ID") in stubbed
    fr = next(s for s in stubs
              if s.find("ObjectList/Field/FieldReference").get("name") == "FullName"
              ).find("ObjectList/Field/FieldReference")
    assert fr.get("UUID")
    assert fr.find("Calculation/Text").text == 'NameFirst & " " & NameLast'
    assert fr.find("BaseTableReference") is not None
    # stub Fields are nameless wrappers and must NOT pollute the AddAction
    # field self-check (scoped paths) — patch parsed fine, so this held.


def test_delta_repairs_commented_out_calc(tmp_path):
    ctx = _built(GOOD_SPEC)
    ctx["fields_by_table"]["Contacts"]["FullName"] = dict(
        ctx["fields_by_table"]["Contacts"]["FullName"],
        calc_text='/* NameFirst & " " & NameLast */')
    d = _delta(tmp_path, GOOD_SPEC, ctx)
    assert not d["noop"]
    assert [f["name"] for f in d["repair_calcs"]["Contacts"]] == ["FullName"]
    assert d["new_fields"] == {} and d["regen_layouts"] == []


def test_patch_repair_stub_for_existing_field(tmp_path):
    ctx = _built(GOOD_SPEC)
    ctx["fields_by_table"]["Contacts"]["FullName"] = dict(
        ctx["fields_by_table"]["Contacts"]["FullName"],
        calc_text='/* NameFirst & " " & NameLast */')
    ctx.update(next_table_id=300, next_to_id=1065300, next_layout_id=60,
               layout_catalog_uuid="LC-UUID",
               theme=etree.fromstring(
                   '<LayoutThemeReference id="1" name="t" UUID="TH" Base="b"/>'),
               base7_frags=_base7_frags_from_fixture())
    root = _patch_root(tmp_path, GOOD_SPEC, ctx)
    assert root.find("Structure/AddAction") is None          # repair-only patch
    stubs = root.findall("Structure/ModifyAction/FieldsForTables/FieldCatalog")
    assert len(stubs) == 1
    fr = stubs[0].find("ObjectList/Field/FieldReference")
    assert fr.get("name") == "FullName"
    assert fr.get("UUID") == ctx["fields_by_table"]["Contacts"]["FullName"]["uuid"]
    assert fr.find("Calculation/Text").text == 'NameFirst & " " & NameLast'
    btref = stubs[0].find("BaseTableReference")
    assert btref.get("name") == "Contacts"
    assert btref.get("UUID") == ctx["tables"]["Contacts"]["uuid"]


def test_check_expected_flags_commented_calc(tmp_path):
    expected = {"file": "X", "entries": [
        {"kind": "field", "key": "field:T::Total", "table": "T", "name": "Total",
         "datatype": "Number", "fieldtype": "Calculated", "formula": "A * B"},
        {"kind": "field", "key": "field:T::RecordID", "table": "T",
         "name": "RecordID", "datatype": "Text", "fieldtype": "Calculated"},
    ]}
    bad = _parsed_from(tmp_path, "bad",
        base_tables=[{"name": "T"}],
        fields=[{"table_name": "T", "name": "Total", "datatype": "Number",
                 "fieldtype": "Calculated", "calc_text": "/* A * B */"},
                {"table_name": "T", "name": "RecordID", "datatype": "Text",
                 "fieldtype": "Calculated", "calc_text": "/* Get(RecordID) */"}],
        tos=[], layouts=[])
    r = gen_scaffold.check_expected(expected, bad)
    assert not r["verified"]
    assert any("Total" in m and "commented" in m for m in r["mismatched"])
    assert any("RecordID" in m and "commented" in m for m in r["mismatched"])
    ok = _parsed_from(tmp_path, "okc",
        base_tables=[{"name": "T"}],
        fields=[{"table_name": "T", "name": "Total", "datatype": "Number",
                 "fieldtype": "Calculated", "calc_text": "A * B"},
                {"table_name": "T", "name": "RecordID", "datatype": "Text",
                 "fieldtype": "Calculated", "calc_text": "Get ( RecordID )"}],
        tos=[], layouts=[])
    r2 = gen_scaffold.check_expected(expected, ok)
    assert not any("commented" in m for m in r2["mismatched"])
