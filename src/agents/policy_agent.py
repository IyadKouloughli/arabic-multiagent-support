# -*- coding: utf-8 -*-
"""Policy Agent: retrieves Arabic company policies with citations and constraints."""
from typing import Dict, Any, List, Optional
from src.policies.retriever import PolicyRetriever

# Intent to canonical policy IDs mapping
INTENT_POLICY_MAP = {
    "order_status": ["P01"],
    "cancel_order": ["P02", "P14"],
    "return_request": ["P03", "P14"],
    "damaged": ["P04", "P14", "P15"],
    "double_charge": ["P05", "P14"],
    "address_change": ["P06"],
    "delivery_delay": ["P01", "P07"],
    "promo": ["P08"],
    "account_change": ["P09", "P11", "P12"],
    "warranty": ["P10"],
    "complaint": ["P12"],
    "faq": ["P13"],
    "adversarial": ["P11"],
}


class PolicyAgent:
    """Retrieves policies with citations and enforces policy boundaries."""

    def __init__(self, retriever: Optional[PolicyRetriever] = None):
        self.retriever = retriever or PolicyRetriever()

    def get_policies(self, text: str, intent: Optional[str] = None, top_k: int = 3) -> Dict[str, Any]:
        """Retrieve relevant policies based on semantic search and canonical intent mapping."""
        # 1. Search by BM25
        search_results = self.retriever.search(text, top_k=top_k)
        retrieved_ids = [p["policy_id"] for p in search_results]

        # 2. Augment with canonical policy for identified intent
        if intent and intent in INTENT_POLICY_MAP:
            for pid in INTENT_POLICY_MAP[intent]:
                if pid not in retrieved_ids:
                    pol = self.retriever.get_policy(pid)
                    if pol:
                        search_results.append(pol)
                        retrieved_ids.append(pid)

        # 3. Format policy context with citations
        context = self.retriever.format_for_prompt(search_results)

        return {
            "policies": search_results,
            "policy_ids": retrieved_ids,
            "context": context
        }
