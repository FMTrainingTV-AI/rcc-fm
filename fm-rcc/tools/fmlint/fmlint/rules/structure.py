"""Structure rules S001–S011 for FMLint.

These are tier-1 (offline) rules that validate the structural integrity
of fmxmlsnippet XML and human-readable FileMaker scripts.
"""

from ..engine import rule, LintRule
from ..types import Diagnostic, Severity


# ---------------------------------------------------------------------------
# S001 — well-formed-xml
# ---------------------------------------------------------------------------

@rule
class WellFormedXml(LintRule):
    """Check that the XML content is well-formed and parseable."""

    rule_id = "S001"
    name = "well-formed-xml"
    category = "structure"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.parse_error:
            sev = self.severity(config)
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"Malformed XML: {parse_result.parse_error}",
                line=0,
            )]
        return []


# ---------------------------------------------------------------------------
# S002 — correct-root
# ---------------------------------------------------------------------------

@rule
class CorrectRoot(LintRule):
    """Check root element is <fmxmlsnippet type="FMObjectList">."""

    rule_id = "S002"
    name = "correct-root"
    category = "structure"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []

        sev = self.severity(config)
        diags = []
        root = parse_result.root

        if root.tag != "fmxmlsnippet":
            diags.append(Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"Root element must be <fmxmlsnippet>, found <{root.tag}>",
                line=0,
            ))

        obj_type = root.get("type")
        if obj_type != "FMObjectList":
            diags.append(Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f'Root type attribute must be "FMObjectList", found "{obj_type}"',
                line=0,
            ))

        return diags


# ---------------------------------------------------------------------------
# S003 — no-script-wrapper
# ---------------------------------------------------------------------------

@rule
class NoScriptWrapper(LintRule):
    """Check that steps are not wrapped in <Script> elements."""

    rule_id = "S003"
    name = "no-script-wrapper"
    category = "structure"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.root is None:
            return []

        sev = self.severity(config)
        diags = []
        for script_el in parse_result.root.iter("Script"):
            # Script references inside Perform Script steps have no Step
            # children — those are fine.  Only flag <Script> elements that
            # have a name attribute AND contain <Step> children.
            if script_el.get("name") and script_el.find("Step") is not None:
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        f'Steps wrapped in <Script name="{script_el.get("name")}">. '
                        "Output steps only — do not wrap in <Script> tags."
                    ),
                    line=0,
                ))
        return diags


# ---------------------------------------------------------------------------
# S004 — step-attributes
# ---------------------------------------------------------------------------

@rule
class StepAttributes(LintRule):
    """Every <Step> must have enable, id, and name attributes."""

    rule_id = "S004"
    name = "step-attributes"
    category = "structure"
    default_severity = Severity.ERROR
    formats = {"xml"}
    tier = 1

    _REQUIRED = ("enable", "id", "name")

    def check_xml(self, parse_result, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            missing = [a for a in self._REQUIRED if step.get(a) is None]
            if missing:
                step_desc = step.get("name") or f"(step #{idx + 1})"
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        f'Step "{step_desc}" missing required attribute(s): '
                        f'{", ".join(missing)}'
                    ),
                    line=idx + 1,
                ))
        return diags


# ---------------------------------------------------------------------------
# S005 / S006 / S007 — paired-blocks, else-ordering, inner-step-context
#
# These three rules share a single stack-based algorithm.  Each diagnostic
# is tagged with the appropriate rule_id:
#   S005 — unmatched openers / closers
#   S006 — Else ordering violations
#   S007 — inner steps outside their required block
# ---------------------------------------------------------------------------

PAIRED_STEPS = {
    "If": {"closer": "End If"},
    "Loop": {"closer": "End Loop"},
    "Open Transaction": {"closer": "Commit Transaction"},
}
CLOSER_TO_OPENER = {v["closer"]: k for k, v in PAIRED_STEPS.items()}
BLOCK_INNER_STEPS = {
    "Else If": "If",
    "Else": "If",
    "Exit Loop If": "Loop",
    "Revert Transaction": "Open Transaction",
}


def _check_block_pairing(steps_iter, sev_s005, sev_s006, sev_s007):
    """Shared stack-based block validation.

    *steps_iter* yields ``(name, line)`` tuples for each step.
    *sev_s005*, *sev_s006*, *sev_s007* are the configured severities for
    each rule.

    Returns a list of Diagnostic objects tagged S005 / S006 / S007.
    """
    diags = []

    # Stack entries: {"opener": str, "line": int, "has_else": bool}
    stack = []

    for name, line in steps_iter:
        # --- Opener ---
        if name in PAIRED_STEPS:
            stack.append({"opener": name, "line": line, "has_else": False})
            continue

        # --- Closer ---
        if name in CLOSER_TO_OPENER:
            expected_opener = CLOSER_TO_OPENER[name]
            if not stack:
                diags.append(Diagnostic(
                    rule_id="S005",
                    severity=sev_s005,
                    message=f'"{name}" without matching "{expected_opener}"',
                    line=line,
                ))
                continue

            top = stack[-1]
            if top["opener"] != expected_opener:
                diags.append(Diagnostic(
                    rule_id="S005",
                    severity=sev_s005,
                    message=(
                        f'"{name}" found but innermost open block is '
                        f'"{top["opener"]}" (opened at line {top["line"]})'
                    ),
                    line=line,
                ))
                # Pop anyway to try to recover alignment
                stack.pop()
            else:
                stack.pop()
            continue

        # --- Inner steps (Else, Else If, Exit Loop If, Revert Transaction) ---
        if name in BLOCK_INNER_STEPS:
            required_opener = BLOCK_INNER_STEPS[name]

            # Find the nearest enclosing block of the required type
            enclosing = None
            for entry in reversed(stack):
                if entry["opener"] == required_opener:
                    enclosing = entry
                    break

            if enclosing is None:
                diags.append(Diagnostic(
                    rule_id="S007",
                    severity=sev_s007,
                    message=f'"{name}" outside of "{required_opener}" block',
                    line=line,
                ))
                continue

            # Else-ordering checks (S006) — only for If-block inner steps
            if name == "Else":
                if enclosing["has_else"]:
                    diags.append(Diagnostic(
                        rule_id="S006",
                        severity=sev_s006,
                        message='Duplicate "Else" in the same If block',
                        line=line,
                    ))
                else:
                    enclosing["has_else"] = True

            elif name == "Else If":
                if enclosing["has_else"]:
                    diags.append(Diagnostic(
                        rule_id="S006",
                        severity=sev_s006,
                        message='"Else If" after "Else" — Else must be the last branch',
                        line=line,
                    ))

    # --- Unclosed blocks ---
    for entry in stack:
        expected_closer = PAIRED_STEPS[entry["opener"]]["closer"]
        diags.append(Diagnostic(
            rule_id="S005",
            severity=sev_s005,
            message=(
                f'"{entry["opener"]}" opened at line {entry["line"]} '
                f'has no matching "{expected_closer}"'
            ),
            line=entry["line"],
        ))

    return diags


@rule
class PairedBlocks(LintRule):
    """Validate block pairing (S005), Else ordering (S006), and inner-step context (S007)."""

    rule_id = "S005"
    name = "paired-blocks"
    category = "structure"
    default_severity = Severity.ERROR
    formats = {"xml", "hr"}
    tier = 1

    def _get_severities(self, config):
        """Look up configured severity for each of the three sub-rules."""
        sev_s005 = config.get_severity("S005", Severity.ERROR)
        sev_s006 = config.get_severity("S006", Severity.ERROR)
        sev_s007 = config.get_severity("S007", Severity.ERROR)
        return sev_s005, sev_s006, sev_s007

    def check_xml(self, parse_result, catalog, context, config):
        sev_s005, sev_s006, sev_s007 = self._get_severities(config)

        def xml_steps():
            for idx, step in enumerate(parse_result.steps):
                name = step.get("name", "")
                if name:
                    yield (name, idx + 1)

        return _check_block_pairing(xml_steps(), sev_s005, sev_s006, sev_s007)

    def check_hr(self, lines, catalog, context, config):
        sev_s005, sev_s006, sev_s007 = self._get_severities(config)

        def hr_steps():
            for ln in lines:
                if ln.is_comment or not ln.step_name:
                    continue
                yield (ln.step_name, ln.line_number)

        return _check_block_pairing(hr_steps(), sev_s005, sev_s006, sev_s007)


# ---------------------------------------------------------------------------
# S008 — known-step-name
# ---------------------------------------------------------------------------

@rule
class KnownStepName(LintRule):
    """Warn when a step name is not found in the catalog."""

    rule_id = "S008"
    name = "known-step-name"
    category = "structure"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")
            if not name or name == "# (comment)":
                continue
            if not catalog.has_step(name):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=f'Unknown step name: "{name}"',
                    line=idx + 1,
                ))
        return diags

    def check_hr(self, lines, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for ln in lines:
            if ln.is_comment or not ln.step_name:
                continue
            name = ln.step_name
            if name == "# (comment)":
                continue
            # All FM step names start with an uppercase letter.  Lines that
            # survive multiline merge but begin with lowercase are text
            # fragments (embedded JS/CSS/HTML), not real steps — skip them
            # to avoid false positives.  Matches the TypeScript linter's
            # filtering behaviour.
            if not name[0].isupper():
                continue
            if not catalog.has_step(name):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=f'Unknown step name: "{name}"',
                    line=ln.line_number,
                ))
        return diags


# ---------------------------------------------------------------------------
# S009 — self-closing-match
# ---------------------------------------------------------------------------

@rule
class SelfClosingMatch(LintRule):
    """Warn when XML self-closing form does not match catalog expectation."""

    rule_id = "S009"
    name = "self-closing-match"
    category = "structure"
    default_severity = Severity.WARNING
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        sev = self.severity(config)
        diags = []
        for idx, step in enumerate(parse_result.steps):
            name = step.get("name", "")
            if not name:
                continue
            expected = catalog.is_self_closing(name)
            if expected is None:
                continue  # Step not in catalog — S008 handles that

            has_children = len(step) > 0  # child elements
            has_text = step.text and step.text.strip()

            if expected and (has_children or has_text):
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        f'Step "{name}" should be self-closing according to '
                        f"the catalog, but has child elements"
                    ),
                    line=idx + 1,
                ))
            elif not expected and not has_children and not has_text:
                # The catalog says it should have children but has none.
                # This is only a warning — some steps can legitimately have
                # all-optional params resulting in no children (e.g. a
                # comment step with no text).  Skip # (comment) since that
                # is explicitly allowed to be self-closing (blank line).
                if name in ("# (comment)", "Else", "End If", "End Loop",
                            "Commit Transaction", "Revert Transaction"):
                    continue
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        f'Step "{name}" should have child elements according '
                        f"to the catalog, but is empty/self-closing"
                    ),
                    line=idx + 1,
                ))
        return diags


# ---------------------------------------------------------------------------
# S010 — empty-script
# ---------------------------------------------------------------------------

@rule
class EmptyScript(LintRule):
    """Info when script has no steps at all."""

    rule_id = "S010"
    name = "empty-script"
    category = "structure"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if parse_result.ok and len(parse_result.steps) == 0:
            sev = self.severity(config)
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message="Script contains no steps",
                line=0,
            )]
        return []

    def check_hr(self, lines, catalog, context, config):
        for ln in lines:
            if ln.step_name:
                return []
        sev = self.severity(config)
        return [Diagnostic(
            rule_id=self.rule_id,
            severity=sev,
            message="Script contains no steps",
            line=0,
        )]


# ---------------------------------------------------------------------------
# S011 — xml-comments
# ---------------------------------------------------------------------------

@rule
class XmlComments(LintRule):
    """Warn about XML comments which FileMaker silently discards."""

    rule_id = "S011"
    name = "xml-comments"
    category = "structure"
    default_severity = Severity.WARNING
    formats = {"xml"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        raw = parse_result.raw_content
        if not raw:
            return []

        sev = self.severity(config)
        diags = []
        # Scan raw content for XML comments; report each occurrence
        start = 0
        first_found = False
        while True:
            pos = raw.find("<!--", start)
            if pos < 0:
                break
            # Calculate line number (1-based)
            line_num = raw.count("\n", 0, pos) + 1
            if not first_found:
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message=(
                        "XML comments (<!-- -->) are silently discarded by "
                        "FileMaker. Use # (comment) steps or disabled Insert "
                        "Text steps instead."
                    ),
                    line=line_num,
                ))
                first_found = True
            else:
                diags.append(Diagnostic(
                    rule_id=self.rule_id,
                    severity=sev,
                    message="Additional XML comment found",
                    line=line_num,
                ))
            # Skip past this comment to find the next
            end_pos = raw.find("-->", pos + 4)
            if end_pos < 0:
                break
            start = end_pos + 3

        return diags
