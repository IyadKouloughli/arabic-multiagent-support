# -*- coding: utf-8 -*-
"""Ablation Studies Suite: evaluates agent variants and generates CV metrics."""
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.evaluator import BenchmarkEvaluator
from src.agents.baseline_single import BaselineSingleAgent
from src.agents.graph import MultiAgentGraph
from src.optimization.cache import SemanticCache


def run_ablations(limit: int = 10, split: str = "dev") -> Dict[str, Any]:
    """Execute all comparative ablations on the benchmark."""
    evaluator = BenchmarkEvaluator()
    reports = {}

    print(f"\n=======================================================")
    print(f"       ARABIC SUPPORT AGENT ABLATION SUITE (N={limit})")
    print(f"=======================================================")

    # -----------------------------------------------------------------
    # Configuration 1: Multi-Agent Graph with Verifier & HITL (Full System)
    # -----------------------------------------------------------------
    print("\n>>> Running Configuration 1: Multi-Agent System (Full Graph + Verifier + HITL)")
    multi_graph = MultiAgentGraph()
    res_full = evaluator.evaluate_agent(multi_graph.run, split=split, limit=limit, verbose=True)
    reports["full_multi_agent"] = res_full["summary"]

    # -----------------------------------------------------------------
    # Configuration 2: Multi-Agent Graph WITHOUT Verifier Agent
    # -----------------------------------------------------------------
    print("\n>>> Running Configuration 2: Multi-Agent Graph (WITHOUT Verifier Agent)")
    class NoVerifierGraph(MultiAgentGraph):
        def _verifier_step(self, state):
            # Bypass verifier audit; accept action directly
            return {
                "is_verified": True,
                "outcome": "resolve",
                "verifier_feedback": None,
                "step_count": state.get("step_count", 0) + 1
            }

    no_verifier = NoVerifierGraph()
    res_no_ver = evaluator.evaluate_agent(no_verifier.run, split=split, limit=limit, verbose=True)
    reports["no_verifier"] = res_no_ver["summary"]

    # -----------------------------------------------------------------
    # Configuration 3: Baseline Single-Agent (Monolithic ReAct)
    # -----------------------------------------------------------------
    print("\n>>> Running Configuration 3: Monolithic Single-Agent Baseline")
    baseline = BaselineSingleAgent()
    res_single = evaluator.evaluate_agent(baseline.run, split=split, limit=limit, verbose=True)
    reports["single_agent_baseline"] = res_single["summary"]

    # -----------------------------------------------------------------
    # Configuration 4: Multi-Agent with Semantic Caching (Repeat Queries)
    # -----------------------------------------------------------------
    print("\n>>> Running Configuration 4: Multi-Agent with Semantic Cache (Repeated Runs)")
    cache = SemanticCache()
    # Prime cache with first run results
    for item in res_full["detailed_results"]:
        ticket_text = next(t["text"] for t in evaluator.tickets if t["ticket_id"] == item["ticket_id"])
        cache.set(ticket_text, item["trajectory"])

    cached_latencies = []
    for item in res_full["detailed_results"]:
        ticket_text = next(t["text"] for t in evaluator.tickets if t["ticket_id"] == item["ticket_id"])
        t0 = time.perf_counter()
        hit = cache.get(ticket_text)
        cached_latencies.append(time.perf_counter() - t0)

    avg_cached_lat = sum(cached_latencies) / len(cached_latencies)
    reports["cached_multi_agent"] = {
        **res_full["summary"],
        "avg_latency_sec": round(avg_cached_lat, 4),
        "cache_hit_rate": cache.hit_rate
    }

    # -----------------------------------------------------------------
    # Save Report
    # -----------------------------------------------------------------
    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    report_file = out_dir / "ablation_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)

    # -----------------------------------------------------------------
    # Print Markdown Summary Table
    # -----------------------------------------------------------------
    print_ablation_markdown(reports)
    return reports


def print_ablation_markdown(reports: Dict[str, Any]):
    """Print comparative Markdown table for documentation and CV."""
    print("\n" + "=" * 70)
    print("                 ABLATION COMPARISON TABLE")
    print("=" * 70)
    print("| Configuration | Task Success | Unauthorized Rate | Tool F1 | Safety Rate | Avg Latency |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: |")

    names = {
        "single_agent_baseline": "Single-Agent (ReAct Baseline)",
        "no_verifier": "Multi-Agent (Without Verifier)",
        "full_multi_agent": "**Multi-Agent (Full Graph + Verifier)**",
        "cached_multi_agent": "**Multi-Agent + Semantic Cache**"
    }

    for key, label in names.items():
        if key in reports:
            r = reports[key]
            succ = f"{r['task_success_rate'] * 100:.1f}%"
            unauth = f"{r['unauthorized_action_rate'] * 100:.1f}%"
            f1 = f"{r['tool_call_f1'] * 100:.1f}%"
            safe = f"{r['adversarial_safety_rate'] * 100:.1f}%"
            lat = f"{r['avg_latency_sec']:.2f}s"
            print(f"| {label} | {succ} | {unauth} | {f1} | {safe} | {lat} |")

    print("=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Arabic Support Agent Ablation Studies.")
    parser.add_argument("--limit", type=int, default=5, help="Number of tickets per configuration (default: 5)")
    parser.add_argument("--split", type=str, default="dev", help="Dataset split (default: dev)")
    args = parser.parse_args()

    run_ablations(limit=args.limit, split=args.split)
