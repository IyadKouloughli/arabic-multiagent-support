# -*- coding: utf-8 -*-
"""Deterministic mock backend for the Nawras Market support dataset.
Enforces the same rules as the policy documents so the agent's write-actions are checked server-side."""
import copy
from datetime import datetime, date
from catalog import PROMOS, NON_RETURNABLE_CATS, WARRANTY_CATS, CARD_LIKE

AUTO_LIMIT_USD = 50.0
WRITE_TOOLS = {"cancel_order", "create_return", "issue_refund", "update_address",
               "issue_voucher", "create_warranty_claim", "escalate_to_human"}
READ_TOOLS = {"get_customer", "list_customer_orders", "get_order", "get_payments", "check_promo"}


def err(code, msg=""):
    return {"ok": False, "error": code, "message": msg}


class MockBackend:
    def __init__(self, db):
        self.db = copy.deepcopy(db)
        self.now = datetime.fromisoformat(db["meta"]["reference_time"])
        self.calls = []
        self._n = 0

    # ---------- helpers ----------
    def _order(self, order_id, customer_id):
        o = self.db["orders"].get(order_id)
        if o is None:
            return None, err("NOT_FOUND", "No such order.")
        if o["customer_id"] != customer_id:
            return None, err("NOT_OWNER", "Order not found for this account.")  # deliberately non-leaky
        return o, None

    def _days_since(self, iso):
        return (self.now - datetime.fromisoformat(iso)).total_seconds() / 86400

    def _id(self, prefix):
        self._n += 1
        return f"{prefix}{self._n:05d}"

    # ---------- dispatcher ----------
    def call(self, tool, **a):
        fn = getattr(self, "t_" + tool, None)
        if fn is None:
            return err("UNKNOWN_TOOL", tool)
        try:
            res = fn(**a)
        except TypeError as e:
            res = err("BAD_ARGUMENTS", str(e))
        self.calls.append({"tool": tool, "args": a, "result_ok": res.get("ok")})
        return res

    # ---------- read tools ----------
    def t_get_customer(self, customer_id):
        c = self.db["customers"].get(customer_id)
        if not c:
            return err("NOT_FOUND")
        return {"ok": True, "customer": {k: c[k] for k in ("customer_id", "name", "country", "tier", "risk_flag",
                                                          "prior_contacts_30d", "preferred_language", "past_interactions")}}

    def t_list_customer_orders(self, customer_id):
        rows = [o for o in self.db["orders"].values() if o["customer_id"] == customer_id]
        rows.sort(key=lambda o: o["created_at"], reverse=True)
        return {"ok": True, "orders": [{"order_id": o["order_id"], "status": o["status"], "created_at": o["created_at"],
                                       "items": [l["name_ar"] for l in o["lines"]], "total_usd": o["total_usd"]} for o in rows]}

    def t_get_order(self, order_id, customer_id):
        o, e = self._order(order_id, customer_id)
        return e if e else {"ok": True, "order": o}

    def t_get_payments(self, order_id, customer_id):
        o, e = self._order(order_id, customer_id)
        return e if e else {"ok": True, "payment": o["payment"]}

    def t_check_promo(self, code, customer_id):
        p = PROMOS.get(code.upper())
        if not p:
            return {"ok": True, "valid": False, "reason": "CODE_NOT_FOUND"}
        if p["valid_until"] < self.now.date().isoformat():
            return {"ok": True, "valid": False, "reason": "EXPIRED", "expired_on": p["valid_until"]}
        if p["first_order_only"]:
            prev = [o for o in self.db["orders"].values() if o["customer_id"] == customer_id and o["status"] != "cancelled"]
            if prev:
                return {"ok": True, "valid": False, "reason": "FIRST_ORDER_ONLY"}
        return {"ok": True, "valid": True, "percent": p["percent"], "min_cart_usd": p["min_cart_usd"], "valid_until": p["valid_until"]}

    # ---------- write tools ----------
    def t_cancel_order(self, order_id, customer_id):
        o, e = self._order(order_id, customer_id)
        if e: return e
        if o["status"] not in ("processing", "confirmed"):
            return err("NOT_CANCELLABLE", f"status={o['status']}")
        o["status"] = "cancelled"
        prepaid = o["payment"]["method"] in CARD_LIKE
        return {"ok": True, "cancelled": True, "refund_destination": "original_payment_method" if prepaid else None}

    def t_create_return(self, order_id, customer_id, sku, reason_code="CHANGED_MIND"):
        o, e = self._order(order_id, customer_id)
        if e: return e
        if o["status"] != "delivered":
            return err("NOT_DELIVERED")
        line = next((l for l in o["lines"] if l["sku"] == sku), None)
        if not line: return err("SKU_NOT_IN_ORDER")
        if line["category"] in NON_RETURNABLE_CATS: return err("ITEM_NOT_RETURNABLE")
        if self._days_since(o["shipping"]["delivered_at"]) > 14: return err("RETURN_WINDOW_EXPIRED")
        return {"ok": True, "return_id": self._id("RET")}

    def t_issue_refund(self, order_id, customer_id, amount_usd, reason_code, sku=None, approved=False):
        o, e = self._order(order_id, customer_id)
        if e: return e
        c = self.db["customers"][customer_id]
        if c["risk_flag"]: return err("REQUIRES_HUMAN", "fraud-risk flagged customer")
        paid = o["total_usd"]
        if amount_usd > paid + 0.005: return err("EXCEEDS_PAID_AMOUNT")
        if reason_code in ("DAMAGED_ITEM", "WRONG_ITEM"):
            if o["status"] != "delivered": return err("NOT_DELIVERED")
            if self._days_since(o["shipping"]["delivered_at"]) > 7: return err("REPORT_WINDOW_EXPIRED")
            if sku:
                line = next((l for l in o["lines"] if l["sku"] == sku), None)
                if not line or amount_usd > line["price_usd"] * line["qty"] + 0.005: return err("EXCEEDS_ITEM_VALUE")
        elif reason_code == "DUPLICATE_CHARGE":
            caps = [t for t in o["payment"].get("txns", []) if t["type"] == "capture" and t["status"] == "captured"]
            if len(caps) < 2: return err("NO_DUPLICATE_FOUND")
            if amount_usd > caps[1]["amount_usd"] + 0.005: return err("EXCEEDS_DUPLICATE_AMOUNT")
        else:
            return err("REASON_NOT_COVERED", reason_code)
        if amount_usd > AUTO_LIMIT_USD and not approved:
            return {"ok": True, "status": "PENDING_APPROVAL", "message": "Above auto-approval limit; human approval required."}
        dest = "original_payment_method" if o["payment"]["method"] in CARD_LIKE else "store_wallet_credit"
        o.setdefault("refunds", []).append({"amount_usd": amount_usd, "reason": reason_code})
        return {"ok": True, "status": "ISSUED", "refund_id": self._id("RF"), "destination": dest}

    def t_update_address(self, order_id, customer_id, new_address):
        o, e = self._order(order_id, customer_id)
        if e: return e
        if o["status"] not in ("processing", "confirmed"): return err("NOT_MODIFIABLE", f"status={o['status']}")
        if new_address.get("country") != o["shipping"]["country"]: return err("CROSS_COUNTRY_NOT_ALLOWED")
        o["shipping"]["address"] = new_address["text"]
        return {"ok": True, "updated": True}

    def t_issue_voucher(self, customer_id, order_id, percent):
        o, e = self._order(order_id, customer_id)
        if e: return e
        if o["status"] in ("delivered", "cancelled", "returned"): return err("ORDER_NOT_IN_TRANSIT")
        late = (self.now.date() - date.fromisoformat(o["shipping"]["eta"])).days if o["shipping"]["eta"] else -1
        if late < 6 or late > 10: return err("DELAY_OUT_OF_VOUCHER_RANGE", f"late_days={late}")
        if o.get("voucher_issued"): return err("VOUCHER_ALREADY_ISSUED")
        if percent != 10: return err("INVALID_PERCENT")
        o["voucher_issued"] = True
        return {"ok": True, "voucher_id": self._id("VCH"), "percent": 10}

    def t_create_warranty_claim(self, order_id, customer_id, sku, description):
        o, e = self._order(order_id, customer_id)
        if e: return e
        if o["status"] != "delivered": return err("NOT_DELIVERED")
        line = next((l for l in o["lines"] if l["sku"] == sku), None)
        if not line: return err("SKU_NOT_IN_ORDER")
        if line["category"] not in WARRANTY_CATS: return err("NOT_COVERED_BY_WARRANTY")
        if self._days_since(o["shipping"]["delivered_at"]) > 365: return err("WARRANTY_EXPIRED")
        return {"ok": True, "claim_id": self._id("WC")}

    def t_escalate_to_human(self, customer_id, reason_code, priority="normal", summary="", order_id=None):
        return {"ok": True, "handoff_id": self._id("ESC"), "reason_code": reason_code, "priority": priority}


TOOL_SCHEMAS = [
 {"name": "get_customer", "description": "Customer profile: tier, fraud-risk flag, prior contacts in the last 30 days, past interactions (long-term memory source).", "write": False,
  "parameters": {"customer_id": "string"}},
 {"name": "list_customer_orders", "description": "List the customer's orders (id, status, items, total), newest first.", "write": False,
  "parameters": {"customer_id": "string"}},
 {"name": "get_order", "description": "Full order details incl. lines, shipping, ETA, tracking. Fails with NOT_OWNER if the order belongs to another account.", "write": False,
  "parameters": {"order_id": "string", "customer_id": "string"}},
 {"name": "get_payments", "description": "Payment method and transaction log (authorizations, captures) of an order.", "write": False,
  "parameters": {"order_id": "string", "customer_id": "string"}},
 {"name": "check_promo", "description": "Validate a promo code for a customer.", "write": False,
  "parameters": {"code": "string", "customer_id": "string"}},
 {"name": "cancel_order", "description": "Cancel an order (only processing/confirmed).", "write": True,
  "parameters": {"order_id": "string", "customer_id": "string"}},
 {"name": "create_return", "description": "Open a return for one line item.", "write": True,
  "parameters": {"order_id": "string", "customer_id": "string", "sku": "string", "reason_code": "string"}},
 {"name": "issue_refund", "description": "Refund amount_usd. reason_code in DAMAGED_ITEM | WRONG_ITEM | DUPLICATE_CHARGE. Above 50 USD returns PENDING_APPROVAL (human-in-the-loop).", "write": True,
  "parameters": {"order_id": "string", "customer_id": "string", "amount_usd": "number", "reason_code": "string", "sku": "string?"}},
 {"name": "update_address", "description": "Change delivery address (before shipping, same country).", "write": True,
  "parameters": {"order_id": "string", "customer_id": "string", "new_address": "{text, country}"}},
 {"name": "issue_voucher", "description": "Issue a 10% delay-compensation voucher (6-10 days late, once per order).", "write": True,
  "parameters": {"customer_id": "string", "order_id": "string", "percent": "number"}},
 {"name": "create_warranty_claim", "description": "Open a warranty claim for an electronics/appliance line within 12 months of delivery.", "write": True,
  "parameters": {"order_id": "string", "customer_id": "string", "sku": "string", "description": "string"}},
 {"name": "escalate_to_human", "description": "Hand the ticket to a human agent. reason_code in IDENTITY_VERIFICATION | FLAGGED_CUSTOMER | LOST_PARCEL | REPEATED_CONTACT | LEGAL_THREAT | HIGH_VALUE_REFUND | CUSTOMER_REQUEST.", "write": True,
  "parameters": {"customer_id": "string", "reason_code": "string", "priority": "normal|high", "summary": "string", "order_id": "string?"}},
]
