# -*- coding: utf-8 -*-
"""Unit and Integration tests for FastAPI endpoints."""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.app import (
    app, health_check, get_policies, get_policy_hash,
    get_metrics, resolve_ticket, TicketRequest
)


def test_health_endpoint():
    data = health_check()
    assert data["status"] == "healthy"
    assert "version" in data


def test_policies_endpoint():
    policies = get_policies()
    assert isinstance(policies, list)
    assert len(policies) == 15
    policy_ids = [p["policy_id"] for p in policies]
    assert "P01" in policy_ids
    assert "P15" in policy_ids

    hash_meta = get_policy_hash()
    assert "policy_hash" in hash_meta
    assert len(hash_meta["policy_hash"]) >= 8


def test_metrics_endpoint():
    data = get_metrics()
    assert "full_multi_agent" in data or "message" in data


def test_resolve_endpoint_order_tracking():
    # Test an Algerian ticket with mixed French
    req = TicketRequest(
        customer_id="C50642",
        text="Salam, je veux savoir l'état de ma commande NW4241472 svp.",
        channel="web_chat",
        ticket_id="T_API_TEST_01"
    )
    res = resolve_ticket(req)
    assert res.ticket_id == "T_API_TEST_01"
    assert res.outcome in ["resolve", "escalate", "clarify"]
    assert len(res.reply) > 0
    assert isinstance(res.tool_calls, list)
    assert res.latency_sec >= 0.0


def test_resolve_endpoint_ambiguous():
    # Test ambiguous ticket requesting order status without order ID
    req = TicketRequest(
        customer_id="C65751",
        text="مرحباً، أود الاستفسار عن حالة طلبي، فلم يصلني أي تحديث منذ فترة.",
        channel="web_chat",
        ticket_id="T_API_TEST_02"
    )
    res = resolve_ticket(req)
    assert res.outcome in ["clarify", "resolve"]
    assert len(res.reply) > 0


if __name__ == "__main__":
    test_health_endpoint()
    test_policies_endpoint()
    test_metrics_endpoint()
    test_resolve_endpoint_order_tracking()
    test_resolve_endpoint_ambiguous()
    print("All API tests passed successfully!")
