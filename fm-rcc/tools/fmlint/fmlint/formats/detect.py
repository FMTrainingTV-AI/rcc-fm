"""Auto-detect whether content is fmxmlsnippet XML or human-readable script."""


def detect_format(content: str) -> str:
    """Return 'xml' or 'hr' based on content heuristics."""
    stripped = content.lstrip()
    if stripped.startswith("<?xml") or stripped.startswith("<fmxmlsnippet"):
        return "xml"
    return "hr"
