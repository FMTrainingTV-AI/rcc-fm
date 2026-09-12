"""Offline tests for the fm-otto driver — env resolution, CLI surface, guardrails.

The live paths (log content, zero-downtime download) need a real box running
OttoFMS and are exercised per-engagement; these tests pin the parts that can
break silently in a refactor: profile-prefixed .env parsing including the Otto
key, the flags-either-side-of-the-verb behaviour, and the write guardrail that
stops `raw` from firing a state-changing call without --yes.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "fm-otto" / "scripts"))

from otto import load_env

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "fm-otto" / "scripts" / "otto.py"


def _run(*args, cwd=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          cwd=cwd, capture_output=True, text=True)


def _write_env(path, prefix="FMS"):
    path.write_text(
        f"# comment line\n"
        f"{prefix}_HOST=fms.example.com\n"
        f"{prefix}_ADMIN_USER = admin \n"
        f"{prefix}_ADMIN_PASS=s3cret=with=equals\n"
        f"{prefix}_OTTO_KEY=dk_abc123\n"
    )


def test_load_env_explicit_path(tmp_path):
    env = tmp_path / "creds.env"
    _write_env(env)
    assert load_env("FMS", env_path=str(env)) == {
        "host": "fms.example.com", "user": "admin",
        "password": "s3cret=with=equals", "key": "dk_abc123",
    }


def test_load_env_profile_prefix(tmp_path):
    env = tmp_path / "creds.env"
    _write_env(env, prefix="FMS2")
    assert load_env("fms2", env_path=str(env))["key"] == "dk_abc123"
    # the default profile finds nothing in an FMS2-only file
    assert load_env("FMS", env_path=str(env)) == {
        "host": None, "user": None, "password": None, "key": None}


def test_load_env_cwd_candidates(tmp_path, monkeypatch):
    fm = tmp_path / "_fm"
    fm.mkdir()
    _write_env(fm / ".env")
    monkeypatch.chdir(tmp_path)
    assert load_env("FMS")["host"] == "fms.example.com"
    (tmp_path / ".env").write_text("FMS_HOST=root.example.com\n")
    assert load_env("FMS")["host"] == "root.example.com"


def test_cli_surface():
    helptext = _run("--help").stdout
    for cmd in ("info", "logs", "log", "download", "deployments",
                "builds", "settings", "apikeys", "files", "spec", "raw"):
        assert cmd in helptext
    assert "--tail" in _run("log", "--help").stdout
    assert "--clone" in _run("download", "--help").stdout


def test_connection_flags_work_on_either_side_of_the_verb():
    """Argparse subparsers normally force globals before the verb; both orders
    are wired deliberately, so a regression here is silent and annoying."""
    for args in (("--host", "h.example.com", "logs"), ("logs", "--host", "h.example.com")):
        r = _run(*args)
        # no host error — it got the host and failed on missing credentials instead
        assert "missing host" not in r.stderr + r.stdout, args


def test_missing_credentials_is_a_clean_message_not_a_traceback(tmp_path):
    r = _run("logs", "--host", "h.example.com", cwd=tmp_path)
    out = r.stderr + r.stdout
    assert r.returncode != 0
    assert "missing credentials" in out
    assert "Traceback" not in out


def test_info_is_the_one_command_that_needs_no_credentials(tmp_path):
    """`info` is the cheap 'does this server even run Otto' probe, so it must not
    demand creds. It will still fail on the network here — just not on auth."""
    r = _run("info", "--host", "127.0.0.1", cwd=tmp_path)
    assert "missing credentials" not in r.stderr + r.stdout


def test_raw_refuses_a_write_without_yes(tmp_path):
    """The guardrail that matters: this API can restart services and undo
    deployments, so a non-GET must not fire on a typo."""
    r = _run("raw", "POST", "/otto/api/restart",
             "--host", "h.example.com", "--user", "u", "--password", "p", cwd=tmp_path)
    out = r.stderr + r.stdout
    assert r.returncode != 0
    assert "--yes" in out
    # it must refuse before any network call is attempted
    assert "cannot reach" not in out
