# -*- coding: utf-8 -*-
"""Oracle Replay Agent: replays gold actions to calibrate and verify the evaluation harness."""
from typing import Dict, Any
from src.env.backend_client import BackendClient


def oracle_agent_runner(ticket: Dict[str, Any], backend: BackendClient) -> Dict[str, Any]:
    """Executes the exact gold trajectory defined in the benchmark ticket.
    
    Used to establish the empirical 100% ceiling and verify that the evaluation
    harness accurately recognizes perfect resolutions.
    """
    gold = ticket.get("gold", {})
    expected_outcome = gold.get("expected_outcome", "resolve")
    required_calls = gold.get("required_tool_calls", [])
    reply_must_include = gold.get("reply_must_include", [])

    # Execute all required tool calls
    for call in required_calls:
        tool_name = call["tool"]
        args = dict(call.get("args", {}))
        
        res = backend.execute(tool_name, **args)
        
        # If refund requires approval and simulated reviewer approves, resume
        if tool_name == "issue_refund" and res.get("status") == "PENDING_APPROVAL":
            if gold.get("simulated_reviewer_decision") == "approve":
                backend.execute("issue_refund", approved=True, **args)

    # Synthesize compliant reply mentioning all required facts
    reply_facts = " ".join(fact.split("=")[-1].replace("_", " ") for fact in reply_must_include)
    reply_text = f"تم التعامل مع طلبك بنجاح. التفاصيل: {reply_facts}"

    return {
        "outcome": expected_outcome,
        "tool_calls": list(backend.all_calls),
        "reply": reply_text,
        "steps": len(required_calls),
        "latency_sec": 0.01
    }
