"""FMLint — FileMaker code linter for fmxmlsnippet XML and human-readable scripts.

Vendored from https://github.com/petrowsky/agentic-fm (Apache 2.0).
See VENDOR.md for the list of local modifications.

Usage:
    from fmlint import lint, LintResult, Diagnostic, Severity

    result = lint(content, fmt="xml")
    for d in result.diagnostics:
        print(f"{d.severity.value}: {d.rule_id} line {d.line}: {d.message}")
"""

from .types import Diagnostic, Severity, LintResult, ParsedHRLine
from .config import LintConfig
from .engine import LintRunner

from pathlib import Path
from typing import Optional


def lint(
    content: str,
    fmt: Optional[str] = None,
    project_root: Optional[str] = None,
    catalog_path: Optional[str] = None,
    context_path: Optional[str] = None,
    config: Optional[dict] = None,
    source: str = "",
) -> LintResult:
    """Lint FileMaker code content.

    Args:
        content: The code to lint (XML or HR format)
        fmt: "xml", "hr", or None for auto-detect
        project_root: Path to project root (for auto-discovering catalog/context)
        catalog_path: Path to step-catalog-en.json
        context_path: Path to CONTEXT.json
        config: Configuration dict (disable, severity, max_tier, etc.)
        source: Source identifier (filename, etc.)

    Returns:
        LintResult with diagnostics
    """
    lint_config = LintConfig.from_dict(config) if config else LintConfig()
    root = Path(project_root) if project_root else None
    cat_path = Path(catalog_path) if catalog_path else None
    ctx_path = Path(context_path) if context_path else None

    runner = LintRunner(
        project_root=root,
        catalog_path=cat_path,
        context_path=ctx_path,
        config=lint_config,
    )
    return runner.lint(content, fmt=fmt, source=source)


def lint_file(
    filepath: str,
    fmt: Optional[str] = None,
    project_root: Optional[str] = None,
    catalog_path: Optional[str] = None,
    context_path: Optional[str] = None,
    config: Optional[dict] = None,
) -> LintResult:
    """Lint a FileMaker code file.

    Args:
        filepath: Path to the file to lint
        fmt: "xml", "hr", or None for auto-detect
        project_root: Path to project root
        catalog_path: Path to step-catalog-en.json
        context_path: Path to CONTEXT.json
        config: Configuration dict

    Returns:
        LintResult with diagnostics
    """
    lint_config = LintConfig.from_dict(config) if config else LintConfig()
    root = Path(project_root) if project_root else None
    cat_path = Path(catalog_path) if catalog_path else None
    ctx_path = Path(context_path) if context_path else None

    runner = LintRunner(
        project_root=root,
        catalog_path=cat_path,
        context_path=ctx_path,
        config=lint_config,
    )
    return runner.lint_file(filepath, fmt=fmt)


__all__ = [
    "lint",
    "lint_file",
    "Diagnostic",
    "Severity",
    "LintResult",
    "LintConfig",
    "LintRunner",
    "ParsedHRLine",
]
