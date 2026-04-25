from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .memory import SessionMemory
from .models import ModelSelection, select_models
from .ollama_client import OllamaClient
from .tools import CommandResult, LocalTooling
from .workspace import StructuredOutput, parse_structured_output

PLANNER_SYSTEM = """You are Planner Agent (mistral/llama3 role). Build concise step-by-step plans."""
CODER_SYSTEM = """You are Coder Agent (deepseek-coder role). Return exactly:
<plan>
...
</plan>
<reflection>
...
</reflection>
<codebase_analysis>
...
</codebase_analysis>
<files>
<file path=\"relative/path\">\nfull content\n</file>
</files>
<commands>
command one
command two
</commands>
<iteration_log>
short generation summary
</iteration_log>
Rules: produce full files, include comments, error handling, and modular architecture.
"""
DEBUGGER_SYSTEM = """You are Debugger Agent (deepseek-coder role). Fix failing code using error logs. Return same structured format."""
REVIEWER_SYSTEM = """You are Reviewer Agent (mistral/llama3 role). Suggest quality/scalability improvements in short bullets."""
REFLECTION_SYSTEM = """You are Reflection Agent. Evaluate output quality, identify weaknesses, and suggest immediate improvements."""


@dataclass
class IterationLog:
    iteration: int
    command: str
    ok: bool
    output: str


class OfflineCodingAgent:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def run(
        self,
        task: str,
        workspace: Path,
        max_iters: int = 5,
        memory_file: Path | None = None,
    ) -> dict:
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        tooling = LocalTooling(workspace)

        memory_path = memory_file or workspace / ".agent_memory.json"
        memory = SessionMemory.load(memory_path)
        memory.conversation_history.append(task)
        memory.compact()

        models = select_models(task)
        codebase_snapshot = self._describe_codebase(tooling.list_files("."))
        planner_output = self._plan(task, models, memory)
        plan_reflection = self._reflect(models, f"Reflect on this plan and improve it:\n\n{planner_output}")
        coded = self._code(task, planner_output, models, memory, codebase_snapshot)
        parsed = self._materialize(coded, tooling)

        iteration_logs: list[IterationLog] = []
        current_output = parsed

        for idx in range(1, max_iters + 1):
            if not current_output.commands:
                break

            failed: CommandResult | None = None
            for command in current_output.commands:
                result = tooling.run_command(command)
                iteration_logs.append(
                    IterationLog(
                        iteration=idx,
                        command=command,
                        ok=result.ok,
                        output=result.merged_output,
                    )
                )
                if not result.ok:
                    failed = result
                    memory.previous_errors.append(result.merged_output)
                    break

            if failed is None:
                break

            debug_response = self._debug(task, planner_output, models, memory, failed)
            fix_reflection = self._reflect(
                models,
                "Classify the error type (syntax/runtime/dependency/logic) and evaluate the fix quality.\n\n"
                f"Command: {failed.command}\nOutput:\n{failed.merged_output}",
            )
            memory.conversation_history.append(fix_reflection)
            current_output = self._materialize(debug_response, tooling)

        review_notes = self._review(task, planner_output, models, memory, tooling.list_files("."))

        memory.project_files = tooling.list_files(".")
        memory.save(memory_path)

        return {
            "models": models,
            "planner_output": planner_output,
            "plan_reflection": plan_reflection,
            "generation_reflection": parsed.reflection,
            "codebase_analysis": parsed.codebase_analysis,
            "review_notes": review_notes,
            "written_files": [generated.path for generated in parsed.files],
            "iterations": iteration_logs,
            "model_iteration_log": parsed.iteration_log,
            "memory_file": str(memory_path),
        }

    def _plan(self, task: str, models: ModelSelection, memory: SessionMemory) -> str:
        prompt = (
            "Analyze request and propose a step-by-step plan under 10 steps.\n"
            f"Task:\n{task}\n\n"
            f"Previous errors:\n{memory.previous_errors[-3:]}\n"
        )
        return self.client.generate(models.planner, prompt, system=PLANNER_SYSTEM)

    def _code(
        self,
        task: str,
        plan: str,
        models: ModelSelection,
        memory: SessionMemory,
        codebase_snapshot: str,
    ) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Planner Notes:\n{plan}\n\n"
            f"Known project files:\n{memory.project_files}\n\n"
            f"Codebase snapshot:\n{codebase_snapshot}\n\n"
            f"Conversation summary:\n{memory.conversation_summary}\n\n"
            "Generate exactly two implementation approaches, compare them briefly, then choose one and implement it.\n"
            "Use required structured format."
        )
        return self.client.generate(models.coder, prompt, system=CODER_SYSTEM)

    def _debug(
        self,
        task: str,
        plan: str,
        models: ModelSelection,
        memory: SessionMemory,
        failed: CommandResult,
    ) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Failed command:\n{failed.command}\n\n"
            f"Error:\n{failed.merged_output}\n\n"
            f"Error type guess:\n{self._classify_error(failed.merged_output)}\n\n"
            f"Recent errors:\n{memory.previous_errors[-5:]}\n\n"
            "Fix all root causes and return full files + commands."
        )
        return self.client.generate(models.coder, prompt, system=DEBUGGER_SYSTEM)

    def _review(
        self,
        task: str,
        plan: str,
        models: ModelSelection,
        memory: SessionMemory,
        files: list[str],
    ) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Files generated:\n{files}\n\n"
            f"Memory errors:\n{memory.previous_errors[-3:]}\n\n"
            "Provide concise quality review and next improvements."
        )
        return self.client.generate(models.planner, prompt, system=REVIEWER_SYSTEM)

    @staticmethod
    def _materialize(raw: str, tooling: LocalTooling) -> StructuredOutput:
        parsed = parse_structured_output(raw)
        if not parsed.files:
            raise ValueError("Model response did not include any <file> blocks.")
        for generated in parsed.files:
            tooling.write_file(generated.path, generated.content)
        return parsed

    def _reflect(self, models: ModelSelection, content: str) -> str:
        return self.client.generate(models.planner, content, system=REFLECTION_SYSTEM)

    @staticmethod
    def _classify_error(error_output: str) -> str:
        lowered = error_output.lower()
        if "syntaxerror" in lowered or "invalid syntax" in lowered:
            return "syntax"
        if "no module named" in lowered or "not found" in lowered:
            return "dependency"
        if "traceback (most recent call last)" in lowered or "exception" in lowered:
            return "runtime"
        return "logic"

    @staticmethod
    def _describe_codebase(files: list[str], max_files: int = 40) -> str:
        if not files:
            return "No files detected."
        sample = files[:max_files]
        suffix = "" if len(files) <= max_files else f"\n...and {len(files) - max_files} more files."
        return "\n".join(sample) + suffix
