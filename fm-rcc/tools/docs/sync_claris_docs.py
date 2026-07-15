#!/usr/bin/env python3
"""Mirror Claris's Markdown help corpus into a local docs cache.

Claris publishes its help site as agent-friendly Markdown following the
llms.txt convention (see skills/fm-docs/references/claris-markdown-docs-reference.md).
This tool pulls selected docsets into ~/.fm-rcc/docs-cache/ so lookups are
local-first and work offline. The corpus is fetched per-install, not
redistributed with the plugin.

Usage:
    python3 sync_claris_docs.py                        # default docsets
    python3 sync_claris_docs.py --docsets pro-help --limit 25   # smoke run
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

INDEX_URL = "https://help.claris.com/llms-full.txt"
DEFAULT_DOCSETS = "pro-help,data-api-guide,odata-guide,app-upgrade-tool-guide,sql-reference"
DEFAULT_DEST = Path.home() / ".fm-rcc" / "docs-cache"
POLITE_SLEEP_S = 0.2


def extract_urls(index_text: str, docsets: list[str], locale: str = "en") -> list[str]:
    """Return sorted, de-duplicated Markdown page URLs for the given docsets."""
    urls: set[str] = set()
    for docset in docsets:
        pattern = re.compile(
            r"https://help\.claris\.com/markdown/%s/%s/[A-Za-z0-9._-]+\.md"
            % (re.escape(locale), re.escape(docset))
        )
        urls.update(pattern.findall(index_text))
    return sorted(urls)


def is_valid_page(text: str) -> bool:
    """Real pages start with YAML frontmatter; 404 redirects serve HTML."""
    return text.startswith("---")


def sync(docsets: list[str], dest: Path, locale: str, limit: int | None) -> dict:
    import requests

    index_text = requests.get(INDEX_URL, timeout=30).text
    urls = extract_urls(index_text, docsets, locale=locale)
    if limit:
        urls = urls[:limit]

    counts = {"fetched": 0, "skipped_invalid": 0, "total": len(urls)}
    for url in urls:
        docset = url.split(f"/markdown/{locale}/", 1)[1].split("/", 1)[0]
        out = dest / docset / url.rsplit("/", 1)[1]
        out.parent.mkdir(parents=True, exist_ok=True)
        body = requests.get(url, timeout=30, allow_redirects=True).text
        if not is_valid_page(body):
            counts["skipped_invalid"] += 1
            continue
        out.write_text(body, encoding="utf-8")
        counts["fetched"] += 1
        time.sleep(POLITE_SLEEP_S)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--docsets", default=DEFAULT_DOCSETS,
                    help=f"comma-separated docset slugs (default: {DEFAULT_DOCSETS})")
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST,
                    help=f"cache directory (default: {DEFAULT_DEST})")
    ap.add_argument("--locale", default="en")
    ap.add_argument("--limit", type=int, default=None,
                    help="max pages to fetch (smoke runs)")
    args = ap.parse_args(argv)

    docsets = [d.strip() for d in args.docsets.split(",") if d.strip()]
    counts = sync(docsets, args.dest, args.locale, args.limit)
    print(f"docs-cache: {counts['fetched']} fetched, "
          f"{counts['skipped_invalid']} invalid-skipped, "
          f"{counts['total']} indexed → {args.dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
