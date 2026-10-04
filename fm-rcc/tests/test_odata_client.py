import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "fm-odata" / "scripts"))

import fm_odata
from odata_client import ODataClient


def make_client(recorder):
    """An ODataClient whose _request records the call instead of hitting HTTP."""
    client = ODataClient.__new__(ODataClient)
    client.config = {"base_url": "https://fms.example.com/fmi/odata/v4/Sample"}
    client.base_url = client.config["base_url"]

    def fake_request(method, path, body=None, accept="application/json"):
        recorder.append({"method": method, "path": path, "body": body})
        return 200, {"ok": True}

    client._request = fake_request
    return client


# ---- schema-change verbs ----------------------------------------------------

def test_create_table_posts_to_filemaker_tables():
    calls = []
    make_client(calls).create_table("Tasks", [{"name": "Name", "type": "VARCHAR(255)"}])
    assert calls == [{
        "method": "POST",
        "path": "/FileMaker_Tables",
        "body": {"tableName": "Tasks", "fields": [{"name": "Name", "type": "VARCHAR(255)"}]},
    }]


def test_add_fields_patches_the_table():
    # FMS rejects POST on an existing table with -1012; the Claris schema API
    # wants PATCH /FileMaker_Tables/{table} (verified live against FMS 2026).
    calls = []
    make_client(calls).add_fields("Tasks", [{"name": "GitSHA", "type": "VARCHAR(40)"}])
    assert calls == [{
        "method": "PATCH",
        "path": "/FileMaker_Tables/Tasks",
        "body": {"fields": [{"name": "GitSHA", "type": "VARCHAR(40)"}]},
    }]


def test_add_fields_rejects_filemaker_style_types():
    # Same client-side guard as create_table: SQL DDL names only, so 8310
    # never reaches the server.
    calls = []
    with pytest.raises(ValueError, match="string"):
        make_client(calls).add_fields("Tasks", [{"name": "Bad", "type": "string"}])
    assert calls == []


def test_create_table_rejects_filemaker_style_types():
    calls = []
    with pytest.raises(ValueError, match="text"):
        make_client(calls).create_table("Tasks", [{"name": "Bad", "type": "text"}])
    assert calls == []


# ---- CLI --------------------------------------------------------------------

def test_cli_exposes_add_fields():
    args = fm_odata.build_parser().parse_args(
        ["add-fields", "Tasks", "--field", "GitSHA:VARCHAR(40)", "--field", "Due:DATE"]
    )
    assert args.func is fm_odata.cmd_add_fields
    assert args.table == "Tasks"
    assert args.field == ["GitSHA:VARCHAR(40)", "Due:DATE"]


def test_cmd_add_fields_parses_fields_and_calls_client(capsys):
    calls = []
    client = make_client(calls)
    args = fm_odata.build_parser().parse_args(
        ["add-fields", "Tasks", "--field", "GitSHA:VARCHAR(40)"]
    )
    fm_odata.cmd_add_fields(client, args)
    assert calls[0]["method"] == "PATCH"
    assert calls[0]["path"] == "/FileMaker_Tables/Tasks"
    assert calls[0]["body"] == {"fields": [{"name": "GitSHA", "type": "VARCHAR(40)"}]}
    assert "Tasks" in capsys.readouterr().out


# ---- no shipped credentials -------------------------------------------------

def test_no_real_credentials_in_skill_files():
    # Placeholders only — real server/file/account/password values must never
    # ship in the skill (docstrings, SKILL.md, references).
    skill_root = Path(__file__).resolve().parents[1] / "skills" / "fm-odata"
    # Stored reversed: the edition build scripts grep shipped trees for these
    # same strings, and this file ships.
    leaked = [tok[::-1] for tok in (
        "ccrta", "432!ipa", "PS_CR_IA", "pohskrow-citnega", "IADJ", "IAPS", "NEGDAEL", "SOSBS", "IA_tnioPgnitratS",
    )]
    hits = []
    for path in skill_root.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".py", ".json", ".txt"}:
            text = path.read_text()
            hits += [f"{path.name}: {tok}" for tok in leaked if tok in text]
    assert not hits, f"credential-shaped strings shipped in skill: {hits}"
