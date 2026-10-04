# -*- coding: utf-8 -*-
"""Long-term customer memory interface."""
from typing import Dict, Any, Optional
from src.env.backend_client import BackendClient


class CustomerMemory:
    """Manages retrieval and formatting of long-term customer context."""

    def __init__(self, backend_client: BackendClient):
        self.backend = backend_client

    def get_context(self, customer_id: str) -> Dict[str, Any]:
        """Fetch full customer profile including risk flags and history directly from DB."""
        if hasattr(self.backend, "_master_db") and "customers" in self.backend._master_db:
            c = self.backend._master_db["customers"].get(customer_id)
            if c:
                return {"found": True, **c}
        return {"customer_id": customer_id, "found": False}

    def format_for_prompt(self, customer_id: str) -> str:
        """Format customer profile into concise prompt memory."""
        ctx = self.get_context(customer_id)
        if not ctx.get("found"):
            return f"Customer ID: {customer_id} (No previous records found)"

        name = ctx.get("name", "Unknown")
        tier = ctx.get("tier", "standard")
        risk = "FLAGGED (High Fraud Risk)" if ctx.get("risk_flag") else "Normal"
        contacts_30d = ctx.get("prior_contacts_30d", 0)
        past = ctx.get("past_interactions", [])

        summary = [
            f"Customer: {name} (ID: {customer_id})",
            f"Tier: {tier} | Risk Status: {risk} | Contacts in past 30 days: {contacts_30d}"
        ]

        if past:
            past_str = ", ".join(f"{p.get('date')}: {p.get('intent')} ({p.get('outcome')})" for p in past[-3:])
            summary.append(f"Recent History: {past_str}")

        return "\n".join(summary)
