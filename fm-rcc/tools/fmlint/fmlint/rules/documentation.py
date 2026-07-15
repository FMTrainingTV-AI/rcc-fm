"""Documentation rules D001–D003 for FMLint.

These are tier-1 (offline) rules that check for proper script documentation
practices: purpose comments, README blocks, and section separation.
"""

from ..engine import rule, LintRule
from ..types import Diagnostic, Severity


# ---------------------------------------------------------------------------
# D001 — purpose-comment
# ---------------------------------------------------------------------------

@rule
class PurposeComment(LintRule):
    """First step should be a comment containing 'PURPOSE:'."""

    rule_id = "D001"
    name = "purpose-comment"
    category = "documentation"
    default_severity = Severity.WARNING
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok or not parse_result.steps:
            return []

        rc = self.rule_config(config)
        sev = self.severity(config)
        keyword = rc.get("keyword", "PURPOSE:")
        case_sensitive = rc.get("case_sensitive", False)

        first = parse_result.steps[0]
        name = first.get("name", "")
        if name != "# (comment)":
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"First step should be a comment containing '{keyword}'",
                line=1,
                fix_hint=f"Add a # (comment) step at the top with '{keyword} <description>'",
            )]

        text_el = first.find("Text")
        text = text_el.text if text_el is not None and text_el.text else ""
        if case_sensitive:
            found = keyword in text
        else:
            found = keyword.upper() in text.upper()
        if not found:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"First comment should contain '{keyword}' to describe the script's intent",
                line=1,
                fix_hint=f"Add '{keyword} <description>' to the first comment",
            )]

        return []

    def check_hr(self, lines, catalog, context, config):
        rc = self.rule_config(config)
        sev = self.severity(config)
        keyword = rc.get("keyword", "PURPOSE:")
        case_sensitive = rc.get("case_sensitive", False)

        # Find the first non-empty line
        first = None
        for ln in lines:
            if ln.raw.strip():
                first = ln
                break

        if first is None:
            return []

        if not first.is_comment:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"First step should be a comment containing '{keyword}'",
                line=first.line_number,
                fix_hint=f"Add a # comment at the top with '{keyword} <description>'",
            )]

        if case_sensitive:
            found = keyword in first.comment_text
        else:
            found = keyword.upper() in first.comment_text.upper()
        if not found:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=f"First comment should contain '{keyword}' to describe the script's intent",
                line=first.line_number,
                fix_hint=f"Add '{keyword} <description>' to the first comment",
            )]

        return []


# ---------------------------------------------------------------------------
# D002 — readme-block
# ---------------------------------------------------------------------------

@rule
class ReadmeBlock(LintRule):
    """Scripts that read parameters should have a disabled Insert Text $README block."""

    rule_id = "D002"
    name = "readme-block"
    category = "documentation"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    _PARAM_PATTERNS = ("Get ( ScriptParameter", "Get(ScriptParameter")

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok or not parse_result.steps:
            return []

        rc = self.rule_config(config)
        sev = self.severity(config)
        doc_variable = rc.get("doc_variable", "$README")

        uses_param = False
        has_readme = False

        for step in parse_result.steps:
            # Check all Calculation CDATA and Text elements for param usage
            for calc in step.iter("Calculation"):
                if calc.text and any(p in calc.text for p in self._PARAM_PATTERNS):
                    uses_param = True
            for text_el in step.iter("Text"):
                if text_el.text and any(p in text_el.text for p in self._PARAM_PATTERNS):
                    uses_param = True

            # Check for disabled Insert Text targeting the doc variable
            name = step.get("name", "")
            enabled = step.get("enable", "True")
            if name == "Insert Text" and enabled == "False":
                field_el = step.find("Field")
                if field_el is not None:
                    field_text = field_el.text if field_el.text else ""
                    field_name = field_el.get("name", "")
                    if doc_variable in field_text or doc_variable in field_name:
                        has_readme = True

        if uses_param and not has_readme:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=(
                    f"Script uses Get(ScriptParameter) but has no {doc_variable} doc block. "
                    f"Consider adding a disabled Insert Text step targeting {doc_variable} "
                    "to document the expected parameter format."
                ),
                line=0,
            )]

        return []

    def check_hr(self, lines, catalog, context, config):
        rc = self.rule_config(config)
        sev = self.severity(config)
        doc_variable = rc.get("doc_variable", "$README")

        uses_param = False
        has_readme = False

        for ln in lines:
            raw = ln.raw
            bracket = ln.bracket_content or ""

            # Check for parameter usage in any content
            if any(p in raw for p in self._PARAM_PATTERNS):
                uses_param = True
            if any(p in bracket for p in self._PARAM_PATTERNS):
                uses_param = True

            # Check for disabled Insert Text (HR format: // Insert Text)
            if ln.disabled and ln.step_name == "Insert Text":
                if doc_variable in raw:
                    has_readme = True

        if uses_param and not has_readme:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=(
                    f"Script uses Get(ScriptParameter) but has no {doc_variable} doc block. "
                    f"Consider adding a disabled Insert Text step targeting {doc_variable} "
                    "to document the expected parameter format."
                ),
                line=0,
            )]

        return []


# ---------------------------------------------------------------------------
# D003 — section-separation
# ---------------------------------------------------------------------------

@rule
class SectionSeparation(LintRule):
    """Large scripts (>20 steps) should use blank comment lines as section separators."""

    rule_id = "D003"
    name = "section-separation"
    category = "documentation"
    default_severity = Severity.INFO
    formats = {"xml", "hr"}
    tier = 1

    def check_xml(self, parse_result, catalog, context, config):
        if not parse_result.ok:
            return []

        rc = self.rule_config(config)
        sev = self.severity(config)
        min_steps = rc.get("min_steps", 20)

        steps = parse_result.steps
        if len(steps) <= min_steps:
            return []

        blank_comments = 0
        for step in steps:
            name = step.get("name", "")
            if name == "# (comment)":
                text_el = step.find("Text")
                if text_el is None or not text_el.text or not text_el.text.strip():
                    blank_comments += 1

        if blank_comments == 0:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=(
                    f"Script has {len(steps)} steps but no blank comment lines "
                    "for section separation. Consider adding blank # (comment) "
                    "steps to visually separate logical sections."
                ),
                line=0,
            )]

        return []

    def check_hr(self, lines, catalog, context, config):
        rc = self.rule_config(config)
        sev = self.severity(config)
        min_steps = rc.get("min_steps", 20)

        # Count actual steps (non-empty lines that have a step_name or are comments)
        step_lines = [ln for ln in lines if ln.step_name or ln.is_comment]
        if len(step_lines) <= min_steps:
            return []

        blank_comments = 0
        for ln in lines:
            if ln.is_comment and not ln.comment_text:
                blank_comments += 1

        if blank_comments == 0:
            return [Diagnostic(
                rule_id=self.rule_id,
                severity=sev,
                message=(
                    f"Script has {len(step_lines)} steps but no blank comment lines "
                    "for section separation. Consider adding blank # lines "
                    "to visually separate logical sections."
                ),
                line=0,
            )]

        return []
