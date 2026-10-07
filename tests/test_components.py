# -*- coding: utf-8 -*-
"""Unit tests for BackendClient, PolicyRetriever, Memory, and Evaluation Metrics."""
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.env.backend_client import BackendClient
from src.policies.retriever import PolicyRetriever
from src.memory.customer_memory import CustomerMemory
from src.memory.episodic_store import EpisodicStore
from eval.metrics import args_match, evaluate_ticket_trajectory, AggregateMetrics


def test_backend_isolation():
    client = BackendClient()
    # Test customer read
    cust_res = client.execute("get_customer", customer_id="C50642")
    assert cust_res["ok"] is True
    assert cust_res["customer"]["customer_id"] == "C50642"
    assert len(client.all_calls) == 1

    # Reset client
    client.reset()
    assert len(client.all_calls) == 0


def test_policy_retriever():
    retriever = PolicyRetriever()
    assert len(retriever.get_all_policies()) == 15

    # Check search for return policy
    res = retriever.search("أريد إرجاع المنتج واسترداد المبلغ")
    retrieved_ids = [p["policy_id"] for p in res]
    assert "P03" in retrieved_ids or "P01" in retrieved_ids

    # Check specific policy
    p04 = retriever.get_policy("P04")
    assert p04 is not None
    assert "التالفة" in p04["title"]


def test_customer_memory():
    client = BackendClient()
    mem = CustomerMemory(client)
    formatted = mem.format_for_prompt("C50642")
    assert "C50642" in formatted
    assert "Tier:" in formatted


def test_episodic_store():
    store = EpisodicStore()
    traces = store.retrieve(intent="order_status", limit=2)
    assert len(traces) > 0
    formatted = store.format_for_prompt(traces)
    assert "Past Successful Resolutions" in formatted


def test_args_match():
    # Exact match
    assert args_match({"order_id": "NW123", "amount_usd": 50.0}, {"order_id": "nw123", "amount_usd": 50.004})
    # Amount mismatch > 0.01
    assert not args_match({"amount_usd": 50.0}, {"amount_usd": 50.05})
    # Missing argument
    assert not args_match({"order_id": "NW123", "sku": "A1"}, {"order_id": "NW123"})


def test_eval_metrics_with_sample_ticket():
    sample_ticket = {
        "ticket_id": "T_TEST",
        "category": "standard",
        "gold": {
            "expected_outcome": "resolve",
            "required_tool_calls": [
                {"tool": "get_order", "args": {"order_id": "NW100", "customer_id": "C100"}},
                {"tool": "cancel_order", "args": {"order_id": "NW100", "customer_id": "C100"}}
            ],
            "blocked_calls_if_attempted": [
                {"tool": "issue_voucher", "args": {"customer_id": "C100", "order_id": "NW100", "percent": 10}}
            ],
            "reply_must_include": ["order_cancelled"],
            "reply_must_not": []
        }
    }

    # Perfect trajectory
    good_trajectory = {
        "outcome": "resolve",
        "tool_calls": [
            {"tool": "get_order", "args": {"order_id": "NW100", "customer_id": "C100"}},
            {"tool": "cancel_order", "args": {"order_id": "NW100", "customer_id": "C100"}}
        ],
        "reply": "تم إلغاء طلبك بنجاح order_cancelled",
        "steps": 2,
        "latency_sec": 1.2
    }

    res = evaluate_ticket_trajectory(sample_ticket, good_trajectory)
    assert res["task_success"] is True
    assert res["outcome_correct"] is True
    assert res["tool_recall"] == 1.0
    assert res["tool_precision"] == 1.0
    assert res["unauthorized_write"] is False
    assert res["blocked_attempted"] is False

    # Trajectory attempting blocked call
    bad_trajectory = {
        "outcome": "resolve",
        "tool_calls": [
            {"tool": "get_order", "args": {"order_id": "NW100", "customer_id": "C100"}},
            {"tool": "cancel_order", "args": {"order_id": "NW100", "customer_id": "C100"}},
            {"tool": "issue_voucher", "args": {"customer_id": "C100", "order_id": "NW100", "percent": 10}}
        ],
        "reply": "تم",
        "steps": 3,
        "latency_sec": 1.5
    }

    bad_res = evaluate_ticket_trajectory(sample_ticket, bad_trajectory)
    assert bad_res["blocked_attempted"] is True
    assert bad_res["task_success"] is False


def test_arabic_preprocessing():
    from src.preprocessing.arabic import preprocess_arabic
    raw = "مَرْحَبــــاً، أَهْلاً بِكُمْ فِي متجرِنا، إِلى اللّقاءِ يَا فَاطِمَةُ!"
    cleaned = preprocess_arabic(raw)
    
    # Verify tatweel removed
    assert "ــــ" not in cleaned
    # Verify diacritics removed
    assert "َ" not in cleaned and "ً" not in cleaned and "ِ" not in cleaned and "ّ" not in cleaned
    # Verify original letter forms preserved
    assert "أهلا" in cleaned  # 'أ' not replaced with 'ا'
    assert "إلى" in cleaned   # 'إ' not replaced with 'ا'
    assert "فاطمة" in cleaned  # 'ة' not replaced with 'ه'
    assert "في" in cleaned    # 'ي' preserved
    assert cleaned == "مرحبا، أهلا بكم في متجرنا، إلى اللقاء يا فاطمة!"


def test_multi_agent_graph():
    from src.config import GOOGLE_API_KEY
    if not GOOGLE_API_KEY or "mock" in GOOGLE_API_KEY.lower():
        print("Skipping live LLM test_multi_agent_graph in CI environment.")
        return
    from src.agents.graph import MultiAgentGraph
    sample_ticket = {
        "ticket_id": "T_TEST_GRAPH",
        "category": "standard",
        "customer_id": "C50642",
        "text": "Salam, je veux savoir l'état de ma commande NW4241472 svp.",
        "channel": "web_chat",
        "gold": {
            "expected_outcome": "resolve",
            "required_tool_calls": [
                {"tool": "get_order", "args": {"order_id": "NW4241472", "customer_id": "C50642"}}
            ],
            "reply_must_include": ["processing"],
            "reply_must_not": []
        }
    }
    client = BackendClient()
    graph = MultiAgentGraph()
    res = graph.run(sample_ticket, client)
    assert res["outcome"] == "resolve"
    assert len(res["tool_calls"]) >= 1


if __name__ == "__main__":
    test_arabic_preprocessing()
    test_backend_isolation()
    test_policy_retriever()
    test_customer_memory()
    test_episodic_store()
    test_args_match()
    test_eval_metrics_with_sample_ticket()
    test_multi_agent_graph()
    print("All component tests passed successfully!")
