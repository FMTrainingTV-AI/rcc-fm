import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "docs"))

from sync_claris_docs import extract_urls, is_valid_page


def test_extract_urls_filters_by_docset_and_locale():
    idx = (
        "https://help.claris.com/markdown/en/pro-help/foo.md\n"
        "https://help.claris.com/markdown/en/odata-guide/bar.md\n"
        "https://help.claris.com/markdown/ja/pro-help/baz.md\n"
        "https://help.claris.com/en/pro-help/content/foo.html\n"
    )
    assert extract_urls(idx, ["pro-help"], locale="en") == [
        "https://help.claris.com/markdown/en/pro-help/foo.md"
    ]


def test_extract_urls_dedupes_and_sorts():
    idx = (
        "https://help.claris.com/markdown/en/pro-help/zeta.md\n"
        "https://help.claris.com/markdown/en/pro-help/alpha.md\n"
        "https://help.claris.com/markdown/en/pro-help/zeta.md\n"
    )
    assert extract_urls(idx, ["pro-help"], locale="en") == [
        "https://help.claris.com/markdown/en/pro-help/alpha.md",
        "https://help.claris.com/markdown/en/pro-help/zeta.md",
    ]


def test_is_valid_page_requires_frontmatter():
    assert is_valid_page("---\ntitle: x\n---\nbody")
    assert not is_valid_page("<!DOCTYPE html><html>404</html>")
    assert not is_valid_page("")
