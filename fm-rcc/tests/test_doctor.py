import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from doctor import run_checks


def test_run_checks_reports_all_categories():
    results = run_checks()
    names = {r["name"] for r in results}
    assert {"FMDeveloperTool", "FMUpgradeTool", "python-lxml", "python-requests", "env-file"} <= names
    assert all(isinstance(r["ok"], bool) for r in results)
    assert all(r["detail"] for r in results)


def test_claris_tools_found_on_this_machine():
    # This machine has the Claris CLI tools installed at /usr/local/bin.
    results = {r["name"]: r for r in run_checks()}
    assert results["FMDeveloperTool"]["ok"]
    assert results["FMUpgradeTool"]["ok"]
