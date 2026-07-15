"""FMLint engine — rule registry, runner, tier detection."""

from pathlib import Path
from typing import Optional

from .types import Diagnostic, Severity, LintResult
from .config import LintConfig
from .catalog import StepCatalog
from .context import LintContext
from .formats.detect import detect_format
from .formats.xml_parser import parse_xml_string, parse_xml_file
from .formats.hr_parser import parse_hr


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

_registry = []
_registered_ids = set()


def rule(cls):
    """Decorator to register a lint rule class.

    Guards against duplicate registration (e.g. module re-import).
    """
    if cls.rule_id not in _registered_ids:
        _registry.append(cls)
        _registered_ids.add(cls.rule_id)
    return cls


def get_rules():
    """Return all registered rule classes."""
    return list(_registry)


def clear_registry():
    """Reset the rule registry. Primarily useful for test isolation."""
    _registry.clear()
    _registered_ids.clear()


# ---------------------------------------------------------------------------
# Rule base class
# ---------------------------------------------------------------------------

class LintRule:
    """Base class for all lint rules.

    Subclasses must set class attributes:
        rule_id: str           e.g. "S001"
        name: str              human-readable name
        category: str          "structure", "naming", etc.
        default_severity: Severity
        formats: set           {"xml"}, {"hr"}, or {"xml", "hr"}
        tier: int              1=offline, 2=context, 3=live
    """

    rule_id = ""
    name = ""
    category = ""
    default_severity = Severity.WARNING
    formats = set()
    tier = 1
    requires_confirmation = False

    def check_xml(self, parse_result, catalog, context, config):
        """Check XML format. Returns list of Diagnostic."""
        return []

    def check_hr(self, lines, catalog, context, config):
        """Check HR format. Returns list of Diagnostic."""
        return []

    def severity(self, config):
        """Get the effective severity for this rule from config."""
        return config.get_severity(self.rule_id, self.default_severity)

    def rule_config(self, config):
        """Get the rule-specific config dict."""
        return config.get_rule_config(self.rule_id)


# ---------------------------------------------------------------------------
# Tier detection
# ---------------------------------------------------------------------------

def detect_tier(project_root: Optional[Path], config: LintConfig) -> int:
    """Detect the highest available validation tier."""
    if config.max_tier is not None:
        return config.max_tier

    max_tier = 1

    if project_root:
        ctx_path = project_root / "agent" / "CONTEXT.json"
        if ctx_path.exists():
            max_tier = 2
        else:
            context_dir = project_root / "agent" / "context"
            if context_dir.exists():
                for _ in context_dir.rglob("*.index"):
                    max_tier = 2
                    break

        auto_path = project_root / "agent" / "config" / "automation.json"
        if auto_path.exists() and max_tier >= 2:
            try:
                import json
                with open(auto_path, "r", encoding="utf-8") as f:
                    auto_data = json.load(f)
                solutions = auto_data.get("solutions", {})
                for sol in solutions.values():
                    if sol.get("odata", {}).get("base_url"):
                        max_tier = 3
                        break
            except (OSError, ValueError):
                pass

    return max_tier


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class LintRunner:
    """Orchestrates rule execution against content."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        catalog_path: Optional[Path] = None,
        context_path: Optional[Path] = None,
        config: Optional[LintConfig] = None,
        config_path: Optional[Path] = None,
    ):
        self.project_root = project_root

        # Load config: explicit config object, or load from files
        if config is not None:
            self.config = config
            # If config was created without rule_configs, load from files
            if not config.rule_configs:
                file_config = LintConfig.load(project_root, config_path)
                config.rule_configs = file_config.rule_configs
        else:
            self.config = LintConfig.load(project_root, config_path)

        # Resolve catalog path. Vendored layout: the catalog ships inside
        # the package at fmlint/catalogs/step-catalog-en.json.
        if catalog_path is None:
            vendored = Path(__file__).resolve().parent / "catalogs" / "step-catalog-en.json"
            if vendored.exists():
                catalog_path = vendored
            elif project_root:
                catalog_path = project_root / "agent" / "catalogs" / "step-catalog-en.json"
        self.catalog = StepCatalog(catalog_path)

        # Resolve context
        self.context = LintContext(context_path, project_root)

        # Detect tier
        self.tier = detect_tier(project_root, self.config)

        # Import rules to trigger registration
        from . import rules as _rules  # noqa: F401

    def lint(self, content: str, fmt: Optional[str] = None, source: str = "") -> LintResult:
        """Lint content string. Auto-detects format if not specified."""
        if fmt is None:
            fmt = detect_format(content)

        result = LintResult(source=source)
        active_rules = self._active_rules(fmt)

        if fmt == "xml":
            parse_result = parse_xml_string(content)
            for rule_instance in active_rules:
                diags = rule_instance.check_xml(
                    parse_result, self.catalog, self.context, self.config
                )
                result.diagnostics.extend(diags)
        else:
            lines = parse_hr(content)
            for rule_instance in active_rules:
                diags = rule_instance.check_hr(
                    lines, self.catalog, self.context, self.config
                )
                result.diagnostics.extend(diags)

        # Sort by line number, then severity
        severity_order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2, Severity.HINT: 3}
        result.diagnostics.sort(key=lambda d: (d.line, severity_order.get(d.severity, 9)))

        return result

    def lint_file(self, filepath: str, fmt: Optional[str] = None) -> LintResult:
        """Lint a file. Auto-detects format from content."""
        path = Path(filepath)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if fmt is None:
            fmt = detect_format(content)
        return self.lint(content, fmt=fmt, source=str(path))

    def _active_rules(self, fmt: str) -> list:
        """Get instantiated rules that apply to this format and tier."""
        active = []
        for cls in get_rules():
            if not self.config.is_enabled(cls.rule_id):
                continue
            if cls.tier > self.tier:
                continue
            if fmt not in cls.formats:
                continue
            active.append(cls())
        return active
