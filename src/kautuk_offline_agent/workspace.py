from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FILE_PATTERN = re.compile(r'<file\s+path="([^"]+)">\n(.*?)\n</file>', re.DOTALL)
RUN_PATTERN = re.compile(r"<run>\n(.*?)\n</run>", re.DOTALL)


@dataclass
class GeneratedArtifact:
    path: Path
    content: str


@dataclass
class ModelOutput:
    artifacts: list[GeneratedArtifact]
    run_commands: list[str]


def parse_model_output(raw: str, root: Path) -> ModelOutput:
    artifacts: list[GeneratedArtifact] = []
    for relative_path, content in FILE_PATTERN.findall(raw):
        safe_path = (root / relative_path).resolve()
        if root.resolve() not in safe_path.parents and safe_path != root.resolve():
            raise ValueError(f"Blocked path outside workspace: {relative_path}")
        artifacts.append(GeneratedArtifact(path=safe_path, content=content.rstrip("\n") + "\n"))

    run_commands = [command.strip() for command in RUN_PATTERN.findall(raw) if command.strip()]
    return ModelOutput(artifacts=artifacts, run_commands=run_commands)


def write_artifacts(artifacts: Iterable[GeneratedArtifact]) -> list[Path]:
    written: list[Path] = []
    for artifact in artifacts:
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(artifact.content, encoding="utf-8")
        written.append(artifact.path)
    return written
