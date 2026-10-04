# -*- coding: utf-8 -*-
"""FastAPI REST Service for Arabic Customer Support Resolution Agent."""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.agents.graph import MultiAgentGraph
from src.env.backend_client import BackendClient
from src.policies.retriever import PolicyRetriever
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
    """Resolve a customer support ticket end-to-end through the LangGraph multi-agent pipeline."""
    tid = req.ticket_id or f"API_{int(Path().stat().st_mtime)}"
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
        return ResolutionResponse(
            ticket_id=tid,
            outcome=trajectory["outcome"],
            reply=trajectory["reply"],
            tool_calls=trajectory["tool_calls"],
            steps=trajectory["steps"],
            latency_sec=round(trajectory["latency_sec"], 3)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/policies")
def get_policies():
    """Retrieve all 15 store policy documents."""
    return retriever.get_all_policies()


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
