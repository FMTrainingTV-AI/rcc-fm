"""
FMSaveAsXML parser — shared utilities.

FMSaveAsXML is FileMaker's round-trip schema format (re-imported via the
Solution Upgrade Tool in FM 2026+). It differs from DDR in three ways:

  1. Encoding varies by exporter version: older exports are UTF-16 with BOM;
     FM 2026 (Source 26.0.1, format 2.3.0.0) emits UTF-8. `_detect_encoding`
     handles both.
  2. Wrapped in <FMSaveAsXML>/<Structure>/<AddAction>/<Catalog…> — a tree of
     "things to add to a blank file" rather than a description of an existing one.
  3. May carry analysis detail (script-step text, calc chunks, where-used) in a
     <DDR_INFO> block when "Include details for analysis tools" was checked —
     signalled by Has_DDR_INFO="True" on the root. Without it, FMSaveAsXML lacks
     the cross-references DDR has. (This parser indexes the structure; DDR_INFO
     mining is left for a later tool.)

This module owns the decoding and the per-catalog extraction logic. Splitter
and summary tools depend on it.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
from typing import Iterator

from lxml import etree


def open_fmsavexml(path: str | Path) -> io.BytesIO:
    """Read an FMSaveAsXML export (UTF-8 or UTF-16) and return a BytesIO of UTF-8 for lxml.

    Encoding is detected per `_detect_encoding`. lxml's iterparse on UTF-16
    directly is fragile (BOM handling differs across libxml2 builds), so we
    decode once up front and normalize to UTF-8; the file is small enough that
    the memory cost is negligible.
    """
    raw = Path(path).read_bytes()
    text = raw.decode(_detect_encoding(raw))
    # Strip the XML declaration since we're re-encoding
    if text.startswith("<?xml"):
        end = text.find("?>") + 2
        text = text[end:].lstrip()
    return io.BytesIO(b'<?xml version="1.0" encoding="UTF-8"?>\n' + text.encode("utf-8"))


def iter_named(elem: etree._Element, tag: str) -> Iterator[etree._Element]:
    """Yield direct or descendant <tag> elements."""
    return elem.iter(tag)


def attrs(elem: etree._Element) -> dict:
    """Return element attributes as a plain dict."""
    return dict(elem.attrib)


def child_text(elem: etree._Element, tag: str) -> str | None:
    c = elem.find(tag)
    return c.text if c is not None else None


# --- Hashing ----------------------------------------------------------------

_STRIP_ATTRS = {"UUID", "hash", "SourceUUID"}


def compute_hash(elem) -> str:
    """Stable content hash of an object's XML, ignoring UUIDs, ids, hashes, DDRREF.
    Lets the differ detect deep changes (script steps, validation, layout objects)
    without parsing them.

    Ignored: ``UUID``, ``SourceUUID`` and ``OwnerID`` child elements (UUID and
    SourceUUID also in attribute form), ``DDRREF`` subtrees, ``id`` and
    ``nextvalue`` attributes throughout. ``OwnerID`` is UUID-class identity
    metadata (a UUID on BaseTable; FMUpgradeTool stamps an EMPTY ``<OwnerID/>``
    onto every script step it patches in — verified by round trip 2026-06-12),
    so keeping it would make every patched-in script hash as modified forever.

    Two caveats callers must know:
    (a) Child-element ``id`` attributes are stripped throughout the entire subtree
        (not just the top-level definition's own id), so sibling reorderings that
        are distinguished *only* by child ``id`` values are NOT detected.
    (b) The return value is a truncated SHA-256 hex digest, 128 bits (32 hex chars).
    """
    e = copy.deepcopy(elem)
    for ddr in e.iter("DDRREF"):
        if ddr.getparent() is not None:
            ddr.getparent().remove(ddr)
    for u in list(e.iter("UUID")):
        if u.getparent() is not None:
            u.getparent().remove(u)
    for su in list(e.iter("SourceUUID")):
        if su.getparent() is not None:
            su.getparent().remove(su)
    for oid in list(e.iter("OwnerID")):
        if oid.getparent() is not None:
            oid.getparent().remove(oid)
    for node in e.iter():
        for a in list(node.attrib):
            if a in _STRIP_ATTRS or a == "id" or a == "nextvalue":
                del node.attrib[a]
    # c14n2 is available in lxml 6.1 and produces deterministic output
    return hashlib.sha256(etree.tostring(e, method="c14n2")).hexdigest()[:32]


# --- Catalog extractors -----------------------------------------------------
# Each returns a list of dicts. They're intentionally shallow — anything richer
# (calc text, script step body, layout objects) is left for later tools so the
# parser stays fast and the JSON stays diff-able.


def parse_base_tables(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("BaseTableCatalog"):
        for bt in cat.iter("BaseTable"):
            out.append({
                "id": bt.get("id"),
                "name": bt.get("name"),
                "comment": bt.get("comment") or "",
                "uuid": _uuid(bt),
                "_hash": compute_hash(bt),
            })
    return out


def parse_fields(root: etree._Element) -> list[dict]:
    """Fields, grouped per base table. Returns one dict per field."""
    out = []
    for ffts in root.iter("FieldsForTables"):
        for fc in ffts.iter("FieldCatalog"):
            btref = fc.find("BaseTableReference")
            table_id = btref.get("id") if btref is not None else None
            table_name = btref.get("name") if btref is not None else None
            ol = fc.find("ObjectList")
            if ol is None:
                continue
            # Two shapes of <Field> can appear in an ObjectList:
            #   1. Definition: <Field id name fieldtype datatype> + Storage/Validation/AutoEnter
            #   2. Calc body:  <Field><FieldReference id name><Calculation/> — formula text
            #                  attached to the calc field by id. We pair these in below.
            calc_bodies: dict[str, str] = {}
            for f in ol.iter("Field"):
                if f.get("name"):
                    continue
                fr = f.find("FieldReference")
                if fr is None:
                    continue
                calc = fr.find("Calculation/Text")
                if calc is not None and fr.get("id"):
                    calc_bodies[fr.get("id")] = (calc.text or "").strip()

            for f in ol.iter("Field"):
                if not f.get("name"):
                    continue  # already harvested above
                storage = f.find("Storage")
                fid = f.get("id")
                # Prefer sibling-shape calc body; fall back to inline Calculation
                # that is a direct child of the Field element (NOT under AutoEnter
                # or Validation, which also contain Calculation children).
                calc_text = calc_bodies.get(fid)
                if calc_text is None:
                    inline_calc = f.find("Calculation")
                    if inline_calc is not None:
                        t = inline_calc.find("Text")
                        if t is not None:
                            calc_text = (t.text or "").strip() or None
                out.append({
                    "table_id": table_id,
                    "table_name": table_name,
                    "id": fid,
                    "name": f.get("name"),
                    "fieldtype": f.get("fieldtype"),  # Normal, Calculation, Summary
                    "datatype": f.get("datatype"),    # Text, Number, Date, Time, Timestamp, Container
                    "comment": f.get("comment") or "",
                    "uuid": _uuid(f),
                    "global": (storage.get("global") == "True") if storage is not None else False,
                    "repetitions": int(storage.get("maxRepetitions", "1")) if storage is not None else 1,
                    "calc_text": calc_text,
                    "_hash": compute_hash(f),
                })
    return out


def parse_table_occurrences(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("TableOccurrenceCatalog"):
        for to in cat.iter("TableOccurrence"):
            bt = to.find("BaseTableSourceReference/BaseTableReference")
            out.append({
                "id": to.get("id"),
                "name": to.get("name"),
                "type": to.get("type"),
                "base_table_id": bt.get("id") if bt is not None else None,
                "base_table_name": bt.get("name") if bt is not None else None,
                "uuid": _uuid(to),
                "_hash": compute_hash(to),
            })
    return out


def parse_relationships(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("RelationshipCatalog"):
        for rel in cat.iter("Relationship"):
            left = rel.find("LeftTable/TableOccurrenceReference")
            right = rel.find("RightTable/TableOccurrenceReference")
            preds = []
            for jp in rel.iter("JoinPredicate"):
                lf = jp.find("LeftField/FieldReference")
                rf = jp.find("RightField/FieldReference")
                preds.append({
                    "op": jp.get("type"),
                    "left_field": lf.get("name") if lf is not None else None,
                    "right_field": rf.get("name") if rf is not None else None,
                })
            out.append({
                "id": rel.get("id"),
                "uuid": _uuid(rel),
                "left_to": left.get("name") if left is not None else None,
                "right_to": right.get("name") if right is not None else None,
                "predicates": preds,
                "_hash": compute_hash(rel),
            })
    return out


def script_steps_index(root: etree._Element) -> tuple[dict, dict]:
    """Index each script's step-body fragment under <StepsForScripts>.

    FMSaveAsXML splits a script in two: the CATALOG entry (ScriptCatalog >
    Script: name/options/UUID) and the STEP BODIES, which live in a separate
    <StepsForScripts> element (the last child of Structure/AddAction, analogous
    to FieldsForTables). Each StepsForScripts > Script wraps a
    <ScriptReference id name UUID> linking back to the catalog entry (the UUID
    attribute equals the catalog Script's <UUID> child text) plus an
    <ObjectList> of <Step> elements. Folders, separators and step-less scripts
    have no entry.

    Returns ``(by_uuid, by_id)``: ScriptReference UUID attr -> <Script> steps
    element, and ScriptReference id attr -> same (fallback for UUID-less files).
    """
    by_uuid: dict[str, etree._Element] = {}
    by_id: dict[str, etree._Element] = {}
    for sfs in root.iter("StepsForScripts"):
        for entry in sfs.findall("Script"):
            ref = entry.find("ScriptReference")
            if ref is None:
                continue
            if ref.get("UUID"):
                by_uuid[ref.get("UUID")] = entry
            if ref.get("id"):
                by_id[ref.get("id")] = entry
    return by_uuid, by_id


def parse_scripts(root: etree._Element) -> list[dict]:
    """Script index. ``_hash`` covers the catalog entry AND the script's step
    bodies from <StepsForScripts> (see ``script_steps_index``): when steps
    exist, the hash is sha256("<catalog-hash>:<steps-hash>") truncated like
    compute_hash — deterministic, and any step edit changes it. ``step_count``
    is the number of <Step> elements, or None when the script has no steps
    entry (folders, separators, empty scripts)."""
    steps_by_uuid, steps_by_id = script_steps_index(root)
    out = []
    for cat in root.iter("ScriptCatalog"):
        for s in cat.iter("Script"):
            opts = s.find("Options")
            uuid_ = _uuid(s)
            steps = steps_by_uuid.get(uuid_) if uuid_ else None
            if steps is None and s.get("id"):
                steps = steps_by_id.get(s.get("id"))
            h = compute_hash(s)
            step_count = None
            if steps is not None:
                h = hashlib.sha256(
                    f"{h}:{compute_hash(steps)}".encode()).hexdigest()[:32]
                step_count = len(steps.findall("ObjectList/Step"))
            out.append({
                "id": s.get("id"),
                "name": s.get("name"),
                "is_folder": s.get("isFolder") == "True",
                "uuid": uuid_,
                "hidden": (opts.get("hidden") == "True") if opts is not None else False,
                "run_with_full_access": (opts.get("runwithfullaccess") == "True") if opts is not None else False,
                "step_count": step_count,
                "_hash": h,
            })
    return out


# Bit 26 of the layout-level <Options> is engine-managed instance state, not
# schema: FMUpgradeTool sets it on layout AddAction, and both values occur
# across normally-created layouts within one file (2026-06-12 dry run).
_LAYOUT_STATE_OPTIONS_BIT = 1 << 26


def _layout_hash_view(L: etree._Element) -> etree._Element:
    """Layout subtree as hashed — per-instance state removed.

    FMUpgradeTool's layout AddAction renumbers internal object ids; the ids
    themselves are hash-stripped, but <Accessibility><Label> holds a reference
    to them, so it must go too. Without this view a perfectly applied layout
    re-diffs as modified (deep structure) forever.
    """
    e = copy.deepcopy(L)
    for acc in e.iter("Accessibility"):
        for lab in list(acc.iter("Label")):
            lab.getparent().remove(lab)
    opts = e.find("Options")  # direct child only: LayoutObject Options are content
    if opts is not None and (opts.text or "").strip().isdigit():
        opts.text = str(int(opts.text) & ~_LAYOUT_STATE_OPTIONS_BIT)
    return e


def parse_layouts(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("LayoutCatalog"):
        for L in cat.iter("Layout"):
            toref = L.find("TableOccurrenceReference")
            out.append({
                "id": L.get("id"),
                "name": L.get("name"),
                "is_folder": L.get("isFolder") == "True",
                "uuid": _uuid(L),
                "table_occurrence": toref.get("name") if toref is not None else None,
                "width": L.get("width"),
                "_hash": compute_hash(_layout_hash_view(L)),
            })
    return out


def parse_value_lists(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("ValueListCatalog"):
        for vl in cat.iter("ValueList"):
            src = vl.find("Source")
            out.append({
                "id": vl.get("id"),
                "name": vl.get("name"),
                "source": src.get("value") if src is not None else None,
                "uuid": _uuid(vl),
                "_hash": compute_hash(vl),
            })
    return out


def parse_custom_functions(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("CustomFunctionsCatalog"):
        for cf in cat.iter("CustomFunction"):
            display = cf.find("Display")
            params = [p.get("name") for p in cf.iter("Parameter")]
            out.append({
                "id": cf.get("id"),
                "name": cf.get("name"),
                "access": cf.get("access"),
                "signature": display.text if display is not None else None,
                "parameters": params,
                "uuid": _uuid(cf),
                "_hash": compute_hash(cf),
            })
    return out


def parse_external_data_sources(root: etree._Element) -> list[dict]:
    out = []
    for cat in root.iter("ExternalDataSourceCatalog"):
        for eds in cat.iter("ExternalDataSource"):
            paths = [p.text for p in eds.iter("UniversalPathList")]
            out.append({
                "id": eds.get("id"),
                "name": eds.get("name"),
                "type": eds.get("type"),
                "paths": paths,
                "uuid": _uuid(eds),
                "_hash": compute_hash(eds),
            })
    return out


def parse_file_header(root: etree._Element) -> dict:
    """The <FMSaveAsXML> root attributes."""
    return {
        "fmsavexml_version": root.get("version"),
        "source_app_version": root.get("Source"),
        "filename": root.get("File"),
        "uuid": root.get("UUID"),
        "locale": root.get("locale"),
        "has_ddr_info": root.get("Has_DDR_INFO") == "True",
    }


# --- Catalog UUID extraction -------------------------------------------------

CATALOG_TAGS = ["BaseTableCatalog", "FieldsForTables", "TableOccurrenceCatalog",
                "RelationshipCatalog", "ValueListCatalog", "CustomFunctionsCatalog",
                "ScriptCatalog", "LayoutCatalog", "ExternalDataSourceCatalog"]


def parse_catalog_uuids(root) -> dict:
    out = {}
    for tag in CATALOG_TAGS:
        el = next(root.iter(tag), None)
        out[tag] = _uuid(el) if el is not None else None
    return out


# --- Snapshot CLI -----------------------------------------------------------

CATALOG_PARSERS = {
    "base_tables": parse_base_tables, "fields": parse_fields,
    "table_occurrences": parse_table_occurrences, "relationships": parse_relationships,
    "scripts": parse_scripts, "layouts": parse_layouts, "value_lists": parse_value_lists,
    "custom_functions": parse_custom_functions, "external_data_sources": parse_external_data_sources,
}


def snapshot(export_path: str | Path, out_dir: str | Path) -> Path:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    root = etree.parse(open_fmsavexml(export_path)).getroot()
    meta = parse_file_header(root) | {"export_path": str(Path(export_path).resolve())}
    (out / "_meta.json").write_text(json.dumps(meta, indent=1))
    (out / "catalogs.json").write_text(json.dumps(parse_catalog_uuids(root), indent=1))
    for name, fn in CATALOG_PARSERS.items():
        (out / f"{name}.json").write_text(json.dumps(fn(root), indent=1))
    return out


# --- Internals --------------------------------------------------------------


def _detect_encoding(raw: bytes) -> str:
    """Sniff the byte encoding of an FMSaveAsXML blob.

    FileMaker has shipped two: UTF-16 with BOM (older exports) and UTF-8
    (FM 2026 / Source 26.0.1, format 2.3.0.0). Detect by BOM, falling back to a
    null-byte sniff for headerless UTF-16.
    """
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    # No BOM: UTF-16-encoded ASCII carries a null byte in every other position;
    # UTF-8 of this (mostly ASCII) XML does not.
    return "utf-16" if b"\x00" in raw[:64] else "utf-8"


def _uuid(elem: etree._Element) -> str | None:
    u = elem.find("UUID")
    return u.text if u is not None else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse an FMSaveAsXML export into per-catalog JSON")
    ap.add_argument("export"); ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    snapshot(a.export, a.out)
    print(f"snapshot written to {a.out}")
