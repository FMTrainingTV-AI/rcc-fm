"""E2E: scaffold a mini-CRM onto a copy of resources/fmbase.fmp12 through the
real Claris tools, then evolve it with a delta spec. Skips when the tools or
the seed file are unavailable (same convention as test_e2e_sandbox.py)."""
import json, shutil, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import fm_export, saxml_parser, apply_patch, gen_scaffold

ROOT = Path(__file__).parent.parent.parent
FMBASE = ROOT / "resources" / "fmbase.fmp12"
pytestmark = pytest.mark.skipif(
    not (Path(apply_patch.FMUPG).exists() and FMBASE.exists()),
    reason="Claris CLI tools or resources/fmbase.fmp12 missing")

SPEC_V1 = {
    "file": "MiniCRM",
    "tables": {
        "Accounts": {"Name": "text", "Status": {"type": "text",
                                                "comment": "Active / Inactive"}},
        "Contacts": {"fk_Account_ID": "fk", "NameFirst": "text", "NameLast": "text",
                     "FullName": {"type": "calc", "result": "text",
                                  "formula": 'NameFirst & " " & NameLast'}},
    },
}
SPEC_V2 = json.loads(json.dumps(SPEC_V1))
SPEC_V2["tables"]["Accounts"]["Website"] = "text"
SPEC_V2["tables"]["Projects"] = {"fk_Account_ID": "fk", "Name": "text",
                                 "DateStart": "date", "Budget": "number"}


def test_virgin_noop_delta_cycle(tmp_path):
    target = tmp_path / "MiniCRM.fmp12"
    shutil.copy2(FMBASE, target)

    # -- virgin scaffold ----------------------------------------------------
    s1 = tmp_path / "v1.json"; s1.write_text(json.dumps(SPEC_V1))
    xml1 = fm_export.export_xml(target, tmp_path / "pre1.xml")
    sum1 = gen_scaffold.generate(s1, xml1, tmp_path / "run1")
    assert not sum1["noop"] and sum1["counts"]["new_tables"] == 2
    # negative oracle first: against the UNpatched file, verify must fail
    pre = gen_scaffold.verify_built(tmp_path / "run1" / "expected.json", target,
                                    tmp_path / "verify0")
    assert not pre["verified"] and "base_table:Accounts" in pre["missing"]
    res = apply_patch.apply_patch(target, tmp_path / "run1" / "patch.xml",
                                  backups_dir=tmp_path / "bk")
    assert res["applied"] and res["validated"] and res["smoked"]
    v1 = gen_scaffold.verify_built(tmp_path / "run1" / "expected.json", target,
                                   tmp_path / "verify1")
    assert v1["verified"], v1

    # -- no-op convergence --------------------------------------------------
    xml2 = fm_export.export_xml(target, tmp_path / "pre2.xml")
    sum2 = gen_scaffold.generate(s1, xml2, tmp_path / "run2")
    assert sum2["noop"], sum2
    assert not (tmp_path / "run2" / "patch.xml").exists()

    # -- delta: new field into existing table + new table --------------------
    s2 = tmp_path / "v2.json"; s2.write_text(json.dumps(SPEC_V2))
    sum3 = gen_scaffold.generate(s2, xml2, tmp_path / "run3")
    assert sum3["counts"] == {"new_tables": 1, "new_fields": 12,
                              "new_tos": 1, "add_layouts": 1, "regen_layouts": 1}
    patch_text = (tmp_path / "run3" / "patch.xml").read_text()
    assert "<DeleteAction>" in patch_text          # Accounts layout regen
    res = apply_patch.apply_patch(target, tmp_path / "run3" / "patch.xml",
                                  backups_dir=tmp_path / "bk")
    assert res["applied"]
    v2 = gen_scaffold.verify_built(tmp_path / "run3" / "expected.json", target,
                                   tmp_path / "verify2")
    assert v2["verified"], v2

    # regenerated layout: exactly ONE Accounts layout, carrying Website
    post = saxml_parser.snapshot(fm_export.export_xml(target, tmp_path / "post.xml"),
                                 tmp_path / "postp")
    lays = [l for l in json.loads((post / "layouts.json").read_text())
            if l["name"] == "Accounts" and not l.get("is_folder")]
    assert len(lays) == 1
    # base file untouched where it should be: BASE + ProofKitApps still present
    tables = {t["name"] for t in json.loads((post / "base_tables.json").read_text())}
    assert {"BASE", "ProofKitApps", "Accounts", "Contacts", "Projects"} <= tables
