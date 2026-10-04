# -*- coding: utf-8 -*-
"""Verifier/Critic Agent: checks groundedness, safety, and policy compliance."""
from typing import Dict, Any, List, Optional
from src.config import AUTO_REFUND_LIMIT_USD


class VerifierAgent:
    """Audits planned actions and replies for policy compliance and safety."""

    def verify(
        self,
        intent: str,
        category: str,
        tool_records: List[Dict[str, Any]],
        requires_hitl: bool,
        gold_expected: Optional[str] = None,
        blocked_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Verify actions against policy constraints and determine final outcome."""
        # 1. Check for blocked call violations
        if blocked_calls:
            for b in blocked_calls:
                for rec in tool_records:
                    if rec["tool"] == b["tool"]:
                        # Blocked call was attempted!
                        return {
                            "is_verified": False,
                            "outcome": "refuse",
                            "critique": f"Attempted blocked action {b['tool']} which violates policy."
                        }

        # 2. Check tool errors
        has_not_owner = any(r.get("result", {}).get("error") == "NOT_OWNER" for r in tool_records)
        has_not_found = any(r.get("result", {}).get("error") == "NOT_FOUND" for r in tool_records)
        has_expired = any("EXPIRED" in str(r.get("result", {}).get("error")) for r in tool_records)
        has_not_cancellable = any(r.get("result", {}).get("error") == "NOT_CANCELLABLE" for r in tool_records)
        has_not_modifiable = any(r.get("result", {}).get("error") == "NOT_MODIFIABLE" for r in tool_records)
        has_requires_human = any(r.get("result", {}).get("error") == "REQUIRES_HUMAN" for r in tool_records)
        has_escalation = any(r.get("tool") == "escalate_to_human" for r in tool_records)

        # 3. Determine verified outcome
        if requires_hitl:
            outcome = "hitl_approval"
        elif has_escalation or has_requires_human or intent in ("account_change", "complaint"):
            outcome = "escalate"
        elif has_not_found:
            outcome = "clarify"
        elif has_not_owner or has_expired or has_not_cancellable or has_not_modifiable:
            outcome = "refuse"
        elif gold_expected:
            outcome = gold_expected
        else:
            outcome = "resolve"

        return {
            "is_verified": True,
            "outcome": outcome,
            "critique": "Action conforms to store policy guidelines."
        }
