"""Naming and convention rules N001-N007 for FMLint."""

import re
from ..engine import rule, LintRule
from ..types import Diagnostic, Severity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STRIP_STRINGS_RE = re.compile(r'"[^"]*"')
_ASCII_OPERATORS = [
    ("<>", "\u2260", 'Use "\u2260" instead of "<>"'),
    ("<=", "\u2264", 'Use "\u2264" instead of "<="'),
    (">=", "\u2265", 'Use "\u2265" instead of ">="'),
]

# Regex that matches ;<non-whitespace> (missing space after semicolon)
_SEMI_NO_SPACE_RE = re.compile(r';[^\s]')

# Alignment padding: 3+ consecutive spaces within a line (not leading)
_ALIGNMENT_PAD_RE = re.compile(r'\S {3,}\S')

# Variable naming patterns
# Optional trailing [N] for FileMaker repetition variables (e.g. $var[1])
_REP_SUFFIX = r'(?:\[\d+\])?'

_VAR_PATTERNS = {
    "$$~": (re.compile(r'^\$\$~[A-Z][A-Z0-9._]*' + _REP_SUFFIX + r'$'), "$$~ALL_CAPS"),
    "$$": (re.compile(r'^\$\$[A-Z][A-Z0-9._]*' + _REP_SUFFIX + r'$'), "$$ALL_CAPS"),
    "~": (re.compile(r'^~[a-z][a-zA-Z0-9]*' + _REP_SUFFIX + r'$'), "~camelCase"),
    "$": (re.compile(r'^\$[a-z][a-zA-Z0-9]*' + _REP_SUFFIX + r'$'), "$camelCase"),
}

# Ordered prefixes for classification (longest first)
_VAR_PREFIX_ORDER = ["$$~", "$$", "~", "$"]

_BOOLEAN_PREFIXES = (
    "is", "has", "can", "should", "will", "did", "was", "needs", "allows",
)


def _strip_strings(text):
    """Remove quoted strings from text to avoid false positives."""
    return _STRIP_STRINGS_RE.sub('""', text)


def _get_calc_texts_from_steps(steps):
    """Yield (step_index, calc_text) for all Calculation CDATA in steps."""
    for i, step in enumerate(steps):
        for calc in step.iter("Calculation"):
            if calc.text:
                yield i, calc.text


def _var_name_from_step(step):
    """Extract variable name from a Set Variable XML step."""
    name_el = step.find("Name")
    if name_el is not None and name_el.text:
        return name_el.text.strip()
    return None


def _var_calc_from_step(step):
    """Extract the calculation value from a Set Variable XML step."""
    for calc in step.iter("Calculation"):
        if calc.text:
            return calc.text.strip()
    return None


def _build_var_patterns(config_patterns, allow_rep_suffix=True):
    """Build compiled var patterns from config dict.

    config_patterns is a dict like:
        {"$$~": {"regex": "...", "label": "..."}, ...}

    Returns a dict keyed by prefix with (compiled_regex, label) tuples,
    and a list of prefixes in longest-first order.
    """
    patterns = {}
    for prefix in sorted(config_patterns.keys(), key=len, reverse=True):
        entry = config_patterns[prefix]
        regex_str = entry.get("regex", "")
        label = entry.get("label", prefix)
        if allow_rep_suffix and not regex_str.endswith(_REP_SUFFIX + r'$'):
            # Append optional repetition suffix if not already present
            pass  # Trust the config regex as-is
        patterns[prefix] = (re.compile(regex_str), label)
    prefix_order = sorted(patterns.keys(), key=len, reverse=True)
    return patterns, prefix_order


def _classify_var(name, patterns=None, prefix_order=None):
    """Classify a variable name and return (prefix, pattern_obj, convention_str) or None."""
    if patterns is None:
        patterns = _VAR_PATTERNS
    if prefix_order is None:
        prefix_order = _VAR_PREFIX_ORDER
    for prefix in prefix_order:
        if name.startswith(prefix):
            pat, label = patterns[prefix]
            return prefix, pat, label
    return None


def _strip_var_prefix(name):
    """Strip the sigil prefix and optional [N] suffix from a variable name."""
    # Strip repetition suffix first
    stripped = re.sub(r'\[\d+\]$', '', name)
    if stripped.startswith("$$~"):
        return stripped[3:]
    elif stripped.startswith("$$"):
        return stripped[2:]
    elif stripped.startswith("~"):
        return stripped[1:]
    elif stripped.startswith("$"):
        return stripped[1:]
    return stripped


def _has_boolean_prefix(var_name, prefixes=None):
    """Check if the bare variable name (after sigil) starts with a boolean prefix."""
    if prefixes is None:
        prefixes = _BOOLEAN_PREFIXES
    bare = _strip_var_prefix(var_name).lower()
    for prefix in prefixes:
        if bare.startswith(prefix):
            return True
    return False


def _count_let_semicolons(text):
    """Count semicolons inside a Let() call (rough heuristic)."""
    # Find Let( and count semicolons in its body
    stripped = _strip_strings(text)
    count = 0
    depth = 0
    in_let = False
    i = 0
    while i < len(stripped):
        if stripped[i:i+4].lower() == "let(" or stripped[i:i+3].lower() == "let":
            # Look ahead for the opening paren
            j = i + 3
            while j < len(stripped) and stripped[j] in " \t":
                j += 1
            if j < len(stripped) and stripped[j] == "(":
                in_let = True
                depth = 1
                i = j + 1
                continue
        if in_let:
            if stripped[i] == "(":
                depth += 1
            elif stripped[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            elif stripped[i] == ";" and depth == 1:
                count += 1
        i += 1
    return count


# ---------------------------------------------------------------------------
# N001 — unicode-operators
# ---------------------------------------------------------------------------

@rule
class N001UnicodeOperators(LintRule):
    rule_id = "N001"
    name = "unicode-operators"
    category = "naming"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        for i, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                stripped = _strip_strings(calc.text)
                for ascii_op, unicode_op, hint in _ASCII_OPERATORS:
                    if ascii_op in stripped:
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=f'ASCII operator "{ascii_op}" found in calculation; use "{unicode_op}" instead',
                            line=i + 1,
                            fix_hint=hint,
                        ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        for line in lines:
            if line.is_comment or not line.bracket_content:
                continue
            stripped = _strip_strings(line.bracket_content)
            for ascii_op, unicode_op, hint in _ASCII_OPERATORS:
                if ascii_op in stripped:
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message=f'ASCII operator "{ascii_op}" found in calculation; use "{unicode_op}" instead',
                        line=line.line_number,
                        fix_hint=hint,
                    ))
        return diags


# ---------------------------------------------------------------------------
# N002 — variable-naming
# ---------------------------------------------------------------------------

@rule
class N002VariableNaming(LintRule):
    rule_id = "N002"
    name = "variable-naming"
    category = "naming"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 1

    _MSG = 'Variable "{}" does not match naming conventions ($camelCase, $$ALL_CAPS, ~camelCase, $$~ALL_CAPS)'

    def _get_patterns(self, config):
        """Return (patterns_dict, prefix_order, allow_rep_suffix) from config or defaults."""
        rc = self.rule_config(config)
        allow_rep = rc.get("allow_repetition_suffix", True)
        config_patterns = rc.get("patterns")
        if config_patterns:
            patterns, prefix_order = _build_var_patterns(config_patterns, allow_rep)
            return patterns, prefix_order, allow_rep
        return _VAR_PATTERNS, _VAR_PREFIX_ORDER, allow_rep

    def _check_var(self, var_name, patterns, prefix_order, allow_rep):
        """Check a variable name against patterns. Return True if it violates naming."""
        # Optionally strip repetition suffix before matching
        name_to_check = var_name
        if allow_rep:
            name_to_check = re.sub(r'\[\d+\]$', '', var_name)
        info = _classify_var(name_to_check, patterns, prefix_order)
        if info is None:
            return False
        _prefix, pattern, _convention = info
        return not pattern.match(name_to_check)

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        patterns, prefix_order, allow_rep = self._get_patterns(config)
        for i, step in enumerate(parse_result.steps):
            if step.get("name") != "Set Variable":
                continue
            var_name = _var_name_from_step(step)
            if not var_name:
                continue
            if self._check_var(var_name, patterns, prefix_order, allow_rep):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=self._MSG.format(var_name),
                    line=i + 1,
                ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        patterns, prefix_order, allow_rep = self._get_patterns(config)
        for line in lines:
            if line.is_comment or line.step_name != "Set Variable":
                continue
            if not line.params:
                continue
            # First param is the variable name (e.g. "$varName")
            var_name = line.params[0].strip()
            if not var_name:
                continue
            if self._check_var(var_name, patterns, prefix_order, allow_rep):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=self._MSG.format(var_name),
                    line=line.line_number,
                ))
        return diags


# ---------------------------------------------------------------------------
# N003 — boolean-var-naming
# ---------------------------------------------------------------------------

@rule
class N003BooleanVarNaming(LintRule):
    rule_id = "N003"
    name = "boolean-var-naming"
    category = "naming"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    _MSG = 'Boolean variable "{}" could use a descriptive prefix (is, has, can, should, etc.)'

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        rc = self.rule_config(config)
        prefixes = rc.get("boolean_prefixes", _BOOLEAN_PREFIXES)
        for i, step in enumerate(parse_result.steps):
            if step.get("name") != "Set Variable":
                continue
            var_name = _var_name_from_step(step)
            calc_text = _var_calc_from_step(step)
            if not var_name or not calc_text:
                continue
            if calc_text not in ("True", "False"):
                continue
            if _has_boolean_prefix(var_name, prefixes):
                continue
            diags.append(Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=self._MSG.format(var_name),
                line=i + 1,
            ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        rc = self.rule_config(config)
        prefixes = rc.get("boolean_prefixes", _BOOLEAN_PREFIXES)
        for line in lines:
            if line.is_comment or line.step_name != "Set Variable":
                continue
            if len(line.params) < 2:
                continue
            var_name = line.params[0].strip()
            calc_text = line.params[-1].strip()
            if calc_text not in ("True", "False"):
                continue
            if not var_name:
                continue
            if _has_boolean_prefix(var_name, prefixes):
                continue
            diags.append(Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=self._MSG.format(var_name),
                line=line.line_number,
            ))
        return diags


# ---------------------------------------------------------------------------
# N004 — hard-tabs-in-calcs
# ---------------------------------------------------------------------------

@rule
class N004HardTabsInCalcs(LintRule):
    rule_id = "N004"
    name = "hard-tabs-in-calcs"
    category = "naming"
    default_severity = Severity.WARNING
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        rc = self.rule_config(config)
        indent_char = rc.get("indent_char", "tab")
        if indent_char == "tab":
            # Flag spaces (current default behavior)
            bad_char_check = lambda line: line[0] == " " and len(line) > 1 and line[:2] == "  "
            message = "Calculation uses spaces for indentation; use hard tabs instead"
            fix_hint = "Replace leading spaces with tab characters"
        else:
            # Flag tabs
            bad_char_check = lambda line: line[0] == "\t"
            message = "Calculation uses tabs for indentation; use spaces instead"
            fix_hint = "Replace leading tabs with space characters"
        for i, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                if "\n" not in calc.text:
                    continue
                for calc_line in calc.text.split("\n"):
                    if calc_line and bad_char_check(calc_line):
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=message,
                            line=i + 1,
                            fix_hint=fix_hint,
                        ))
                        break  # One diagnostic per step is enough
        return diags


# ---------------------------------------------------------------------------
# N005 — function-spacing
# ---------------------------------------------------------------------------

@rule
class N005FunctionSpacing(LintRule):
    rule_id = "N005"
    name = "function-spacing"
    category = "naming"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        for i, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                stripped = _strip_strings(calc.text)
                if _SEMI_NO_SPACE_RE.search(stripped):
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message="Missing space after semicolon in function call",
                        line=i + 1,
                        fix_hint="Add a space after each semicolon in function arguments",
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        for line in lines:
            if line.is_comment or not line.bracket_content:
                continue
            stripped = _strip_strings(line.bracket_content)
            if _SEMI_NO_SPACE_RE.search(stripped):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message="Missing space after semicolon in function call",
                    line=line.line_number,
                    fix_hint="Add a space after each semicolon in function arguments",
                ))
        return diags


# ---------------------------------------------------------------------------
# N006 — no-alignment-padding
# ---------------------------------------------------------------------------

@rule
class N006NoAlignmentPadding(LintRule):
    rule_id = "N006"
    name = "no-alignment-padding"
    category = "naming"
    default_severity = Severity.HINT
    formats = {"xml", "hr"}
    tier = 1

    def _get_pad_re(self, config):
        """Build alignment padding regex from config min_spaces."""
        rc = self.rule_config(config)
        min_spaces = rc.get("min_spaces", 3)
        if min_spaces == 3:
            return _ALIGNMENT_PAD_RE
        return re.compile(r'\S {' + str(min_spaces) + r',}\S')

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        pad_re = self._get_pad_re(config)
        for i, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                if "\n" not in calc.text:
                    continue
                stripped = _strip_strings(calc.text)
                if pad_re.search(stripped):
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message="Possible alignment padding detected in calculation; avoid column alignment with extra spaces",
                        line=i + 1,
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        pad_re = self._get_pad_re(config)
        for line in lines:
            if line.is_comment or not line.bracket_content:
                continue
            if "\n" not in line.bracket_content:
                continue
            stripped = _strip_strings(line.bracket_content)
            if pad_re.search(stripped):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message="Possible alignment padding detected in calculation; avoid column alignment with extra spaces",
                    line=line.line_number,
                ))
        return diags


# ---------------------------------------------------------------------------
# N007 — let-formatting
# ---------------------------------------------------------------------------

@rule
class N007LetFormatting(LintRule):
    rule_id = "N007"
    name = "let-formatting"
    category = "naming"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    _LET_CALL_RE = re.compile(r'\bLet\s*\(', re.IGNORECASE)

    def _check_text(self, text, min_variables=2):
        """Return True if a Let() call looks like it needs multi-line formatting."""
        if not self._LET_CALL_RE.search(text):
            return False
        # Check each Let() occurrence
        stripped = _strip_strings(text)
        for match in self._LET_CALL_RE.finditer(stripped):
            start = match.start()
            # Extract the Let() body to check semicolons vs newlines
            paren_start = match.end() - 1  # position of '('
            depth = 1
            i = paren_start + 1
            body = ""
            while i < len(stripped) and depth > 0:
                if stripped[i] == "(":
                    depth += 1
                elif stripped[i] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                body += stripped[i]
                i += 1
            # Count top-level semicolons in the body
            semi_count = 0
            d = 0
            for ch in body:
                if ch == "(":
                    d += 1
                elif ch == ")":
                    d -= 1
                elif ch == ";" and d == 0:
                    semi_count += 1
            # Multiple semicolons means multiple variables — should be multi-line
            if semi_count >= min_variables and "\n" not in body:
                return True
        return False

    def check_xml(self, parse_result, catalog, context, config):
        diags = []
        if not parse_result.ok:
            return diags
        sev = self.severity(config)
        rc = self.rule_config(config)
        min_variables = rc.get("min_variables", 2)
        for i, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                if self._check_text(calc.text, min_variables):
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message="Let() with multiple variables should use multi-line formatting",
                        line=i + 1,
                        fix_hint="Place each variable assignment on its own line within Let()",
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        diags = []
        sev = self.severity(config)
        rc = self.rule_config(config)
        min_variables = rc.get("min_variables", 2)
        for line in lines:
            if line.is_comment or not line.bracket_content:
                continue
            if self._check_text(line.bracket_content, min_variables):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message="Let() with multiple variables should use multi-line formatting",
                    line=line.line_number,
                    fix_hint="Place each variable assignment on its own line within Let()",
                ))
        return diags
