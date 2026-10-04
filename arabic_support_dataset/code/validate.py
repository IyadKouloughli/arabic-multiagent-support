# -*- coding: utf-8 -*-
"""Replays every gold trajectory against the mock backend and checks label/text/policy consistency."""
import json, re, sys, collections
from backend import MockBackend, WRITE_TOOLS

db = json.load(open("data/db.json", encoding="utf-8"))
tickets = [json.loads(l) for l in open("data/tickets.jsonl", encoding="utf-8")]
OID = re.compile(r"NW\d{7}")
errors, stats = [], collections.Counter()

def bad(t, msg): errors.append(f"{t['ticket_id']} [{t['gold']['intent']}/{t['gold']['case_type']}]: {msg}")

for t in tickets:
    g = t["gold"]; be = MockBackend(db)
    # 1. text vs order-id metadata
    found = set(OID.findall(t["text"]))
    if found != set(t["order_ids_mentioned"]): bad(t, f"order ids in text {found} != metadata {t['order_ids_mentioned']}")
    if len(t["text"].strip()) < 8: bad(t, "text too short")
    # 2. replay gold calls
    pending = False
    for c in g["required_tool_calls"]:
        args = dict(c["args"])
        r = be.call(c["tool"], **args)
        if c.get("expect_error"):
            if r.get("ok") or r.get("error") != c["expect_error"]: bad(t, f"{c['tool']} expected {c['expect_error']} got {r}")
            continue
        if not r.get("ok"): bad(t, f"{c['tool']} failed: {r}"); continue
        if c["tool"] == "issue_refund":
            if c.get("requires_approval"):
                if r.get("status") != "PENDING_APPROVAL": bad(t, f"expected PENDING_APPROVAL got {r}")
                pending = True
                if g["simulated_reviewer_decision"] == "approve":
                    r2 = be.call("issue_refund", approved=True, **args)
                    if r2.get("status") != "ISSUED": bad(t, f"approved refund not issued: {r2}")
            elif r.get("status") != "ISSUED": bad(t, f"auto refund not ISSUED: {r}")
    # 3. blocked calls must be rejected by backend
    for b in g["blocked_calls_if_attempted"]:
        r = be.call(b["tool"], **b["args"])
        if r.get("ok") and r.get("status") != "PENDING_APPROVAL" or (not r.get("ok") and r.get("error") != b["expected_error"]):
            bad(t, f"blocked call {b['tool']} expected {b['expected_error']} got {r}")
    # 4. outcome <-> calls consistency
    names = [c["tool"] for c in g["required_tool_calls"]]; oc = g["expected_outcome"]
    if oc == "escalate" and "escalate_to_human" not in names: bad(t, "escalate without escalate_to_human")
    if oc == "hitl_approval" and not pending: bad(t, "hitl without pending refund")
    if oc in ("refuse", "clarify") and any(n in WRITE_TOOLS for n in names): bad(t, "write call in refuse/clarify ticket")
    if oc == "resolve" and any(n == "escalate_to_human" for n in names): bad(t, "resolve with escalation")
    if t["category"] == "adversarial" and "adversarial" not in t: bad(t, "missing adversarial meta")
    stats[oc] += 1

print("tickets:", len(tickets), "| validation errors:", len(errors))
for e in errors[:40]: print(" -", e)
print("outcomes:", dict(stats))
sys.exit(1 if errors else 0)
