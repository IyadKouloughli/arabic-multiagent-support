# -*- coding: utf-8 -*-
"""GraphState definition for LangGraph Multi-Agent Customer Support System."""
from typing import List, Dict, Any, Optional, TypedDict


class GraphState(TypedDict, total=False):
    # --- Input Ticket Data ---
    ticket_id: str
    customer_id: str
    text: str
    channel: str
    created_at: str
    reference_time: str
    order_ids_mentioned: List[str]
    category: str

    # --- Memory Subsystems ---
    customer_profile: Dict[str, Any]
    episodic_traces: List[Dict[str, Any]]

    # --- Triage Agent Outputs ---
    language_variety: str
    variety_code: str
    intent: str
    urgency: str
    risk_level: str
    order_id: Optional[str]
    candidate_order_ids: List[str]

    # --- Policy Agent (RAG) Outputs ---
    relevant_policies: List[Dict[str, Any]]
    policy_ids: List[str]
    policy_context: str

    # --- Action Agent Outputs ---
    tool_calls_executed: List[Dict[str, Any]]
    action_observations: List[Dict[str, Any]]
    pending_action: Optional[Dict[str, Any]]
    step_count: int

    # --- Verifier / Critic Outputs ---
    is_verified: bool
    verifier_feedback: Optional[str]
    requires_hitl: bool
    hitl_reason: Optional[str]
    simulated_reviewer_decision: Optional[str]

    # --- Final Outcome & Response ---
    outcome: str
    reply_must_include: List[str]
    reply_must_not: List[str]
    final_reply: str
    escalation_reason: Optional[str]
