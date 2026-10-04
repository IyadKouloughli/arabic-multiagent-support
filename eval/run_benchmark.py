# -*- coding: utf-8 -*-
"""CLI script to run benchmark evaluations on the Nawras Market dataset."""
import sys
import json
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.evaluator import BenchmarkEvaluator
from eval.oracle_agent import oracle_agent_runner
from src.agents.baseline_single import BaselineSingleAgent


def main():
    parser = argparse.ArgumentParser(description="Evaluate customer support agents on Arabic benchmark.")
    parser.add_argument("--agent", choices=["oracle", "baseline"], default="oracle",
                        help="Agent architecture to evaluate ('oracle' or 'baseline')")
    parser.add_argument("--split", choices=["dev", "test"], default="dev",
                        help="Dataset split to evaluate on (default: 'dev')")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of tickets to evaluate")
    parser.add_argument("--output", type=str, default=None,
                        help="Optional path to save JSON evaluation report")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-ticket logging")

    args = parser.parse_args()

    evaluator = BenchmarkEvaluator()

    if args.agent == "oracle":
        runner = oracle_agent_runner
    elif args.agent == "baseline":
        baseline = BaselineSingleAgent()
        runner = baseline.run
    else:
        raise ValueError(f"Unknown agent type: {args.agent}")

    results = evaluator.evaluate_agent(
        agent_runner=runner,
        split=args.split,
        limit=args.limit,
        verbose=not args.quiet
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Results saved to: {out_path}")


if __name__ == "__main__":
    main()
