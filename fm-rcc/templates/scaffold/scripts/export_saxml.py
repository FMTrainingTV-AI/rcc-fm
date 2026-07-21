#!/usr/bin/env python3
"""Pull a Save-as-XML export from the hosted FileMaker file — remotely.

Triggers the Agent_SaXML_Export script in the hosted file over OData, waits for
it to export the requested catalogs server-side, then downloads the XML through
a text field on the log table. No FileMaker Pro, no plugins — plain HTTPS.

Usage (from the project root):
  python3 scripts/export_saxml.py                      # ScriptCatalog only
  python3 scripts/export_saxml.py --catalogs ScriptCatalog,FieldCatalog
  python3 scripts/export_saxml.py --catalogs all       # FULL structural export (all catalogs)
  python3 scripts/export_saxml.py --project <folder>   # borrow another project's connection

Connection facts come from hostedFile.md beside this script's folder — or,
with --project, from that folder's hostedFile.md (an FM project root, or an
engagement root whose FM surface lives in _fm/). Output ALWAYS lands in THIS
copy's schema/ddrs/YYYY-MM-DD/: the repo you're working in keeps its own
exports, wherever the connection points.

Every run prints a sha256 — compare hashes across runs: identical hash =
nothing changed in the file, different hash = something did. That check
catches silent failures no tool banner will admit to.

Requires only Python 3 (standard library). No pip installs.
"""
import argparse
import base64
import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load_config(md_path):
    """Read `key - value` lines (server / file / account / pass) from hostedFile.md."""
    text = Path(md_path).read_text()

    def grab(key):
        m = re.search(rf"^\s*{key}\s*-\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE)
        if not m:
            raise ValueError(f"Could not find '{key}' in {md_path}")
        return m.group(1).strip()

    server = grab("server")
    database = re.sub(r"\.fmp12$", "", grab("file"), flags=re.IGNORECASE)
    return {
        "server": server,
        "database": database,
        "account": grab("account"),
        "password": grab("pass"),
        "base_url": f"https://{server}/fmi/odata/v4/{database}",
        # Where the export script drops its result in THIS file — chosen during
        # the setup interview (workflow/02) and recorded in hostedFile.md.
        "drop_table": grab("dropTable"),
        "text_field": grab("textField"),
    }


def _req(cfg, method, path, body=None, timeout=300):
    url = cfg["base_url"] + path
    auth = base64.b64encode(f"{cfg['account']}:{cfg['password']}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "*/*"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogs", default="ScriptCatalog",
                    help="comma-separated FM26 catalog names (default: ScriptCatalog), "
                         "or 'all' for a full structural export (no catalog selection)")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--project", default=None,
                    help="read connection facts (hostedFile.md) from this folder instead — "
                         "an FM project root, or an engagement root containing "
                         "_fm/; output still lands in THIS copy's schema/ddrs/")
    args = ap.parse_args()

    cfg_root = ROOT
    if args.project:
        cfg_root = Path(args.project).resolve()
        if not (cfg_root / "hostedFile.md").exists() and (cfg_root / "_fm" / "hostedFile.md").exists():
            cfg_root = cfg_root / "_fm"
    if not (cfg_root / "hostedFile.md").exists():
        sys.exit(f"No hostedFile.md at {cfg_root} — point --project at an FM project root (or its _fm/).")

    cfg = load_config(cfg_root / "hostedFile.md")
    run_id = args.run_id or time.strftime("run-%Y%m%d-%H%M%S")
    catalogs = [c.strip() for c in args.catalogs.split(",") if c.strip()]

    options = {
        "include_details": False,        # DDR_INFO OFF (huge, rarely needed)
        "split_catalogs": False,         # splitting OFF (one small file)
        "standalone_binarydata": False,
    }
    if [c.lower() for c in catalogs] != ["all"]:
        options["catalogs_included"] = catalogs   # selection ON; "all" omits it -> full export

    param = {"runId": run_id, "options": options}

    print(f"→ triggering Agent_SaXML_Export  runId={run_id}  catalogs={catalogs}")
    t0 = time.time()
    status, raw = _req(cfg, "POST", "/Script.Agent_SaXML_Export",
                       {"scriptParameterValue": json.dumps(param)})
    resp = json.loads(raw)
    print(f"  HTTP {status} in {time.time() - t0:.1f}s")

    script_result = resp.get("scriptResult", {})
    result = json.loads(script_result.get("resultParameter") or "{}")
    print(f"  script result: {result}")

    if result.get("stage") != "done" or result.get("error") != 0:
        print("✗ export script reported failure — stopping before transport")
        sys.exit(1)

    rec_id = result["recordId"]
    print(f"→ pulling {cfg['text_field']} from {cfg['drop_table']}({rec_id})")
    t1 = time.time()
    status, raw = _req(cfg, "GET",
                       f"/{cfg['drop_table']}({rec_id})?$select={cfg['text_field']}")
    text = json.loads(raw).get(cfg["text_field"]) or ""
    blob = text.encode("utf-8")
    print(f"  HTTP {status} in {time.time() - t1:.1f}s")

    out_dir = ROOT / "schema" / "ddrs" / time.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"saxml_{run_id}.xml"
    out.write_bytes(blob)

    digest = hashlib.sha256(blob).hexdigest()
    print(f"✅ {out.relative_to(ROOT)}")
    print(f"   bytes={len(blob)}  sha256={digest}")
    if len(blob) == 0:
        print("✗ ZERO BYTES — the real failure signal; do not trust 'error 0' alone")
        sys.exit(1)


if __name__ == "__main__":
    main()
