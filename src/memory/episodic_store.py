# -*- coding: utf-8 -*-
"""Episodic memory store for few-shot trajectory guidance."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import EPISODIC_SEED_PATH


class EpisodicStore:
    """Stores and retrieves past successful resolution traces."""

    def __init__(self, seed_path: Optional[Path] = None):
        path = seed_path or EPISODIC_SEED_PATH
        self.traces: List[Dict[str, Any]] = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.traces.append(json.loads(line))

    def retrieve(self, intent: Optional[str] = None, variety: Optional[str] = None, limit: int = 2) -> List[Dict[str, Any]]:
        """Retrieve relevant past trajectories matching intent or dialect variety."""
        matches = []
        for t in self.traces:
            score = 0
            if intent and t.get("intent") == intent:
                score += 2
            if variety and (t.get("language_variety") == variety or t.get("variety_code") == variety):
                score += 1
            if score > 0:
                matches.append((score, t))

        matches.sort(key=lambda x: x[0], reverse=True)
        if matches:
            return [m[1] for m in matches[:limit]]
        return self.traces[:limit]

    def add_trace(self, trace: Dict[str, Any]):
        """Append a newly verified resolution trace into memory."""
        self.traces.append(trace)

    def format_for_prompt(self, traces: List[Dict[str, Any]]) -> str:
        """Format traces into few-shot prompt examples."""
        if not traces:
            return ""

        formatted = ["### Past Successful Resolutions (Few-Shot Demonstrations):"]
        for idx, t in enumerate(traces, 1):
            formatted.append(f"Example {idx}:")
            formatted.append(f"- Customer text: {t.get('text')}")
            formatted.append(f"- Intent: {t.get('intent')}")
            calls = [f"{c['tool']}({json.dumps(c.get('args', {}), ensure_ascii=False)})" for c in t.get("tool_calls", [])]
            formatted.append(f"- Resolution Actions: {' -> '.join(calls) if calls else 'None (Direct response)'}")
            formatted.append(f"- Outcome: {t.get('outcome')}\n")

        return "\n".join(formatted)
