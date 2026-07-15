import json, shutil, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))
import fm_export, saxml_parser, saxml_diff, gen_patch, apply_patch

SB = Path(__file__).parent.parent.parent / "sandbox"
pytestmark = pytest.mark.skipif(not (SB / "dev.fmp12").exists(), reason="sandbox missing")

def test_full_pipeline(tmp_path):
    dev_fmp, prod_fmp = tmp_path / "dev.fmp12", tmp_path / "prod.fmp12"
    shutil.copy2(SB / "dev.fmp12", dev_fmp); shutil.copy2(SB / "prod.fmp12", prod_fmp)
    dev_xml = fm_export.export_xml(dev_fmp, tmp_path / "dev.xml", do_stamp_guids=True)
    prod_xml = fm_export.export_xml(prod_fmp, tmp_path / "prod.xml", do_stamp_guids=True)
    devp = saxml_parser.snapshot(dev_xml, tmp_path / "devp")
    prodp = saxml_parser.snapshot(prod_xml, tmp_path / "prodp")
    ignore = json.loads((Path(__file__).resolve().parents[2] / "tools" / "patch" / "saxml_ignore.json").read_text())
    diff = saxml_diff.diff_snapshots(devp, prodp, ignore)
    diff_path = tmp_path / "diff.json"; diff_path.write_text(json.dumps(diff))
    keys = [i["key"] for i in diff["items"]
            if i["change"] == "added" and i["patchability"] == "proven" and not i["ignored"]]
    assert keys, "fixtures should differ"
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"source_diff": str(diff_path), "selected": keys}))
    patch = tmp_path / "patch.xml"
    gen_patch.generate(dev_xml, prod_xml, diff_path, sel, patch)
    # Negative oracle check BEFORE applying: verify_applied is the pipeline's
    # only defense against silent no-ops, so prove it CAN fail — against the
    # unpatched prod every selected key must come back unresolved.
    pre = apply_patch.verify_applied(dev_xml, prod_fmp, sel, tmp_path / "verify-pre")
    assert not pre["verified"]
    assert set(pre["unresolved"]) == set(keys)
    res = apply_patch.apply_patch(prod_fmp, patch, backups_dir=tmp_path / "bk")
    assert res["applied"] and res["validated"] and res["smoked"]
    v = apply_patch.verify_applied(dev_xml, prod_fmp, sel, tmp_path / "verify")
    assert v["verified"], f"unresolved after patch: {v['unresolved'][:10]}"


def test_caution_delete_pipeline(tmp_path):
    """Caution-tier E2E: DeleteAction through the safe applier, semantically
    verified by re-export. The sandbox diff is purely additive (prod is a
    subset of dev), so there is no real prod-only object to delete — instead
    we treat prod as its own dev side via a hand-built diff that marks one
    real shared field (Accounts::Website) as removed, generate with
    allow_caution=True, apply to a prod copy, then re-export and assert the
    field is gone from fields.json. verify_applied is the wrong oracle here
    (vs the real dev export the deleted field would re-appear as 'added'),
    hence the direct fields.json assertion."""
    prod_fmp = tmp_path / "prod.fmp12"
    shutil.copy2(SB / "prod.fmp12", prod_fmp)
    diff = {"items": [{"key": "field:Accounts::Website", "kind": "field",
                       "change": "removed"}]}
    diff_path = tmp_path / "diff.json"; diff_path.write_text(json.dumps(diff))
    sel = tmp_path / "selection.json"
    sel.write_text(json.dumps({"selected": ["field:Accounts::Website"]}))
    patch = tmp_path / "patch.xml"
    gen_patch.generate(SB / "prod.xml", SB / "prod.xml", diff_path, sel, patch,
                       allow_caution=True)
    assert "<DeleteAction>" in patch.read_text()
    res = apply_patch.apply_patch(prod_fmp, patch, backups_dir=tmp_path / "bk")
    assert res["applied"] and res["validated"] and res["smoked"]
    assert Path(res["backup"]).exists()
    post_xml = fm_export.export_xml(prod_fmp, tmp_path / "post.xml")
    postp = saxml_parser.snapshot(post_xml, tmp_path / "postp")
    fields = json.loads((postp / "fields.json").read_text())
    assert not any(f["table_name"] == "Accounts" and f["name"] == "Website"
                   for f in fields), "Accounts::Website should be deleted"
    # the rest of the Accounts table survived the delete
    assert any(f["table_name"] == "Accounts" and f["name"] == "Name" for f in fields)
