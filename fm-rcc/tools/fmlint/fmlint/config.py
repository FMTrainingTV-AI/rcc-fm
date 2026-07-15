"""FMLint configuration — loads rule settings from config files."""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .types import Severity


# ---------------------------------------------------------------------------
# Config file discovery
# ---------------------------------------------------------------------------

def _find_config_files(project_root: Optional[Path] = None) -> list:
    """Return config file paths in priority order (defaults first, overrides last)."""
    files = []

    # 1. Built-in defaults (shipped with fmlint)
    builtin = Path(__file__).parent / "fmlint.config.json"
    if builtin.exists():
        files.append(builtin)

    # 2. Project-level overrides (gitignored, per-solution)
    if project_root:
        project_cfg = project_root / "agent" / "config" / "fmlint.config.json"
        if project_cfg.exists():
            files.append(project_cfg)

    return files


def _load_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins for leaf values."""
    merged = dict(base)
    for key, val in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = _deep_merge(merged[key], val)
        else:
            merged[key] = val
    return merged


# ---------------------------------------------------------------------------
# LintConfig
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "error": Severity.ERROR,
    "warning": Severity.WARNING,
    "info": Severity.INFO,
    "hint": Severity.HINT,
}

# Valid rule ID pattern — letter prefix + three digits
_RULE_ID_RE = re.compile(r'^[A-Z]\d{3}$')

# Known rule ID prefixes and their valid ranges
_KNOWN_PREFIXES = {
    "S": range(1, 12),    # S001–S011
    "N": range(1, 8),     # N001–N007
    "D": range(1, 4),     # D001–D003
    "R": range(1, 10),    # R001–R009
    "B": range(1, 7),     # B001–B006
    "C": range(1, 7),     # C001–C006
}

# Rule-specific config keys that must be numeric
_NUMERIC_KEYS = {
    "stale_minutes", "min_steps", "min_spaces",
    "min_variables",
}


def _validate_rules_config(rules: dict) -> list:
    """Validate a rules config dict. Returns a list of warning strings."""
    warnings = []

    for rule_id, rc in rules.items():
        if not isinstance(rc, dict):
            warnings.append(f'Config for "{rule_id}": expected object, got {type(rc).__name__}')
            continue

        # Check rule ID format
        if not _RULE_ID_RE.match(rule_id):
            warnings.append(f'Unknown rule ID format: "{rule_id}"')
        else:
            prefix = rule_id[0]
            num = int(rule_id[1:])
            if prefix not in _KNOWN_PREFIXES:
                warnings.append(f'Unknown rule ID prefix: "{rule_id}"')
            elif num not in _KNOWN_PREFIXES[prefix]:
                warnings.append(f'Unknown rule ID: "{rule_id}"')

        # Check severity string
        sev = rc.get("severity")
        if sev is not None and sev not in _SEVERITY_MAP:
            warnings.append(
                f'{rule_id}: invalid severity "{sev}" '
                f'(expected: {", ".join(_SEVERITY_MAP)})'
            )

        # Check enabled is boolean
        enabled = rc.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            warnings.append(
                f'{rule_id}: "enabled" should be boolean, got {type(enabled).__name__}'
            )

        # Check numeric fields (bool is a subclass of int in Python,
        # so exclude it explicitly)
        for key in _NUMERIC_KEYS:
            val = rc.get(key)
            if val is not None and (isinstance(val, bool) or not isinstance(val, (int, float))):
                warnings.append(
                    f'{rule_id}: "{key}" should be a number, got {type(val).__name__}'
                )

        # Check N002 regex patterns compile
        if rule_id == "N002" and "patterns" in rc:
            patterns = rc["patterns"]
            if isinstance(patterns, dict):
                for prefix_key, pat_info in patterns.items():
                    if isinstance(pat_info, dict) and "regex" in pat_info:
                        try:
                            re.compile(pat_info["regex"])
                        except re.error as e:
                            warnings.append(
                                f'N002: invalid regex for prefix "{prefix_key}": {e}'
                            )

        # Check extra_known_functions is a list
        if rule_id == "C003" and "extra_known_functions" in rc:
            if not isinstance(rc["extra_known_functions"], list):
                warnings.append(
                    f'C003: "extra_known_functions" should be a list, '
                    f'got {type(rc["extra_known_functions"]).__name__}'
                )

    return warnings


@dataclass
class LintConfig:
    """Configuration for a lint run.

    The `rule_configs` dict maps rule_id -> dict of rule-specific settings.
    Each entry has at minimum 'enabled' and 'severity', plus rule-specific keys.

    After loading, check `config_warnings` for validation issues (typos,
    invalid severities, bad regexes, etc.).
    """
    rule_configs: dict = field(default_factory=dict)  # rule_id -> {...}
    disabled_rules: set = field(default_factory=set)   # CLI-level overrides
    max_tier: Optional[int] = None
    config_warnings: list = field(default_factory=list)

    def is_enabled(self, rule_id: str) -> bool:
        """Check if a rule is enabled (CLI override takes precedence)."""
        if rule_id in self.disabled_rules:
            return False
        rc = self.rule_configs.get(rule_id, {})
        return rc.get("enabled", True)

    def get_severity(self, rule_id: str, default: Severity = Severity.WARNING) -> Severity:
        """Get the configured severity for a rule."""
        rc = self.rule_configs.get(rule_id, {})
        sev_str = rc.get("severity", "")
        return _SEVERITY_MAP.get(sev_str, default)

    def get_rule_config(self, rule_id: str) -> dict:
        """Get the full config dict for a specific rule."""
        return self.rule_configs.get(rule_id, {})

    @classmethod
    def load(cls, project_root: Optional[Path] = None, extra_config: Optional[Path] = None) -> "LintConfig":
        """Load config from default + project + optional extra config files."""
        cfg = cls()

        # Load and merge config files
        merged_rules = {}
        for config_path in _find_config_files(project_root):
            data = _load_json(config_path)
            rules = data.get("rules", {})
            merged_rules = _deep_merge(merged_rules, rules)

        # Extra config (e.g. from --config CLI flag)
        if extra_config and extra_config.exists():
            data = _load_json(extra_config)
            rules = data.get("rules", {})
            merged_rules = _deep_merge(merged_rules, rules)

        cfg.rule_configs = merged_rules
        cfg.config_warnings = _validate_rules_config(merged_rules)
        return cfg

    @classmethod
    def from_dict(cls, data: dict) -> "LintConfig":
        """Create config from a dict (for programmatic use / backward compat)."""
        cfg = cls()
        if "disable" in data:
            cfg.disabled_rules = set(data["disable"])
        if "max_tier" in data:
            cfg.max_tier = data["max_tier"]
        # If a full rules block is provided, use it
        if "rules" in data:
            cfg.rule_configs = data["rules"]
        return cfg
