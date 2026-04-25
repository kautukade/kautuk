from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def merged_output(self) -> str:
        return (self.stdout + "\n" + self.stderr).strip()


class LocalTooling:
    """Local toolset used by the agent; mirrors the expected tool contract."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def _safe_path(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        if self.workspace not in candidate.parents and candidate != self.workspace:
            raise ValueError(f"Path escapes workspace: {path}")
        return candidate

    def read_file(self, path: str) -> str:
        return self._safe_path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> Path:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def list_files(self, directory: str = ".") -> list[str]:
        root = self._safe_path(directory)
        if not root.exists():
            return []
        return sorted(
            str(path.relative_to(self.workspace))
            for path in root.rglob("*")
            if path.is_file()
        )

    def run_command(self, command: str) -> CommandResult:
        completed = subprocess.run(
            command,
            cwd=self.workspace,
            shell=True,
            capture_output=True,
            text=True,
        )
        return CommandResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def install_package(self, package: str) -> CommandResult:
        return self.run_command(f"python -m pip install {package}")
