"""Human-readable script parser for FMLint.

Parses HR format lines like:
  # comment text
  // Disabled Step [ params ]
  Set Variable [ $name ; expression ]
  If [ condition ]
"""

from ..types import ParsedHRLine


def parse_hr(text: str) -> list:
    """Parse HR script text into a list of ParsedHRLine objects."""
    raw_lines = text.split("\n")
    merged = _merge_multiline(raw_lines)
    return [_parse_line(m_text, m_line) for m_text, m_line in merged]


def _merge_multiline(lines: list) -> list:
    """Merge continuation lines when brackets span multiple lines."""
    result = []
    accumulator = ""
    start_line = 1
    bracket_depth = 0
    in_quote = False

    for i, line in enumerate(lines):
        trimmed = line.strip()

        if bracket_depth == 0 and (trimmed.startswith("#") or trimmed == ""):
            result.append((line, i + 1))
            continue

        if bracket_depth == 0:
            accumulator = line
            start_line = i + 1
        else:
            accumulator += "\n" + line

        for ch in line:
            if ch == '"':
                in_quote = not in_quote
                continue
            if in_quote:
                continue
            if ch == "[":
                bracket_depth += 1
            elif ch == "]":
                bracket_depth -= 1

        if bracket_depth <= 0:
            result.append((accumulator, start_line))
            accumulator = ""
            bracket_depth = 0
            in_quote = False

    if accumulator:
        result.append((accumulator, start_line))

    return result


def _parse_line(raw: str, line_number: int) -> ParsedHRLine:
    """Parse a single HR script line."""
    trimmed = raw.lstrip()
    indent = len(raw) - len(trimmed)

    # Empty line
    if not trimmed:
        return ParsedHRLine(raw=raw, line_number=line_number, indent=indent)

    # Comment: # ...
    if trimmed.startswith("#"):
        comment_text = trimmed[1:].strip()
        return ParsedHRLine(
            raw=raw, line_number=line_number, is_comment=True,
            comment_text=comment_text, step_name="# (comment)", indent=indent,
        )

    # Disabled step: // ...
    disabled = False
    work_text = trimmed
    if trimmed.startswith("//"):
        disabled = True
        work_text = trimmed[2:].strip()

    # Extract step name and bracket content
    bracket_idx = _find_top_level_bracket(work_text)

    if bracket_idx >= 0:
        step_name = work_text[:bracket_idx].strip()
        close_bracket = _find_matching_bracket(work_text, bracket_idx)
        if close_bracket >= 0:
            bracket_content = work_text[bracket_idx + 1:close_bracket].strip()
        else:
            bracket_content = work_text[bracket_idx + 1:].strip()
        params = _split_params(bracket_content)
    else:
        step_name = work_text.strip()
        bracket_content = ""
        params = []

    return ParsedHRLine(
        raw=raw, line_number=line_number, disabled=disabled,
        step_name=step_name, bracket_content=bracket_content,
        params=params, indent=indent,
    )


def _find_top_level_bracket(text: str) -> int:
    """Find the first top-level '[' not inside quotes."""
    in_quote = False
    for i, ch in enumerate(text):
        if ch == '"':
            in_quote = not in_quote
        if not in_quote and ch == "[":
            return i
    return -1


def _find_matching_bracket(text: str, open_idx: int) -> int:
    """Find the matching ']' for an opening '['."""
    depth = 0
    in_quote = False
    for i in range(open_idx, len(text)):
        ch = text[i]
        if ch == '"':
            in_quote = not in_quote
        if in_quote:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_params(content: str) -> list:
    """Split bracket content by semicolons, respecting quotes and nesting."""
    params = []
    current = ""
    in_quote = False
    paren_depth = 0
    bracket_depth = 0

    for ch in content:
        if ch == '"':
            in_quote = not in_quote
            current += ch
            continue

        if in_quote:
            current += ch
            continue

        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth -= 1
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth -= 1

        if ch == ";" and paren_depth == 0 and bracket_depth == 0:
            params.append(current.strip())
            current = ""
            continue

        current += ch

    if current.strip():
        params.append(current.strip())

    return params


def extract_calculation_from_params(params: list) -> str:
    """Extract the calculation expression from HR step parameters.

    For most steps, the calculation is the last parameter.
    For Set Variable, it's the second parameter (Value).
    For Set Field, it's the second parameter.
    """
    if len(params) >= 2:
        return params[-1].strip()
    if len(params) == 1:
        return params[0].strip()
    return ""
