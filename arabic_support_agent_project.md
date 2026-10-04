# Arabic-first Customer Support Resolution Agent
### A multi-agent, human-in-the-loop system (agentic AI portfolio project)

---

## 1. The real problem it solves

Banks, telecoms, and e-commerce companies in the Arab world receive thousands of support tickets in MSA and dialects (Algerian, Egyptian, Gulf, etc.), often mixed with French or English. Human agents spend most of their time on repetitive cases such as refunds, plan changes, and order status, and generic chatbots either hallucinate policies or can't take real actions.

This system **resolves tickets end to end**: it reads the ticket, checks policy, calls internal tools, takes the action, and **escalates to a human when the risk is high**.

**Why it is strong for a CV:**
- It is a real business problem with measurable ROI (cost per ticket, resolution time).
- It plays to an Arabic NLP background.
- It is clearly different from a plain RAG chatbot.

---

## 2. Architecture

| Agent | Role |
|---|---|
| **Triage agent** | Detects language and dialect, intent, urgency, and risk level (small, cheap model) |
| **Policy agent** | Retrieves company policies with citations (RAG), abstains if nothing is found |
| **Action agent** | Uses tools: CRM lookup, order/billing API, refund, ticket update (mock APIs with real schemas) |
| **Verifier/critic agent** | Checks that the answer is grounded in the policy and that the planned action is allowed |
| **Supervisor** | Orchestrates the others, enforces step and budget limits |

### Orchestration
LangGraph (state machine with checkpoints). The agent loop is:

**reason → act → observe → update state → repeat** until the ticket is resolved, escalated, or the step budget is exhausted.

### Memory
- **Short-term:** graph state for the current ticket
- **Long-term:** customer history and past resolutions (vector store plus structured DB)
- **Episodic:** past successful resolution traces reused as few-shot examples

### Human-in-the-loop
Actions above a risk threshold (refunds over X, account changes, low verifier confidence) pause the graph with `interrupt`. A reviewer approves, edits, or rejects in a small UI (Streamlit or Gradio), and the graph resumes from the checkpoint. Human decisions are logged and become evaluation data.

---

## 3. How you prove it works (evaluation story)

### 3.1 Build a benchmark
300 to 500 tickets (synthetic generation plus manual verification), with gold labels for intent, correct tool calls, and final outcome. Include:
- dialect variety
- ambiguous tickets
- policy edge cases
- adversarial cases (prompt injection, requests for unauthorized refunds)

### 3.2 Metrics

| Dimension | Metrics |
|---|---|
| Task quality | Task success rate, correct escalation rate, tool-call accuracy (right tool, right arguments) |
| Hallucination | Groundedness/faithfulness against retrieved policy, citation precision, unsupported-claim rate, abstention rate |
| Latency | p50/p95 end-to-end, per-agent latency, steps per ticket |
| Cost | Tokens and $ per ticket, cost per *resolved* ticket |
| Safety | Injection resistance, unauthorized action rate (target: 0) |
| Human load | % auto-resolved, % escalated, human override rate |

### 3.3 Ablations (what impresses interviewers)
- Single agent vs multi-agent
- With vs without the verifier (hallucination drop vs added latency)
- Large model for everything vs **model routing** (small model for triage, large for hard cases)
- With vs without semantic cache and prompt caching
- Sequential vs parallel tool calls

### 3.4 Tooling
- Langfuse or LangSmith for traces
- LLM-as-judge calibrated against a human-labeled subset (report agreement)
- CI regression suite that fails if success rate drops or cost rises

---

## 4. Optimization levers

- **Latency:** streaming, parallel tool calls, small models for triage, capped loop steps
- **Cost:** model routing, prompt caching, semantic cache, trimmed context
- **Hallucination:** forced citations, verifier agent, "I don't know, escalate" path, structured outputs validated with Pydantic

---

## 5. Suggested stack

Python, LangGraph, FastAPI, Pydantic, a vector DB (Qdrant or pgvector), PostgreSQL, Langfuse, Docker, and a cloud deployment.

Use an API model plus an open model (Qwen or Llama) for the routing comparison. Arabic embeddings such as multilingual-e5 or bge-m3 work for retrieval.

---

## 6. Timeline (about 5 weeks)

| Week | Focus |
|---|---|
| **1** | Domain choice, mock APIs, policy documents, ticket dataset |
| **2** | Baseline single agent plus evaluation harness (build this *before* optimizing) |
| **3** | Multi-agent graph, memory, and HITL |
| **4** | Optimization and ablations |
| **5** | Deployment, dashboard, write-up, demo video |

---

## 7. How it reads on your CV

> Built an Arabic-first multi-agent support resolution system (LangGraph) with tool use, long-term memory, and human-in-the-loop approval; evaluated on a 400-ticket benchmark: **X% task success, Y% fewer hallucinated claims via verifier agent, Z% lower cost per ticket via model routing and caching, p95 latency under N s.**

Fill in X, Y, and Z from your own measurements. Real numbers from ablations are what give the project its weight.

---

## 8. Alternatives if you prefer another domain

- **Multi-agent compliance/contract reviewer** (legal or finance documents, high HITL value)
- **Incident-response (SRE) agent** that reads logs and metrics, proposes fixes, and asks approval before executing
- **Loan or KYC document processing agent** (extraction, validation, human review of edge cases)

**Recommendation:** the support agent, because the evaluation is easiest to make rigorous and the Arabic dialect angle is a differentiator.

---

## 9. Possible next steps

- LangGraph state design
- Benchmark dataset format
