from __future__ import annotations

import re
from dataclasses import dataclass


PLAN_PATTERN = re.compile(r"<plan>\n(.*?)\n</plan>", re.DOTALL)
REFLECTION_PATTERN = re.compile(r"<reflection>\n(.*?)\n</reflection>", re.DOTALL)
FILE_PATTERN = re.compile(r'<file\s+path="([^"]+)">\n(.*?)\n</file>', re.DOTALL)
COMMANDS_PATTERN = re.compile(r"<commands>\n(.*?)\n</commands>", re.DOTALL)
ITERATION_LOG_PATTERN = re.compile(r"<iteration_log>\n(.*?)\n</iteration_log>", re.DOTALL)


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class StructuredOutput:
    plan: str
    reflection: str
    files: list[GeneratedFile]
    commands: list[str]
    iteration_log: str


def parse_structured_output(raw: str) -> StructuredOutput:
    plan_match = PLAN_PATTERN.search(raw)
    plan = plan_match.group(1).strip() if plan_match else ""
    reflection_match = REFLECTION_PATTERN.search(raw)
    reflection = reflection_match.group(1).strip() if reflection_match else ""

    files = [GeneratedFile(path=path, content=content.rstrip("\n") + "\n") for path, content in FILE_PATTERN.findall(raw)]

    commands_match = COMMANDS_PATTERN.search(raw)
    commands: list[str] = []
    if commands_match:
        commands = [line.strip() for line in commands_match.group(1).splitlines() if line.strip()]

    iteration_log_match = ITERATION_LOG_PATTERN.search(raw)
    iteration_log = iteration_log_match.group(1).strip() if iteration_log_match else ""

    return StructuredOutput(
        plan=plan,
        reflection=reflection,
        files=files,
        commands=commands,
        iteration_log=iteration_log,
    )
