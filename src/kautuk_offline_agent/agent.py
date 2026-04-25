from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from typing import Callable

from .memory import SessionMemory
from .models import ModelSelection, select_models
from .ollama_client import OllamaClient
from .tools import CommandResult, LocalTooling
from .workspace import StructuredOutput, parse_structured_output

PLANNER_SYSTEM = """You are Planner Agent (mistral/llama3 role). Build concise step-by-step plans."""
CODER_SYSTEM = """You are Coder Agent (deepseek-coder role). Return exactly:
<spec>
...
</spec>
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


@dataclass
class FileChange:
    path: str
    status: str
    diff_preview: str


class OfflineCodingAgent:
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def run(
        self,
        task: str,
        workspace: Path,
        max_iters: int = 5,
        memory_file: Path | None = None,
        progress_callback: Callable[[str], None] | None = None,
        approve_major_changes: bool = False,
        major_change_threshold: int = 10,
        apply_changes_callback: Callable[[list[dict]], bool] | None = None,
    ) -> dict:
        workspace = workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        tooling = LocalTooling(workspace)

        memory_path = memory_file or workspace / ".agent_memory.json"
        memory = SessionMemory.load(memory_path)
        memory.conversation_history.append(task)
        memory.compact()

        models = select_models(task)
        all_files = tooling.list_files(".")
        relevant_files = self._select_relevant_files(task, all_files)
        codebase_snapshot = self._describe_codebase(relevant_files)
        self._emit_progress(progress_callback, "Analyzed codebase and selected relevant files.")
        technical_spec = self._build_spec(task, models, codebase_snapshot)
        self._emit_progress(progress_callback, "Built technical specification.")
        planner_output = self._plan(task, models, memory)
        self._emit_progress(progress_callback, "Generated plan.")
        plan_reflection = self._reflect(models, f"Reflect on this plan and improve it:\n\n{planner_output}")
        self._emit_progress(progress_callback, "Reflected on plan quality.")
        coded = self._code(task, technical_spec, planner_output, models, memory, codebase_snapshot)
        parsed, file_changes = self._materialize(
            coded,
            tooling,
            approve_major_changes=approve_major_changes,
            major_change_threshold=major_change_threshold,
            apply_changes_callback=apply_changes_callback,
        )
        self._emit_progress(progress_callback, "Materialized generated files.")

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
                self._emit_progress(progress_callback, f"Iteration {idx} executed successfully.")
                break

            debug_response = self._debug(task, planner_output, models, memory, failed)
            fix_reflection = self._reflect(
                models,
                "Classify the error type (syntax/runtime/dependency/logic) and evaluate the fix quality.\n\n"
                f"Command: {failed.command}\nOutput:\n{failed.merged_output}",
            )
            memory.conversation_history.append(fix_reflection)
            current_output, debug_changes = self._materialize(
                debug_response,
                tooling,
                apply_changes_callback=apply_changes_callback,
            )
            file_changes.extend(debug_changes)
            self._emit_progress(progress_callback, f"Iteration {idx} failed; applied automated debug fix.")

        review_notes = self._review(task, planner_output, models, memory, tooling.list_files("."))
        self._emit_progress(progress_callback, "Completed review step.")

        memory.project_files = tooling.list_files(".")
        memory.save(memory_path)

        return {
            "models": models,
            "planner_output": planner_output,
            "technical_spec": technical_spec,
            "model_spec": parsed.spec,
            "plan_reflection": plan_reflection,
            "generation_reflection": parsed.reflection,
            "codebase_analysis": parsed.codebase_analysis,
            "review_notes": review_notes,
            "written_files": [generated.path for generated in parsed.files],
            "file_changes": [change.__dict__ for change in file_changes],
            "relevant_files": relevant_files,
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

    def _build_spec(self, task: str, models: ModelSelection, codebase_snapshot: str) -> str:
        prompt = (
            "Create a concise technical specification with requirements, constraints, and architecture.\n\n"
            f"Task:\n{task}\n\n"
            f"Relevant codebase context:\n{codebase_snapshot}\n"
        )
        return self.client.generate(models.planner, prompt, system=PLANNER_SYSTEM)

    def _code(
        self,
        task: str,
        technical_spec: str,
        plan: str,
        models: ModelSelection,
        memory: SessionMemory,
        codebase_snapshot: str,
    ) -> str:
        prompt = (
            f"Task:\n{task}\n\n"
            f"Technical specification:\n{technical_spec}\n\n"
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
    def _materialize(
        raw: str,
        tooling: LocalTooling,
        approve_major_changes: bool = True,
        major_change_threshold: int = 10,
        apply_changes_callback: Callable[[list[dict]], bool] | None = None,
    ) -> tuple[StructuredOutput, list[FileChange]]:
        parsed = parse_structured_output(raw)
        if not parsed.files:
            raise ValueError("Model response did not include any <file> blocks.")
        if len(parsed.files) > major_change_threshold and not approve_major_changes:
            raise ValueError(
                f"Major change detected ({len(parsed.files)} files). "
                "Set approve_major_changes=True to continue."
            )
        pending_changes: list[tuple[str, str, str]] = []
        changes: list[FileChange] = []
        for generated in parsed.files:
            try:
                existing = tooling.read_file(generated.path)
                status = "modified"
            except FileNotFoundError:
                existing = ""
                status = "created"
            diff_lines = list(
                unified_diff(
                    existing.splitlines(),
                    generated.content.splitlines(),
                    fromfile=f"a/{generated.path}",
                    tofile=f"b/{generated.path}",
                    lineterm="",
                    n=2,
                )
            )
            preview = "\n".join(diff_lines[:40])
            changes.append(FileChange(path=generated.path, status=status, diff_preview=preview))
            pending_changes.append((generated.path, generated.content, status))

        if apply_changes_callback is not None:
            approved = apply_changes_callback([change.__dict__ for change in changes])
            if not approved:
                raise ValueError("User declined applying proposed file changes.")

        for path, content, _status in pending_changes:
            tooling.write_file(path, content)
        return parsed, changes

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

    @staticmethod
    def _select_relevant_files(task: str, files: list[str], max_files: int = 25) -> list[str]:
        if not files:
            return []
        keywords = {token for token in task.lower().split() if len(token) > 3}
        scored: list[tuple[int, str]] = []
        for path in files:
            lower_path = path.lower()
            score = sum(1 for keyword in keywords if keyword in lower_path)
            scored.append((score, path))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [path for score, path in scored if score > 0][:max_files]
        if selected:
            return selected
        return files[:max_files]

    @staticmethod
    def _emit_progress(progress_callback: Callable[[str], None] | None, message: str) -> None:
        if progress_callback is not None:
            progress_callback(message)
