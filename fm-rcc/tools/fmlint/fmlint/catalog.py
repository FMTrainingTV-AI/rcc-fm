"""Step catalog loader for FMLint.

Loads step names and metadata from step-catalog-en.json lazily.
"""

import json
from pathlib import Path
from typing import Optional


class StepCatalog:
    """Lazy-loading accessor for the FileMaker step catalog."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self._path = catalog_path
        self._entries = None  # dict: step_name -> entry dict
        self._names = None    # set of known step names (lowercase)

    def _ensure_loaded(self):
        if self._entries is not None:
            return
        self._entries = {}
        self._names = set()
        if self._path and self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                name = entry.get("name", "")
                if name:
                    self._entries[name] = entry
                    self._names.add(name.lower())

    def get(self, step_name: str) -> Optional[dict]:
        self._ensure_loaded()
        return self._entries.get(step_name)

    def known_names(self) -> set:
        self._ensure_loaded()
        return set(self._entries.keys())

    def known_names_lower(self) -> set:
        self._ensure_loaded()
        return set(self._names)

    def has_step(self, step_name: str) -> bool:
        self._ensure_loaded()
        return step_name.lower() in self._names

    def get_block_pair(self, step_name: str) -> Optional[dict]:
        entry = self.get(step_name)
        if entry:
            return entry.get("blockPair")
        return None

    def is_self_closing(self, step_name: str) -> Optional[bool]:
        entry = self.get(step_name)
        if entry:
            return entry.get("selfClosing")
        return None
