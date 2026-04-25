from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class SessionMemory:
    conversation_history: list[str] = field(default_factory=list)
    project_files: list[str] = field(default_factory=list)
    previous_errors: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "SessionMemory":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            conversation_history=list(data.get("conversation_history", [])),
            project_files=list(data.get("project_files", [])),
            previous_errors=list(data.get("previous_errors", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
