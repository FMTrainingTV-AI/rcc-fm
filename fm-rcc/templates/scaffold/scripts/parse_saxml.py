#!/usr/bin/env python3
"""Parse a Save-as-XML ScriptCatalog export into an agent-readable knowledge base.

Takes a saxml_*.xml export produced by export_saxml.py and turns it into two
artifacts an agent (or human) can actually read and query:

  schema/parsed/<run>.json    - structured: every script, its flags, and its steps
  schema/readable/<run>.md    - overview + per-script step-by-step, in plain text

What the lightweight ScriptCatalog export contains, and therefore what we parse:
  - ScriptCatalog  - the inventory: every script and folder, with id, name, the
                     hidden/access/run-with-full-access flags, and who last
                     modified it. Folders are FLAT markers here — this export does
                     not encode which scripts live in which folder, so we list
                     folders separately and never invent a hierarchy.
  - StepsForScripts - the logic: each script's ordered steps, joined back to the
                     catalog by script id. This is why the export is a knowledge
                     base and not just a table of contents.

Step parameters are extracted best-effort: comments, variable/field names,
calculations, and script/layout references come through readably; exotic step
types fall back to their step name plus whatever values are present. Faithful
rendering of every FileMaker step type is a bigger job (the fm-scripts domain) —
this is the honest first pass.

Usage (from the engagement root):
  python3 scripts/parse_saxml.py                     # newest export under schema/ddrs/
  python3 scripts/parse_saxml.py --input <file.xml>  # a specific export (from anywhere)

Output always lands in THIS copy's schema/parsed/ + schema/readable/ — the
repo you're working in keeps its own knowledge base, wherever the input
export came from.

Standard library only. No pip installs.
"""
import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Step-level bookkeeping tags that carry no logic — skip when summarizing params.
_SKIP_TAGS = {"UUID", "OwnerID", "Options"}


def newest_export():
    """Most recent saxml_*.xml under schema/ddrs/<date>/, by name (names sort by time)."""
    candidates = sorted((ROOT / "schema" / "ddrs").glob("*/saxml_*.xml"))
    if not candidates:
        sys.exit("No exports found under schema/ddrs/. Run export_saxml.py first.")
    return candidates[-1]


def calc_text(el):
    """All text inside a <Calculation> (handles nested chunks / CDATA)."""
    return " ".join(t.strip() for t in el.itertext() if t and t.strip())


def summarize_params(step):
    """A compact, readable summary of a step's parameters.

    Generic on purpose: pull the informative leaves (named references, values,
    calculation text) so unmapped step types still say something useful instead
    of nothing.
    """
    pv = step.find("ParameterValues")
    if pv is None:
        return ""
    chunks = []
    for param in pv.findall("Parameter"):
        bits = []
        for el in param.iter():
            if el.tag == "Calculation":
                c = calc_text(el)
                if c:
                    bits.append(f"[{c}]")
                continue
            val = el.attrib.get("value")
            if val:
                bits.append(val)
            name = el.attrib.get("name")
            if name and el.tag != "Parameter":
                bits.append(name)
        # de-dupe preserving order
        seen, uniq = set(), []
        for b in bits:
            if b not in seen:
                seen.add(b)
                uniq.append(b)
        if uniq:
            chunks.append(" ".join(uniq))
    return " · ".join(chunks)


def parse_catalog(script_catalog):
    """Flat list of catalog entries (scripts and folder markers) with their flags."""
    entries = []
    for s in script_catalog.findall("Script"):
        opt = s.find("Options")
        uuid = s.find("UUID")
        entries.append({
            "id": s.attrib.get("id"),
            "name": s.attrib.get("name"),
            "is_folder": s.attrib.get("isFolder") == "True",
            "hidden": (opt.attrib.get("hidden") == "True") if opt is not None else None,
            "access": opt.attrib.get("access") if opt is not None else None,
            "run_full_access": (opt.attrib.get("runwithfullaccess") == "True") if opt is not None else None,
            "compatibility": opt.attrib.get("compatibility") if opt is not None else None,
            "last_modified_by": uuid.attrib.get("userName") if uuid is not None else None,
            "last_modified_account": uuid.attrib.get("accountName") if uuid is not None else None,
            "last_modified": uuid.attrib.get("timestamp") if uuid is not None else None,
            "modifications": uuid.attrib.get("modifications") if uuid is not None else None,
        })
    return entries


def parse_steps(steps_for_scripts):
    """Map script id -> ordered list of steps (index, name, enable, params)."""
    by_id = {}
    for sc in steps_for_scripts.findall("Script"):
        ref = sc.find("ScriptReference")
        ol = sc.find("ObjectList")
        if ref is None or ol is None:
            continue
        steps = []
        for st in ol.findall("Step"):
            steps.append({
                "index": int(st.attrib.get("index", "0")),
                "name": st.attrib.get("name", "?"),
                "enabled": st.attrib.get("enable") != "False",
                "params": summarize_params(st),
            })
        steps.sort(key=lambda s: s["index"])
        by_id[ref.attrib.get("id")] = steps
    return by_id


def build(xml_path):
    raw = Path(xml_path).read_bytes()
    root = ET.fromstring(raw)
    sc = root.find(".//ScriptCatalog")
    sfs = root.find(".//StepsForScripts")
    if sc is None:
        sys.exit(f"{xml_path} has no ScriptCatalog — is this a ScriptCatalog export?")

    entries = parse_catalog(sc)
    steps_by_id = parse_steps(sfs) if sfs is not None else {}

    scripts, folders = [], []
    for e in entries:
        if e["is_folder"]:
            folders.append(e)
        else:
            e = dict(e)
            e["steps"] = steps_by_id.get(e["id"], [])
            e["step_count"] = len(e["steps"])
            scripts.append(e)

    # Record the source path relative to the project when it lives inside it;
    # fall back to the bare filename for an input from elsewhere. (Never crash
    # on relative_to — inputs may be given as relative paths from the root.)
    try:
        source_rel = str(Path(xml_path).resolve().relative_to(ROOT))
    except ValueError:
        source_rel = Path(xml_path).name

    meta = {
        "file": root.attrib.get("File"),
        "saxml_version": root.attrib.get("version"),
        "source_app": root.attrib.get("Source"),
        "source_xml": source_rel,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "counts": {
            "folders": len(folders),
            "scripts": len(scripts),
            "scripts_with_steps": sum(1 for s in scripts if s["step_count"]),
            "empty_scripts": sum(1 for s in scripts if not s["step_count"]),
            "total_steps": sum(s["step_count"] for s in scripts),
        },
    }
    return meta, folders, scripts


def write_json(out, meta, folders, scripts):
    out.write_text(json.dumps(
        {"meta": meta, "folders": folders, "scripts": scripts},
        indent=2, ensure_ascii=False))


def write_readable(out, meta, folders, scripts):
    from collections import Counter
    L = []
    L.append(f"# Script knowledge base — {meta['file']}")
    L.append("")
    L.append(f"- Source: FMSaveAsXML {meta['saxml_version']} / FileMaker {meta['source_app']}")
    L.append(f"- From: `{meta['source_xml']}`  (sha256 `{meta['sha256'][:16]}…`)")
    c = meta["counts"]
    L.append(f"- Totals: **{c['scripts']} scripts** "
             f"({c['scripts_with_steps']} with steps, {c['empty_scripts']} empty), "
             f"**{c['folders']} folders**, **{c['total_steps']:,} steps**")
    L.append("")
    L.append("> Folders are listed flat: this lightweight ScriptCatalog export does not")
    L.append("> encode which scripts belong to which folder.")
    L.append("")

    L.append("## Folders")
    L.append("")
    for f in sorted(folders, key=lambda x: (x["name"] or "").lower()):
        L.append(f"- {f['name']}")
    L.append("")

    freq = Counter()
    for s in scripts:
        for st in s["steps"]:
            freq[st["name"]] += 1
    L.append("## Step-type frequency (top 30)")
    L.append("")
    L.append("| count | step |")
    L.append("|------:|------|")
    for name, n in freq.most_common(30):
        L.append(f"| {n} | {name} |")
    L.append("")

    L.append("## Scripts")
    L.append("")
    for s in sorted(scripts, key=lambda x: (x["name"] or "").lower()):
        flags = []
        if s["hidden"]:
            flags.append("hidden")
        if s["run_full_access"]:
            flags.append("full-access")
        flag = f" _[{', '.join(flags)}]_" if flags else ""
        L.append(f"### {s['name']}{flag}")
        L.append(f"`id {s['id']}` · {s['step_count']} steps · "
                 f"last modified {s['last_modified'] or '?'} by {s['last_modified_by'] or '?'}")
        L.append("")
        if not s["steps"]:
            L.append("_(empty script)_")
            L.append("")
            continue
        for st in s["steps"]:
            off = "" if st["enabled"] else "✗ "
            p = f" — {st['params']}" if st["params"] else ""
            L.append(f"{st['index'] + 1}. {off}{st['name']}{p}")
        L.append("")
    out.write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None,
                    help="path to a saxml_*.xml, from anywhere (default: newest under "
                         "this copy's schema/ddrs/); output always lands beside this script")
    args = ap.parse_args()

    xml_path = Path(args.input).resolve() if args.input else newest_export()
    run = re.sub(r"^saxml_|\.xml$", "", Path(xml_path).name)

    meta, folders, scripts = build(xml_path)

    pdir = ROOT / "schema" / "parsed"
    rdir = ROOT / "schema" / "readable"
    pdir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)
    pjson = pdir / f"{run}.json"
    rmd = rdir / f"{run}.md"
    write_json(pjson, meta, folders, scripts)
    write_readable(rmd, meta, folders, scripts)

    c = meta["counts"]
    print(f"→ parsed {meta['source_xml']}")
    print(f"  {c['scripts']} scripts ({c['scripts_with_steps']} with steps, "
          f"{c['empty_scripts']} empty) · {c['folders']} folders · {c['total_steps']:,} steps")
    print(f"✅ {pjson.relative_to(ROOT)}")
    print(f"✅ {rmd.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
