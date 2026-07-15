import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))
import fm_export, saxml_parser
from lxml import etree

SB = Path(__file__).parent.parent.parent / "sandbox"

@pytest.mark.skipif(not (SB / "prod.fmp12").exists(), reason="run setup_sandbox.sh first")
def test_export_prod_fixture(tmp_path):
    out = fm_export.export_xml(SB / "prod.fmp12", tmp_path / "prod.xml")
    root = etree.parse(saxml_parser.open_fmsavexml(out)).getroot()
    h = saxml_parser.parse_file_header(root)
    assert h["fmsavexml_version"]  # e.g. 2.3.0.0
    names = {b["name"] for b in saxml_parser.parse_base_tables(root)}
    assert "Accounts" in names


@pytest.mark.skipif(not (SB / "prod.fmp12").exists(), reason="run setup_sandbox.sh first")
def test_is_open_in_pro_sandbox_not_open():
    """Sandbox files are not open in FileMaker Pro during tests; lsof+pgrep must return False."""
    result = fm_export.is_open_in_pro(SB / "prod.fmp12")
    assert result is False, (
        "Expected sandbox/prod.fmp12 not to be locked by FileMaker Pro. "
        "If FileMaker Pro has this file open, close it before running tests."
    )


def test_stamp_guids_dest_path_then_atomic_replace(monkeypatch, tmp_path):
    """Crash-safe contract: stamp into a temp -dest_path copy, then atomically
    replace the source — a timeout/crash mid-write can never corrupt it."""
    calls = {}
    src = tmp_path / "x.fmp12"
    src.write_bytes(b"orig")
    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        dest = Path(cmd[cmd.index("-dest_path") + 1])
        dest.write_bytes(b"stamped")  # the tool writes the stamped copy here
        class R: returncode = 0; stdout = ""; stderr = ""
        return R()
    monkeypatch.setattr(fm_export.subprocess, "run", fake_run)
    fm_export.stamp_guids(src)
    assert "-dest_path" in calls["cmd"] and "-inplace" not in calls["cmd"]
    assert src.read_bytes() == b"stamped"            # atomically replaced
    assert not list(tmp_path.glob(".x.stamping*"))   # temp cleaned up
