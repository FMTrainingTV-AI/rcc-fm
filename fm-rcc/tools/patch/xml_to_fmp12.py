#!/usr/bin/env python3
"""Convert a Save-as-XML export back into a working .fmp12 — one command.

There is no Claris CLI verb for XML -> file (FMDeveloperTool only goes the
other way), so this tool builds the file: it copies a known-good base file,
then grows it to match the export via the patch pipeline (diff -> generate ->
apply -> verify), all invisibly. What you see is: export in, FileMaker file
out, verify verdict printed.

Usage (run from the project root):
  python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/xml_to_fmp12.py                        # newest export under ./schema/ddrs/ (or ./_fm/schema/ddrs/)
  python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/xml_to_fmp12.py --input <export.xml>   # a specific export (from anywhere)
  python3 ${CLAUDE_PLUGIN_ROOT}/tools/patch/xml_to_fmp12.py --out <target.fmp12>   # choose the output (default: ./dev/<export-name>.fmp12)

CREATION-ONLY: the target must not exist (no --force; delete it yourself).
This tool never modifies an existing file — that's what keeps it outside the
patch pipeline's review gates. To change a real file, use the fm-patch skill.

The rebuild carries whatever catalogs the export holds. A ScriptCatalog-only
export yields a scripts-only skeleton whose step references to absent tables/
fields/layouts show as missing inside the file — export more catalogs first
if you need more of the structure. Accounts, privilege sets, themes, and
custom menus never travel (manual-tier; FileMaker-only territory). A base
pre-loaded with the source file's themes (--base) unblocks that source's
themed layouts — the generator matches layout->theme deps by name.

Requires the Claris CLI tools (FMDeveloperTool / FMUpgradeTool). Python
stdlib only.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent            # tools/patch/ — gen_patch & co. live here
PLUGIN = HERE.parent.parent                       # the plugin root


def newest_export():
    roots = (Path.cwd() / "schema" / "ddrs", Path.cwd() / "_fm" / "schema" / "ddrs")
    candidates = sorted(c for r in roots for c in r.glob("*/saxml_*.xml"))
    if not candidates:
        sys.exit("No exports found under ./schema/ddrs/ or ./_fm/schema/ddrs/ — "
                 "pass --input, or export first (fm-patch export / remote export).")
    return candidates[-1]


def generator_kinds(tools):
    """The kinds gen_patch can actually Add — read from the module, not guessed."""
    import importlib.util
    sys.path.insert(0, str(tools))   # gen_patch imports sibling modules bare
    try:
        spec = importlib.util.spec_from_file_location("gen_patch", tools / "gen_patch.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return set(mod.SUPPORTED_KINDS)
    finally:
        sys.path.pop(0)


def run(label, cmd, quiet=False):
    print(f"→ {label}")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        lines = [l for l in (r.stdout + "\n" + r.stderr).splitlines()
                 if l.strip() and "warning:" not in l]
        print("\n".join(lines[-30:]))
        sys.exit(f"✗ {label} failed (exit {r.returncode})")
    if not quiet and r.stdout.strip():
        for line in r.stdout.strip().splitlines()[-3:]:
            print(f"  {line}")
    return r.stdout


# Offender shapes in gen_patch's DependencyError output. The offender is the
# selected object that can't be built: a layout whose theme the base lacks, a
# script whose step references can never resolve (dropped deps, anonymous
# import-map fields), a relationship keyed on a broken reference, etc.
OFFENDER_PATTERNS = (
    # direct-key offenders: "  <kind>:<name>: <reason>"
    re.compile(r"^\s+((?:base_table|field|table_occurrence|relationship|layout"
               r"|value_list|custom_function|script):.+?): ", re.MULTILINE),
    # script step scopes: "  steps(script:<name>): <reason>"
    re.compile(r"^\s+steps\((script:.+)\): (?:references|unresolved)", re.MULTILINE),
)


def parse_offenders(text, selected):
    hits = set()
    for pat in OFFENDER_PATTERNS:
        hits.update(m.group(1) for m in pat.finditer(text))
    # "fields(<table>)" labels identify only the table's fields FRAGMENT — the
    # generator can't say which field carries the broken reference, so every
    # selected field of that table goes (source-file brokenness like
    # '<Table Missing>' lands here; finer granularity is a gen_patch upgrade).
    for m in re.finditer(r"^\s+fields\(([^)]+)\):", text, re.MULTILINE):
        prefix = f"field:{m.group(1)}::"
        hits.update(k for k in selected if k.startswith(prefix))
    return hits & selected


def main():
    ap = argparse.ArgumentParser(description="Save-as-XML export -> new .fmp12")
    ap.add_argument("--input", default=None,
                    help="path to a saxml_*.xml export (default: newest under ./schema/ddrs/ or ./_fm/schema/ddrs/)")
    ap.add_argument("--out", default=None,
                    help="target .fmp12 to create (default: ./dev/<export-name>.fmp12); must not exist")
    ap.add_argument("--base", default=None,
                    help="base .fmp12 to grow from (default: the plugin's fmbase.fmp12)")
    ap.add_argument("--tools", default=None,
                    help="patch tools dir (default: this tool's own directory)")
    ap.add_argument("--account", default="Admin", help="base-file account (default: Admin)")
    ap.add_argument("--pwd", default="", help="base-file password (default: blank)")
    ap.add_argument("--keep-workdir", action="store_true",
                    help="keep the intermediate build dir for inspection")
    args = ap.parse_args()

    tools = Path(args.tools) if args.tools else HERE
    base = Path(args.base) if args.base else PLUGIN / "resources" / "fmbase.fmp12"
    xml_in = Path(args.input).resolve() if args.input else newest_export()
    out = Path(args.out).resolve() if args.out else Path.cwd() / "dev" / f"{xml_in.stem.removeprefix('saxml_')}.fmp12"

    for p, what in ((tools, "patch tools dir"), (base, "base file"), (xml_in, "input export")):
        if not p.exists():
            sys.exit(f"✗ {what} not found: {p}")
    if out.exists():
        sys.exit(f"✗ target already exists: {out} — this tool only CREATES files; "
                 "delete the target yourself if you mean it.")

    wd = out.parent / f".{out.stem}-build"
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"in:   {xml_in}")
    print(f"out:  {out}")
    print(f"base: {base}")
    t0 = time.time()

    # 1. the target starts life as a copy of the base file
    shutil.copy2(base, out)
    try:
        build(args, tools, base, xml_in, out, wd, t0)
    except BaseException:
        if out.exists():
            out.unlink()
            print(f"  (removed half-built target {out.name}; workdir kept at {wd})")
        raise


def build(args, tools, base, xml_in, out, wd, t0):
    # 2. export the copy, parse both sides, diff
    run("export base copy as XML", ["python3", tools / "fm_export.py", out,
                                    "-o", wd / "base.xml", "--stamp-guids"], quiet=True)
    run("parse input export", ["python3", tools / "saxml_parser.py", xml_in, "-o", wd / "dev_parsed"], quiet=True)
    run("parse base export", ["python3", tools / "saxml_parser.py", wd / "base.xml", "-o", wd / "prod_parsed"], quiet=True)
    run("diff", ["python3", tools / "saxml_diff.py", wd / "dev_parsed", wd / "prod_parsed",
                 "-o", wd / "diff.json"])

    # 3. select every buildable "added" object; report what can't travel
    kinds_ok = generator_kinds(tools)
    diff = json.loads((wd / "diff.json").read_text())
    added = [i for i in diff["items"] if i.get("change") == "added" and not i.get("ignored")]
    buildable = [i for i in added if i.get("patchability") in ("proven", "caution")
                 and i.get("kind") in kinds_ok
                 and not i.get("duplicate_name")]
    skipped = [i for i in added if i not in buildable]
    if not buildable:
        sys.exit("✗ nothing buildable in this export vs. the base — is the export empty?")
    kinds = {}
    for i in buildable:
        kinds[i["kind"]] = kinds.get(i["kind"], 0) + 1
    print(f"  candidates: {len(buildable)} objects: " + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    if skipped:
        print(f"  SKIPPED {len(skipped)} manual-tier/duplicate objects (FileMaker-only): "
              + ", ".join(sorted({i['kind'] for i in skipped})))

    # 4.–6. generate → apply → verify, with two feedback loops:
    #   inner (gen): prune what the generator PROVES unbuildable (e.g. layouts
    #     whose theme the base lacks — full fidelity needs a theme-prepared base)
    #   outer (verify): prune what FMUpgradeTool silently no-ops — the banner
    #     lies, so only the re-export re-diff decides, and it feeds back here.
    #   KNOWN LIMIT (observed at ~2,000-object scale): FMUpgradeTool can abort
    #   mid-patch while printing "applied" — one bad apply then reads as mass
    #   per-object refusal here and over-prunes. Queued fix: retry-before-drop
    #   (re-apply a patch of just the unresolved before dropping any of them);
    #   wave-apply per catalog is the fallback shape. Until then, check big
    #   thin-looking results against --keep-workdir + FMUpgradeTool -v.
    selected = {i["key"] for i in buildable}
    dropped_verify = set()
    for vround in range(1, 4):
        if vround > 1:
            out.unlink()
            shutil.copy2(base, out)

        print(f"→ generate build patch (pruning unbuildables)" +
              (f" — verify round {vround}" if vround > 1 else ""))
        for rnd in range(1, 11):
            (wd / "selection.json").write_text(json.dumps({"selected": sorted(selected)}))
            r = subprocess.run(["python3", str(tools / "gen_patch.py"),
                                "--dev-export", str(xml_in), "--prod-export", str(wd / "base.xml"),
                                "--diff", str(wd / "diff.json"), "--selection", str(wd / "selection.json"),
                                "-o", str(wd / "patch.xml"), "--allow-caution"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                print(f"  patch generated: {len(selected)} of {len(buildable)} objects survive")
                break
            offenders = parse_offenders(r.stdout + "\n" + r.stderr, selected)
            if not offenders:
                lines = [l for l in (r.stdout + "\n" + r.stderr).splitlines()
                         if l.strip() and "warning:" not in l]
                print("\n".join(lines[-30:]))
                sys.exit(f"✗ gen_patch failed with no prunable offenders (exit {r.returncode})")
            selected -= offenders
            by_kind = {}
            for k in offenders:
                kk = k.split(":", 1)[0]
                by_kind[kk] = by_kind.get(kk, 0) + 1
            print("  prune round %d: dropped %s → %d remain"
                  % (rnd, ", ".join(f"{n} {k}" for k, n in sorted(by_kind.items())), len(selected)))
            if not selected:
                sys.exit("✗ everything pruned away — nothing buildable against this base")
        else:
            sys.exit("✗ prune loop did not converge in 10 rounds")

        run("apply (backup → validate → smoke → in-place)",
            ["python3", tools / "apply_patch.py", "apply", out, wd / "patch.xml",
             "--account", args.account, "--pwd", args.pwd, "--backups-dir", wd / "backups"])

        print("→ verify (re-export + re-diff)")
        r = subprocess.run(["python3", str(tools / "apply_patch.py"), "verify",
                            "--dev-export", str(xml_in), "--patched", str(out),
                            "--selection", str(wd / "selection.json"),
                            "--workdir", str(wd / f"verify{vround}"),
                            "--account", args.account, "--pwd", args.pwd],
                           capture_output=True, text=True)
        try:
            v = json.loads(r.stdout[r.stdout.find("{"):])
        except ValueError:
            print(r.stdout[-2000:])
            print(r.stderr[-2000:], file=sys.stderr)
            sys.exit("✗ verify produced no parseable result")
        if v.get("verified"):
            print(f"  verified: all {len(selected)} selected objects present in the rebuilt file")
            break
        unresolved = set(v.get("unresolved", [])) & selected
        if not unresolved:
            print(json.dumps(v, indent=2))
            sys.exit("✗ verify failed with nothing prunable — investigate the workdir")
        dropped_verify |= unresolved
        selected -= unresolved
        print(f"  verify round {vround}: {len(unresolved)} silently no-opped — "
              f"dropping and rebuilding: {', '.join(sorted(unresolved)[:5])}")
        if not selected:
            sys.exit("✗ everything dropped at verify — nothing survives against this base")
    else:
        sys.exit("✗ did not verify clean within 3 rounds")

    # 7. consistency check straight from the horse's mouth
    fmdev = shutil.which("FMDeveloperTool") or "/usr/local/bin/FMDeveloperTool"
    run("consistency check", [fmdev, "--checkConsistency", out], quiet=False)

    if not args.keep_workdir:
        shutil.rmtree(wd)
    print(f"✅ {out}")
    print(f"   {out.stat().st_size:,} bytes · {len(selected)} of {len(buildable)} candidate objects built · "
          f"{time.time() - t0:.0f}s")
    if dropped_verify:
        print(f"   ⚠ {len(dropped_verify)} dropped at verify (FMUpgradeTool silently refused them): "
              + ", ".join(sorted(dropped_verify)[:8]))


if __name__ == "__main__":
    main()
