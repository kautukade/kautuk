from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import OfflineCodingAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline autonomous coding assistant using Ollama.")
    parser.add_argument("task", help="Natural language coding request.")
    parser.add_argument(
        "--workspace",
        default="generated_project",
        help="Workspace directory where files will be generated.",
    )
    parser.add_argument("--max-iters", type=int, default=3, help="Maximum auto-fix attempts.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    agent = OfflineCodingAgent()
    result = agent.run(task=args.task, workspace=Path(args.workspace), max_iters=args.max_iters)

    serializable = {
        "models": result["models"].__dict__,
        "plan": result["plan"],
        "written_files": result["written_files"],
        "run_results": [r.__dict__ for r in result["run_results"]],
    }
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
