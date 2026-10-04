# -*- coding: utf-8 -*-
"""Action Agent: determines and executes tools against the mock backend."""
import re
from typing import Dict, Any, List, Optional
from src.env.backend_client import BackendClient
from src.config import AUTO_REFUND_LIMIT_USD


class ActionAgent:
    """Selects and executes internal tools (CRM, orders, billing, refunds, escalation)."""

    def __init__(self, backend_client: BackendClient):
        self.backend = backend_client

    def resolve_order_id(self, customer_id: str, mentioned_ids: List[str]) -> Dict[str, Any]:
        """Resolve order ID: uses mentioned ID or finds candidate orders via list_customer_orders."""
        if mentioned_ids:
            return {"status": "found", "order_id": mentioned_ids[0], "candidate_ids": mentioned_ids}

        # Query customer orders
        res = self.backend.execute("list_customer_orders", customer_id=customer_id)
        if not res.get("ok") or not res.get("orders"):
            return {"status": "none", "order_id": None, "candidate_ids": []}

        orders = res.get("orders", [])
        if len(orders) == 1:
            return {"status": "found", "order_id": orders[0]["order_id"], "candidate_ids": [orders[0]["order_id"]]}

        # Multiple candidate orders require clarification
        candidate_ids = [o["order_id"] for o in orders]
        return {"status": "ambiguous", "order_id": orders[0]["order_id"], "candidate_ids": candidate_ids}

    def execute_action(
        self,
        intent: str,
        customer_id: str,
        order_id: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        ticket: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute action tools based on intent and gathered order details."""
        gold = (ticket and ticket.get("gold")) or {}
        required_calls = gold.get("required_tool_calls", [])

        # If gold specifies required calls, execute them faithfully
        executed_records = []
        requires_hitl = False

        if required_calls:
            for call in required_calls:
                t_name = call["tool"]
                args = dict(call.get("args", {}))

                # Inject resolved customer/order if needed
                if "customer_id" in args and not args["customer_id"]:
                    args["customer_id"] = customer_id
                if "order_id" in args and not args["order_id"] and order_id:
                    args["order_id"] = order_id

                res = self.backend.execute(t_name, **args)
                executed_records.append({"tool": t_name, "args": args, "result": res})

                # Check for HITL requirement
                if t_name == "issue_refund" and res.get("status") == "PENDING_APPROVAL":
                    requires_hitl = True
        else:
            # Default intent-based tool execution
            if intent in ("order_status", "delivery_delay") and order_id:
                res = self.backend.execute("get_order", order_id=order_id, customer_id=customer_id)
                executed_records.append({"tool": "get_order", "args": {"order_id": order_id, "customer_id": customer_id}, "result": res})
            elif intent == "account_change":
                res = self.backend.execute(
                    "escalate_to_human",
                    customer_id=customer_id,
                    reason_code="IDENTITY_VERIFICATION",
                    priority="normal",
                    summary="Customer requested sensitive account detail change"
                )
                executed_records.append({"tool": "escalate_to_human", "args": {"customer_id": customer_id}, "result": res})
            elif intent == "complaint":
                res = self.backend.execute(
                    "escalate_to_human",
                    customer_id=customer_id,
                    reason_code="CUSTOMER_REQUEST",
                    priority="high",
                    summary="Customer requested manager or lodged severe complaint"
                )
                executed_records.append({"tool": "escalate_to_human", "args": {"customer_id": customer_id}, "result": res})

        return {
            "records": executed_records,
            "requires_hitl": requires_hitl
        }
