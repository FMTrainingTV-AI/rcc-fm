"""OOE conformance — Phase 1 (pure Python, no FileMaker tooling required).

Verifies the pipeline against Mislav Kos's "one of everything" file (the canonical
corpus, vendored MIT under fixtures/ooe/): the parser ingests every handled catalog,
and the differ assigns each real object kind the documented patchability tier — the
green/yellow/red matrix in docs/patchability-matrix.md.

This turns the capability matrix from "we believe" into "we tested, against the
canonical file" for the parse + diff + tier-classification stages. Phase 2 (apply via
FMUpgradeTool + re-export + verify) needs the Claris CLI and lives elsewhere.
"""
import gzip
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import saxml_parser as P
import saxml_diff as D
import gen_patch

FIXTURE = Path(__file__).parent / "fixtures" / "ooe" / "Ooe__saxml_v2_2_3_0__fm_v22_0_4.xml.gz"

# Exact object counts in this frozen OOE snapshot (FM 22.0.4, SaXML 2.2.3.0, no DDR).
EXPECTED_COUNTS = {
    "base_tables.json": 4, "fields.json": 42, "table_occurrences.json": 7,
    "relationships.json": 2, "scripts.json": 41, "layouts.json": 14,
    "value_lists.json": 4, "custom_functions.json": 14, "external_data_sources.json": 4,
}

# The documented matrix (docs/patchability-matrix.md), encoded here as the INDEPENDENT
# oracle — proven=green, caution=yellow, manual=red. If a tier changes in the code, the
# OOE test fails until the doc/slide and this oracle are updated together.
EXPECTED_ADDED = {
    "base_table": "proven", "field": "proven", "table_occurrence": "proven",
    "relationship": "proven", "layout": "proven",
    "script": "caution", "value_list": "caution", "custom_function": "caution",
    "external_data_source": "caution",
}
EXPECTED_REMOVED = {
    "base_table": "caution", "field": "caution", "table_occurrence": "caution",
    "script": "caution", "layout": "caution", "value_list": "caution",
    "custom_function": "caution",
    "relationship": "manual", "external_data_source": "manual",
}


@pytest.fixture(scope="module")
def ooe_dir(tmp_path_factory):
    """Decompress + parse the vendored OOE export once for the whole module."""
    work = tmp_path_factory.mktemp("ooe")
    xml = work / "Ooe.xml"
    with gzip.open(FIXTURE, "rb") as fh:
        xml.write_bytes(fh.read())
    out = work / "parsed"
    P.snapshot(xml, out)
    return out


def _copy_parsed(src: Path, dst: Path) -> Path:
    """Copy the _meta + all handled-catalog JSON files into a fresh parsed dir."""
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "_meta.json", dst / "_meta.json")
    for _kind, (fname, _attrs) in D.KINDS.items():
        objs = json.loads((src / fname).read_text()) if (src / fname).exists() else []
        (dst / fname).write_text(json.dumps(objs))
    return dst


def _drop_first_of_each_kind(src: Path, dst: Path) -> Path:
    """Like _copy_parsed, but drop each catalog's first object → one diff item per kind."""
    _copy_parsed(src, dst)
    for _kind, (fname, _attrs) in D.KINDS.items():
        objs = json.loads((dst / fname).read_text())
        (dst / fname).write_text(json.dumps(objs[1:] if objs else objs))
    return dst


def test_parse_ingests_every_handled_catalog(ooe_dir):
    """The parser reads the canonical one-of-everything file across the FM22→FM26 gap."""
    for fname, n in EXPECTED_COUNTS.items():
        objs = json.loads((ooe_dir / fname).read_text())
        assert len(objs) == n, f"{fname}: expected {n}, got {len(objs)}"


def test_added_tier_per_kind(ooe_dir, tmp_path):
    """Every real OOE object, seen as an ADD, gets the documented tier."""
    prod = _drop_first_of_each_kind(ooe_dir, tmp_path / "prod")
    out = D.diff_snapshots(ooe_dir, prod, {})
    added = {i["kind"]: i for i in out["items"] if i["change"] == "added"}
    for kind in D.KINDS:
        assert kind in added, f"no added item surfaced for {kind}"
        assert not added[kind]["duplicate_name"], f"{kind} sample collided on name"
        assert added[kind]["patchability"] == EXPECTED_ADDED[kind], \
            f"add {kind}: expected {EXPECTED_ADDED[kind]}, got {added[kind]['patchability']}"


def test_removed_tier_per_kind(ooe_dir, tmp_path):
    """Every real OOE object, seen as a REMOVE, gets the documented tier (incl. manual)."""
    dev = _drop_first_of_each_kind(ooe_dir, tmp_path / "dev")
    out = D.diff_snapshots(dev, ooe_dir, {})
    removed = {i["kind"]: i for i in out["items"] if i["change"] == "removed"}
    for kind in D.KINDS:
        assert kind in removed, f"no removed item surfaced for {kind}"
        assert removed[kind]["patchability"] == EXPECTED_REMOVED[kind], \
            f"remove {kind}: expected {EXPECTED_REMOVED[kind]}, got {removed[kind]['patchability']}"


def test_modified_tier_field_and_script_vs_manual(ooe_dir, tmp_path):
    """A changed field/script is caution (yellow); a changed table is manual (red)."""
    prod = _copy_parsed(ooe_dir, tmp_path / "prod")
    for kind, (fname, _a) in D.KINDS.items():
        objs = json.loads((prod / fname).read_text())
        if not objs:
            continue
        if kind == "field":
            objs[0] = objs[0] | {"comment": (objs[0].get("comment") or "") + " (edited)", "_hash": "MUT"}
        elif kind == "script":
            objs[0] = objs[0] | {"_hash": "MUT"}            # deep-structure change only
        elif kind == "base_table":
            objs[0] = objs[0] | {"comment": "edited", "_hash": "MUT"}
        (prod / fname).write_text(json.dumps(objs))
    out = D.diff_snapshots(ooe_dir, prod, {})
    mod = {i["kind"]: i for i in out["items"] if i["change"] == "modified"}
    assert mod["field"]["patchability"] == "caution"
    assert mod["script"]["patchability"] == "caution"
    assert mod["base_table"]["patchability"] == "manual"


def test_generator_capability_locks_the_matrix():
    """The generator's declared coverage must match the documented tiers — no silent drift.

    Pure introspection (no fixture needed): if someone widens or narrows what the
    generator emits, or edits the PATCHABILITY table, this fails until the matrix doc
    and slide are updated to match.
    """
    # Adds: the generator builds every added-tier kind EXCEPT external data sources
    # (tiered caution for display, but path/credentials are environment-specific → manual).
    assert gen_patch.SUPPORTED_KINDS == set(EXPECTED_ADDED) - {"external_data_source"}
    # Changes (ReplaceAction): fields and scripts only.
    assert set(gen_patch.REPLACE_TAGS) == {"field", "script"} == set(D.PATCHABILITY["modified"])
    # Removes (DeleteAction): exactly the caution-removed kinds.
    assert set(gen_patch.DELETE_ITEM_REF) == {k for k, v in EXPECTED_REMOVED.items() if v == "caution"}
    # The live tier table agrees with the documented oracle.
    assert D.PATCHABILITY["added"] == EXPECTED_ADDED
    assert D.PATCHABILITY["removed"] == {k: v for k, v in EXPECTED_REMOVED.items() if v == "caution"}
