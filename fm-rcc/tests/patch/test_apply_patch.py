"""Unit tests for apply_patch.verify_applied (no Claris tools required)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import apply_patch

MINIMAL = ('<FMSaveAsXML version="2.3.0.0" Has_DDR_INFO="{ddr}">'
           '<Structure><AddAction membercount="0"></AddAction></Structure>'
           '</FMSaveAsXML>')


def _fake_export(calls):
    def fake(fmp12, out_xml, account="Admin", pwd="", include_ddr=False, **kw):
        calls.append(include_ddr)
        out = Path(out_xml)
        out.write_text(MINIMAL.format(ddr="True" if include_ddr else "False"))
        return out
    return fake


def test_verify_reexports_with_dev_ddr_setting(monkeypatch, tmp_path):
    """The verify re-export MUST mirror the dev export's Has_DDR_INFO setting.

    Asymmetric exports re-diff DDR-only content (script step annotations) as
    spurious 'modified (deep structure)' items — found in the 2026-06-12
    real-file dry run: dev exported with --ddr-info, verify re-exported
    without, 10 untouched scripts reported modified.
    """
    for ddr_flag, expected in (("True", True), ("False", False)):
        dev = tmp_path / f"dev-{ddr_flag}.xml"
        dev.write_text(MINIMAL.format(ddr=ddr_flag))
        sel = tmp_path / f"sel-{ddr_flag}.json"
        sel.write_text(json.dumps({"selected": []}))
        calls = []
        monkeypatch.setattr(apply_patch.fm_export, "export_xml", _fake_export(calls))
        apply_patch.verify_applied(dev, tmp_path / "patched.fmp12", sel,
                                   tmp_path / f"wd-{ddr_flag}")
        assert calls == [expected], (
            f"dev Has_DDR_INFO={ddr_flag}: verify should re-export "
            f"include_ddr={expected}, got {calls}")
