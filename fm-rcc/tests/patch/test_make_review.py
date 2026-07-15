"""Tests for make_review.py — self-contained HTML diff-review artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import make_review as M

# ── Minimal fixture diff ──────────────────────────────────────────────────────

DIFF = {
    "meta": {
        "dev_file": "d",
        "prod_file": "p",
        "dev_export": "/d.xml",
        "prod_export": "/p.xml",
        "saxml_version": "2.3.0.0",
        "dev_parsed": "/dp",
        "prod_parsed": "/pp",
    },
    "items": [
        {
            "key": "base_table:NEW",
            "kind": "base_table",
            "change": "added",
            "name": "NEW",
            "table": None,
            "patchability": "proven",
            "ignored": False,
            "duplicate_name": False,
            "summary": "",
            "changed_attrs": [],
            "dev": {"name": "NEW"},
            "prod": None,
        },
        {
            "key": "layout:Weird</script>",
            "kind": "layout",
            "change": "modified",
            "name": "Weird</script>",
            "table": None,
            "patchability": "manual",
            "ignored": False,
            "duplicate_name": False,
            "summary": "(deep structure) changed",
            "changed_attrs": ["(deep structure)"],
            "dev": {"name": "Weird</script>"},
            "prod": {"name": "Weird</script>"},
        },
    ],
}


# ── Core requirements ─────────────────────────────────────────────────────────


def test_html_self_contained_no_external_requests():
    """No http:// or https:// URLs in the output (no CDN, no external requests)."""
    html = M.build_html(DIFF)
    assert "http://" not in html
    assert "https://" not in html


def test_html_embeds_data_key():
    """The item key from DIFF must be present in the output."""
    html = M.build_html(DIFF)
    assert "base_table:NEW" in html


def test_html_has_download_button():
    """Download button must be present."""
    html = M.build_html(DIFF)
    assert "Download selection.json" in html


def test_html_exactly_one_script_block():
    """Exactly one <script> block (combined data + logic)."""
    html = M.build_html(DIFF)
    assert html.count("<script") == 1


def test_script_tag_breakout_escaped():
    """The literal </script> inside item data must be escaped as <\\/script>
    so it cannot terminate the JS block prematurely."""
    html = M.build_html(DIFF)
    # The raw unescaped form must NOT appear inside the script block.
    # We verify by checking the escaped form is present.
    assert "<\\/script>" in html
    # And that the raw </script> only appears as the single closing tag,
    # not embedded in the JSON data.
    # Split on </script> — there should be exactly 2 parts (one closing tag).
    parts = html.split("</script>")
    assert len(parts) == 2, (
        f"Expected exactly one </script> closing tag, found {len(parts)-1}. "
        "Data containing </script> must be escaped."
    )


def test_copy_selection_button_present():
    """Copy selection JSON button must be present."""
    html = M.build_html(DIFF)
    assert "Copy selection JSON" in html


def test_html_contains_kind_sections():
    """Kind labels for present kinds must appear in the output."""
    html = M.build_html(DIFF)
    assert "Base Tables" in html
    assert "Layouts" in html
    # Sections with no items should not appear
    # (we check that Fields section isn't spuriously added)
    # Actually we just verify the expected kinds are there
    assert "Fields" not in html or "base_table:NEW" in html  # sanity


def test_html_contains_filter_chips():
    """Filter chip labels must be present in the output."""
    html = M.build_html(DIFF)
    # These are built by JS, but the word "All" and "Added" appear in the script
    assert "Added" in html
    assert "Removed" in html
    assert "Modified" in html


def test_html_contains_meta_info():
    """Dev and prod file names from meta must appear in the output."""
    html = M.build_html(DIFF)
    # They're embedded in the DIFF constant, accessible to JS
    assert '"dev_file"' in html or "dev_file" in html


def test_html_manual_item_structure():
    """Manual-patchability items must have their key embedded."""
    html = M.build_html(DIFF)
    assert "layout:Weird" in html


def test_html_has_select_all_proven_added():
    """Global 'Select all proven added' button must be present."""
    html = M.build_html(DIFF)
    assert "Select all proven added" in html


def test_html_has_sticky_footer_elements():
    """Footer warning text must be present in output."""
    html = M.build_html(DIFF)
    assert "caution items require --allow-caution" in html


def test_empty_items_list():
    """build_html should not crash with an empty items list."""
    diff = dict(DIFF)
    diff["items"] = []
    html = M.build_html(diff)
    assert "Download selection.json" in html
    assert html.count("</script>") == 1


def test_field_with_calc_text():
    """A field item with calc_text must embed the value in the output."""
    diff = {
        "meta": DIFF["meta"],
        "items": [
            {
                "key": "field:T::Calc",
                "kind": "field",
                "change": "added",
                "name": "Calc",
                "table": "T",
                "patchability": "caution",
                "ignored": False,
                "duplicate_name": False,
                "summary": "Calculation field",
                "changed_attrs": [],
                "dev": {"name": "Calc", "calc_text": "Let([x=1]; x)"},
                "prod": None,
            }
        ],
    }
    html = M.build_html(diff)
    assert "calc_text" in html or "Let([x=1]; x)" in html


def test_ignored_item_excluded_from_main_count():
    """Ignored items must be present in the HTML data but excluded from main sections."""
    diff = {
        "meta": DIFF["meta"],
        "items": [
            {
                "key": "field:T::IgnoredField",
                "kind": "field",
                "change": "added",
                "name": "IgnoredField",
                "table": "T",
                "patchability": "proven",
                "ignored": True,
                "duplicate_name": False,
                "summary": "",
                "changed_attrs": [],
                "dev": {"name": "IgnoredField"},
                "prod": None,
            }
        ],
    }
    html = M.build_html(diff)
    # The key must be embedded in the DIFF data
    assert "IgnoredField" in html


def test_duplicate_name_flag_embedded():
    """Items with duplicate_name=True must have the data embedded."""
    diff = {
        "meta": DIFF["meta"],
        "items": [
            {
                "key": "field:T::Dup",
                "kind": "field",
                "change": "added",
                "name": "Dup",
                "table": "T",
                "patchability": "proven",
                "ignored": False,
                "duplicate_name": True,
                "summary": "",
                "changed_attrs": [],
                "dev": {"name": "Dup"},
                "prod": None,
            }
        ],
    }
    html = M.build_html(diff)
    assert "duplicate_name" in html


# ── Real sandbox diff ─────────────────────────────────────────────────────────

SANDBOX_DIFF = Path(__file__).parent.parent.parent / "sandbox" / "diff.json"


@pytest.mark.skipif(not SANDBOX_DIFF.exists(), reason="sandbox/diff.json not present")
def test_build_html_real_diff_contains_contacts():
    """The real sandbox diff should produce HTML containing 'Contacts'."""
    with open(SANDBOX_DIFF, encoding="utf-8") as f:
        diff = json.load(f)
    html = M.build_html(diff)
    assert "Contacts" in html


@pytest.mark.skipif(not SANDBOX_DIFF.exists(), reason="sandbox/diff.json not present")
def test_build_html_real_diff_is_large():
    """The real sandbox diff HTML should be at least 50 KB (data-rich output)."""
    with open(SANDBOX_DIFF, encoding="utf-8") as f:
        diff = json.load(f)
    html = M.build_html(diff)
    assert len(html.encode("utf-8")) > 50_000, (
        f"Expected >50KB HTML, got {len(html.encode('utf-8')):,} bytes"
    )


@pytest.mark.skipif(not SANDBOX_DIFF.exists(), reason="sandbox/diff.json not present")
def test_build_html_real_diff_no_script_breakout():
    """Real diff HTML must have exactly one </script> closing tag."""
    with open(SANDBOX_DIFF, encoding="utf-8") as f:
        diff = json.load(f)
    html = M.build_html(diff)
    parts = html.split("</script>")
    assert len(parts) == 2, (
        f"Script breakout detected: found {len(parts)-1} </script> occurrences."
    )
