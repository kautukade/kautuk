from __future__ import annotations

import re
from dataclasses import dataclass


SPEC_PATTERN = re.compile(r"<spec>\n(.*?)\n</spec>", re.DOTALL)
PLAN_PATTERN = re.compile(r"<plan>\n(.*?)\n</plan>", re.DOTALL)
REFLECTION_PATTERN = re.compile(r"<reflection>\n(.*?)\n</reflection>", re.DOTALL)
CODEBASE_ANALYSIS_PATTERN = re.compile(r"<codebase_analysis>\n(.*?)\n</codebase_analysis>", re.DOTALL)
FILE_PATTERN = re.compile(r'<file\s+path="([^"]+)">\n(.*?)\n</file>', re.DOTALL)
COMMANDS_PATTERN = re.compile(r"<commands>\n(.*?)\n</commands>", re.DOTALL)
ITERATION_LOG_PATTERN = re.compile(r"<iteration_log>\n(.*?)\n</iteration_log>", re.DOTALL)


@dataclass
class GeneratedFile:
    path: str
    content: str


@dataclass
class StructuredOutput:
    spec: str
    plan: str
    reflection: str
    codebase_analysis: str
    files: list[GeneratedFile]
    commands: list[str]
    iteration_log: str


def parse_structured_output(raw: str) -> StructuredOutput:
    spec_match = SPEC_PATTERN.search(raw)
    spec = spec_match.group(1).strip() if spec_match else ""
    plan_match = PLAN_PATTERN.search(raw)
    plan = plan_match.group(1).strip() if plan_match else ""
    reflection_match = REFLECTION_PATTERN.search(raw)
    reflection = reflection_match.group(1).strip() if reflection_match else ""
    codebase_analysis_match = CODEBASE_ANALYSIS_PATTERN.search(raw)
    codebase_analysis = codebase_analysis_match.group(1).strip() if codebase_analysis_match else ""

    files = [GeneratedFile(path=path, content=content.rstrip("\n") + "\n") for path, content in FILE_PATTERN.findall(raw)]

    commands_match = COMMANDS_PATTERN.search(raw)
    commands: list[str] = []
    if commands_match:
        commands = [line.strip() for line in commands_match.group(1).splitlines() if line.strip()]

    iteration_log_match = ITERATION_LOG_PATTERN.search(raw)
    iteration_log = iteration_log_match.group(1).strip() if iteration_log_match else ""

    return StructuredOutput(
        spec=spec,
        plan=plan,
        reflection=reflection,
        codebase_analysis=codebase_analysis,
        files=files,
        commands=commands,
        iteration_log=iteration_log,
    )
