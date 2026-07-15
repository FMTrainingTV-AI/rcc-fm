"""Headless FMSaveAsXML export of a local .fmp12 via FMDeveloperTool.

If the file is open in FileMaker Pro, it is closed first via AppleScript and
reopened afterward (unless --keep-closed). The CLI tools require closed files.
"""
from __future__ import annotations
import argparse, os, subprocess, sys, time
from pathlib import Path

FMDEV = "/usr/local/bin/FMDeveloperTool"
FMUPG = "/usr/local/bin/FMUpgradeTool"
FM_APP = "FileMaker Pro"  # 26.x; "FileMaker Pro 2025" is also installed — always target 26


def _osascript(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"FileMaker Pro did not respond to automation within {timeout}s — "
            "grant Automation permission in System Settings → Privacy & Security → "
            "Automation, or close the file manually"
        )
    if r.returncode != 0:
        raise RuntimeError(f"osascript failed: {r.stderr.strip()}")
    return r.stdout.strip()


def pro_running() -> bool:
    """Check if FileMaker Pro is running using pgrep (fast; avoids System Events timeout)."""
    r = subprocess.run(["pgrep", "-x", FM_APP], capture_output=True)
    return r.returncode == 0


def _file_locked(fmp12: Path) -> bool:
    # rc=1 means "no openers" OR lsof permission error — we accept the false negative
    # because FMDeveloperTool fails loudly on a genuinely locked file.
    # Note: pro_running() uses exact pgrep match (-x) while this greps the lsof COMMAND
    # column substring; fmserverd locks route to the "locked by another process" branch
    # in export_xml, which is correct.
    r = subprocess.run(["lsof", "--", str(fmp12)], capture_output=True, text=True)
    return r.returncode == 0 and "FileMaker" in r.stdout


def is_open_in_pro(fmp12: Path) -> bool:
    """Return True iff FileMaker Pro is running AND has the file locked (lsof+pgrep; no AE)."""
    return pro_running() and _file_locked(fmp12)


def close_in_pro(fmp12: Path, timeout: int = 30) -> None:
    """Close *fmp12* in FileMaker Pro via AppleScript, then wait until the lock is released.

    Window titles are typically the bare file stem.  The script tries an exact
    name match first and falls back to a ``contains`` match inside a single
    osascript call.

    Notes:
    - On first interactive use macOS will show a TCC permission prompt for
      Automation; grant it in System Settings → Privacy & Security → Automation.
    - The stem-contains fallback may match unrelated windows — only call this
      when you are confident the stem uniquely identifies the target file.
    """
    stem = Path(fmp12).stem
    script = (
        f'with timeout of 8 seconds\n'
        f'  tell application "{FM_APP}"\n'
        f'    if (count of (every window whose name is "{stem}")) > 0 then\n'
        f'      close (every window whose name is "{stem}")\n'
        f'    else\n'
        f'      close (every window whose name contains "{stem}")\n'
        f'    end if\n'
        f'  end tell\n'
        f'end timeout'
    )
    _osascript(script, timeout=10)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _file_locked(fmp12):
            return
        time.sleep(0.5)
    raise TimeoutError(
        f"{Path(fmp12).name} still locked after {timeout}s — the window may "
        f"already be closed with {FM_APP} still flushing; wait and retry, and "
        "reopen the file manually if needed")


def open_in_pro(fmp12: Path) -> None:
    subprocess.run(["open", "-a", FM_APP, str(fmp12)], check=True)


def stamp_guids(fmp12: Path, account: str = "Admin", pwd: str = "") -> None:
    """Claris best practice: stable UUIDs before export so patches can reference them.

    Crash-safe: stamps into a temp copy via ``-dest_path`` and atomically
    renames it over the source on success. A timeout or crash mid-write can
    therefore never corrupt the source (an earlier ``-inplace`` variant
    could). Without either flag FMUpgradeTool writes a separate
    ``<name> upgraded.fmp12`` and leaves the source untouched.
    """
    fmp12 = Path(fmp12)
    tmp = fmp12.with_name(f".{fmp12.stem}.stamping{fmp12.suffix}")
    cmd = [FMUPG, "--generateGUIDs", "-src_path", str(fmp12),
           "-dest_path", str(tmp), "-force", "-src_account", account]
    if pwd:
        cmd += ["-src_pwd", pwd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "FMUpgradeTool hung (>600s) stamping GUIDs — source file untouched; "
            "check the file isn't locked and the tool installation")
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"generateGUIDs failed ({r.returncode}): {r.stdout} {r.stderr}")
    os.replace(tmp, fmp12)


def export_xml(fmp12: Path, out_xml: Path, account: str = "Admin", pwd: str = "",
               include_ddr: bool = False, do_stamp_guids: bool = False,
               keep_closed: bool = False) -> Path:
    fmp12, out_xml = Path(fmp12).resolve(), Path(out_xml).resolve()
    if not fmp12.exists():
        raise FileNotFoundError(fmp12)
    out_xml.parent.mkdir(parents=True, exist_ok=True)
    reopen = False
    if _file_locked(fmp12):
        if pro_running():
            close_in_pro(fmp12)
            reopen = not keep_closed
        else:
            raise RuntimeError(
                f"{fmp12.name} is locked by another process (hosted? other client?)"
            )
    try:
        if do_stamp_guids:
            stamp_guids(fmp12, account, pwd)
        cmd = [FMDEV, "--saveAsXML", str(fmp12), account, pwd, "-t", str(out_xml), "-f"]
        if include_ddr:
            cmd.append("-id")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "FMDeveloperTool hung (>300s) — check the file isn't locked and the tool installation"
            )
        if r.returncode != 0 or not out_xml.exists():
            raise RuntimeError(f"saveAsXML failed ({r.returncode}): {r.stdout} {r.stderr}")
    finally:
        if reopen:
            try:
                open_in_pro(fmp12)
            except Exception as e:
                print(f"Warning: could not reopen {fmp12.name}: {e}", file=sys.stderr)
    return out_xml


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fmp12"); ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--account", default="Admin"); ap.add_argument("--pwd", default="")
    ap.add_argument("--ddr-info", action="store_true")
    ap.add_argument("--stamp-guids", action="store_true")
    ap.add_argument("--keep-closed", action="store_true")
    a = ap.parse_args()
    p = export_xml(a.fmp12, a.out, a.account, a.pwd, a.ddr_info, a.stamp_guids, a.keep_closed)
    print(p)
