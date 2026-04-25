from __future__ import annotations

import re
from dataclasses import dataclass


PLAN_PATTERN = re.compile(r"<plan>\n(.*?)\n</plan>", re.DOTALL)
FILE_PATTERN = re.compile(r'<file\s+path="([^"]+)">\n(.*?)\n</file>', re.DOTALL)
COMMANDS_PATTERN = re.compile(r"<commands>\n(.*?)\n</commands>", re.DOTALL)


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class StructuredOutput:
    plan: str
    files: list[GeneratedFile]
    commands: list[str]


def parse_structured_output(raw: str) -> StructuredOutput:
    plan_match = PLAN_PATTERN.search(raw)
    plan = plan_match.group(1).strip() if plan_match else ""

    files = [GeneratedFile(path=path, content=content.rstrip("\n") + "\n") for path, content in FILE_PATTERN.findall(raw)]

    commands_match = COMMANDS_PATTERN.search(raw)
    commands: list[str] = []
    if commands_match:
        commands = [line.strip() for line in commands_match.group(1).splitlines() if line.strip()]

    return StructuredOutput(plan=plan, files=files, commands=commands)
