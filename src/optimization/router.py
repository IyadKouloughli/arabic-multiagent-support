# -*- coding: utf-8 -*-
"""Model Router: routes tickets between fast small models and advanced reasoning models."""
from typing import Dict, Any, Optional
from src.config import DEFAULT_MAIN_MODEL, DEFAULT_FAST_MODEL


class ModelRouter:
    """Intelligently routes tickets to optimal model tiers based on risk and complexity."""

    def __init__(
        self,
        main_model: str = DEFAULT_MAIN_MODEL,
        fast_model: str = DEFAULT_FAST_MODEL
    ):
        self.main_model = main_model
        self.fast_model = fast_model
        self.routed_to_fast = 0
        self.routed_to_main = 0

    def select_model(
        self,
        intent: str,
        risk_level: str,
        urgency: str,
        category: str = "standard"
    ) -> str:
        """Select model based on query risk and complexity.
        
        Routing Policy:
        - High-risk, adversarial, or legal complaints -> Main Model
        - Ambiguous edge cases, duplicate charge disputes -> Main Model
        - Routine FAQ, clear order tracking, promo inquiries -> Fast Model
        """
        # Complex and safety-critical cases
        if (
            category == "adversarial" or
            risk_level == "high" or
            intent in ("complaint", "double_charge", "account_change", "multi_intent")
        ):
            self.routed_to_main += 1
            return self.main_model

        # Routine cases can use faster/cheaper model
        self.routed_to_fast += 1
        return self.fast_model

    @property
    def fast_ratio(self) -> float:
        """Proportion of queries served by the fast/cheaper model."""
        total = self.routed_to_fast + self.routed_to_main
        return (self.routed_to_fast / total) if total > 0 else 0.0
