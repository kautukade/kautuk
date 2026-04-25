from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class SessionMemory:
    conversation_history: list[str] = field(default_factory=list)
    conversation_summary: str = ""
    project_files: list[str] = field(default_factory=list)
    previous_errors: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "SessionMemory":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            conversation_history=list(data.get("conversation_history", [])),
            conversation_summary=str(data.get("conversation_summary", "")),
            project_files=list(data.get("project_files", [])),
            previous_errors=list(data.get("previous_errors", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def compact(self, max_items: int = 20) -> None:
        if len(self.conversation_history) <= max_items:
            return
        older = self.conversation_history[:-max_items]
        if older:
            self.conversation_summary = f"{self.conversation_summary} {' | '.join(older)}".strip()
        self.conversation_history = self.conversation_history[-max_items:]
