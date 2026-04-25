from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSelection:
    planner: str
    coder: str
    chat: str


def select_models(task: str) -> ModelSelection:
    """Choose local models for planning/coding/chat based on task complexity."""
    task_lower = task.lower()
    simple = len(task.split()) < 12 and not any(
        keyword in task_lower
        for keyword in ("build", "create", "app", "script", "api", "debug", "refactor")
    )

    if simple:
        return ModelSelection(planner="llama3", coder="deepseek-coder", chat="gemma:2b")

    return ModelSelection(planner="mistral", coder="deepseek-coder", chat="gemma:2b")
