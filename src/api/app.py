# -*- coding: utf-8 -*-
"""FastAPI REST Service for Arabic Customer Support Resolution Agent."""
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from src.agents.graph import MultiAgentGraph
from src.env.backend_client import BackendClient
from src.policies.retriever import PolicyRetriever
from src.optimization.cache import SemanticCache
from src.config import POLICIES_PATH

app = FastAPI(
    title="Nawras Market Arabic Multi-Agent Support API",
    description="Production REST API for autonomous customer support resolution in Arabic dialects.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
backend_client = BackendClient()
multi_graph = MultiAgentGraph()
retriever = PolicyRetriever()
semantic_cache = SemanticCache(enforce_scope_isolation=True)


class TicketRequest(BaseModel):
    customer_id: str = Field(..., example="C50642")
    text: str = Field(..., example="Salam, je veux savoir l'état de ma commande NW4241472 svp.")
    channel: str = Field("web_chat", example="web_chat")
    ticket_id: Optional[str] = Field(None, example="T_API_001")


class ResolutionResponse(BaseModel):
    ticket_id: str
    outcome: str
    reply: str
    tool_calls: List[Dict[str, Any]]
    steps: int
    latency_sec: float
    cached: bool = False


@app.get("/api/v1/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Arabic Multi-Agent Support Resolution System",
        "version": "1.0.0"
    }


@app.post("/api/v1/resolve", response_model=ResolutionResponse)
def resolve_ticket(req: TicketRequest):
    """Resolve a customer support ticket.
    
    Architectural Guarantees:
    - Scope Isolation: Informational FAQ inquiries check and populate the semantic cache (<1ms).
    - Real-Time Guardrails: Any order-specific inquiry obligatorily bypasses the cache to
      query live backend database states, enforcing server-side time windows and status checks.
    """
    tid = req.ticket_id or f"API_{int(time.time() * 1000)}"

    # 1. Scope Isolation Check: Only general FAQs can be served from cache
    if semantic_cache.is_cacheable(req.text):
        cached_res = semantic_cache.get(req.text)
        if cached_res:
            return ResolutionResponse(
                ticket_id=tid,
                outcome=cached_res.get("outcome", "resolve"),
                reply=cached_res.get("reply", ""),
                tool_calls=[],
                steps=0,
                latency_sec=0.0005,
                cached=True
            )

    # 2. Live Multi-Agent Execution for order inquiries and cache misses
    ticket_dict = {
        "ticket_id": tid,
        "customer_id": req.customer_id,
        "text": req.text,
        "channel": req.channel,
        "category": "standard"
    }

    # Reset backend session state for isolation
    backend_client.reset()

    try:
        trajectory = multi_graph.run(ticket_dict, backend_client)

        # 3. Cache clean informational resolutions (never cache write tools)
        if semantic_cache.is_cacheable(req.text) and not trajectory.get("tool_calls"):
            semantic_cache.set(req.text, trajectory)

        return ResolutionResponse(
            ticket_id=tid,
            outcome=trajectory["outcome"],
            reply=trajectory["reply"],
            tool_calls=trajectory["tool_calls"],
            steps=trajectory["steps"],
            latency_sec=round(trajectory["latency_sec"], 3),
            cached=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/policies")
def get_policies():
    """Retrieve all 15 store policy documents."""
    return retriever.get_all_policies()


@app.get("/api/v1/policies/hash")
def get_policy_hash():
    """Retrieve current policy SHA-256 fingerprint for cache synchronization."""
    return {
        "policy_hash": retriever.get_policy_hash(),
        "count": len(retriever.policies)
    }


@app.get("/api/v1/cache/stats")
def get_cache_stats():
    """Retrieve runtime telemetry on semantic cache scope isolation and hits/misses."""
    return semantic_cache.stats


@app.post("/api/v1/cache/invalidate")
def invalidate_cache():
    """Explicitly invalidate the entire semantic cache."""
    semantic_cache.invalidate_all(reason="admin_requested")
    return {
        "ok": True,
        "message": "Semantic cache successfully invalidated.",
        "current_policy_hash": semantic_cache.current_policy_hash
    }


@app.get("/api/v1/metrics")
def get_metrics():
    """Retrieve benchmark and ablation study summary."""
    report_file = Path("results/ablation_report.json")
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"message": "Ablation report not yet generated."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
