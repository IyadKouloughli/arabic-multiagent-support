# -*- coding: utf-8 -*-
"""Mock Backend Client for isolated ticket resolution sessions."""
import json
import copy
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.config import DB_PATH, DATASET_DIR

# Ensure backend from dataset code is importable
dataset_code_dir = str(DATASET_DIR / "code")
if dataset_code_dir not in sys.path:
    sys.path.insert(0, dataset_code_dir)

from backend import MockBackend, TOOL_SCHEMAS, WRITE_TOOLS, READ_TOOLS


class BackendClient:
    """Provides isolated, observable access to Nawras Market mock backend."""

    def __init__(self, db_path: Optional[Path] = None):
        path = db_path or DB_PATH
        with open(path, "r", encoding="utf-8") as f:
            self._master_db = json.load(f)
        self.backend: Optional[MockBackend] = None
        self.call_history: List[Dict[str, Any]] = []
        self.reset()

    def reset(self, custom_db: Optional[Dict[str, Any]] = None):
        """Reset backend state for a new ticket session."""
        db_snapshot = custom_db if custom_db is not None else self._master_db
        self.backend = MockBackend(copy.deepcopy(db_snapshot))
        self.call_history = []

    def execute(self, tool: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool against the backend and record the call."""
        if self.backend is None:
            raise RuntimeError("BackendClient has not been initialized or reset.")

        result = self.backend.call(tool, **kwargs)
        record = {
            "tool": tool,
            "args": copy.deepcopy(kwargs),
            "result": copy.deepcopy(result),
            "is_write": tool in WRITE_TOOLS
        }
        self.call_history.append(record)
        return result

    @property
    def write_calls(self) -> List[Dict[str, Any]]:
        """Return all write calls executed in the current session."""
        return [c for c in self.call_history if c["is_write"]]

    @property
    def all_calls(self) -> List[Dict[str, Any]]:
        """Return all tool calls executed in the current session."""
        return self.call_history

    @staticmethod
    def get_tool_schemas() -> List[Dict[str, Any]]:
        """Return schema definitions for all available tools."""
        return copy.deepcopy(TOOL_SCHEMAS)

    @staticmethod
    def is_write_tool(tool_name: str) -> bool:
        """Check if a tool is a mutating write action."""
        return tool_name in WRITE_TOOLS
