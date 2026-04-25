from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import OfflineCodingAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline autonomous coding assistant using Ollama.")
    parser.add_argument("task", help="Natural language coding request.")
    parser.add_argument("--workspace", default="generated_project", help="Directory to generate code into.")
    parser.add_argument("--memory-file", default=None, help="Optional path for persistent memory JSON.")
    parser.add_argument("--stream", action="store_true", help="Print incremental progress updates.")
    parser.add_argument(
        "--max-iters",
        type=int,
        default=5,
        help="Maximum debug iterations (execution loop).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    agent = OfflineCodingAgent()

    result = agent.run(
        task=args.task,
        workspace=Path(args.workspace),
        max_iters=max(1, min(args.max_iters, 5)),
        memory_file=Path(args.memory_file) if args.memory_file else None,
        progress_callback=(lambda msg: print(f"[progress] {msg}")) if args.stream else None,
    )

    serializable = {
        "models": result["models"].__dict__,
        "planner_output": result["planner_output"],
        "plan_reflection": result["plan_reflection"],
        "generation_reflection": result["generation_reflection"],
        "codebase_analysis": result["codebase_analysis"],
        "review_notes": result["review_notes"],
        "written_files": result["written_files"],
        "relevant_files": result["relevant_files"],
        "iterations": [entry.__dict__ for entry in result["iterations"]],
        "model_iteration_log": result["model_iteration_log"],
        "memory_file": result["memory_file"],
    }
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
