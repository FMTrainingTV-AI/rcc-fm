#!/usr/bin/env python3
"""FileMaker Server Admin API driver — status, databases, and file download.

The Admin API (v2) is the third door into a FileMaker deployment: OData/Data
API talk to the DATA, this talks to the SERVER. Its killer capability for the
patch pipeline: GET /databases/{id} downloads the hosted .fmp12 (as a zip) —
the file must be closed, so the download subcommand does close -> download ->
reopen, and ALWAYS reopens, even when the download fails.

Usage:
  python3 fms_admin.py databases                 # list hosted files
  python3 fms_admin.py metadata                  # server identity/version
  python3 fms_admin.py status                    # server status
  python3 fms_admin.py scripterrorslog           # script-error log SETTINGS (v2 has no log content)
  python3 fms_admin.py download MyFile           # close -> download zip -> reopen (+ unzip)
  python3 fms_admin.py download 3 --keep-zip

Credentials (first match wins):
  --host/--user/--password flags
  --env <path>          an explicit .env file
  ./.env or ./_fm/.env  relative to the current working directory (gitignored)
.env keys, per profile prefix (default profile FMS; switch with --profile):
  FMS_HOST / FMS_ADMIN_USER / FMS_ADMIN_PASS
  FMS2_HOST / FMS2_ADMIN_USER / FMS2_ADMIN_PASS   (--profile FMS2)

Guardrails: download REFUSES a file with connected clients unless
--force-close; it never touches any file other than the one named.

Requires only Python 3 (standard library). No pip installs.
"""
import argparse
import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
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
    }


class Admin:
    def __init__(self, host, user, password):
        self.base = f"https://{host}/fmi/admin/api/v2"
        self.host = host
        auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        status, body = self._raw("POST", "/user/auth", headers={"Authorization": f"Basic {auth}"}, data=b"")
        tok = json.loads(body).get("response", {}).get("token")
        if not tok:
            sys.exit(f"✗ auth failed against {host}: {body.decode()[:200]}")
        self.token = tok

    def _raw(self, method, path, headers=None, data=None, timeout=300):
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Accept": "*/*", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def call(self, method, path, body=None, timeout=300):
        headers = {"Authorization": f"Bearer {self.token}"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        status, raw = self._raw(method, path, headers, data, timeout)
        try:
            return status, json.loads(raw)
        except ValueError:
            return status, raw

    def logout(self):
        self._raw("DELETE", f"/user/auth/{self.token}",
                  headers={"Authorization": f"Bearer {self.token}"}, timeout=15)

    def databases(self):
        _, d = self.call("GET", "/databases")
        return d["response"]["databases"]

    def set_db_status(self, db_id, status_word):
        code, d = self.call("PATCH", f"/databases/{db_id}", {"status": status_word})
        return code, d


def cmd_databases(a, args):
    for f in a.databases():
        print(f"{f['id']:>3}  {f['filename']:35} {f['status']:8} "
              f"{f['size']:>14,}B  clients={f['clients']}")


def cmd_json(a, args):
    paths = {"metadata": "/server/metadata", "status": "/server/status",
             "scripterrorslog": "/server/scripterrorslog"}
    _, d = a.call("GET", paths[args.cmd])
    print(json.dumps(d.get("response", d), indent=2))


def cmd_download(a, args):
    dbs = a.databases()
    hits = [f for f in dbs if f["id"] == args.database or f["filename"] == args.database
            or f["filename"] == f"{args.database}.fmp12"]
    if len(hits) != 1:
        sys.exit(f"✗ '{args.database}' matched {len(hits)} of {len(dbs)} databases — "
                 "use the exact filename or id from `databases`")
    db = hits[0]
    if db["clients"] > 0 and not args.force_close:
        sys.exit(f"✗ {db['filename']} has {db['clients']} connected client(s) — "
                 "closing would kick them. Re-run with --force-close if you mean it.")

    out_dir = Path(args.out) if args.out else Path.cwd() / "dev" / "downloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{Path(db['filename']).stem}.zip"

    was_open = db["status"] != "CLOSED"
    if was_open:
        print(f"→ closing {db['filename']} (status {db['status']})")
        code, d = a.set_db_status(db["id"], "CLOSED")
        if code != 200:
            sys.exit(f"✗ close failed: {d}")
        time.sleep(2)
    try:
        print(f"→ downloading {db['filename']} ({db['size']:,} bytes on server)")
        status, raw = a.call("GET", f"/databases/{db['id']}", timeout=1800)
        if status != 200 or not isinstance(raw, (bytes, bytearray)):
            sys.exit(f"✗ download failed (HTTP {status}): {str(raw)[:200]}")
        zip_path.write_bytes(raw)
    finally:
        if was_open:
            print(f"→ reopening {db['filename']}")
            a.set_db_status(db["id"], "OPENED")
            for _ in range(15):
                time.sleep(2)
                cur = next(f for f in a.databases() if f["id"] == db["id"])
                if cur["status"] == "NORMAL":
                    print("  reopened: NORMAL")
                    break
            else:
                print("  ⚠ file did not reach NORMAL within 30s — check the server", file=sys.stderr)

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"✅ {zip_path}  ({zip_path.stat().st_size:,} bytes)  sha256={digest[:16]}…")
    if not args.keep_zip:
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            z.extractall(out_dir)
        zip_path.unlink()
        for n in names:
            got = out_dir / n
            print(f"✅ {got}  ({got.stat().st_size:,} bytes)")


def main():
    ap = argparse.ArgumentParser(description="FileMaker Server Admin API driver")
    ap.add_argument("--profile", default="FMS", help=".env prefix for host/creds (default: FMS)")
    ap.add_argument("--env", default=None, help="path to a .env file (default: ./.env, then ./_fm/.env)")
    ap.add_argument("--host"), ap.add_argument("--user"), ap.add_argument("--password")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("databases")
    sub.add_parser("metadata")
    sub.add_parser("status")
    sub.add_parser("scripterrorslog")
    dl = sub.add_parser("download")
    dl.add_argument("database", help="database id or filename (with or without .fmp12)")
    dl.add_argument("--out", default=None, help="output dir (default: ./dev/downloads/)")
    dl.add_argument("--keep-zip", action="store_true", help="keep the zip instead of extracting")
    dl.add_argument("--force-close", action="store_true",
                    help="close even with connected clients (they get kicked)")
    args = ap.parse_args()

    cfg = load_env(args.profile, args.env)
    host = args.host or cfg["host"]
    user = args.user or cfg["user"]
    password = args.password or cfg["password"]
    if not all((host, user, password)):
        sys.exit(f"✗ missing host/user/password — set {args.profile.upper()}_HOST / "
                 f"{args.profile.upper()}_ADMIN_USER / {args.profile.upper()}_ADMIN_PASS "
                 "in ./.env (or ./_fm/.env), or pass flags")

    a = Admin(host, user, password)
    try:
        if args.cmd == "databases":
            cmd_databases(a, args)
        elif args.cmd == "download":
            cmd_download(a, args)
        else:
            cmd_json(a, args)
    finally:
        a.logout()


if __name__ == "__main__":
    main()
