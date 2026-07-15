"""Core types for FMLint — FileMaker code linter."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Diagnostic severity levels."""
    ERROR = "error"      # Will break in FileMaker
    WARNING = "warning"  # Likely bug or convention violation
    INFO = "info"        # Style suggestion
    HINT = "hint"        # Optional improvement


@dataclass
class Diagnostic:
    """A single lint finding."""
    rule_id: str
    severity: Severity
    message: str
    line: int = 0            # 1-based (0 = file-level)
    column: int = 0          # 1-based (0 = whole line)
    end_line: int = 0
    end_column: int = 0
    fix_hint: Optional[str] = None

    def to_dict(self):
        d = {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }
        if self.fix_hint:
            d["fix_hint"] = self.fix_hint
        return d


@dataclass
class LintResult:
    """Collection of diagnostics for a single file or content block."""
    source: str = ""
    diagnostics: list = field(default_factory=list)

    @property
    def errors(self):
        return [d for d in self.diagnostics if d.severity == Severity.ERROR]

    @property
    def warnings(self):
        return [d for d in self.diagnostics if d.severity == Severity.WARNING]

    @property
    def ok(self):
        return len(self.errors) == 0

    def to_dict(self):
        return {
            "source": self.source,
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class ParsedHRLine:
    """A parsed line from a human-readable FileMaker script."""
    raw: str
    line_number: int
    disabled: bool = False
    is_comment: bool = False
    comment_text: str = ""
    step_name: str = ""
    bracket_content: str = ""
    params: list = field(default_factory=list)
    indent: int = 0
