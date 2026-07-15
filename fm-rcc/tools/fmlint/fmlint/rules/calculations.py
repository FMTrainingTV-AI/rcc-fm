"""Calculation rules C001–C003, C006 for FMLint.

These are tier-1 (offline) rules that check calculation expressions for
common syntax issues: unclosed strings, unbalanced parentheses, unknown
function names, and HTML/XML entities where literal operators belong.
"""

import re

from ..engine import rule, LintRule
from ..types import Diagnostic, Severity


_STRIP_STRINGS_RE = re.compile(r'"[^"]*"')

# Steps where bracket content is literal text, not a FM calculation.
# These must be skipped by rules that analyze calculation expressions.
NON_CALC_STEPS = {
    "Insert Text", "Insert File", "Insert Picture", "Insert Audio/Video",
    "Insert PDF", "Insert From URL", "Insert From Device",
    "Show Custom Dialog", "Send Mail", "Send Event",
    "Set Web Viewer", "Export Field Contents",
    "Open URL", "Open File", "Dial Phone",
}


def _strip_strings(text):
    return _STRIP_STRINGS_RE.sub('""', text)


def _is_calc_step(ln):
    """Return True if the HR line's bracket content should be treated as a calculation."""
    return ln.step_name not in NON_CALC_STEPS


# ---------------------------------------------------------------------------
# C001 — unclosed-string
# ---------------------------------------------------------------------------

@rule
class UnclosedString(LintRule):
    """Detect unclosed string literals in calculations."""

    rule_id = "C001"
    name = "unclosed-string"
    category = "calculations"
    default_severity = Severity.ERROR
    formats = {"xml", "hr"}
    tier = 1

    def _has_unclosed(self, text):
        count = 0
        for ch in text:
            if ch == '"':
                count += 1
        return count % 2 != 0

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []

        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if calc.text and self._has_unclosed(calc.text):
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message="Unclosed string literal in calculation",
                        line=idx + 1,
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for ln in lines:
            if ln.is_comment or not ln.bracket_content or not _is_calc_step(ln):
                continue
            if self._has_unclosed(ln.bracket_content):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message="Unclosed string literal in calculation",
                    line=ln.line_number,
                ))
        return diags


# ---------------------------------------------------------------------------
# C002 — unbalanced-parens
# ---------------------------------------------------------------------------

@rule
class UnbalancedParens(LintRule):
    """Detect unbalanced parentheses in calculations."""

    rule_id = "C002"
    name = "unbalanced-parens"
    category = "calculations"
    default_severity = Severity.ERROR
    formats = {"xml", "hr"}
    tier = 1

    def _check_parens(self, text):
        stripped = _strip_strings(text)
        depth = 0
        for ch in stripped:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth < 0:
                return "Extra closing parenthesis ')' in calculation"
        if depth > 0:
            return f"Unclosed parenthesis in calculation ({depth} unclosed)"
        return None

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []

        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                msg = self._check_parens(calc.text)
                if msg:
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message=msg,
                        line=idx + 1,
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for ln in lines:
            if ln.is_comment or not ln.bracket_content or not _is_calc_step(ln):
                continue
            msg = self._check_parens(ln.bracket_content)
            if msg:
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=msg,
                    line=ln.line_number,
                ))
        return diags


# ---------------------------------------------------------------------------
# C003 — known-function
# ---------------------------------------------------------------------------

@rule
class KnownFunction(LintRule):
    """Check that function names in calculations are recognized FileMaker functions.

    This is a best-effort check — it extracts likely function calls (word followed
    by opening paren) and warns on unrecognized names. It uses the FM function
    docs directory if available, otherwise falls back to a built-in set of
    common functions.
    """

    rule_id = "C003"
    name = "known-function"
    category = "calculations"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 1

    # Common FileMaker functions (subset for offline validation)
    _KNOWN_FUNCTIONS = {
        # Logical
        "if", "case", "choose", "let", "while", "evaluate",
        "getasboolean", "isempty", "isvalid",
        # Text
        "left", "right", "middle", "length", "position", "substitute",
        "trim", "trimleft", "trimright", "trimall",
        "upper", "lower", "proper", "exact",
        "char", "code", "filter", "filtervalues",
        "getvalue", "valuecount", "leftvalues", "rightvalues", "middlevalues",
        "patterncount", "replace", "quote", "textcolor", "textfont",
        "textformatremove", "textsize", "textstyleadd", "textstyleremove",
        "wordcount", "leftwords", "rightwords", "middlewords",
        # Number
        "abs", "ceiling", "div", "exp", "floor", "int", "lg", "ln", "log",
        "mod", "random", "round", "setprecision", "sign", "sqrt", "truncate",
        # Date / Time / Timestamp
        "date", "day", "dayname", "dayofweek", "dayofyear",
        "hour", "minute", "month", "monthname", "seconds", "time",
        "timestamp", "weekofyear", "weekofyearfiscal", "year",
        # Get functions
        "get",
        # Aggregate
        "average", "count", "list", "max", "min", "sum",
        # JSON
        "jsonsetelement", "jsongetelement", "jsonlistkeys", "jsonlistvalues",
        "jsonformatelements", "jsondeleteelement", "jsongetelementtype",
        "jsonmakearray", "jsonparseelements", "jsongetarrayelement",
        # MBS (common plugin)
        "mbs",
        # Container
        "base64decode", "base64encode", "getcontainerattribute",
        "getthumbnail", "verifycontainer",
        # Design
        "databasenames", "fieldnames", "fieldtype", "layoutnames",
        "layoutobjectnames", "relationinfo", "scriptnames", "tablenames",
        "tableids", "fieldids", "layoutids", "scriptids",
        "valuelistnames", "valuelistitems", "valuelistids",
        # Other common
        "executesql", "getfield", "getfieldname", "getnthrecord",
        "getrepetition", "setrecursion", "self",
        "getasdate", "getasnumber", "getastext", "getastimestamp", "getastime",
        "textcolorremove", "sortvalues", "uniquevalues",
    }

    # Regex to find function-call-like patterns: word followed by (
    _FUNC_CALL_RE = re.compile(r'\b([A-Za-z_]\w*)\s*\(')

    # Names to skip (not functions, but look like them)
    _SKIP = {"and", "or", "not", "xor", "true", "false"}

    def _extract_functions(self, text):
        stripped = _strip_strings(text)
        found = set()
        for match in self._FUNC_CALL_RE.finditer(stripped):
            name = match.group(1)
            if name.lower() not in self._SKIP:
                found.add(name)
        return found

    def _get_known_functions(self, config):
        """Return the known functions set, extended with any extra_known_functions from config."""
        rc = self.rule_config(config)
        extra = rc.get("extra_known_functions", [])
        if not extra:
            return self._KNOWN_FUNCTIONS
        # Build an extended set with the extras lowercased
        extended = set(self._KNOWN_FUNCTIONS)
        for fn in extra:
            extended.add(fn.lower())
        return extended

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []

        sev = self.severity(config)
        known = self._get_known_functions(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                for func_name in self._extract_functions(calc.text):
                    if func_name.lower() not in known:
                        diags.append(Diagnostic(
                            rule_id=self.rule_id,
                            severity=sev,
                            message=f'Unknown function "{func_name}" in calculation',
                            line=idx + 1,
                        ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        sev = self.severity(config)
        known = self._get_known_functions(config)
        diags = []
        for ln in lines:
            if ln.is_comment or not ln.bracket_content:
                continue
            for func_name in self._extract_functions(ln.bracket_content):
                if func_name.lower() not in known:
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message=f'Unknown function "{func_name}" in calculation',
                        line=ln.line_number,
                    ))
        return diags


# ---------------------------------------------------------------------------
# C006 — html-entities-in-calc
# ---------------------------------------------------------------------------

# Entities that represent operators and are never valid in FM calculations.
# Maps the entity text to the literal operator the author intended.
_ENTITY_TO_OPERATOR = {
    "&gt;":  ">",
    "&lt;":  "<",
    "&ge;":  ">=",  # HTML entity, not even standard XML
    "&le;":  "<=",  # HTML entity, not even standard XML
    "&amp;": "&",
    "&quot;": '"',
    "&apos;": "'",
    "&ne;":  "<>",  # HTML entity for not-equal
}

# Pre-compile a single pattern that matches any of the entities (case-insensitive).
_ENTITY_RE = re.compile(
    "|".join(re.escape(e) for e in _ENTITY_TO_OPERATOR),
    re.IGNORECASE,
)


@rule
class C006HtmlEntitiesInCalc(LintRule):
    """Detect HTML/XML entities used in place of literal operators in calculations.

    Inside <Calculation><![CDATA[...]]></Calculation> blocks, text is literal —
    entity encoding is not interpreted.  Writing ``&gt;`` instead of ``>``
    produces a broken calculation because FileMaker sees the ampersand and
    semicolon as literal characters, not the operator.

    The same applies to HR bracket content, which represents raw calculation
    text that will eventually be placed inside a CDATA block.
    """

    rule_id = "C006"
    name = "html-entities-in-calc"
    category = "calculations"
    default_severity = Severity.ERROR
    formats = {"xml", "hr"}
    tier = 1

    def _find_entities(self, text):
        """Return list of (entity, replacement) found in *text* outside quoted strings."""
        stripped = _strip_strings(text)
        hits = []
        for m in _ENTITY_RE.finditer(stripped):
            entity = m.group(0).lower()
            replacement = _ENTITY_TO_OPERATOR.get(entity, "")
            hits.append((m.group(0), replacement))
        return hits

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            for calc in step.iter("Calculation"):
                if not calc.text:
                    continue
                for entity, replacement in self._find_entities(calc.text):
                    diags.append(Diagnostic(
                        rule_id=self.rule_id,
                        severity=sev,
                        message=f'HTML entity "{entity}" in calculation — use the literal operator "{replacement}" instead',
                        line=idx + 1,
                        fix_hint=f'Replace "{entity}" with "{replacement}"',
                    ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for ln in lines:
            if ln.is_comment or not ln.bracket_content or not _is_calc_step(ln):
                continue
            for entity, replacement in self._find_entities(ln.bracket_content):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=f'HTML entity "{entity}" in calculation — use the literal operator "{replacement}" instead',
                    line=ln.line_number,
                    fix_hint=f'Replace "{entity}" with "{replacement}"',
                ))
        return diags
