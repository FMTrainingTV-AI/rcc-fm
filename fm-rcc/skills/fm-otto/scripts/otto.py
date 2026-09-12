#!/usr/bin/env python3
"""OttoFMS Developer API driver — logs, deployments, builds, server ops.

OttoFMS sits on the same box as FileMaker Server and answers on /otto/api.
It is a SEPARATE service from the FMS Admin API but shares the admin-console
identity, so one profile in .env drives both this and fms_admin.py.

Its killer capability for us: GET /server-info/logs/{name} returns the actual
LOG CONTENT as text — Event.log, Access.log, the Otto logs. The FMS Admin API
has no such endpoint (see the fm-admin skill), so this is the supported way to
read a server's logs without filesystem access to the box.

Usage:
  python3 otto.py info                      # Otto + FMS versions (no auth needed)
  python3 otto.py logs                      # which log files exist
  python3 otto.py log Event.log --tail 50   # LOG CONTENT — the reason this exists
  python3 otto.py log Event.log --out ./ev.log
  python3 otto.py download MyFile           # hosted file, NO close, no downtime
  python3 otto.py download MyFile --clone   # schema-only clone
  python3 otto.py deployments               # deployment history
  python3 otto.py builds
  python3 otto.py settings
  python3 otto.py apikeys                   # Data API key LABELS (never secrets)
  python3 otto.py files "/FMS Backups"      # browse server folders
  python3 otto.py spec --out ./otto.json    # the server's own OpenAPI spec
  python3 otto.py raw GET /otto/api/info    # escape hatch for the other ~80 endpoints

Credentials (first match wins) — identical convention to fms_admin.py:
  --host/--user/--password flags
  --key <otto-api-key>  or  --env <path>
  ./.env or ./_fm/.env  relative to the current working directory (gitignored)
.env keys, per profile prefix (default profile FMS; switch with --profile):
  FMS_HOST / FMS_ADMIN_USER / FMS_ADMIN_PASS      (same creds as fms_admin.py)
  FMS_OTTO_KEY                                     (optional Otto API key -> Bearer)

Auth: admin-console Basic, or an Otto Admin API key as Bearer. Otto validates a
Bearer token by proxying to the local Admin API, so a bad key surfaces as
"Local Admin API error ... code: 1703".

Guardrail: this API can restart services, delete builds and undo deployments.
Every named subcommand here is READ-ONLY. Writes go through `raw`, which
refuses any non-GET method unless you pass --yes.

Requires only Python 3 (standard library). No pip installs.
"""
import argparse
import base64
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def load_env(profile, env_path=None):
    env = {}
    candidates = ([Path(env_path)] if env_path
                  else [Path.cwd() / ".env", Path.cwd() / "_fm" / ".env"])
    for cand in candidates:
        if cand.exists():
            for line in cand.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
            break
    p = profile.upper()
    return {
        "host": env.get(f"{p}_HOST"),
        "user": env.get(f"{p}_ADMIN_USER"),
        "password": env.get(f"{p}_ADMIN_PASS"),
        "key": env.get(f"{p}_OTTO_KEY"),
    }


class Otto:
    """Thin client. No login step: Otto takes Basic or Bearer on every call."""

    def __init__(self, host, user=None, password=None, key=None):
        self.host = host
        self.root = f"https://{host}"
        if key:
            self.auth = f"Bearer {key}"
        elif user and password:
            self.auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        else:
            self.auth = None

    def _raw(self, method, path, body=None, timeout=300):
        headers = {"Accept": "*/*"}
        if self.auth:
            headers["Authorization"] = self.auth
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(self.root + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers.get("Content-Type", "")
        except urllib.error.URLError as e:
            sys.exit(f"✗ cannot reach {self.host}: {e.reason}")

    def call(self, method, path, body=None, timeout=300):
        """JSON call. Returns (status, parsed). Exits on an Otto-level error."""
        status, raw, ctype = self._raw(method, path, body, timeout)
        # /otto/ is a single-page app with a catch-all: an unmatched path returns
        # the app's HTML shell with HTTP 200. Never let that parse as success.
        if "text/html" in ctype:
            sys.exit(f"✗ {path} hit the OttoFMS web app, not the API — that path does not exist. "
                     "Check it against `otto.py spec`.")
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw

    def get(self, path):
        status, d = self.call("GET", path)
        if status != 200:
            msg = d.get("messages", [{}])[0].get("text", d) if isinstance(d, dict) else d
            sys.exit(f"✗ HTTP {status} on {path}: {str(msg)[:200]}")
        return d.get("response", d) if isinstance(d, dict) else d


def cmd_info(o, args):
    """Deliberately unauthenticated — the one endpoint that answers without creds,
    which makes it the cheapest liveness probe for a server you're not sure about."""
    r = o.get("/otto/api/info")
    fms, otto = r.get("FileMakerServer", {}), r.get("Otto", {})
    print(f"host          {o.host}")
    print(f"FileMaker     {fms.get('version', {}).get('long', '?')}   running={fms.get('fmsRunning')}")
    print(f"OttoFMS       {otto.get('version', '?')}  (build {otto.get('build', '?')})")
    print(f"licence       valid={otto.get('isLicenseValid')}   OCC connected={otto.get('isOCCConnected')}")
    if otto.get("serverNickname"):
        print(f"nickname      {otto['serverNickname']}")


def cmd_logs(o, args):
    r = o.get("/otto/api/server-info/logs")
    for label, key in (("FileMaker Server", "fmsLogs"), ("OttoFMS", "ottoLogs")):
        names = r.get(key, [])
        print(f"\n{label} ({len(names)})")
        for n in names:
            print(f"  {n}")
    print("\nRead one with:  otto.py log <name> --tail 50")


def cmd_log(o, args):
    """The headline capability: actual log text, which the FMS Admin API cannot return."""
    path = f"/otto/api/server-info/logs/{urllib.parse.quote(args.name)}"
    status, raw, ctype = o._raw("GET", path, timeout=600)
    if "text/html" in ctype:
        sys.exit(f"✗ '{args.name}' is not a log the server offers — run `otto.py logs`.")
    if status != 200:
        sys.exit(f"✗ HTTP {status} fetching {args.name}: {raw[:200].decode(errors='replace')}")
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        print(f"✅ {out}  ({len(raw):,} bytes)")
        return
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    shown = lines[-args.tail:] if args.tail else lines
    if args.tail and len(lines) > args.tail:
        print(f"… {len(lines) - args.tail:,} earlier lines omitted "
              f"({len(raw):,} bytes total; --out to save it all)\n")
    print("\n".join(shown))


def cmd_download(o, args):
    """Pull a hosted file WITHOUT closing it.

    Otto snapshots into its own temp backup folder server-side and streams that,
    so the live file keeps serving clients — no close/reopen dance, no downtime.
    That makes this strictly better than the Admin API path (fm-admin) whenever
    Otto is installed. --clone gets a schema-only clone instead.
    """
    name = args.database if args.database.endswith(".fmp12") else f"{args.database}.fmp12"
    q = "?clone=1" if args.clone else ""
    path = f"/otto/api/fm-file/{urllib.parse.quote(name)}/download{q}"
    print(f"→ asking Otto for {'a clone of ' if args.clone else ''}{name} (file stays open)")
    status, raw, ctype = o._raw("GET", path, timeout=1800)
    if "text/html" in ctype:
        sys.exit(f"✗ '{name}' is not a file Otto can see — check the name against fm-admin `databases`.")
    if status != 200:
        sys.exit(f"✗ HTTP {status}: {raw[:300].decode(errors='replace')}")
    if not raw[:4] == b"\x00\x01\x00\x00":
        sys.exit(f"✗ response is not a FileMaker file (got {len(raw):,} bytes of {ctype}); "
                 "the server may have returned an error envelope.")
    out_dir = Path(args.out) if args.out else Path.cwd() / "dev" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem + ("_clone" if args.clone else "")
    dest = out_dir / f"{stem}.fmp12"
    dest.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    print(f"✅ {dest}  ({len(raw):,} bytes)  sha256={digest[:16]}…")
    print("   the hosted file was never closed — clients kept working")


def cmd_deployments(o, args):
    r = o.get("/otto/api/deployment")
    deps = r.get("deployments", r) if isinstance(r, dict) else r
    if not deps:
        print("(no deployments on this server)")
        return
    for d in deps:
        print(f"{str(d.get('id', '?')):>6}  {str(d.get('status', '?')):12} "
              f"{str(d.get('createdAt', '')):26} {d.get('label') or d.get('name') or ''}")


def cmd_builds(o, args):
    r = o.get("/otto/api/build/list")
    builds = r.get("builds", r) if isinstance(r, dict) else r
    if not builds:
        print("(no builds on this server)")
        return
    print(json.dumps(builds, indent=2))


def cmd_apikeys(o, args):
    """Labels and metadata only. The key secrets are not printed — they are
    credentials, and a transcript is not where they belong."""
    r = o.get("/otto/api/api-key")
    keys = r.get("api-keys", r) if isinstance(r, dict) else r
    if not keys:
        print("(no Data API keys configured)")
        return
    for k in keys:
        safe = {x: k.get(x) for x in ("label", "database", "createdAt", "lastUsed", "expiration") if x in k}
        print(json.dumps(safe))


def cmd_files(o, args):
    q = f"?path={urllib.parse.quote(args.path)}" if args.path else ""
    r = o.get(f"/otto/api/files{q}")
    for f in r.get("files", []):
        kind = "dir " if f.get("type") == "dir" else "file"
        print(f"{kind}  {str(f.get('modifiedTime', '')):26} {f.get('name')}")


def cmd_settings(o, args):
    print(json.dumps(o.get("/otto/api/settings"), indent=2))


def cmd_spec(o, args):
    """The server documents itself. Prefer its copy over anything remembered:
    endpoints move between OttoFMS releases."""
    status, raw, ctype = o._raw("GET", "/otto/apidoc/openapi.json", timeout=120)
    if status != 200 or "json" not in ctype:
        sys.exit(f"✗ no spec at /otto/apidoc/openapi.json (HTTP {status}, {ctype})")
    spec = json.loads(raw)
    if args.out:
        Path(args.out).write_bytes(raw)
        print(f"✅ {args.out}  ({len(raw):,} bytes)")
    tags = {}
    for path, item in spec.get("paths", {}).items():
        for m, op in item.items():
            if m in ("get", "post", "put", "patch", "delete"):
                tags.setdefault((op.get("tags") or ["(untagged)"])[0], []).append(
                    f"{m.upper():6} {path}")
    print(f"\n{spec.get('info', {}).get('title')} {spec.get('info', {}).get('version')} — "
          f"{sum(len(v) for v in tags.values())} operations")
    for t in sorted(tags):
        print(f"\n### {t} ({len(tags[t])})")
        for line in sorted(tags[t]):
            print(f"  {line}")


def cmd_raw(o, args):
    method = args.method.upper()
    if method != "GET" and not args.yes:
        sys.exit(f"✗ {method} can change or destroy server state (restarts, deletes, undo). "
                 "Re-run with --yes once you have confirmed it with the human.")
    body = json.loads(args.body) if args.body else None
    status, d = o.call(method, args.path, body)
    print(json.dumps(d, indent=2) if not isinstance(d, (bytes, bytearray))
          else d[:4000].decode(errors="replace"))
    if status >= 400:
        sys.exit(1)


def main():
    # Connection flags are attached to the top-level parser AND every subcommand,
    # so both `otto.py --host h info` and `otto.py info --host h` work. SUPPRESS
    # keeps an unset subcommand copy from clobbering a value given before the verb.
    conn = argparse.ArgumentParser(add_help=False)
    conn.add_argument("--profile", default=argparse.SUPPRESS,
                      help=".env prefix for host/creds (default: FMS)")
    conn.add_argument("--env", default=argparse.SUPPRESS,
                      help="path to a .env file (default: ./.env, then ./_fm/.env)")
    for f in ("--host", "--user", "--password"):
        conn.add_argument(f, default=argparse.SUPPRESS)
    conn.add_argument("--key", default=argparse.SUPPRESS, help="Otto API key (sent as Bearer)")

    ap = argparse.ArgumentParser(description="OttoFMS Developer API driver", parents=[conn])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        return sub.add_parser(name, parents=[conn], **kw)

    add("info", help="Otto + FMS versions (no auth required)")
    add("logs", help="list available log files")
    lg = add("log", help="print/save a log file's CONTENT")
    lg.add_argument("name", help="log file name, e.g. Event.log (see `logs`)")
    lg.add_argument("--tail", type=int, default=50, help="last N lines (0 = all; default 50)")
    lg.add_argument("--out", default=None, help="save the whole file here instead of printing")
    dl = add("download", help="pull a hosted file WITHOUT closing it (no downtime)")
    dl.add_argument("database", help="filename, with or without .fmp12")
    dl.add_argument("--clone", action="store_true", help="schema-only clone instead of the data file")
    dl.add_argument("--out", default=None, help="output dir (default: ./dev/downloads/)")
    add("deployments"), add("builds")
    add("settings"), add("apikeys")
    fl = add("files", help="browse server folders")
    fl.add_argument("path", nargs="?", default=None)
    sp = add("spec", help="the server's own OpenAPI spec, grouped by tag")
    sp.add_argument("--out", default=None)
    rw = add("raw", help="any endpoint (GET free; writes need --yes)")
    rw.add_argument("method"), rw.add_argument("path")
    rw.add_argument("--body", default=None, help="JSON request body")
    rw.add_argument("--yes", action="store_true", help="confirm a state-changing call")

    args = ap.parse_args()
    prof = getattr(args, "profile", "FMS").upper()
    cfg = load_env(prof, getattr(args, "env", None))
    host = getattr(args, "host", None) or cfg["host"]
    key = getattr(args, "key", None) or cfg["key"]
    user = getattr(args, "user", None) or cfg["user"]
    password = getattr(args, "password", None) or cfg["password"]
    if not host:
        sys.exit(f"✗ missing host — set {prof}_HOST in ./.env (or ./_fm/.env), or pass --host")
    if args.cmd != "info" and not (key or (user and password)):
        sys.exit(f"✗ missing credentials — set {prof}_ADMIN_USER / {prof}_ADMIN_PASS "
                 f"(or {prof}_OTTO_KEY) in ./.env, or pass flags. "
                 "Only `info` works unauthenticated.")

    o = Otto(host, user, password, key)
    {"info": cmd_info, "logs": cmd_logs, "log": cmd_log, "download": cmd_download,
     "deployments": cmd_deployments,
     "builds": cmd_builds, "settings": cmd_settings, "apikeys": cmd_apikeys,
     "files": cmd_files, "spec": cmd_spec, "raw": cmd_raw}[args.cmd](o, args)


if __name__ == "__main__":
    main()
