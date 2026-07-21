"""Tests for xml_to_fmp12.py — offender parsing + CLI contract offline; a full
XML→file rebuild through the real Claris tools when the sandbox is present
(same convention as test_e2e_sandbox.py)."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "patch"))
import xml_to_fmp12 as x2f

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "patch" / "xml_to_fmp12.py"
SB = ROOT / "sandbox"


# ---- parse_offenders ---------------------------------------------------------

GEN_ERR = """\
DependencyError: 3 objects cannot be built:
  layout:Invoices: references theme com.filemaker.theme.custom.acme which the base lacks
  steps(script:Nightly Sync): references layout:Dashboard which was dropped
  fields(Orders): references '<Table Missing>'
"""


def test_parse_offenders_direct_and_step_scopes():
    selected = {"layout:Invoices", "script:Nightly Sync", "script:Other"}
    hits = x2f.parse_offenders(GEN_ERR, selected)
    assert hits == {"layout:Invoices", "script:Nightly Sync"}


def test_parse_offenders_fields_fragment_expands_to_selected_fields():
    selected = {"field:Orders::Total", "field:Orders::Status", "field:Customers::Name"}
    hits = x2f.parse_offenders(GEN_ERR, selected)
    assert hits == {"field:Orders::Total", "field:Orders::Status"}


def test_parse_offenders_only_returns_selected():
    # an offender the caller never selected must not be "pruned"
    assert x2f.parse_offenders(GEN_ERR, {"script:Unrelated"}) == set()


# ---- generator introspection -------------------------------------------------

def test_generator_kinds_reads_real_module():
    kinds = x2f.generator_kinds(ROOT / "tools" / "patch")
    assert {"base_table", "field", "script"} <= kinds


# ---- CLI contract ------------------------------------------------------------

def test_cli_refuses_existing_target(tmp_path):
    xml = tmp_path / "saxml_x.xml"
    xml.write_text("<x/>")
    out = tmp_path / "exists.fmp12"
    out.write_bytes(b"")
    r = subprocess.run([sys.executable, str(SCRIPT), "--input", str(xml), "--out", str(out)],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode != 0
    assert "already exists" in r.stderr + r.stdout


def test_cli_no_exports_message(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode != 0
    assert "No exports found" in r.stderr + r.stdout


# ---- E2E: rebuild the sandbox dev file from its export -----------------------

@pytest.mark.skipif(
    not ((SB / "dev.xml").exists() and (ROOT / "resources" / "fmbase.fmp12").exists()
         and Path("/usr/local/bin/FMUpgradeTool").exists()),
    reason="sandbox export, fmbase, or Claris CLI tools missing")
def test_e2e_rebuild_from_sandbox_export(tmp_path):
    out = tmp_path / "rebuilt.fmp12"
    r = subprocess.run([sys.executable, str(SCRIPT), "--input", str(SB / "dev.xml"),
                        "--out", str(out)],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert out.exists() and out.stat().st_size > 0
    assert "verified" in r.stdout
    assert "consistency check" in r.stdout
