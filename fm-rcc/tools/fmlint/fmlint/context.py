"""CONTEXT.json and index file loader for FMLint."""

import json
import os
from pathlib import Path
from typing import Optional


class LintContext:
    """Provides access to CONTEXT.json and index file data for reference validation."""

    def __init__(self, context_path: Optional[Path] = None, project_root: Optional[Path] = None):
        self._context_path = context_path
        self._project_root = project_root
        self._data = None
        self._loaded = False

        # Extracted reference maps
        self.fields = {}       # (to_name, field_name) -> str(field_id)
        self.layouts = {}      # layout_name -> str(layout_id)
        self.scripts = {}      # script_name -> str(script_id)
        self.tables = set()    # table-occurrence names
        self.generated_at = None
        self.layout_name = None
        self.solution_name = None

    def load(self) -> bool:
        """Load CONTEXT.json. Returns True if loaded successfully."""
        if self._loaded:
            return self._data is not None

        self._loaded = True
        path = self._context_path
        if not path and self._project_root:
            path = self._project_root / "agent" / "CONTEXT.json"

        if not path or not path.exists():
            return False

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        self._extract_references()
        return True

    def _extract_references(self):
        data = self._data
        if not data:
            return

        self.generated_at = data.get("generated_at")
        self.layout_name = data.get("current_layout", {}).get("name")
        self.solution_name = data.get("solution")

        for key, info in data.get("tables", {}).items():
            to_name = info.get("to", key)
            # Register both the JSON key and the TO name (they may differ
            # depending on whether the Context() function keys by base table
            # or by TO name — we support both formats)
            self.tables.add(key)
            self.tables.add(to_name)
            for field_name, field_info in info.get("fields", {}).items():
                self.fields[(key, field_name)] = str(field_info.get("id", ""))
                if to_name != key:
                    self.fields[(to_name, field_name)] = str(field_info.get("id", ""))

        for layout_name, layout_info in data.get("layouts", {}).items():
            self.layouts[layout_name] = str(layout_info.get("id", ""))

        for script_name, script_info in data.get("scripts", {}).items():
            self.scripts[script_name] = str(script_info.get("id", ""))

    @property
    def available(self) -> bool:
        if not self._loaded:
            self.load()
        return self._data is not None

    @property
    def raw(self) -> Optional[dict]:
        if not self._loaded:
            self.load()
        return self._data
