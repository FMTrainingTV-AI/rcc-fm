"""Offline tests for the fm-admin driver — env resolution + CLI surface.

The live paths (auth, download dance) need a real FMS box and are exercised
per-engagement; these tests pin the parts that can break silently in a
refactor: profile-prefixed .env parsing, candidate ordering, and the
subcommand/flag surface.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "fm-admin" / "scripts"))

from fms_admin import load_env

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "fm-admin" / "scripts" / "fms_admin.py"


def _write_env(path, prefix="FMS"):
    path.write_text(
        f"# comment line\n"
        f"{prefix}_HOST=fms.example.com\n"
        f"{prefix}_ADMIN_USER = admin \n"
        f"{prefix}_ADMIN_PASS=s3cret=with=equals\n"
    )


def test_load_env_explicit_path(tmp_path):
    env = tmp_path / "creds.env"
    _write_env(env)
    cfg = load_env("FMS", env_path=str(env))
    assert cfg == {"host": "fms.example.com", "user": "admin", "password": "s3cret=with=equals"}


def test_load_env_profile_prefix(tmp_path):
    env = tmp_path / "creds.env"
    _write_env(env, prefix="FMS2")
    assert load_env("fms2", env_path=str(env))["host"] == "fms.example.com"
    # the default profile finds nothing in an FMS2-only file
    assert load_env("FMS", env_path=str(env)) == {"host": None, "user": None, "password": None}


def test_load_env_cwd_candidates(tmp_path, monkeypatch):
    # ./_fm/.env is found when ./.env is absent…
    fm = tmp_path / "_fm"
    fm.mkdir()
    _write_env(fm / ".env")
    monkeypatch.chdir(tmp_path)
    assert load_env("FMS")["host"] == "fms.example.com"
    # …and ./.env wins when both exist.
    (tmp_path / ".env").write_text("FMS_HOST=root.example.com\n")
    assert load_env("FMS")["host"] == "root.example.com"


def test_cli_requires_credentials(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "databases"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode != 0
    assert "missing host/user/password" in r.stderr + r.stdout


def test_cli_surface():
    helptext = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                              capture_output=True, text=True).stdout
    for cmd in ("databases", "metadata", "status", "scripterrorslog", "download"):
        assert cmd in helptext
    dl_help = subprocess.run([sys.executable, str(SCRIPT), "download", "--help"],
                             capture_output=True, text=True).stdout
    for flag in ("--out", "--keep-zip", "--force-close"):
        assert flag in dl_help
