"""Spec-driven schema scaffolder: make a FileMaker file match a schema spec.

gen:    spec + FMSaveAsXML export of the target -> one FMUpgradeTool patch
        (AddAction for missing tables/fields/TOs/layouts, then DeleteActions
        that retire stale generator-owned layouts) + expected.json.
verify: expected.json + re-export of the patched file -> spec coverage check.

Conventions baked in (docs/specs/2026-06-12-schema-scaffold-design.md): every
table gets the BASE-7 audit core cloned from the base file's BASE table; FKs
are plain Number fields — no relationship graph (the web layer joins on FK
values); one generator-owned full-field layout per table, named after the
table, doubles as the Data API layout. Reconciler is additive-only: objects
in the file but not in the spec are reported as drift, never changed.
"""
from __future__ import annotations
import argparse, copy, json, re, sys
from pathlib import Path
from xml.sax.saxutils import escape
from lxml import etree
import fm_export, saxml_parser
from gen_patch import fresh_uuid

# Audit core, in canonical order, with (datatype, fieldtype). Cloned from the
# base file's BASE table at generation time — never synthesized from scratch.
BASE7_TYPES = {
    "ID": ("Number", "Normal"),
    "RecordID": ("Text", "Calculated"),
    "kTrue": ("Number", "Calculated"),
    "CreationTimestamp": ("Timestamp", "Normal"),
    "CreationAccount": ("Text", "Normal"),
    "ModifyTimestamp": ("Timestamp", "Normal"),
    "ModifyAccount": ("Text", "Normal"),
}
RESERVED_TABLES = {"BASE", "ProofKitApps"}   # live in the base file; never spec'd
SIMPLE_TYPES = {"text": "Text", "number": "Number", "date": "Date",
                "timestamp": "Timestamp", "container": "Container"}
CALC_RESULTS = {"text": "Text", "number": "Number", "date": "Date",
                "timestamp": "Timestamp"}
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
FK_RE = re.compile(r"^fk_([A-Za-z0-9_]+)_ID$")


class SpecError(Exception):
    def __init__(self, problems: list[str]):
        super().__init__("invalid spec:\n  " + "\n  ".join(problems))
        self.problems = problems


def _reject_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise SpecError([f"duplicate key {k!r} in spec JSON"])
        d[k] = v
    return d


def load_spec(path: str | Path) -> dict:
    try:
        raw = json.loads(Path(path).read_text(), object_pairs_hook=_reject_dupes)
    except json.JSONDecodeError as e:
        raise SpecError([f"{path}: not valid JSON — {e}"]) from e
    return load_spec_dict(raw)


def load_spec_dict(raw: dict) -> dict:
    problems: list[str] = []
    fname = raw.get("file")
    if fname is None:
        problems.append("spec 'file' key is missing")
        fname = ""
    elif not isinstance(fname, str) or not NAME_RE.match(fname):
        problems.append(f"spec 'file' must be an identifier-style name, got {fname!r}")
    tables = raw.get("tables")
    if not isinstance(tables, dict) or not tables:
        problems.append("spec 'tables' must be a non-empty object")
        tables = {}
    norm: dict[str, list[dict]] = {}
    for tname, fields in tables.items():
        if not NAME_RE.match(tname):
            problems.append(f"table {tname!r}: not an identifier-style name (no spaces)")
        if tname in RESERVED_TABLES:
            problems.append(f"table {tname!r}: reserved (lives in the base file)")
        if not isinstance(fields, dict) or not fields:
            problems.append(f"table {tname}: fields must be a non-empty object")
            fields = {}
        entries = []
        for name, fdef in fields.items():
            if isinstance(fdef, str):
                fdef = {"type": fdef}
            if not isinstance(fdef, dict):
                problems.append(f"{tname}.{name}: definition must be a string or object")
                continue
            if not NAME_RE.match(name):
                problems.append(f"{tname}.{name}: not an identifier-style field name")
            if name in BASE7_TYPES:
                problems.append(f"{tname}.{name}: collides with the BASE-7 audit core "
                                "(those fields are added automatically)")
            ftype = fdef.get("type")
            if name.startswith("fk_") and ftype != "fk":
                problems.append(f"{tname}.{name}: fk_-named fields must use type 'fk'")
            entry = {"name": name, "type": ftype, "comment": fdef.get("comment", "")}
            if ftype == "fk":
                m = FK_RE.match(name)
                if m:
                    entry["fk_stem"] = m.group(1)
                else:
                    problems.append(f"{tname}.{name}: fk fields must be named fk_<Parent>_ID")
                entry["parent"] = fdef.get("parent")
                entry["datatype"], entry["fieldtype"] = "Number", "Normal"
            elif ftype == "calc":
                formula, result = fdef.get("formula"), fdef.get("result")
                if not formula or result not in CALC_RESULTS:
                    problems.append(f"{tname}.{name}: calc needs 'formula' and 'result' "
                                    f"in {sorted(CALC_RESULTS)}")
                else:
                    entry["formula"] = formula
                    entry["datatype"], entry["fieldtype"] = CALC_RESULTS[result], "Calculated"
            elif ftype in SIMPLE_TYPES:
                entry["datatype"], entry["fieldtype"] = SIMPLE_TYPES[ftype], "Normal"
            else:
                problems.append(f"{tname}.{name}: unknown type {ftype!r}")
            entries.append(entry)
        norm[tname] = entries
    # FK parent resolution: explicit "parent" wins; else exact table-name match
    # on the stem; else stem+'s' (fk_Account_ID -> Accounts). Validation only —
    # no relationships are generated (design decision: graph is developer turf).
    for tname, entries in norm.items():
        for e in entries:
            if e.get("type") != "fk" or "fk_stem" not in e:
                continue
            parent = e.get("parent")
            if parent is None:
                stem = e["fk_stem"]
                parent = stem if stem in norm else (stem + "s" if stem + "s" in norm else None)
            if parent is None or parent not in norm:
                problems.append(f"{tname}.{e['name']}: cannot resolve FK parent table "
                                "(declare an explicit \"parent\")")
            else:
                e["parent"] = parent
                if not e["comment"]:
                    e["comment"] = f"-> {parent}.ID"
            e.pop("fk_stem", None)
    if problems:
        raise SpecError(problems)
    return {"file": fname, "tables": norm}


def expand_spec(spec: dict) -> dict[str, list[dict]]:
    """Per-table ordered field list: BASE-7 audit core first, then domain fields."""
    out: dict[str, list[dict]] = {}
    for tname, entries in spec["tables"].items():
        base = [{"name": n, "datatype": dt, "fieldtype": ft, "base7": True}
                for n, (dt, ft) in BASE7_TYPES.items()]
        out[tname] = base + [dict(e) for e in entries]
    return out


def expected_entries(expanded: dict) -> list[dict]:
    """Flat expected-object list; keys match saxml_diff.obj_key grammar."""
    out = []
    for tname, fields in expanded.items():
        out.append({"kind": "base_table", "key": f"base_table:{tname}", "name": tname})
        for f in fields:
            entry = {"kind": "field", "key": f"field:{tname}::{f['name']}",
                     "table": tname, "name": f["name"],
                     "datatype": f["datatype"], "fieldtype": f["fieldtype"]}
            if f.get("formula"):
                entry["formula"] = f["formula"]
            out.append(entry)
        out.append({"kind": "table_occurrence", "key": f"table_occurrence:{tname}",
                    "name": tname})
        out.append({"kind": "layout", "key": f"layout:{tname}", "name": tname,
                    "table": tname})
    return out


def harvest_context(export_path: str | Path, parsed_dir: str | Path) -> dict:
    """Everything gen needs from the target file's export: existing-object
    indexes (reconcile), next free ids, the LayoutCatalog UUID, the theme
    reference, and the BASE-7 raw <Field> fragments (cloned per new table —
    the mechanized form of Joe's 'duplicate BASE' convention)."""
    parsed = Path(parsed_dir)
    root = etree.parse(saxml_parser.open_fmsavexml(export_path)).getroot()
    # Exports also carry Structure/ModifyAction calc-stub FieldCatalogs that
    # would shadow the real ones — only ever walk Structure/AddAction.
    add = root.find("Structure/AddAction")
    if add is None:
        raise ValueError(f"{export_path}: no Structure/AddAction — not FMSaveAsXML?")
    _load = lambda fn: json.loads((parsed / fn).read_text())

    def _by_name(objs, kind):
        out = {}
        dupes: set[str] = set()
        for o in objs:
            if o["name"] in out:
                dupes.add(o["name"])
            out[o["name"]] = o
        if dupes:
            raise ValueError(
                f"duplicate {kind} names in target export: {sorted(dupes)} — "
                "the scaffolder keys by name; resolve duplicates in FileMaker first")
        return out

    tables = _by_name(_load("base_tables.json"), "base_table")
    tos = _by_name(_load("table_occurrences.json"), "table_occurrence")
    all_layouts = _load("layouts.json")
    # Separator layouts named '--' or '-' (all-dash) may legitimately repeat;
    # also skip folders before the dupe check.
    non_folder = [l for l in all_layouts
                  if not l.get("is_folder") and not all(c == '-' for c in (l.get("name") or "-"))]
    layouts = _by_name(non_folder, "layout")
    # Keep the full non-folder dict (including separators) for the return value.
    layouts_full = {l["name"]: l for l in all_layouts if not l.get("is_folder")}
    fields_by_table: dict[str, dict] = {}
    max_field_id: dict[str, int] = {}
    for f in _load("fields.json"):
        fields_by_table.setdefault(f["table_name"], {})[f["name"]] = f
        max_field_id[f["table_name"]] = max(max_field_id.get(f["table_name"], 0),
                                            int(f["id"]))
    catalogs = _load("catalogs.json")
    if not catalogs.get("LayoutCatalog"):
        raise ValueError("base export has no LayoutCatalog UUID — cannot target "
                         "the layout catalog (re-export with --stamp-guids)")
    base7_frags: dict[str, etree._Element] = {}
    for fc in add.iter("FieldCatalog"):
        btref = fc.find("BaseTableReference")
        if btref is None or btref.get("name") != "BASE":
            continue
        for fe in fc.iter("Field"):
            if fe.get("name") in BASE7_TYPES:
                base7_frags[fe.get("name")] = fe
    missing = [n for n in BASE7_TYPES if n not in base7_frags]
    if missing:
        raise ValueError(f"base file's BASE table lacks audit-core fields: {missing}")
    theme = None
    for lay in add.iter("Layout"):
        t = lay.find("LayoutThemeReference")
        if t is not None:
            theme = t
            break
    if theme is None:
        raise ValueError("no LayoutThemeReference in base export — cannot theme layouts")
    return {
        "tables": tables, "tos": tos, "layouts": layouts_full,
        "fields_by_table": fields_by_table, "max_field_id": max_field_id,
        "next_table_id": max((int(t["id"]) for t in tables.values()), default=129) + 1,
        "next_to_id": max((int(t["id"]) for t in tos.values()), default=1065089) + 1,
        "next_layout_id": max((int(l["id"]) for l in all_layouts), default=1) + 1,
        "layout_catalog_uuid": catalogs["LayoutCatalog"],
        "theme": theme, "base7_frags": base7_frags,
    }


def compute_delta(expanded: dict, ctx: dict) -> dict:
    """Spec minus file. Additive-only: drift (file content absent from the
    spec, or type mismatches) is reported, never patched."""
    conflicts = []
    for tname in expanded:
        to = ctx["tos"].get(tname)
        if to is not None and to.get("base_table_name") != tname:
            conflicts.append(
                f"TO name collision: table occurrence {tname!r} exists but points "
                f"at base table {to.get('base_table_name')!r} — rename it in "
                "FileMaker before scaffolding")
        lay = ctx["layouts"].get(tname)
        if lay is not None and lay.get("table_occurrence") != tname:
            conflicts.append(
                f"layout name collision: layout {tname!r} exists but is bound to "
                f"TO {lay.get('table_occurrence')!r} — rename it in FileMaker "
                "before scaffolding")
    if conflicts:
        raise ValueError("scaffold conflicts:\n  " + "\n  ".join(conflicts))
    _norm = lambda s: " ".join((s or "").split())
    new_tables, new_fields, repair_calcs, drift = [], {}, {}, []
    for tname, flist in expanded.items():
        if tname not in ctx["tables"]:
            new_tables.append(tname)
            continue
        have = ctx["fields_by_table"].get(tname, {})
        missing = [f for f in flist if f["name"] not in have]
        if missing:
            new_fields[tname] = missing
        for f in flist:
            ex = have.get(f["name"])
            if ex and (ex["datatype"] != f["datatype"]
                       or ex["fieldtype"] != f["fieldtype"]):
                drift.append(
                    f"field {tname}::{f['name']}: file has "
                    f"{ex['fieldtype']}/{ex['datatype']}, spec wants "
                    f"{f['fieldtype']}/{f['datatype']} — left untouched")
            # Existing calc whose live formula differs from the spec (incl. the
            # FMUpgradeTool silent /* … */ comment-out class, found live
            # 2026-06-12) gets a ModifyAction repair stub — same mechanism that
            # protects calcs in fresh patches.
            elif (ex and f.get("formula")
                  and _norm(ex.get("calc_text")) != _norm(f["formula"])):
                repair_calcs.setdefault(tname, []).append(f)
    new_tos = [t for t in expanded if t not in ctx["tos"]]
    add_layouts = [t for t in expanded if t not in ctx["layouts"]]
    regen_layouts = [t for t in expanded
                     if t in ctx["layouts"] and t in new_fields]
    for tname in ctx["tables"]:
        if tname not in expanded and tname not in RESERVED_TABLES:
            drift.append(f"table {tname}: exists in file but not in spec — left untouched")
    # Extra fields on spec'd tables: reported because the generator-owned layout
    # will not carry them if that table's layout is ever regenerated.
    spec_field_names = {t: {f["name"] for f in fl} for t, fl in expanded.items()}
    for tname, have in ctx["fields_by_table"].items():
        if tname not in expanded:
            continue
        for fname in have:
            if fname not in spec_field_names[tname]:
                drift.append(
                    f"field {tname}::{fname}: exists in file but not in spec — left "
                    "in the table, but it will NOT appear on the regenerated layout "
                    "if this table's layout is ever regenerated")
    spec_tables = set(expanded)
    for toname, to in ctx["tos"].items():
        if toname not in spec_tables and to.get("base_table_name") not in RESERVED_TABLES:
            drift.append(f"table occurrence {toname}: exists in file but not in spec — left untouched")
    for lname, lay in ctx["layouts"].items():
        if lname not in spec_tables and (
                lay.get("table_occurrence") not in RESERVED_TABLES
                and lay.get("table_occurrence")):
            drift.append(f"layout {lname}: exists in file but not in spec — left untouched")
    noop = not (new_tables or new_fields or new_tos or add_layouts
                or regen_layouts or repair_calcs)
    return {"new_tables": new_tables, "new_fields": new_fields, "new_tos": new_tos,
            "add_layouts": add_layouts, "regen_layouts": regen_layouts,
            "repair_calcs": repair_calcs, "drift": drift, "noop": noop}


# ---------------------------------------------------------------------------
# Patch synthesis (Task 5)
# ---------------------------------------------------------------------------

# Proven field tails (pk-fmsp 2026-06-10 patches, accepted by FMUpgradeTool 26.0.1.68)
STD_VALID = ('<Validation alwaysValidate="False" type="OnlyDuringDataEntry" '
             'allowOverride="True" notEmpty="False" unique="False" existing="False"/>')
STD_STORE = ('<Storage autoIndex="True" index="None" global="False" maxRepetitions="1">'
             '<LanguageReference name="English" id="21"/></Storage>')
TAIL = '<TagList/><Annotation/><DisplayNames enable="False"/>'
FMT = ('<ExtendedAttributes><Formatting><Graphic><Options>5</Options></Graphic>'
       '<Time><Options>143</Options></Time><Numeric><Options>2304</Options>'
       '<Style><Negative><Color red="221" green="0" blue="0" alpha="1.00"/></Negative>'
       '</Style><DecimalDigits>2</DecimalDigits></Numeric></Formatting>'
       '</ExtendedAttributes>')
LABEL_CSS = "self:normal .self\n{\n\ttext-align: right;\n}\n"


def _attr(s: str) -> str:
    return escape(s or "", {'"': "&quot;"})


def domain_field_xml(fid: int, entry: dict, to_ref: str, fuuid: str) -> str:
    """One synthesized <Field>. Calc fields are STORED calcs with the owning
    table's TO as calculation context; everything else is a plain Normal field."""
    c = _attr(entry.get("comment", ""))
    if entry["fieldtype"] == "Calculated":
        return (f'<Field id="{fid}" name="{entry["name"]}" fieldtype="Calculated" '
                f'datatype="{entry["datatype"]}" comment="{c}">'
                f'<UUID>{fuuid}</UUID>'
                f'<AutoEnter alwaysEvaluate="False"/>'
                f'<Storage storeCalculationResults="True" autoIndex="True" index="None" '
                f'global="False" maxRepetitions="1">'
                f'<LanguageReference name="English" id="21"/></Storage>'
                f'<Calculation>{to_ref}<Text>{escape(entry["formula"])}</Text></Calculation>'
                f'{TAIL}</Field>')
    return (f'<Field id="{fid}" name="{entry["name"]}" fieldtype="Normal" '
            f'datatype="{entry["datatype"]}" comment="{c}">'
            f'<UUID>{fuuid}</UUID>'
            f'<AutoEnter type="" prohibitModification="False"/>'
            f'{STD_VALID}{STD_STORE}{TAIL}</Field>')


def clone_base7(ctx: dict, to_id, tname: str, to_uuid: str) -> list:
    """Duplicate the base file's BASE-7 field definitions for a new table:
    sequential ids 1-7, fresh UUIDs, calc contexts re-pointed at the new TO.
    Auto-enter/validation/storage options ride along verbatim."""
    out = []
    for i, name in enumerate(BASE7_TYPES, start=1):
        el = copy.deepcopy(ctx["base7_frags"][name])
        el.set("id", str(i))
        u = el.find("UUID")
        if u is None:
            u = etree.SubElement(el, "UUID")
        u.text = fresh_uuid()
        for tor in el.iter("TableOccurrenceReference"):
            tor.set("id", str(to_id))
            tor.set("name", tname)
            tor.set("UUID", to_uuid)
        out.append(el)
    return out


def layout_xml(layout_id: int, tname: str, to_id, to_uuid: str,
               triples: list, theme_xml: str) -> str:
    """Generator-owned full-field layout (the proven pk-fmsp shape): one
    label + edit-box pair per field in the Body, every field a TableView
    column. triples = [(field_id, field_name, field_uuid)] in layout order."""
    to_ref = f'<TableOccurrenceReference id="{to_id}" name="{tname}" UUID="{to_uuid}"/>'
    objs, tv = [], []
    for i, (fid, fname, fuuid) in enumerate(triples):
        lbl, box = 2 * i + 1, 2 * i + 2
        objs.append(
            f'<LayoutObject id="{lbl}" type="Text" name="" kind="2">'
            f'<UUID>{fresh_uuid()}</UUID>'
            f'<Bounds top="{120 + 35 * i}" left="30" bottom="{141 + 35 * i}" right="190"/>'
            f'<Options>805306368</Options>'
            f'<Text><Options>0</Options><StyledText><Data>{escape(fname)}</Data></StyledText></Text>'
            f'<LocalCSS type="ObjectCustomStyle" name="" displayName="">{LABEL_CSS}</LocalCSS>'
            f'</LayoutObject>')
        objs.append(
            f'<LayoutObject id="{box}" type="Edit Box" name="" kind="1">'
            f'<UUID>{fresh_uuid()}</UUID>'
            f'<Bounds top="{114 + 35 * i}" left="206" bottom="{145 + 35 * i}" right="560"/>'
            f'<Options>805306368</Options>'
            f'<Field><FieldReference id="{fid}" name="{fname}" repetition="1" '
            f'UUID="{fuuid}">{to_ref}</FieldReference>'
            f'<Options>32</Options><Display Style="0" show="1"/>'
            f'<Usage inputMode="0" type="1"/></Field>'
            f'{FMT}'
            f'<Accessibility><Label>{lbl}</Label></Accessibility>'
            f'</LayoutObject>')
        w = 75 if fname in ("ID", "kTrue") or fname.startswith("fk_") else (
            150 if "Timestamp" in fname else 120)
        tv.append(
            f'<TableViewLayoutObject hidden="False" id="{i + 1}" name="{fname}" width="{w}">'
            f'<FieldReference id="{fid}" name="{fname}" repetition="1" '
            f'UUID="{fuuid}">{to_ref}</FieldReference>'
            f'</TableViewLayoutObject>')
    # max(658, content+30): proven runs only ever emitted 658; the +30 band is
    # safer for 15+ field tables (content never overflows the part).
    body = max(658, 145 + 35 * (len(triples) - 1) + 30)
    nl = "\n"
    return (
        f'<Layout id="{layout_id}" name="{tname}" width="1024">'
        f'{to_ref}{theme_xml}'
        f'<PartsList membercount="2">'
        f'<Part type="Top Navigation" kind="12">'
        f'<Definition type="Top Navigation" kind="12" size="110" absolute="0" Options="0"/></Part>'
        f'<Part type="Body" kind="4">'
        f'<Definition type="Body" kind="4" size="{body}" absolute="110" Options="0"/>'
        f'<ObjectList membercount="{len(objs)}">{nl.join(objs)}</ObjectList>'
        f'</Part></PartsList>'
        f'<TableView><ObjectList membercount="{len(tv)}">{nl.join(tv)}</ObjectList></TableView>'
        f'<UUID>{fresh_uuid()}</UUID><TagList/>'
        f'<GridStyle><Color red="0.500000" green="0.500000" blue="0.500000" alpha="1.000000"/>'
        f'<Style>5</Style></GridStyle>'
        f'<ClientType>0</ClientType>'
        f'<Options hidden="False">64440436737</Options>'
        f'<MenuSet><CustomMenuSetReference id="0" name="[File Default]" UUID=""/></MenuSet>'
        f'</Layout>')


def build_patch(expanded: dict, delta: dict, ctx: dict) -> str:
    """Assemble the one-shot patch. AddAction in proven catalog order
    (BaseTables -> Fields -> TOs -> Layouts), then DeleteActions retiring
    regenerated layouts (mirrors gen_patch's validated Add->Delete order;
    deletes target the OLD layout by UUID, so the same-name re-add is safe)."""
    nl = "\n"
    # serialize ONLY the open-tag attributes as a self-closed element — the
    # harvested theme element may carry children/tail from the export tree
    theme_el = ctx["theme"]
    theme_xml = "<LayoutThemeReference " + " ".join(
        f'{k}="{_attr(v)}"' for k, v in theme_el.attrib.items()) + "/>"
    next_tbl, next_to, next_lay = (ctx["next_table_id"], ctx["next_to_id"],
                                   ctx["next_layout_id"])
    bts, fcs, tos_x, lays, deletes = [], [], [], [], []
    table_info: dict = {}   # name -> {"id","uuid"} (new or existing)
    to_info: dict = {}      # name -> (to_id, to_uuid)
    for tname in expanded:
        if tname in delta["new_tables"]:
            tid, tuuid = next_tbl, fresh_uuid()
            next_tbl += 1
            table_info[tname] = {"id": str(tid), "uuid": tuuid}
            bts.append(f'<BaseTable id="{tid}" comment="" name="{tname}">'
                       f'<UUID>{tuuid}</UUID><TagList/></BaseTable>')
        elif tname in ctx["tables"]:
            t = ctx["tables"][tname]
            table_info[tname] = {"id": t["id"], "uuid": t["uuid"]}
        if tname in delta["new_tos"]:
            to_id, to_uuid = next_to, fresh_uuid()
            next_to += 1
            to_info[tname] = (to_id, to_uuid)
            t = table_info.get(tname)
            if t is None:
                raise ValueError(
                    f"patch self-check failed — table {tname} needed by TO but not "
                    "resolvable (delta inconsistent)")
            tos_x.append(
                f'<TableOccurrence View="Full" height="0" id="{to_id}" name="{tname}" type="Local">'
                f'<UUID>{to_uuid}</UUID>'
                f'<BaseTableSourceReference type="BaseTableReference">'
                f'<BaseTableReference id="{t["id"]}" name="{tname}" UUID="{t["uuid"]}"/>'
                f'</BaseTableSourceReference>'
                f'<CoordRect top="{170 + 140 * ((len(tos_x)) // 8)}" '
                f'left="{20 + 170 * ((len(tos_x)) % 8)}" '
                f'bottom="{286 + 140 * ((len(tos_x)) // 8)}" '
                f'right="{151 + 170 * ((len(tos_x)) % 8)}"/>'
                f'<Color red="120" green="120" blue="120" alpha="1.00"/>'
                f'<TagList/></TableOccurrence>')
        else:
            t = ctx["tos"][tname]
            to_info[tname] = (t["id"], t["uuid"])

    field_triples: dict = {}   # table -> [(id, name, uuid)] in layout order
    for tname, flist in expanded.items():
        to_id, to_uuid = to_info[tname]
        to_ref = (f'<TableOccurrenceReference id="{to_id}" name="{tname}" '
                  f'UUID="{to_uuid}"/>')
        if tname in delta["new_tables"]:
            els = clone_base7(ctx, to_id, tname, to_uuid)
            parts = [etree.tostring(e, encoding="unicode") for e in els]
            triples = [(int(e.get("id")), e.get("name"), e.find("UUID").text)
                       for e in els]
            for j, entry in enumerate(flist[7:], start=8):
                fu = fresh_uuid()
                parts.append(domain_field_xml(j, entry, to_ref, fu))
                triples.append((j, entry["name"], fu))
            keys = nl.join(f"<key>{i + 1}</key>" for i in range(len(parts)))
            t = table_info.get(tname)
            if t is None:
                raise ValueError(
                    f"patch self-check failed — table {tname} needed by FieldCatalog but not "
                    "resolvable (delta inconsistent)")
            fcs.append(
                f'<FieldCatalog><SortOrder>1</SortOrder>'
                f'<CustomOrderList>{keys}</CustomOrderList>'
                f'<UUID>{fresh_uuid()}</UUID><TagList/>'
                f'<BaseTableReference id="{t["id"]}" name="{tname}" UUID="{t["uuid"]}"/>'
                f'<ObjectList membercount="{len(parts)}">{nl.join(parts)}</ObjectList>'
                f'</FieldCatalog>')
            field_triples[tname] = triples
        else:
            have = ctx["fields_by_table"].get(tname, {})
            triples = [(int(have[f["name"]]["id"]), f["name"], have[f["name"]]["uuid"])
                       for f in flist if f["name"] in have]
            new = delta["new_fields"].get(tname, [])
            if new:
                fid = ctx["max_field_id"][tname]
                parts = []
                for entry in new:
                    fid += 1
                    fu = fresh_uuid()
                    parts.append(domain_field_xml(fid, entry, to_ref, fu))
                    triples.append((fid, entry["name"], fu))
                t = table_info.get(tname)
                if t is None:
                    raise ValueError(
                        f"patch self-check failed — table {tname} needed by FieldCatalog but not "
                        "resolvable (delta inconsistent)")
                fcs.append(   # into-existing shape: no SortOrder/CustomOrderList
                    f'<FieldCatalog><UUID>{fresh_uuid()}</UUID><TagList/>'
                    f'<BaseTableReference id="{t["id"]}" name="{tname}" UUID="{t["uuid"]}"/>'
                    f'<ObjectList membercount="{len(parts)}">{nl.join(parts)}</ObjectList>'
                    f'</FieldCatalog>')
            # restore spec order for the regenerated layout
            order = {f["name"]: i for i, f in enumerate(flist)}
            triples.sort(key=lambda tr: order.get(tr[1], 999))
            field_triples[tname] = triples

    for tname in expanded:
        if tname in delta["add_layouts"] or tname in delta["regen_layouts"]:
            to_id, to_uuid = to_info[tname]
            lays.append(layout_xml(next_lay, tname, to_id, to_uuid,
                                   field_triples[tname], theme_xml))
            next_lay += 1
        if tname in delta["regen_layouts"]:
            old = ctx["layouts"][tname]
            if not old.get("uuid"):
                raise ValueError(
                    f"layout {tname!r} has no UUID in the export — UUID-less "
                    "deletes are silently skipped; re-export with --stamp-guids")
            deletes.append(f'<DeleteAction><ItemReference UUID="{old["uuid"]}" '
                           f'type="LayoutReference"/></DeleteAction>')

    add_parts = []
    if bts:
        add_parts.append(f'<BaseTableCatalog membercount="{len(bts)}">{nl.join(bts)}'
                         f'</BaseTableCatalog>')
    if fcs:
        # membercount on FieldsForTables: proven precedent is mixed (absent in
        # crm-tables, "1" in accounts-fields); the tool accepts both.
        add_parts.append(f'<FieldsForTables membercount="{len(fcs)}">{nl.join(fcs)}'
                         f'</FieldsForTables>')
    if tos_x:
        add_parts.append(f'<TableOccurrenceCatalog membercount="{len(tos_x)}">'
                         f'{nl.join(tos_x)}</TableOccurrenceCatalog>')
    if lays:
        add_parts.append(f'<LayoutCatalog><UUID>{ctx["layout_catalog_uuid"]}</UUID>'
                         f'<TagList/>{nl.join(lays)}</LayoutCatalog>')
    patch = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<FMUpgradeToolPatch version="2.3.0.0">\n<Structure>\n'
             + (f'<AddAction>{nl.join(add_parts)}</AddAction>\n' if add_parts else "")
             + nl.join(deletes) + ('\n' if deletes else '')
             + '</Structure>\n</FMUpgradeToolPatch>\n')

    root = etree.fromstring(patch.encode("utf-8"))
    n_stubs = _calc_reapply(root, delta.get("repair_calcs", {}), ctx)

    # self-check: counts must equal the delta before anything is written.
    # Paths are scoped to Structure/AddAction — the ModifyAction calc stubs
    # carry nameless <Field> wrappers that must not pollute the field count.
    # want_fields is delta-derived (not builder-accumulated) so a builder bug
    # that silently skips a field cannot shrink both sides equally and pass.
    # Guard: Phantom entries in new_tables won't be in expanded — skip them so
    # the tables-count check (not a KeyError) catches the inconsistency.
    want_fields = (sum(len(expanded[t]) for t in delta["new_tables"] if t in expanded)
                   + sum(len(v) for v in delta["new_fields"].values()))
    checks = [
        (len(root.findall("Structure/AddAction/BaseTableCatalog/BaseTable")),
         len(delta["new_tables"]), "tables"),
        (len(root.findall("Structure/AddAction/FieldsForTables/FieldCatalog/ObjectList/Field")),
         want_fields, "fields"),
        (len(root.findall("Structure/AddAction/TableOccurrenceCatalog/TableOccurrence")),
         len(delta["new_tos"]), "TOs"),
        (len(root.findall("Structure/AddAction/LayoutCatalog/Layout")),
         len(delta["add_layouts"]) + len(delta["regen_layouts"]), "layouts"),
        (len(root.findall("Structure/DeleteAction")), len(delta["regen_layouts"]), "deletes"),
    ]
    bad = [f"{label}: patch has {got}, delta wants {want}"
           for got, want, label in checks if got != want]
    # Every repair the delta asked for must be carried by a stub (AddAction
    # calcs add more stubs on top, so >= for the combined total).
    repair_count = sum(len(v) for v in delta.get("repair_calcs", {}).values())
    if n_stubs < repair_count:
        bad.append(f"calc stubs: patch has {n_stubs}, repairs alone need {repair_count}")
    if bad:
        raise ValueError("patch self-check failed — " + "; ".join(bad))
    return etree.tostring(root, encoding="UTF-8",
                          xml_declaration=True).decode("utf-8")


def _calc_reapply(root, repair_calcs: dict, ctx: dict) -> int:
    """Port of gen_patch's ModifyAction calc re-apply pass. Calc formulas that
    reference same-patch fields cannot compile while their context TO is still
    a forward reference, so FMUpgradeTool silently comments them out
    (`/* formula */`) while printing "Patch File Applied" — found live on this
    project 2026-06-12 (Contacts::FullName arrived commented out). The fix is
    the FMSaveAsXML round-trip's own mechanism: a Structure/ModifyAction/
    FieldsForTables re-apply pass, one stub FieldCatalog per calc-carrying
    field. Covers (a) every calc-carrying field in this patch's AddAction and
    (b) repair stubs for EXISTING fields whose live formula drifted from the
    spec (the reconciler's repair_calcs). Appended as Structure's LAST child,
    matching gen_patch's validated action order. Returns the stub count."""
    structure = root.find("Structure")
    stubs = []
    add = structure.find("AddAction") if structure is not None else None
    if add is not None:
        for fc in add.iter("FieldCatalog"):
            btref = fc.find("BaseTableReference")
            ol = fc.find("ObjectList")
            if btref is None or ol is None:
                continue
            for f in ol.iter("Field"):
                if not f.get("name"):
                    continue
                payloads = []
                calc = f.find("Calculation")
                if calc is not None:
                    payloads.append(copy.deepcopy(calc))
                ae = f.find("AutoEnter")
                if ae is not None and ae.find(".//Calculation") is not None:
                    payloads.append(copy.deepcopy(ae))
                val = f.find("Validation")
                if val is not None and val.find(".//Calculation") is not None:
                    payloads.append(copy.deepcopy(val))
                if not payloads:
                    continue
                stub = etree.Element("FieldCatalog")
                stub.append(copy.deepcopy(btref))
                sol = etree.SubElement(stub, "ObjectList", membercount="1")
                sf = etree.SubElement(sol, "Field")
                fr = etree.SubElement(sf, "FieldReference", id=f.get("id") or "",
                                      name=f.get("name"), repetition="1")
                u = f.find("UUID")
                if u is not None and u.text:
                    fr.set("UUID", u.text.strip())
                for p in payloads:
                    fr.append(p)
                fr.append(copy.deepcopy(btref))
                stubs.append(stub)
    for tname, entries in repair_calcs.items():
        t = ctx["tables"][tname]
        to = ctx["tos"][tname]
        for entry in entries:
            ex = ctx["fields_by_table"][tname][entry["name"]]
            stub = etree.Element("FieldCatalog")
            btref = etree.SubElement(stub, "BaseTableReference",
                                     id=t["id"], name=tname)
            if t.get("uuid"):
                btref.set("UUID", t["uuid"])
            sol = etree.SubElement(stub, "ObjectList", membercount="1")
            sf = etree.SubElement(sol, "Field")
            fr = etree.SubElement(sf, "FieldReference", id=ex["id"],
                                  name=entry["name"], repetition="1")
            if ex.get("uuid"):
                fr.set("UUID", ex["uuid"])
            calc = etree.fromstring(
                f'<Calculation>'
                f'<TableOccurrenceReference id="{to["id"]}" name="{tname}" '
                f'UUID="{to.get("uuid", "")}"/>'
                f'<Text>{escape(entry["formula"])}</Text></Calculation>')
            fr.append(calc)
            fr.append(copy.deepcopy(btref))
            stubs.append(stub)
    if not stubs:
        return 0
    modify = etree.SubElement(structure, "ModifyAction", membercount="1")
    ffts = etree.SubElement(modify, "FieldsForTables", membercount=str(len(stubs)))
    for s in stubs:
        ffts.append(s)
    return len(stubs)


# ---------------------------------------------------------------------------
# Coverage oracle, generate orchestration, CLI (Task 6)
# ---------------------------------------------------------------------------

def check_expected(expected: dict, parsed_dir: str | Path) -> dict:
    """Spec-coverage oracle: every expected object must exist in the parsed
    re-export, fields with the right datatype/fieldtype, layouts bound to
    the right TO. Pure function — unit-testable without Claris tools."""
    parsed = Path(parsed_dir)
    _load = lambda fn: json.loads((parsed / fn).read_text())
    tables = {t["name"] for t in _load("base_tables.json")}
    fields = {(f["table_name"], f["name"]): f for f in _load("fields.json")}
    tos = {t["name"] for t in _load("table_occurrences.json")}
    layouts = {l["name"]: l for l in _load("layouts.json") if not l.get("is_folder")}
    missing, mismatched = [], []
    for e in expected["entries"]:
        if e["kind"] == "base_table":
            if e["name"] not in tables:
                missing.append(e["key"])
        elif e["kind"] == "field":
            f = fields.get((e["table"], e["name"]))
            if f is None:
                missing.append(e["key"])
            elif f["datatype"] != e["datatype"] or f["fieldtype"] != e["fieldtype"]:
                mismatched.append(
                    f'{e["key"]}: file has {f["fieldtype"]}/{f["datatype"]}, '
                    f'expected {e["fieldtype"]}/{e["datatype"]}')
            elif e["fieldtype"] == "Calculated":
                # FMUpgradeTool comments out uncompilable calc formulas
                # (`/* … */`) while reporting success — a field that EXISTS
                # with the right type can still be a dead calc. Catch both the
                # commented and empty forms; with a spec formula on record,
                # also catch silent divergence.
                ct = (f.get("calc_text") or "").strip()
                norm = lambda s: " ".join((s or "").split())
                if ct.startswith("/*") or not ct:
                    mismatched.append(
                        f'{e["key"]}: calc arrived commented out/empty '
                        f'({ct[:50]!r}) — regenerate (repair pass) and re-apply')
                elif e.get("formula") and norm(ct) != norm(e["formula"]):
                    mismatched.append(
                        f'{e["key"]}: live formula {ct[:50]!r} differs from '
                        f'spec {e["formula"][:50]!r}')
        elif e["kind"] == "table_occurrence":
            if e["name"] not in tos:
                missing.append(e["key"])
        elif e["kind"] == "layout":
            l = layouts.get(e["name"])
            if l is None:
                missing.append(e["key"])
            elif l.get("table_occurrence") != e["table"]:
                mismatched.append(
                    f'{e["key"]}: bound to TO {l.get("table_occurrence")!r}, '
                    f'expected {e["table"]!r}')
    return {"verified": not missing and not mismatched,
            "missing": missing, "mismatched": mismatched}


def generate(spec_path: str | Path, export_path: str | Path,
             out_dir: str | Path, parsed_dir: Path | None = None) -> dict:
    """gen: spec + target export -> patch.xml + expected.json in out_dir.
    No patch.xml is written on a no-op delta. Never touches any .fmp12."""
    spec = load_spec(spec_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if parsed_dir is None:
        parsed_dir = saxml_parser.snapshot(export_path, out / "pre_parsed")
    ctx = harvest_context(export_path, parsed_dir)
    expanded = expand_spec(spec)
    delta = compute_delta(expanded, ctx)
    (out / "expected.json").write_text(json.dumps(
        {"file": spec["file"], "entries": expected_entries(expanded)}, indent=1))
    counts = {"new_tables": len(delta["new_tables"]),
              "new_fields": sum(len(v) for v in delta["new_fields"].values())
                            + sum(len(expanded[t]) for t in delta["new_tables"]),
              "new_tos": len(delta["new_tos"]),
              "add_layouts": len(delta["add_layouts"]),
              "regen_layouts": len(delta["regen_layouts"])}
    summary = {"file": spec["file"], "noop": delta["noop"],
               "drift": delta["drift"], "counts": counts,
               "out": str(out), "expected": str(out / "expected.json")}
    if delta["noop"]:
        return summary
    patch = build_patch(expanded, delta, ctx)
    (out / "patch.xml").write_text(patch)
    summary["patch"] = str(out / "patch.xml")
    return summary


def verify_built(expected_path: str | Path, target: str | Path,
                 workdir: str | Path, account: str = "Admin", pwd: str = "") -> dict:
    """verify: re-export the (closed) target and run the coverage oracle.
    Scaffold catalogs never need DDR info, so the re-export omits it."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    xml = fm_export.export_xml(Path(target), workdir / "post.xml", account, pwd)
    parsed = saxml_parser.snapshot(xml, workdir / "post_parsed")
    return check_expected(json.loads(Path(expected_path).read_text()), parsed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen", help="spec + target export -> patch.xml + expected.json")
    g.add_argument("spec"); g.add_argument("export")
    g.add_argument("-o", "--out", required=True)
    v = sub.add_parser("verify", help="expected.json + patched file -> coverage check")
    v.add_argument("expected"); v.add_argument("target")
    v.add_argument("--workdir", required=True)
    v.add_argument("--account", default="Admin"); v.add_argument("--pwd", default="")
    a = ap.parse_args()
    if a.cmd == "gen":
        try:
            print(json.dumps(generate(a.spec, a.export, a.out), indent=1))
        except (SpecError, ValueError) as e:
            print(str(e), file=sys.stderr)
            sys.exit(2)
    else:
        r = verify_built(a.expected, a.target, a.workdir, a.account, a.pwd)
        print(json.dumps(r, indent=1))
        sys.exit(0 if r["verified"] else 1)
