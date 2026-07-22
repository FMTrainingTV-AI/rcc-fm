"""Generate FMUpgradeTool patch XML from a diff selection.

Automates Claris's documented manual workflow for FMUpgradeTool patches:
export both files as FMSaveAsXML, diff them, copy XML fragments for the new
objects from the source (dev) export into a <FMUpgradeToolPatch> document.
This module harvests the selected fragments from the dev export, remaps
identity (UUIDs + numeric ids) against the prod export, verifies dependency
closure, and emits a patch FMUpgradeTool can apply to the prod file.

Scope: AddAction for every supported kind; behind allow_caution additionally
ReplaceAction for *modified* fields and scripts and DeleteAction for *removed*
base tables, fields, table occurrences, scripts, layouts, value lists and
custom functions. Modified items of any other kind are rejected (v1) — handle
them manually. Custom functions can't be Replace'd at all (official limitation;
delete + re-add manually).

Added scripts carry their STEP BODIES: FMSaveAsXML keeps those outside the
ScriptCatalog in a StepsForScripts element (last child of Structure/AddAction),
one <Script><ScriptReference/><ObjectList of Step/></Script> entry per script.
The patch mirrors that placement (validated by round trip: generate -> apply ->
re-export -> step hashes equal, 2026-06-12). Modified scripts whose steps
differ are REJECTED — ReplaceAction cannot carry step bodies.

Replace/Delete shapes (per the official App Upgrade Tool Guide,
resources mirror: app-upgrade-tool-guide/{replace-action-example,patch-file}.md;
validated against FMUpgradeTool on 2026-06-11 — a real Field replace changed a
comment, a real Field delete removed the field):

  <ReplaceAction>
    <Replace type="<ElementName>" UUID="<target's CURRENT prod UUID>">
      <ParentReference .../>      <!-- BaseTableReference for fields;
                                       CatalogReference for catalog-level
                                       objects like scripts -->
      <ElementName id="<prod id>" ...>   <!-- COMPLETE replacement object -->
        <UUID><same prod UUID></UUID>
        ...
      </ElementName>
    </Replace>
  </ReplaceAction>

  <DeleteAction>
    <ItemReference UUID="<prod UUID>" type="<KindReference>">
      <BaseTableReference .../>   <!-- required for type="FieldReference" -->
    </ItemReference>
  </DeleteAction>

ReplaceAction can SILENTLY NO-OP (exit 0, "Patch File Applied", zero effect) —
every applied patch must be verified independently (Task 7's applier re-diffs).

Identity rules:
  - Patch root version MUST equal the dev export's FMSaveAsXML version attr
    (read dynamically; FMDeveloperTool emits 2.2.3.0, FM Pro 2026 emits 2.3.0.0).
  - Object DEFINITIONS carry a <UUID> child; REFERENCES (tags ending in
    "Reference") carry UUID/id/name attributes.
  - Every new object gets a fresh uppercase uuid4, unique within the patch,
    and a numeric id clear of prod's ids in that id-space. Field ids are
    per-table: fields of an added table keep dev ids; fields added into an
    existing prod table renumber from that table's prod max field id.
  - Catalogs that exist in prod keep prod's catalog <UUID>; absent ones get
    a fresh UUID.
  - All <DDRREF> elements and all `hash` attributes are stripped.
  - Calc fields additionally get a Structure/ModifyAction re-apply pass
    (mirroring FMSaveAsXML's own shape) so formulas that reference fields by
    name aren't silently commented out by the tool — see _calc_modify_action.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import uuid
from pathlib import Path

from lxml import etree

import saxml_parser as P
from saxml_diff import obj_key


class DependencyError(Exception):
    def __init__(self, problems: list[str], missing_keys=None, missing_refs=None):
        super().__init__("unresolved references:\n  " + "\n  ".join(problems))
        self.problems = problems
        # diff keys of referenced-but-unselected objects that are themselves
        # available as 'added' diff items — i.e. the deps you'd also need to tick.
        self.missing_keys = set(missing_keys or ())
        # Structured form of the same failures, one entry per unresolved
        # reference: {key, kind, name, label}. `key` is the diff key when the
        # reference resolves to a known dev object, else None — a None key is
        # the signal that no amount of co-selection fixes it. Callers must use
        # this rather than pattern-matching `problems` strings, which do not
        # contain diff keys verbatim.
        self.missing_refs = list(missing_refs or ())


def _note_missing(st, key, kind, name, label) -> None:
    """Record one unresolved reference in structured form.

    key is the diff key of the object that would satisfy it, or None when
    nothing in the diff can — the caller uses that distinction to tell an
    auto-includable dependency from a hard blocker."""
    if "missing_refs" in st:
        st["missing_refs"].append(
            {"key": key, "kind": kind, "name": name, "label": label})


def fresh_uuid() -> str:
    return str(uuid.uuid4()).upper()


# Catalog dependency order inside AddAction — the tool processes top-to-bottom
# and forward references FAIL, so layouts go last.
CATALOG_ORDER: list[tuple[str, str]] = [
    ("base_table", "BaseTableCatalog"),
    ("field", "FieldsForTables"),
    ("table_occurrence", "TableOccurrenceCatalog"),
    ("relationship", "RelationshipCatalog"),
    ("value_list", "ValueListCatalog"),
    ("custom_function", "CustomFunctionsCatalog"),
    ("script", "ScriptCatalog"),
    ("layout", "LayoutCatalog"),
]
SUPPORTED_KINDS = {k for k, _ in CATALOG_ORDER}

# ReplaceAction v1: fields and scripts only. The Replace `type` attr is the
# element name; the child *Reference names the PARENT of the replaced object
# (BaseTableReference for a field, the ScriptCatalog itself for a script —
# expressed as <CatalogReference catalogName uuid>, the same reference shape
# patch-file.md documents for whole-catalog deletes). Script replace swaps the
# CATALOG definition (name/options) ONLY — step bodies live in StepsForScripts,
# and the official format can't replace them (Replace XML "must not contain an
# ObjectList element", patch-file.md). _build_replaces therefore REJECTS
# modified scripts whose step bodies differ between dev and prod: a
# catalog-only swap would silently keep prod's old steps.
REPLACE_TAGS = {"field": "Field", "script": "Script"}
REPLACE_PARENT_CATALOG = {"script": "ScriptCatalog"}

# DeleteAction: ItemReference @type values per patch-file.md's supported list.
# (relationship deletes need RelationshipReference but our diff keys carry no
# UUID-stable identity for them yet; external_data_source unproven — both stay
# manual in v1.)
DELETE_ITEM_REF = {
    "base_table": "BaseTableReference",
    "field": "FieldReference",          # must carry a BaseTableReference child
    "table_occurrence": "TableOccurrenceReference",
    "script": "ScriptReference",
    "layout": "LayoutReference",
    "value_list": "ValueListReference",
    "custom_function": "CustomFunctionReference",
}

# Reference tag -> diff kind, for resolving reference elements during the walk.
REF_KINDS = {
    "BaseTableReference": "base_table",
    "TableOccurrenceReference": "table_occurrence",
    "FieldReference": "field",
    "RelationshipReference": "relationship",
    "ValueListReference": "value_list",
    "CustomFunctionReference": "custom_function",
    "ScriptReference": "script",
    "LayoutReference": "layout",
    "ExternalDataSourceReference": "external_data_source",
}


def _uuid_child(elem) -> str | None:
    u = elem.find("UUID")
    if u is None or u.text is None:
        return None
    return u.text.strip() or None


def _rel_dict(rel) -> dict:
    """Minimal relationship dict matching saxml_diff.obj_key's grammar."""
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
    return {
        "left_to": left.get("name") if left is not None else None,
        "right_to": right.get("name") if right is not None else None,
        "predicates": preds,
    }


def _index(root) -> tuple[dict, dict]:
    """Build per-kind key -> {elem, id, uuid, ...} indexes plus per-table
    FieldCatalog info. Iteration mirrors saxml_parser so keys line up with
    the diff's obj_key grammar.

    Indexing is scoped to Structure/AddAction: exports also carry a
    Structure/ModifyAction/FieldsForTables section (a re-apply pass for calc
    formulas, one stub FieldCatalog per calc field) whose stubs would
    otherwise shadow the real per-table FieldCatalogs."""
    scope = root.find("Structure/AddAction")
    if scope is None:
        scope = root
    idx: dict[str, dict] = {k: {} for k in SUPPORTED_KINDS | {"external_data_source"}}
    fieldcats: dict[str, dict] = {}  # table name -> {elem, uuid, btref:{id,name,uuid}}
    root = scope

    for cat in root.iter("BaseTableCatalog"):
        for el in cat.iter("BaseTable"):
            idx["base_table"][f"base_table:{el.get('name')}"] = {
                "elem": el, "id": el.get("id"), "uuid": _uuid_child(el)}

    for ffts in root.iter("FieldsForTables"):
        for fc in ffts.iter("FieldCatalog"):
            btref = fc.find("BaseTableReference")
            tn = btref.get("name") if btref is not None else None
            if tn is not None:
                fieldcats[tn] = {
                    "elem": fc, "uuid": _uuid_child(fc),
                    "btref": {"id": btref.get("id"), "name": tn,
                              "uuid": btref.get("UUID")}}
            ol = fc.find("ObjectList")
            if ol is None:
                continue
            for f in ol.iter("Field"):
                if not f.get("name"):
                    continue  # nameless calc-body sibling, harvested with its field
                key = obj_key("field", {"table_name": tn, "name": f.get("name")})
                idx["field"][key] = {"elem": f, "id": f.get("id"),
                                     "uuid": _uuid_child(f), "table_name": tn,
                                     "objectlist": ol}

    for cat in root.iter("TableOccurrenceCatalog"):
        for el in cat.iter("TableOccurrence"):
            bt = el.find("BaseTableSourceReference/BaseTableReference")
            idx["table_occurrence"][f"table_occurrence:{el.get('name')}"] = {
                "elem": el, "id": el.get("id"), "uuid": _uuid_child(el),
                "base_table_name": bt.get("name") if bt is not None else None,
                "name": el.get("name")}

    for cat in root.iter("RelationshipCatalog"):
        for el in cat.iter("Relationship"):
            key = obj_key("relationship", _rel_dict(el))
            idx["relationship"][key] = {"elem": el, "id": el.get("id"),
                                        "uuid": _uuid_child(el)}

    simple = [("script", "ScriptCatalog", "Script"),
              ("layout", "LayoutCatalog", "Layout"),
              ("value_list", "ValueListCatalog", "ValueList"),
              ("custom_function", "CustomFunctionsCatalog", "CustomFunction"),
              ("external_data_source", "ExternalDataSourceCatalog", "ExternalDataSource")]
    for kind, cat_tag, obj_tag in simple:
        for cat in root.iter(cat_tag):
            for el in cat.iter(obj_tag):
                idx[kind][f"{kind}:{el.get('name')}"] = {
                    "elem": el, "id": el.get("id"), "uuid": _uuid_child(el)}

    return idx, fieldcats


def _max_id(entries) -> int:
    best = 0
    for e in entries:
        try:
            best = max(best, int(e["id"]))
        except (TypeError, ValueError):
            pass
    return best


class PatchBuilder:
    def __init__(self, dev_root, prod_root, diff: dict):
        self.dev_root = dev_root
        self.prod_root = prod_root
        self.diff = diff
        scope = dev_root.find("Structure/AddAction")
        self.dev_scope = scope if scope is not None else dev_root

        self.dev, self.dev_fieldcats = _index(dev_root)
        self.prod, self.prod_fieldcats = _index(prod_root)
        self.prod_cat_uuids = P.parse_catalog_uuids(prod_root)

        # dev UUID -> diff key, so an unresolved reference UUID can be named as
        # the dependency it points at (used by dependency_graph()).
        self.dev_uuid_to_key: dict[str, str] = {}
        for _k in self.dev:
            for _key, _e in self.dev[_k].items():
                if _e.get("uuid"):
                    self.dev_uuid_to_key[_e["uuid"]] = _key

        # Script step bodies live OUTSIDE ScriptCatalog, in StepsForScripts
        # (last child of AddAction). (by_uuid, by_id) per side.
        self.dev_steps = P.script_steps_index(self.dev_scope)
        self.prod_steps = P.script_steps_index(prod_root)

        # Every UUID prod knows about (child text or attribute) — references to
        # these need no remapping.
        self.prod_uuids: set[str] = set()
        for el in prod_root.iter():
            if el.tag == "UUID" and el.text and el.text.strip():
                self.prod_uuids.add(el.text.strip())
            u = el.get("UUID")
            if u:
                self.prod_uuids.add(u)

        # SHARED map: same kind+key in both files -> dev uuid resolves to prod
        # uuid, and we remember prod's numeric id for that target.
        self.shared_uuid_map: dict[str, str] = {}
        self.shared_id_for_target: dict[str, str] = {}
        for kind in self.dev:
            for key, d in self.dev[kind].items():
                p = self.prod[kind].get(key)
                if p is None:
                    continue
                if d["uuid"] and p["uuid"]:
                    self.shared_uuid_map[d["uuid"]] = p["uuid"]
                    if p["id"] is not None:
                        self.shared_id_for_target[p["uuid"]] = p["id"]

        # dev TO name -> base table name (for FieldReference fallback path)
        self.dev_to_table = {e["name"]: e["base_table_name"]
                             for e in self.dev["table_occurrence"].values()}

        # prod theme inventory for LayoutThemeReference resolution
        self.prod_theme_uuids: set[str] = set()
        self.prod_theme_names: set[str] = set()
        for th in prod_root.iter("Theme"):
            u = _uuid_child(th)
            if u:
                self.prod_theme_uuids.add(u)
            if th.get("name"):
                self.prod_theme_names.add(th.get("name"))
        for ref in prod_root.iter("LayoutThemeReference"):
            if ref.get("UUID"):
                self.prod_theme_uuids.add(ref.get("UUID"))
            if ref.get("name"):
                self.prod_theme_names.add(ref.get("name"))

        # prod max ids per id-space
        self.prod_max = {kind: _max_id(self.prod[kind].values())
                         for kind in SUPPORTED_KINDS if kind != "field"}
        self.prod_field_max: dict[str, int] = {}
        for e in self.prod["field"].values():
            tn = e["table_name"]
            try:
                self.prod_field_max[tn] = max(self.prod_field_max.get(tn, 0), int(e["id"]))
            except (TypeError, ValueError):
                self.prod_field_max.setdefault(tn, 0)

    # -- public API -----------------------------------------------------------

    def build(self, selected_keys: list[str], allow_caution: bool = False) -> etree._Element:
        diff_items = {i["key"]: i for i in self.diff.get("items", [])}

        # 1. validate selection, split by change type
        seen: set[str] = set()
        keys: list[str] = []          # added -> AddAction
        replace_keys: list[str] = []  # modified -> ReplaceAction
        delete_keys: list[str] = []   # removed -> DeleteAction
        caution: list[str] = []
        for key in selected_keys:
            if key in seen:
                continue
            seen.add(key)
            item = diff_items.get(key)
            if item is None:
                raise ValueError(f"selected key not present in diff: {key}")
            if item.get("ignored"):
                raise ValueError(f"selected key is marked ignored in the diff: {key}")
            if item.get("duplicate_name"):
                raise ValueError(
                    f"selected key has a duplicate name — only the last same-named "
                    f"object survives diff keying, so patching would silently drop "
                    f"the rest; resolve the duplicate in FileMaker first: {key}")
            if item.get("patchability") == "manual":
                raise ValueError(
                    f"selected key is manual-tier (not auto-patchable): {key}")
            change = item.get("change")
            if change == "added":
                if item.get("kind") not in SUPPORTED_KINDS:
                    raise ValueError(f"AddAction not supported for kind '{item.get('kind')}': {key}")
                keys.append(key)
            elif change == "modified":
                caution.append(key)
                replace_keys.append(key)
            elif change == "removed":
                caution.append(key)
                delete_keys.append(key)
            else:
                raise ValueError(f"unsupported change '{change}' for {key}")
        if caution and not allow_caution:
            raise ValueError(
                "selection includes modified/removed items, which generate "
                "ReplaceAction/DeleteAction and require allow_caution "
                "(--allow-caution): " + ", ".join(caution))
        for key in replace_keys:
            kind = diff_items[key].get("kind")
            if kind not in REPLACE_TAGS:
                raise ValueError(
                    f"ReplaceAction not supported for kind '{kind}' in v1 "
                    f"(field and script only — handle manually): {key}")
        for key in delete_keys:
            kind = diff_items[key].get("kind")
            if kind not in DELETE_ITEM_REF:
                raise ValueError(
                    f"DeleteAction not supported for kind '{kind}' "
                    f"(handle manually): {key}")

        sel_by_kind: dict[str, list[str]] = {k: [] for k in SUPPORTED_KINDS}
        for key in keys:
            sel_by_kind[diff_items[key]["kind"]].append(key)

        # per-build mutable state (builder stays reusable across builds)
        st = {
            "uuid_map": dict(self.shared_uuid_map),
            "id_for_target": dict(self.shared_id_for_target),
            "added": {k: {} for k in SUPPORTED_KINDS},
            "used_uuids": set(),
            "missing_keys": set(),
            "missing_refs": [],
        }
        problems: list[str] = []

        # 2. register added objects: fresh UUIDs + new numeric ids
        added_tables = {key.split(":", 1)[1] for key in sel_by_kind["base_table"]}
        counters = {k: self.prod_max.get(k, 0) for k in SUPPORTED_KINDS if k != "field"}
        field_counters = dict(self.prod_field_max)

        for kind, _cat in CATALOG_ORDER:
            for key in sel_by_kind[kind]:
                entry = self.dev[kind].get(key)
                if entry is None:
                    raise ValueError(f"{key} not found in dev export")
                if kind == "field":
                    tn = entry["table_name"]
                    if tn in added_tables:
                        new_id = entry["id"]  # table is new: keep dev field ids
                    elif tn in self.prod_fieldcats:
                        field_counters[tn] = field_counters.get(tn, 0) + 1
                        new_id = str(field_counters[tn])
                    else:
                        problems.append(
                            f"{key}: table '{tn}' is neither selected for add nor present in prod")
                        known = f"base_table:{tn}" in self.dev["base_table"]
                        if known:
                            st["missing_keys"].add(f"base_table:{tn}")
                        _note_missing(st, f"base_table:{tn}" if known else None,
                                      "base_table", tn, key)
                        continue
                else:
                    counters[kind] += 1
                    new_id = str(counters[kind])
                fresh = self._fresh(st)
                if entry["uuid"]:
                    st["uuid_map"][entry["uuid"]] = fresh
                st["id_for_target"][fresh] = new_id
                st["added"][kind][key] = {"entry": entry, "fresh": fresh, "new_id": new_id}

        # 3. harvest fragments + assemble AddAction in dependency order
        add = etree.Element("AddAction")
        fragments: list[tuple[str, etree._Element]] = []  # (label, elem) for the ref walk

        for kind, cat_tag in CATALOG_ORDER:
            if not st["added"][kind]:
                continue
            if kind == "field":
                wrap = self._assemble_fields(st, fragments, added_tables)
            else:
                wrap = self._catalog_wrapper(cat_tag, len(st["added"][kind]))
                for key, info in st["added"][kind].items():
                    frag = copy.deepcopy(info["entry"]["elem"])
                    frag.set("id", info["new_id"])
                    wrap.append(frag)
                    fragments.append((key, frag))
            if wrap is not None and len(wrap):
                add.append(wrap)

        # 3a. step bodies for added scripts — StepsForScripts goes LAST in
        # AddAction, mirroring the donor export's placement (it is the last
        # child of Structure/AddAction in every FMSaveAsXML observed; validated
        # against FMUpgradeTool --update + re-export round trip 2026-06-12).
        steps_wrap = self._assemble_script_steps(st, fragments)
        if steps_wrap is not None:
            add.append(steps_wrap)

        # 3b. ReplaceActions for modified items, DeleteActions for removed ones
        replace_actions = self._build_replaces(replace_keys, diff_items, fragments)
        delete_actions = self._build_deletes(delete_keys, diff_items)

        # 4. pass A — strip DDRREF/hash, remap <UUID> definition children
        self._pass_strip_and_uuids(add, st)
        for ra in replace_actions:
            self._pass_strip_and_uuids(ra, st)

        # 5. pass B — remap reference attributes, resolve themes, collect problems
        for label, frag in fragments:
            self._pass_references(label, frag, st, problems)

        # 6. dependency closure: report everything at once
        if problems:
            raise DependencyError(problems, st["missing_keys"], st["missing_refs"])

        # 7. wrap. Action order: AddAction, ReplaceAction(s), DeleteAction(s),
        # ModifyAction calc re-apply last (order validated end-to-end against
        # FMUpgradeTool --validatePatch/--update 2026-06-11; the official guide
        # mandates no order, only "one or more *Action elements").
        patch = etree.Element("FMUpgradeToolPatch",
                              version=self.dev_root.get("version") or "")
        structure = etree.SubElement(patch, "Structure")
        if len(add):
            structure.append(add)
        for ra in replace_actions:
            structure.append(ra)
        for da in delete_actions:
            structure.append(da)
        modify = self._calc_modify_action(self._calc_pairs(add, replace_actions))
        if modify is not None:
            structure.append(modify)
        return patch

    # -- assembly helpers -------------------------------------------------------

    def _fresh(self, st) -> str:
        while True:
            u = fresh_uuid()
            if u not in st["used_uuids"] and u not in self.prod_uuids:
                st["used_uuids"].add(u)
                return u

    def _catalog_wrapper(self, cat_tag: str, count: int) -> etree._Element:
        """Catalog element carrying prod's catalog UUID when the catalog exists
        in prod, a fresh UUID when it only exists in dev. membercount/TagList
        mirror the dev donor's shape."""
        donor = next(self.dev_scope.iter(cat_tag), None)
        wrap = etree.Element(cat_tag)
        if donor is not None and donor.get("membercount") is not None:
            wrap.set("membercount", str(count))
        prod_uuid = self.prod_cat_uuids.get(cat_tag)
        donor_uuid = _uuid_child(donor) if donor is not None else None
        if prod_uuid:
            etree.SubElement(wrap, "UUID").text = prod_uuid
        elif donor_uuid:
            etree.SubElement(wrap, "UUID").text = fresh_uuid()
        if donor is not None and donor.find("TagList") is not None:
            etree.SubElement(wrap, "TagList")
        return wrap

    @staticmethod
    def _steps_entry(steps_idx, entry):
        """Resolve a script index entry to its StepsForScripts <Script> element
        (None for folders, separators and step-less scripts)."""
        by_uuid, by_id = steps_idx
        e = by_uuid.get(entry["uuid"]) if entry["uuid"] else None
        if e is None and entry["id"] is not None:
            e = by_id.get(entry["id"])
        return e

    def _assemble_script_steps(self, st, fragments) -> etree._Element | None:
        """One StepsForScripts <Script> entry (ScriptReference + ObjectList of
        Steps) per added script that has step bodies in dev. The entry's
        ScriptReference UUID/id remap to the new script's fresh identity via
        the normal reference walk; each Step's own UUID child gets a fresh
        value in the strip/uuid pass and its `hash` attribute is stripped.
        References inside steps (fields, TOs, layouts, other scripts) ride the
        same walk, so dependency closure covers step content too."""
        entries = []
        for key, info in st["added"]["script"].items():
            src = self._steps_entry(self.dev_steps, info["entry"])
            if src is None:
                # Self-check mirroring the fields harvest mismatch guard: when
                # the diff's parser counted steps for this script, a lookup
                # miss here would silently emit a step-less shell of it.
                ditem = next((i for i in self.diff.get("items", [])
                              if i.get("key") == key), None) or {}
                step_count = ((ditem.get("dev") or {}).get("step_count")
                              if isinstance(ditem.get("dev"), dict) else None)
                if step_count:
                    raise RuntimeError(
                        f"harvest mismatch: steps for {key} not found in dev "
                        f"StepsForScripts (diff recorded step_count={step_count})")
                continue  # folder/separator or genuinely empty script
            entries.append((key, copy.deepcopy(src)))
        if not entries:
            return None
        wrap = etree.Element("StepsForScripts", membercount=str(len(entries)))
        for key, frag in entries:
            wrap.append(frag)
            fragments.append((f"steps({key})", frag))
        return wrap

    def _assemble_fields(self, st, fragments, added_tables) -> etree._Element | None:
        """Group selected fields under per-table FieldCatalogs.

        Added table  -> harvest the table's whole dev FieldCatalog, pruned to
                        the selected fields (calc-body siblings ride along).
        Existing one -> build a wrapper FieldCatalog carrying prod's per-table
                        FieldCatalog UUID + prod BaseTableReference."""
        by_table: dict[str, list[str]] = {}
        for key, info in st["added"]["field"].items():
            by_table.setdefault(info["entry"]["table_name"], []).append(key)
        if not by_table:
            return None

        wrap = self._catalog_wrapper("FieldsForTables", len(by_table))
        for tn, field_keys in by_table.items():
            selected = set(field_keys)
            if tn in added_tables:
                fc = copy.deepcopy(self.dev_fieldcats[tn]["elem"])
                self._prune_fieldcatalog(fc, tn, selected)
            else:
                fc = self._build_fieldcatalog(tn, field_keys, st)
            # Self-check: "Patch File Applied" prints even when a malformed
            # catalog silently no-ops, so never emit fewer definitions than
            # were selected.
            n_defs = sum(1 for f in fc.iter("Field") if f.get("name"))
            if n_defs != len(selected):
                raise RuntimeError(
                    f"harvest mismatch for table '{tn}': {len(selected)} fields "
                    f"selected but {n_defs} definitions harvested")
            wrap.append(fc)
            fragments.append((f"fields({tn})", fc))
        return wrap

    def _prune_fieldcatalog(self, fc, tn: str, selected: set[str]) -> None:
        ol = fc.find("ObjectList")
        if ol is None:
            return
        keep_ids: set[str] = set()
        for ch in list(ol):  # named field definitions first
            if ch.tag == "Field" and ch.get("name"):
                key = obj_key("field", {"table_name": tn, "name": ch.get("name")})
                if key in selected:
                    keep_ids.add(ch.get("id"))
                else:
                    ol.remove(ch)
        for ch in list(ol):  # then nameless calc-body siblings
            if ch.tag == "Field" and not ch.get("name"):
                fr = ch.find("FieldReference")
                if fr is None or fr.get("id") not in keep_ids:
                    ol.remove(ch)
        if ol.get("membercount") is not None:
            ol.set("membercount", str(len(ol)))
        for col in fc.iter("CustomOrderList"):
            for k in list(col):
                if k.tag == "key" and (k.text or "").strip() not in keep_ids:
                    col.remove(k)

    def _build_fieldcatalog(self, tn: str, field_keys: list[str], st) -> etree._Element:
        prod_fc = self.prod_fieldcats[tn]
        fc = etree.Element("FieldCatalog")
        if prod_fc["uuid"]:
            etree.SubElement(fc, "UUID").text = prod_fc["uuid"]
        etree.SubElement(fc, "TagList")
        btref = etree.SubElement(fc, "BaseTableReference")
        if prod_fc["btref"]["id"] is not None:
            btref.set("id", prod_fc["btref"]["id"])
        btref.set("name", tn)
        if prod_fc["btref"]["uuid"]:
            btref.set("UUID", prod_fc["btref"]["uuid"])
        ol = etree.SubElement(fc, "ObjectList")
        for key in field_keys:
            info = st["added"]["field"][key]
            frag = copy.deepcopy(info["entry"]["elem"])
            frag.set("id", info["new_id"])
            ol.append(frag)
            body = self._calc_body_sibling(info["entry"])
            if body is not None:
                ol.append(copy.deepcopy(body))
        ol.set("membercount", str(len(ol)))
        return fc

    @staticmethod
    def _calc_body_sibling(entry) -> etree._Element | None:
        """Some exports keep a calc field's formula in a NAMELESS sibling
        <Field> (FieldReference + Calculation) in the same ObjectList; harvest
        it with the field. The FieldReference id/UUID are remapped by the
        reference walk like any other reference."""
        ol = entry.get("objectlist")
        if ol is None:
            return None
        for ch in ol:
            if ch.tag == "Field" and not ch.get("name"):
                fr = ch.find("FieldReference")
                if fr is not None and fr.get("id") == entry["id"]:
                    return ch
        return None

    @staticmethod
    def _calc_pairs(add, replace_actions) -> list[tuple]:
        """(BaseTableReference, Field) pairs needing the calc re-apply pass:
        every named field harvested into AddAction FieldCatalogs plus every
        Field replacement (its Replace already carries the table parent)."""
        pairs = []
        for fc in add.iter("FieldCatalog"):
            btref = fc.find("BaseTableReference")
            ol = fc.find("ObjectList")
            if btref is None or ol is None:
                continue
            pairs += [(btref, f) for f in ol.iter("Field") if f.get("name")]
        for ra in replace_actions:
            rep = ra.find("Replace")
            if rep is None or rep.get("type") != "Field":
                continue
            btref, f = rep.find("BaseTableReference"), rep.find("Field")
            if btref is not None and f is not None:
                pairs.append((btref, f))
        return pairs

    def _calc_modify_action(self, pairs) -> etree._Element | None:
        """Calc formulas that reference fields by name cannot compile while
        their context table occurrence is still a forward reference (the
        mandated catalog order puts FieldsForTables before
        TableOccurrenceCatalog), so FMUpgradeTool silently comments them out
        (`/* formula */`) while still printing "Patch File Applied".

        FMSaveAsXML solves the same chicken-and-egg in its own round-trip with
        a Structure/ModifyAction/FieldsForTables re-apply pass; we emit the
        identical shape for every harvested calc field (one stub FieldCatalog
        per field, carrying the already-remapped Calculation). Verified
        empirically: without this pass `Quantity * UnitPrice` lands commented
        out; with it, all formulas land verbatim. Replaced calc fields get the
        same stub (the export itself emits these stubs for existing fields),
        guarding the formula through the Replace.

        MUST be called after the strip/uuid/reference passes — stubs copy the
        already-remapped id/UUID/Calculation from the fragments."""
        stubs = []
        for btref, f in pairs:
            # Three calc carriers need the re-apply pass, not just top-level
            # <Calculation> (fieldtype="Calculated"): auto-enter calcs
            # (AutoEnter > Calculated/Calculation) land commented out exactly
            # the same way (proven empirically 2026-06-12 — 'NameFirst & " " &
            # NameLast' arrived as /* … */ without a stub, verbatim with one),
            # and validation calcs share the compile path.
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
            fr = etree.SubElement(sf, "FieldReference",
                                  id=f.get("id") or "",
                                  name=f.get("name"), repetition="1")
            u = _uuid_child(f)
            if u:
                fr.set("UUID", u)
            for payload in payloads:
                fr.append(payload)
            fr.append(copy.deepcopy(btref))
            stubs.append(stub)
        if not stubs:
            return None
        modify = etree.Element("ModifyAction", membercount="1")
        ffts = etree.SubElement(modify, "FieldsForTables",
                                membercount=str(len(stubs)))
        for stub in stubs:
            ffts.append(stub)
        return modify

    # -- ReplaceAction / DeleteAction (allow_caution tier) ----------------------

    def _build_replaces(self, replace_keys, diff_items, fragments) -> list:
        """One <ReplaceAction><Replace> per modified item (mirrors the official
        example's one-Replace-per-action shape). The replacement is the full
        DEV fragment re-identified as the prod object: id attr = prod id, and
        its dev <UUID> child remaps to the prod UUID via the shared map in the
        strip/uuid pass. Internal references ride the normal reference walk."""
        actions = []
        for key in replace_keys:
            kind = diff_items[key]["kind"]
            dev_e = self.dev[kind].get(key)
            prod_e = self.prod[kind].get(key)
            if dev_e is None:
                raise ValueError(f"{key} not found in dev export")
            if prod_e is None:
                raise ValueError(f"{key} not found in prod export")
            if not dev_e["uuid"] or not prod_e["uuid"]:
                raise ValueError(
                    f"{key} lacks a UUID in {'dev' if not dev_e['uuid'] else 'prod'} "
                    "export — run FMUpgradeTool --generateGUIDs and re-export")
            if kind == "script":
                self._reject_step_divergence(key, dev_e, prod_e)
            frag = copy.deepcopy(dev_e["elem"])
            if prod_e["id"] is not None:
                frag.set("id", prod_e["id"])
            ra = etree.Element("ReplaceAction")
            rep = etree.SubElement(ra, "Replace", type=REPLACE_TAGS[kind],
                                   UUID=prod_e["uuid"])
            if kind == "field":
                self._graft_calc_body(frag, dev_e)
                self._preserve_serial_state(key, frag, prod_e)
                pf = self.prod_fieldcats[prod_e["table_name"]]
                btref = etree.SubElement(rep, "BaseTableReference",
                                         name=pf["btref"]["name"])
                if pf["btref"]["id"] is not None:
                    btref.set("id", pf["btref"]["id"])
                if pf["btref"]["uuid"]:
                    btref.set("UUID", pf["btref"]["uuid"])
            else:
                cat_tag = REPLACE_PARENT_CATALOG[kind]
                cat_uuid = self.prod_cat_uuids.get(cat_tag)
                if not cat_uuid:
                    raise ValueError(
                        f"{key}: prod export has no {cat_tag} UUID to anchor the Replace")
                etree.SubElement(rep, "CatalogReference",
                                 catalogName=cat_tag, uuid=cat_uuid)
            rep.append(frag)
            actions.append(ra)
            fragments.append((key, frag))
        return actions

    @staticmethod
    def _preserve_serial_state(key: str, frag, prod_e) -> None:
        """A field Replace ships dev's whole definition — including the serial
        counter's nextvalue, which is per-INSTANCE state, not schema. Shipping
        a stale dev counter silently resets prod's and mints duplicate serials
        (proven: prod 100 -> 5 with exit 0), and the hash strips nextvalue so
        even verify_applied can't see it. Keep prod's counter."""
        dev_sn = frag.find("AutoEnter/SerialNumber")
        if dev_sn is None:
            return
        prod_sn = prod_e["elem"].find("AutoEnter/SerialNumber")
        if prod_sn is not None and prod_sn.get("nextvalue") is not None:
            dev_sn.set("nextvalue", prod_sn.get("nextvalue"))
        elif dev_sn.get("nextvalue") is not None:
            print(f"warning: {key}: dev adds a serial number; its nextvalue "
                  f"({dev_sn.get('nextvalue')}) ships as-is — confirm it is "
                  "ahead of existing prod data", file=sys.stderr)

    def _reject_step_divergence(self, key: str, dev_e, prod_e) -> None:
        """A script Replace swaps only the CATALOG entry; step bodies live in
        StepsForScripts and the official patch format cannot replace them
        (Replace XML "must not contain an ObjectList element" — patch-file.md;
        ScriptStepReference exists only for DeleteAction). Replacing the
        catalog entry while steps differ would print "Patch File Applied" yet
        silently keep prod's old steps, so we refuse. Options-only changes
        (hidden, full-access, ...) with identical steps are still allowed."""
        dev_steps = self._steps_entry(self.dev_steps, dev_e)
        prod_steps = self._steps_entry(self.prod_steps, prod_e)
        dev_h = P.compute_hash(dev_steps) if dev_steps is not None else None
        prod_h = P.compute_hash(prod_steps) if prod_steps is not None else None
        if dev_h != prod_h:
            raise ValueError(
                f"{key}: step bodies differ between dev and prod. ReplaceAction "
                "can only swap a script's catalog entry (name/options) — the "
                "patch format cannot replace StepsForScripts content, so the "
                "patched file would silently keep the OLD steps. Handle "
                "manually (copy the script in FileMaker Pro, or delete + "
                "re-add it as removed + added selections).")

    @staticmethod
    def _graft_calc_body(frag, dev_e) -> None:
        """Replacements must be COMPLETE objects. When the dev export keeps a
        calc field's formula in the nameless sibling shape (see
        _calc_body_sibling) the harvested definition has no inline
        <Calculation>; graft the sibling's in so the Replace doesn't drop the
        formula."""
        if frag.find("Calculation") is not None:
            return
        body = PatchBuilder._calc_body_sibling(dev_e)
        if body is None:
            return
        calc = body.find("FieldReference/Calculation")
        if calc is None:
            calc = body.find("Calculation")
        if calc is not None:
            frag.append(copy.deepcopy(calc))

    def _build_deletes(self, delete_keys, diff_items) -> list:
        """One <DeleteAction><ItemReference type UUID> per removed item, per
        patch-file.md. All references MUST have UUIDs or the tool silently
        skips the action; field deletes additionally carry the parent
        BaseTableReference child the docs require."""
        actions = []
        for key in delete_keys:
            kind = diff_items[key]["kind"]
            prod_e = self.prod[kind].get(key)
            if prod_e is None:
                raise ValueError(f"{key} not found in prod export")
            if not prod_e["uuid"]:
                raise ValueError(
                    f"{key} has no UUID in prod export — run FMUpgradeTool "
                    "--generateGUIDs and re-export (UUID-less deletes are "
                    "silently skipped)")
            da = etree.Element("DeleteAction")
            ir = etree.SubElement(da, "ItemReference", UUID=prod_e["uuid"],
                                  type=DELETE_ITEM_REF[kind])
            if kind == "field":
                pf = self.prod_fieldcats[prod_e["table_name"]]
                btref = etree.SubElement(ir, "BaseTableReference",
                                         name=pf["btref"]["name"])
                if pf["btref"]["id"] is not None:
                    btref.set("id", pf["btref"]["id"])
                if pf["btref"]["uuid"]:
                    btref.set("UUID", pf["btref"]["uuid"])
            actions.append(da)
        return actions

    # -- walk passes ------------------------------------------------------------

    def _pass_strip_and_uuids(self, add, st) -> None:
        for ddr in list(add.iter("DDRREF")):
            parent = ddr.getparent()
            if parent is not None:
                parent.remove(ddr)
        for el in add.iter():
            if "hash" in el.attrib:
                del el.attrib["hash"]
            if el.tag != "UUID":
                continue
            text = (el.text or "").strip()
            if not text:
                continue
            if text in st["uuid_map"]:
                el.text = st["uuid_map"][text]      # registered added object
            elif text in self.prod_uuids:
                pass                                 # prod identity (catalog UUIDs etc.)
            else:
                # incidental definition riding inside a fragment (LayoutObject,
                # per-table FieldCatalog of an added table, ...) -> fresh, and
                # remember the mapping so references to it remap consistently
                f = self._fresh(st)
                st["uuid_map"][text] = f
                el.text = f

    def _pass_references(self, label: str, frag, st, problems: list[str]) -> None:
        for el in frag.iter():
            tag = el.tag
            if tag == "LayoutThemeReference":
                u = el.get("UUID") or ""
                name = el.get("name") or ""
                if u in self.prod_theme_uuids or (name and name in self.prod_theme_names):
                    continue
                problems.append(
                    f"{label}: layout theme '{name or '?'}' (UUID {u or 'n/a'}) "
                    "not present in prod — adapt a donor theme first")
                # themes are manual-tier: no diff key can ever satisfy this
                _note_missing(st, None, "theme", name or "?", label)
                continue
            u = el.get("UUID")
            if u:
                if u in st["uuid_map"]:
                    target = st["uuid_map"][u]
                    el.set("UUID", target)
                    tid = st["id_for_target"].get(target)
                    if tid is not None and el.get("id") is not None:
                        el.set("id", tid)
                elif u in self.prod_uuids:
                    pass  # already a prod identity
                else:
                    kind = REF_KINDS.get(tag, tag)
                    mk = self.dev_uuid_to_key.get(u)
                    if mk is not None and "missing_keys" in st:
                        st["missing_keys"].add(mk)
                    _note_missing(st, mk, kind, el.get("name", "?"), label)
                    problems.append(
                        f"{label}: references {kind} '{el.get('name', '?')}' "
                        f"(UUID {u}) — not in prod and not selected")
            elif tag in REF_KINDS and el.get("name") is not None and el.get("id") is not None:
                self._fallback_ref(label, el, st, problems)
            elif tag == "CustomMenuSetReference":
                # UUID-less binding: built-in menu sets resolve in any file;
                # anything else names a custom menu set we can't patch in v1.
                nm = el.get("name") or ""
                if nm not in ("[File Default]", "[Standard FileMaker Menus]") \
                        and el.get("id") not in (None, "0"):
                    problems.append(
                        f"{label}: references custom menu set '{nm}' — custom "
                        "menus aren't patchable in v1; recreate it in prod first")
                    _note_missing(st, None, "custom_menu_set", nm, label)
            elif tag.endswith("Reference") and tag not in (
                    "BaseTableSourceReference",) and el.get("name") is not None:
                # Unknown reference shape outside REF_KINDS with no UUID —
                # don't fail (most bind by name to built-ins), but say so.
                print(f"warning: {label}: unhandled reference tag {tag} "
                      f"(name '{el.get('name')}') left as-is", file=sys.stderr)

    def _fallback_ref(self, label: str, el, st, problems: list[str]) -> None:
        """Reference without a UUID attribute: resolve by kind+name."""
        kind = REF_KINDS[el.tag]
        name = el.get("name")
        if kind == "field":
            tor = el.find("TableOccurrenceReference")
            to_name = tor.get("name") if tor is not None else None
            tn = self.dev_to_table.get(to_name)
            if tn is None:
                problems.append(
                    f"{label}: field reference '{name}' has no UUID and its table "
                    f"occurrence '{to_name or '?'}' cannot be resolved")
                _note_missing(st, None, "table_occurrence", to_name or "?", label)
                return
            key = obj_key("field", {"table_name": tn, "name": name})
        else:
            key = f"{kind}:{name}"
        added = st["added"].get(kind, {}).get(key)
        if added:
            el.set("id", added["new_id"])
            return
        d, p = self.dev[kind].get(key), self.prod[kind].get(key)
        if d and p:
            if d["id"] == p["id"]:
                return
            print(f"warning: {label}: {key} referenced by name+id; "
                  f"rewriting id {d['id']} -> prod id {p['id']}", file=sys.stderr)
            if p["id"] is not None:
                el.set("id", p["id"])
            return
        if "missing_keys" in st:
            st["missing_keys"].add(key)
        _note_missing(st, key if self.dev[kind].get(key) else None,
                      kind, name, label)
        problems.append(
            f"{label}: unresolved reference to {kind} '{name}' "
            "(no UUID; not shared with prod, not selected)")


def _unselectable_reason(item: dict) -> str | None:
    """Why this diff item can never be auto-included, or None if it can be."""
    if item.get("ignored"):
        return ("on the ignore list — excluded from the diff; re-run saxml_diff "
                "with a narrower --ignore if it belongs in the patch")
    if item.get("duplicate_name"):
        return ("duplicate name — only the last same-named object survives diff "
                "keying; resolve the duplicate in FileMaker first")
    if item.get("patchability") == "manual":
        return ("manual tier — FMUpgradeTool cannot patch this kind; create it "
                "in FileMaker (or paste it via the fm-xml skill) first")
    if item.get("kind") not in SUPPORTED_KINDS:
        return f"kind '{item.get('kind')}' has no AddAction support"
    return None


def dependency_analysis(dev_root, prod_root, diff: dict,
                        direction: str = "push") -> dict:
    """Dependency edges plus the blockers that must never be silently dropped.

    Returns {"deps": {key: [selectable dep keys]},
             "blockers": {key: [{kind, name, reason}]}}.

    Reuses the builder's real reference resolution: building an item alone
    surfaces exactly the objects that would have to be co-selected
    (DependencyError carries their diff keys). Callers expand `deps`
    transitively — a dep may have its own deps.

    The split matters. A required object that is ignored, manual-tier,
    duplicate-named, or of an unsupported kind CANNOT be auto-included, and the
    old graph simply dropped it: the operator got a selection that looked
    closed and a patch that landed incomplete. Those now land in `blockers`,
    and the review UI must refuse to select anything that has one.

    direction:
      "push" — dev is the source, prod keeps its own history. Only added and
               modified items are probed; removed items are not selectable and
               get no edges.
      "sync" — removed items are selectable too. Delete edges run in REVERSE
               (deleting an object requires deleting its dependents) and are
               NOT computed here; see the caveat on `removed_unanalysed`.
    """
    if direction not in ("push", "sync"):
        raise ValueError(f"direction must be 'push' or 'sync', got {direction!r}")

    builder = PatchBuilder(dev_root, prod_root, diff)
    items = diff.get("items", [])
    by_key = {i["key"]: i for i in items}

    probe_changes = ("added", "modified") if direction == "push" \
        else ("added", "modified", "removed")
    candidates = [i for i in items
                  if i.get("change") in probe_changes
                  and _unselectable_reason(i) is None]
    selectable = {i["key"] for i in candidates}

    deps: dict[str, list[str]] = {}
    blockers: dict[str, list[dict]] = {}

    for item in candidates:
        key = item["key"]
        # modified/removed compile to Replace/DeleteAction, which build()
        # refuses without allow_caution — the probe must pass it or every
        # non-added item would fall out as ValueError with no edges at all
        # (that bug is why modified items had an empty graph before).
        caution = item.get("change") in ("modified", "removed")
        try:
            builder.build([key], allow_caution=caution)
        except DependencyError as e:
            edges: set[str] = set()
            blocked: dict[tuple, dict] = {}   # dedup — one row per distinct dep
            for ref in e.missing_refs:
                k = ref.get("key")
                if k == key:
                    continue
                if k is not None and k in selectable:
                    edges.add(k)
                    continue
                dep = by_key.get(k) if k else None
                if k is None:
                    reason = ("nothing in the diff supplies it — create it in "
                              "prod manually before patching")
                elif dep is not None:
                    reason = _unselectable_reason(dep) or \
                        "not selectable in this direction"
                else:
                    reason = "referenced object is not present in the diff"
                blocked[(k, ref["kind"], ref["name"])] = {
                    "key": k,
                    "kind": ref["kind"],
                    "name": ref["name"],
                    "reason": reason,
                }
            deps[key] = sorted(edges)
            if blocked:
                blockers[key] = sorted(blocked.values(),
                                       key=lambda b: (b["kind"], b["name"]))
        except ValueError as exc:
            # genuine selection-validation failure — not a dependency edge, but
            # it does mean this item cannot be patched. Surface it, don't hide it.
            deps[key] = []
            blockers[key] = [{"key": None, "kind": "selection", "name": str(exc),
                              "reason": "cannot be included in a patch"}]
        else:
            deps[key] = []           # references resolve against prod alone

    # Transitive blocking. An item whose dependency closure contains a blocked
    # object cannot be patched either: auto-include would stop at the gap and
    # hand the generator a selection that is missing a prerequisite. Propagate
    # so the UI never offers a tick that compiles to a broken patch. One pass
    # suffices — the closure is already transitive.
    def _closure(seed: str) -> set[str]:
        out, stack = set(), [seed]
        while stack:
            for d in deps.get(stack.pop(), ()):
                if d not in out:
                    out.add(d)
                    stack.append(d)
        return out

    direct = set(blockers)
    for key in list(deps):
        if key in direct:
            continue
        for dep in sorted(_closure(key)):
            if dep in direct:
                item = by_key.get(dep, {})
                blockers.setdefault(key, []).append({
                    "key": dep,
                    "kind": item.get("kind", dep.split(":", 1)[0]),
                    "name": item.get("name", dep.split(":", 1)[-1]),
                    "reason": "depends on this object, which is itself blocked",
                    "indirect": True,
                })

    result = {"deps": deps, "blockers": blockers}
    if direction == "sync":
        # Honest gap: delete edges point the opposite way (a base table can only
        # go once everything referencing it goes too), which needs a reverse
        # index over the PROD export rather than the builder's forward walk.
        # Not computed — say so rather than imply the closure is complete.
        result["removed_unanalysed"] = sorted(
            i["key"] for i in candidates if i.get("change") == "removed")
    return result


def dependency_graph(dev_root, prod_root, diff: dict) -> dict[str, list[str]]:
    """Back-compat wrapper — edges only. Prefer dependency_analysis(), which
    also reports the blockers this shape has no way to express."""
    return dependency_analysis(dev_root, prod_root, diff)["deps"]


def generate(dev_export, prod_export, diff_path, selection_path, out_path,
             allow_caution: bool = False) -> Path:
    dev_root = etree.parse(P.open_fmsavexml(dev_export)).getroot()
    prod_root = etree.parse(P.open_fmsavexml(prod_export)).getroot()
    diff = json.loads(Path(diff_path).read_text())
    # Coherence check: a diff generated from OTHER exports would harvest
    # unreviewed content. Warn loudly rather than fail (paths legitimately
    # move between machines).
    meta = diff.get("meta", {})
    for side, arg in (("dev_export", dev_export), ("prod_export", prod_export)):
        recorded = meta.get(side)
        if recorded and Path(recorded).resolve() != Path(arg).resolve():
            print(f"warning: diff.json was generated from {side}={recorded} "
                  f"but this run uses {arg} — stale or mismatched diff?",
                  file=sys.stderr)
    sel = json.loads(Path(selection_path).read_text())
    keys = sel["selected"] if isinstance(sel, dict) else list(sel)
    builder = PatchBuilder(dev_root, prod_root, diff)
    patch = builder.build(keys, allow_caution=allow_caution)
    out = Path(out_path)
    etree.ElementTree(patch).write(str(out), xml_declaration=True,
                                   encoding="UTF-8", pretty_print=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate an FMUpgradeTool patch "
                                 "(AddAction; ReplaceAction/DeleteAction with "
                                 "--allow-caution) from a diff selection")
    ap.add_argument("--dev-export", required=True, help="dev FMSaveAsXML export (fragment source)")
    ap.add_argument("--prod-export", required=True, help="prod FMSaveAsXML export (patch target identity)")
    ap.add_argument("--diff", required=True, help="diff.json from saxml_diff.py")
    ap.add_argument("--selection", required=True, help='selection JSON: {"selected": [keys...]}')
    ap.add_argument("-o", "--out", required=True, help="output patch XML path")
    ap.add_argument("--allow-caution", action="store_true",
                    help="allow modified/removed selections (ReplaceAction for "
                         "fields/scripts, DeleteAction for removed objects). "
                         "ReplaceAction can silently no-op — always verify the "
                         "applied result")
    a = ap.parse_args()
    try:
        out = generate(a.dev_export, a.prod_export, a.diff, a.selection, a.out,
                       allow_caution=a.allow_caution)
    except DependencyError as e:
        print("DependencyError — unresolved references:", file=sys.stderr)
        for prob in e.problems:
            print(f"  {prob}", file=sys.stderr)
        sys.exit(2)
    print(f"patch written to {out}")
