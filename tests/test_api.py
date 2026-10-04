# -*- coding: utf-8 -*-
"""Unit and Integration tests for FastAPI endpoints."""
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.app import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_policies_endpoint():
    response = client.get("/api/v1/policies")
    assert response.status_code == 200
    policies = response.json()
    assert isinstance(policies, list)
    assert len(policies) == 15
    policy_ids = [p["policy_id"] for p in policies]
    assert "P01" in policy_ids
    assert "P15" in policy_ids


def test_metrics_endpoint():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "full_multi_agent" in data or "message" in data


def test_resolve_endpoint_order_tracking():
    # Test an Algerian ticket with mixed French
    payload = {
        "customer_id": "C50642",
        "text": "Salam, je veux savoir l'état de ma commande NW4241472 svp.",
        "channel": "web_chat",
        "ticket_id": "T_API_TEST_01"
    }
    response = client.post("/api/v1/resolve", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["ticket_id"] == "T_API_TEST_01"
    assert res["outcome"] in ["resolve", "escalate", "clarify"]
    assert len(res["reply"]) > 0
    assert isinstance(res["tool_calls"], list)
    assert res["latency_sec"] >= 0.0


def test_resolve_endpoint_ambiguous():
    # Test ambiguous ticket requesting order status without order ID
    payload = {
        "customer_id": "C65751",
        "text": "مرحباً، أود الاستفسار عن حالة طلبي، فلم يصلني أي تحديث منذ فترة.",
        "channel": "web_chat",
        "ticket_id": "T_API_TEST_02"
    }
    response = client.post("/api/v1/resolve", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["outcome"] in ["clarify", "resolve"]
    assert len(res["reply"]) > 0


if __name__ == "__main__":
    test_health_endpoint()
    test_policies_endpoint()
    test_metrics_endpoint()
    test_resolve_endpoint_order_tracking()
    test_resolve_endpoint_ambiguous()
    print("All API tests passed successfully!")
