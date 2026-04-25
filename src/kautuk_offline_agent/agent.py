from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .models import ModelSelection, select_models
from .ollama_client import OllamaClient
from .workspace import parse_model_output, write_artifacts

PLANNER_SYSTEM = """You are a senior software architect. Create concise step-by-step implementation plans."""

CODER_SYSTEM = """You are an autonomous coding agent. Output only this XML-like format:
<analysis>short explanation</analysis>
<file path=\"relative/path\">\n...full file content...\n</file>
<file path=\"another/file\">\n...\n</file>
<run>\ncommand to run\n</run>
Rules:
- Always provide complete files, never partial snippets.
- Use clean modular production-ready code.
- Include error handling and comments.
- Emit at least one <file> block.
- Include <run> blocks only for safe local commands.
"""

FIXER_SYSTEM = """You are a debugging assistant. Given command errors, return replacement full files and test commands using the same XML format as requested."""


@dataclass
class IterationResult:
    ok: bool
    command: str
    output: str


class OfflineCodingAgent:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def run(self, task: str, workspace: Path, max_iters: int = 3) -> dict:
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)

        models = select_models(task)
        plan = self._plan(task, models)
        draft = self._implement(task, plan, models)

        parsed = parse_model_output(draft, workspace)
        written_paths = write_artifacts(parsed.artifacts)

        run_results: list[IterationResult] = []
        for command in parsed.run_commands:
            result = self._run_command(command, workspace)
            run_results.append(result)
            if not result.ok:
                for _ in range(max_iters):
                    fix = self._fix(task, plan, models, command, result.output)
                    fix_parsed = parse_model_output(fix, workspace)
                    write_artifacts(fix_parsed.artifacts)
                    rerun = self._run_command(command, workspace)
                    run_results.append(rerun)
                    if rerun.ok:
                        break
                break

        return {
            "models": models,
            "plan": plan,
            "written_files": [str(path.relative_to(workspace)) for path in written_paths],
            "run_results": run_results,
        }

    def _plan(self, task: str, models: ModelSelection) -> str:
        prompt = (
            "Create a practical implementation plan for this coding request. "
            "Keep it under 10 steps.\n\n"
            f"Request:\n{task}\n"
        )
        return self.client.generate(models.planner, prompt, system=PLANNER_SYSTEM)

    def _implement(self, task: str, plan: str, models: ModelSelection) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Plan:\n{plan}\n\n"
            "Now implement. Return full files in the requested XML format."
        )
        return self.client.generate(models.coder, prompt, system=CODER_SYSTEM)

    def _fix(
        self,
        task: str,
        plan: str,
        models: ModelSelection,
        failed_command: str,
        error_output: str,
    ) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Failed command:\n{failed_command}\n\n"
            f"Error output:\n{error_output}\n\n"
            "Provide fixed full files and optionally improved run commands in XML format."
        )
        return self.client.generate(models.coder, prompt, system=FIXER_SYSTEM)

    @staticmethod
    def _run_command(command: str, cwd: Path) -> IterationResult:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
        )
        output = (completed.stdout + "\n" + completed.stderr).strip()
        return IterationResult(ok=completed.returncode == 0, command=command, output=output)
