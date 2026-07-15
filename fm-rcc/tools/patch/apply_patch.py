"""Apply an FMUpgradeTool patch safely: backup -> validate -> smoke -> apply -> verify.

verify re-exports the patched file and re-diffs against the dev export: every
selected change must no longer appear in the diff. Never trust the tool's
"Patch File Applied" banner — it prints even on silent no-ops.
"""
from __future__ import annotations
import argparse, datetime, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from lxml import etree
import fm_export, saxml_parser, saxml_diff

FMUPG = "/usr/local/bin/FMUpgradeTool"


def _redacted(cmd: list[str]) -> str:
    """Command echo with the password masked — run logs and scrollback must
    never carry real credentials."""
    out = list(cmd)
    for i, tok in enumerate(out[:-1]):
        if tok == "-src_pwd":
            out[i + 1] = "***"
    return " ".join(out)


def _run(cmd: list[str], context: str = "") -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"FMUpgradeTool hung (>600s){' during ' + context if context else ''} "
            f"— command: {_redacted(cmd)}")
    print(f"$ {_redacted(cmd)}\n{r.stdout}{r.stderr}", file=sys.stderr)
    return r


def _upg(args: list[str], account: str, pwd: str, context: str = "") -> subprocess.CompletedProcess:
    cmd = [FMUPG] + args + ["-src_account", account] + (["-src_pwd", pwd] if pwd else [])
    return _run(cmd, context)


# Default backups dir anchors to the project root, not the CWD.
DEFAULT_BACKUPS = Path(__file__).resolve().parent.parent / "backups"


def apply_patch(target: Path, patch: Path, account="Admin", pwd="",
                backups_dir: Path = DEFAULT_BACKUPS, skip_smoke=False) -> dict:
    target, patch = Path(target).resolve(), Path(patch).resolve()
    if fm_export._file_locked(target):
        raise RuntimeError(f"{target.name} is open/locked — close it first (apply requires a closed file)")
    result = {"backup": None, "validated": False, "smoked": False,
              "applied": False, "restored": None}

    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / target.name
        shutil.copy2(target, work)
        r = _upg(["--validatePatch", "-src_path", str(work), "-patch_path", str(patch)],
                 account, pwd, "validatePatch (temp copy — target untouched)")
        if r.returncode != 0:
            raise RuntimeError(f"validatePatch failed ({r.returncode}) — aborting before touching {target.name}")
        result["validated"] = True
        if not skip_smoke:
            out = Path(td) / f"smoke-{target.name}"
            r = _upg(["--update", "-src_path", str(work), "-patch_path", str(patch),
                      "-dest_path", str(out), "-force"],
                     account, pwd, "smoke apply (temp copy — target untouched)")
            if r.returncode != 0 or not out.exists():
                raise RuntimeError(f"smoke apply failed ({r.returncode}) — aborting")
            result["smoked"] = True

    # Backup only now — validate/smoke failures above never touch the target,
    # so earlier backups would just be orphans. Verify the copy before
    # trusting it as the restore point.
    backups_dir = Path(backups_dir); backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backups_dir / f"{target.stem}-{ts}.fmp12"
    shutil.copy2(target, backup)
    if backup.stat().st_size != target.stat().st_size:
        raise RuntimeError(f"backup verification failed ({backup}) — aborting before apply")
    result["backup"] = str(backup)

    # The lock was checked at entry, but validate/smoke can take a while —
    # re-check immediately before the only step that mutates the target.
    if fm_export._file_locked(target):
        raise RuntimeError(
            f"{target.name} was opened while validating — close it and re-run "
            "(validate and smoke passed; nothing was modified)")
    try:
        r = _upg(["--update", "-inplace", "-src_path", str(target), "-patch_path", str(patch)],
                 account, pwd, f"IN-PLACE apply on {target.name} (backup: {backup})")
    except RuntimeError:
        result["restored"] = _restore(backup, target)
        print(json.dumps(result, indent=1))
        raise
    if r.returncode != 0:
        result["restored"] = _restore(backup, target)
        print(json.dumps(result, indent=1))
        raise RuntimeError(
            f"apply failed ({r.returncode}); target "
            f"{'auto-restored from' if result['restored'] else 'NOT restored — restore manually from'} {backup}")
    result["applied"] = True
    return result


def _restore(backup: Path, target: Path) -> bool:
    """Best-effort auto-restore after a failed in-place apply."""
    try:
        shutil.copy2(backup, target)
        print(f"auto-restored {target.name} from {backup}", file=sys.stderr)
        return True
    except Exception as e:  # surface, never mask the original failure
        print(f"AUTO-RESTORE FAILED ({e}) — restore manually from {backup}", file=sys.stderr)
        return False


def verify_applied(dev_export: Path, patched_file: Path, selection: Path,
                   workdir: Path, account="Admin", pwd="") -> dict:
    """Re-export patched file, re-diff vs dev export; selected keys must be gone."""
    workdir = Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    # The re-export MUST mirror the dev export's DDR setting — asymmetric
    # exports re-diff DDR-only script annotations as spurious modifieds.
    dev_root = etree.parse(saxml_parser.open_fmsavexml(dev_export)).getroot()
    dev_ddr = saxml_parser.parse_file_header(dev_root)["has_ddr_info"]
    new_xml = fm_export.export_xml(patched_file, workdir / "post.xml", account, pwd,
                                   include_ddr=dev_ddr)
    post_parsed = saxml_parser.snapshot(new_xml, workdir / "post_parsed")
    dev_parsed = saxml_parser.snapshot(dev_export, workdir / "dev_parsed")
    ignore_path = Path(__file__).parent / "saxml_ignore.json"
    ignore = json.loads(ignore_path.read_text()) if ignore_path.exists() else {}
    diff = saxml_diff.diff_snapshots(dev_parsed, post_parsed, ignore)
    still = {i["key"] for i in diff["items"]}
    selected = set(json.loads(Path(selection).read_text())["selected"])
    unresolved = sorted(selected & still)
    return {"verified": not unresolved, "unresolved": unresolved,
            "remaining_diff_items": len(diff["items"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("apply")
    a1.add_argument("target"); a1.add_argument("patch")
    a1.add_argument("--account", default="Admin"); a1.add_argument("--pwd", default="")
    a1.add_argument("--skip-smoke", action="store_true")
    a1.add_argument("--backups-dir", default=str(DEFAULT_BACKUPS))
    a2 = sub.add_parser("verify")
    a2.add_argument("--dev-export", required=True); a2.add_argument("--patched", required=True)
    a2.add_argument("--selection", required=True); a2.add_argument("--workdir", required=True)
    a2.add_argument("--account", default="Admin"); a2.add_argument("--pwd", default="")
    a = ap.parse_args()
    if a.cmd == "apply":
        print(json.dumps(apply_patch(Path(a.target), Path(a.patch), a.account, a.pwd,
                                     backups_dir=Path(a.backups_dir),
                                     skip_smoke=a.skip_smoke), indent=1))
    else:
        out = verify_applied(Path(a.dev_export), Path(a.patched), Path(a.selection),
                             Path(a.workdir), a.account, a.pwd)
        print(json.dumps(out, indent=1))
        sys.exit(0 if out["verified"] else 1)
