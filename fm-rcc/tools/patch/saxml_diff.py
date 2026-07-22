"""Diff two parsed SaXML snapshots (dev vs prod) into diff.json.

added    = in dev, not prod   (AddAction candidate)
removed  = in prod, not dev   (DeleteAction candidate)
modified = both, but shallow attrs or deep content hash differ (ReplaceAction candidate)

ignored items ARE included in output (for display); downstream consumers MUST skip items where ignored=True before generating patches.
duplicate_name=True items carry only the LAST same-named object (dict-keyed by name) and are forced to patchability=manual — resolve duplicates in FileMaker before patching.
"""
from __future__ import annotations
import argparse, fnmatch, json
from pathlib import Path

KINDS = {  # kind -> (snapshot file, shallow attrs compared for 'modified' detail)
    "base_table": ("base_tables.json", ["comment"]),
    "field": ("fields.json", ["fieldtype", "datatype", "comment", "global", "repetitions", "calc_text"]),
    "table_occurrence": ("table_occurrences.json", ["type", "base_table_name"]),
    "relationship": ("relationships.json", ["predicates"]),
    "script": ("scripts.json", ["is_folder", "hidden", "run_with_full_access"]),
    "layout": ("layouts.json", ["table_occurrence", "width"]),
    "value_list": ("value_lists.json", ["source"]),
    "custom_function": ("custom_functions.json", ["signature", "parameters"]),
    "external_data_source": ("external_data_sources.json", ["type", "paths"]),
}

PATCHABILITY = {
    "added": {"base_table": "proven", "field": "proven", "table_occurrence": "proven",
              "relationship": "proven", "layout": "proven", "script": "caution",
              "value_list": "caution",
              # custom_function ADD silently no-ops. The matrix rated this
              # caution on the docs; a real run (2026-07-22, FMUpgradeTool
              # 22.0.5.500) proved otherwise: a patch carrying two
              # <CustomFunction> elements inside CustomFunctionsCatalog printed
              # "Patch File Applied" and produced a file with ZERO custom
              # functions. Nothing lands and nothing errors. Manual only —
              # deliver via clipboard XML (fm-xml skill) instead.
              "custom_function": "manual",
              "external_data_source": "caution"},
    "modified": {"field": "caution", "script": "caution"},   # everything else: manual
    "removed": {"base_table": "caution", "field": "caution", "table_occurrence": "caution",
                "script": "caution", "layout": "caution", "value_list": "caution",
                "custom_function": "caution"},                # everything else: manual
}


def obj_key(kind: str, o: dict) -> str:
    if kind == "field":
        return f"field:{o.get('table_name','')}::{o.get('name','')}"
    if kind == "relationship":
        sig = ";".join(f"{p.get('left_field','')}{p.get('op','')}{p.get('right_field','')}" for p in o.get("predicates", []))
        return f"relationship:{o.get('left_to','?')}|{o.get('right_to','?')}|{sig}"
    return f"{kind}:{o.get('name','')}"


def display_name(kind: str, o: dict) -> str:
    if kind == "relationship":
        return f"{o.get('left_to','?')} ↔ {o.get('right_to','?')}"
    return o.get("name") or "(unnamed)"


def _load(parsed_dir: Path, fname: str) -> list[dict]:
    p = parsed_dir / fname
    return json.loads(p.read_text()) if p.exists() else []


def _ignored(kind: str, key_name: str, ignore: dict) -> bool:
    return any(fnmatch.fnmatchcase(key_name, pat) for pat in ignore.get(kind, []))


def _dupe_keys(kind: str, objs: list[dict]) -> set[str]:
    seen, dupes = set(), set()
    for o in objs:
        k = obj_key(kind, o)
        if k in seen:
            dupes.add(k)
        seen.add(k)
    return dupes


def diff_snapshots(dev_dir: Path, prod_dir: Path, ignore: dict) -> dict:
    dev_meta = json.loads((dev_dir / "_meta.json").read_text())
    prod_meta = json.loads((prod_dir / "_meta.json").read_text())
    items = []
    for kind, (fname, attrs) in KINDS.items():
        dev_objs, prod_objs = _load(dev_dir, fname), _load(prod_dir, fname)
        dev = {obj_key(kind, o): o for o in dev_objs}
        prod = {obj_key(kind, o): o for o in prod_objs}
        dupes = _dupe_keys(kind, dev_objs) | _dupe_keys(kind, prod_objs)
        for key in sorted(dev.keys() | prod.keys()):
            d, p = dev.get(key), prod.get(key)
            name_part = key.split(":", 1)[1]
            base = {
                "key": key, "kind": kind,
                "name": display_name(kind, d or p),
                "table": (d or p).get("table_name") if kind == "field" else None,
                "ignored": _ignored(kind, name_part, ignore),
                "duplicate_name": key in dupes,
            }
            if d and not p:
                tier = PATCHABILITY["added"].get(kind, "manual")
                # Container field Add silently no-ops (proven 2026-07-22,
                # FMUpgradeTool 22.0.5.500): validatePatch passed, smoke
                # passed, "Patch File Applied" printed, fields absent on
                # re-export. Not the storage XML — a corrected
                # <Storage global="False" maxRepetitions="1"/> no-oped
                # identically. It is the datatype. Deliver containers via
                # clipboard XML (fm-xml skill) instead.
                if kind == "field" and d.get("datatype") == "Container":
                    tier = "manual"
                if key in dupes:
                    tier = "manual"
                items.append(base | {"change": "added",
                    "patchability": tier,
                    "summary": _summary(kind, d), "changed_attrs": [], "dev": d, "prod": None})
            elif p and not d:
                tier = PATCHABILITY["removed"].get(kind, "manual")
                if key in dupes:
                    tier = "manual"
                items.append(base | {"change": "removed",
                    "patchability": tier,
                    "summary": _summary(kind, p), "changed_attrs": [], "dev": None, "prod": p})
            else:
                changed = [a for a in attrs if d.get(a) != p.get(a)]
                if d.get("_hash") != p.get("_hash") and not changed:
                    changed = ["(deep structure)"]
                if changed:
                    tier = PATCHABILITY["modified"].get(kind, "manual")
                    if key in dupes:
                        tier = "manual"
                    items.append(base | {"change": "modified",
                        "patchability": tier,
                        "summary": ", ".join(changed) + " changed",
                        "changed_attrs": changed, "dev": d, "prod": p})
    return {
        "meta": {
            "dev_export": dev_meta["export_path"], "prod_export": prod_meta["export_path"],
            "dev_parsed": str(dev_dir.resolve()), "prod_parsed": str(prod_dir.resolve()),
            "saxml_version": dev_meta["fmsavexml_version"],
            "dev_file": dev_meta["filename"], "prod_file": prod_meta["filename"],
        },
        "items": items,
    }


def _summary(kind: str, o: dict) -> str:
    if kind == "field":
        t = o.get("fieldtype", "?")
        return f"{o.get('datatype','?')} ({t})" + (" — calc" if o.get("calc_text") else "")
    if kind == "relationship":
        return f"{len(o.get('predicates', []))} predicate(s)"
    return ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dev_parsed"); ap.add_argument("prod_parsed")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--ignore", default=str(Path(__file__).parent / "saxml_ignore.json"))
    a = ap.parse_args()
    ignore = json.loads(Path(a.ignore).read_text()) if Path(a.ignore).exists() else {}
    result = diff_snapshots(Path(a.dev_parsed), Path(a.prod_parsed), ignore)
    Path(a.out).write_text(json.dumps(result, indent=1))
    counts = {}
    for it in result["items"]:
        counts[it["change"]] = counts.get(it["change"], 0) + 1
    print(f"diff written to {a.out}: {counts}")
