# -*- coding: utf-8 -*-
"""Benchmark Evaluator: runs tickets through an agent and aggregates metrics."""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import TICKETS_PATH
from src.env.backend_client import BackendClient
from eval.metrics import evaluate_ticket_trajectory, AggregateMetrics


class BenchmarkEvaluator:
    """Orchestrates evaluation of support agents against benchmark tickets."""

    def __init__(self, tickets_path: Optional[Path] = None):
        path = tickets_path or TICKETS_PATH
        with open(path, "r", encoding="utf-8") as f:
            self.tickets = [json.loads(line) for line in f if line.strip()]
        self.backend_client = BackendClient()

    def get_split(self, split: str = "dev") -> List[Dict[str, Any]]:
        """Filter tickets by split ('dev' or 'test')."""
        return [t for t in self.tickets if t.get("split") == split]

    def evaluate_agent(
        self,
        agent_runner,
        split: str = "dev",
        limit: Optional[int] = None,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """Run evaluation over a ticket split.
        
        Args:
            agent_runner: Callable taking (ticket: dict, backend: BackendClient) -> trajectory dict.
            split: 'dev' or 'test'.
            limit: Optional maximum number of tickets to evaluate.
            verbose: If True, prints per-ticket progress and summary.
            
        Returns:
            Dictionary with aggregate summary and detailed ticket results.
        """
        eval_tickets = self.get_split(split)
        if limit is not None:
            eval_tickets = eval_tickets[:limit]

        aggregator = AggregateMetrics()
        detailed_results = []

        if verbose:
            print(f"\n==========================================")
            print(f"Starting Benchmark Evaluation: {split} split ({len(eval_tickets)} tickets)")
            print(f"==========================================")

        for idx, ticket in enumerate(eval_tickets, 1):
            tid = ticket.get("ticket_id")
            intent = ticket.get("gold", {}).get("intent")
            category = ticket.get("category")
            
            # Reset mock backend to fresh state for isolation
            self.backend_client.reset()

            start_t = time.perf_counter()
            try:
                trajectory = agent_runner(ticket, self.backend_client)
            except Exception as e:
                trajectory = {
                    "outcome": "error",
                    "tool_calls": list(self.backend_client.all_calls),
                    "reply": f"Agent error: {str(e)}",
                    "steps": 0,
                    "latency_sec": time.perf_counter() - start_t
                }

            if "latency_sec" not in trajectory:
                trajectory["latency_sec"] = time.perf_counter() - start_t
            if "tool_calls" not in trajectory:
                trajectory["tool_calls"] = list(self.backend_client.all_calls)

            # Evaluate trajectory against gold
            eval_res = evaluate_ticket_trajectory(ticket, trajectory)
            aggregator.record(eval_res)
            detailed_results.append({
                "ticket_id": tid,
                "intent": intent,
                "category": category,
                "eval": eval_res,
                "trajectory": trajectory
            })

            if verbose:
                status = "PASS" if eval_res["task_success"] else "FAIL"
                print(f"[{idx:03d}/{len(eval_tickets):03d}] {tid} ({intent} | {category}) -> {status} (exp: {eval_res['expected_outcome']}, got: {eval_res['actual_outcome']})")

        summary = aggregator.summary()

        if verbose:
            print(f"\n==========================================")
            print(f"Evaluation Summary ({split} split, N={len(eval_tickets)}):")
            print(f"Task Success Rate:         {summary['task_success_rate'] * 100:.2f}%")
            print(f"Outcome Accuracy:          {summary['outcome_accuracy'] * 100:.2f}%")
            print(f"Unauthorized Action Rate:  {summary['unauthorized_action_rate'] * 100:.2f}%")
            print(f"Tool-call F1 Score:        {summary['tool_call_f1'] * 100:.2f}%")
            print(f"Adversarial Safety Rate:   {summary['adversarial_safety_rate'] * 100:.2f}%")
            print(f"Avg Latency per ticket:    {summary['avg_latency_sec']}s")
            print(f"==========================================\n")

        return {
            "summary": summary,
            "detailed_results": detailed_results
        }
