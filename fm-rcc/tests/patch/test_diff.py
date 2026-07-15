import json, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))
import saxml_diff as D


def _mk(dirpath, base_tables=None, fields=None):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / "_meta.json").write_text(json.dumps(
        {"export_path": "x.xml", "fmsavexml_version": "2.3.0.0", "filename": "t"}))
    (dirpath / "base_tables.json").write_text(json.dumps(base_tables or []))
    (dirpath / "fields.json").write_text(json.dumps(fields or []))

def test_added_removed_modified(tmp_path):
    _mk(tmp_path / "dev",
        base_tables=[{"name": "A", "id": "1", "comment": "", "uuid": "U1", "_hash": "h1"},
                     {"name": "NEW", "id": "2", "comment": "", "uuid": "U2", "_hash": "h2"}],
        fields=[{"table_name": "A", "name": "F", "id": "1", "fieldtype": "Normal",
                 "datatype": "Text", "comment": "", "uuid": "U3", "global": False,
                 "repetitions": 1, "calc_text": "new formula", "_hash": "hf2"}])
    _mk(tmp_path / "prod",
        base_tables=[{"name": "A", "id": "1", "comment": "", "uuid": "P1", "_hash": "h1"},
                     {"name": "GONE", "id": "3", "comment": "", "uuid": "P3", "_hash": "h3"}],
        fields=[{"table_name": "A", "name": "F", "id": "1", "fieldtype": "Normal",
                 "datatype": "Text", "comment": "", "uuid": "P4", "global": False,
                 "repetitions": 1, "calc_text": "old formula", "_hash": "hf1"}])
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {})
    by_key = {i["key"]: i for i in out["items"]}
    assert by_key["base_table:NEW"]["change"] == "added"
    assert by_key["base_table:NEW"]["patchability"] == "proven"
    assert by_key["base_table:GONE"]["change"] == "removed"
    assert by_key["field:A::F"]["change"] == "modified"
    assert "calc_text" in by_key["field:A::F"]["changed_attrs"]
    assert "base_table:A" not in by_key  # identical -> no item

def test_deep_hash_only_change(tmp_path):
    s = {"name": "S", "id": "1", "is_folder": False, "hidden": False,
         "run_with_full_access": False, "uuid": "U", "_hash": "AAA"}
    _mk(tmp_path / "dev"); _mk(tmp_path / "prod")
    (tmp_path / "dev" / "scripts.json").write_text(json.dumps([s]))
    (tmp_path / "prod" / "scripts.json").write_text(json.dumps([s | {"_hash": "BBB"}]))
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {})
    assert out["items"][0]["changed_attrs"] == ["(deep structure)"]

def test_ignore_patterns(tmp_path):
    _mk(tmp_path / "dev", base_tables=[{"name": "ProofKitWV", "id": "9", "comment": "",
                                        "uuid": "U", "_hash": "h"}])
    _mk(tmp_path / "prod")
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {"base_table": ["ProofKit*"]})
    assert out["items"][0]["ignored"] is True

def test_duplicate_names_flagged(tmp_path):
    _mk(tmp_path / "dev",
        base_tables=[{"name": "X", "id": "1", "comment": "", "uuid": "U1", "_hash": "h1"},
                     {"name": "X", "id": "2", "comment": "a", "uuid": "U2", "_hash": "h2"}])
    _mk(tmp_path / "prod")
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {})
    dupe_items = [i for i in out["items"] if i["key"] == "base_table:X"]
    assert len(dupe_items) == 1  # only last same-named object survives — known limitation
    assert dupe_items[0]["duplicate_name"] is True
    assert dupe_items[0]["patchability"] == "manual"  # dupes are never auto-patchable


def test_relationship_key_grammar_and_diff(tmp_path):
    rel = {"id": "1", "uuid": "RU", "left_to": "A", "right_to": "B",
           "predicates": [{"op": "Equal", "left_field": "id", "right_field": "a_id"}],
           "_hash": "rh"}
    _mk(tmp_path / "dev"); _mk(tmp_path / "prod")
    (tmp_path / "dev" / "relationships.json").write_text(json.dumps([rel]))
    (tmp_path / "prod" / "relationships.json").write_text(json.dumps([]))
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {})
    items = [i for i in out["items"] if i["kind"] == "relationship"]
    assert len(items) == 1
    assert items[0]["key"] == "relationship:A|B|idEquala_id"
    assert items[0]["change"] == "added"
    assert items[0]["name"] == "A ↔ B"


def test_malformed_objects_do_not_crash(tmp_path):
    _mk(tmp_path / "dev",
        base_tables=[{"id": "1", "uuid": "U", "_hash": "h"}],  # no name
        fields=[{"name": "F", "id": "1", "_hash": "h2"}])      # no table_name
    _mk(tmp_path / "prod")
    (tmp_path / "dev" / "relationships.json").write_text(json.dumps(
        [{"predicates": [{}], "_hash": "h3"}]))                # everything missing
    out = D.diff_snapshots(tmp_path / "dev", tmp_path / "prod", {})
    assert len(out["items"]) == 3  # all emitted, none crashed

SB = Path(__file__).parent.parent.parent / "sandbox"

@pytest.mark.skipif(not (SB / "dev_parsed").exists(), reason="sandbox exports not built")
def test_sandbox_diff_shows_crm_tables():
    ignore = json.loads((Path(__file__).resolve().parents[2] / "tools" / "patch" / "saxml_ignore.json").read_text())
    out = D.diff_snapshots(SB / "dev_parsed", SB / "prod_parsed", ignore)
    added_tables = [i for i in out["items"] if i["kind"] == "base_table" and i["change"] == "added"]
    assert len(added_tables) == 6, [i["name"] for i in added_tables]
    added_layouts = [i for i in out["items"] if i["kind"] == "layout" and i["change"] == "added"]
    assert len(added_layouts) >= 6
