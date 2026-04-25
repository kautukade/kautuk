# kautuk offline coding agent

A local-first autonomous coding assistant for Ollama that simulates a multi-agent workflow:

- **Planner Agent** (`mistral` / `llama3`) for step planning
- **Coder Agent** (`deepseek-coder`) for full file generation
- **Debugger Agent** (`deepseek-coder`) for auto-fix loops
- **Reviewer Agent** (`mistral` / `llama3`) for quality improvements

## Features

- Structured generation contract with `<plan>`, `<reflection>`, `<codebase_analysis>`, `<files>`, `<commands>`, and `<iteration_log>` blocks
- Safe local tools API (`read_file`, `write_file`, `list_files`, `run_command`, `install_package`)
- Destructive command guardrails (blocks risky commands unless explicitly overridden)
- Persistent memory (`conversation_history`, `project_files`, `previous_errors`)
- Execution loop with automatic debugging up to 5 iterations and command timeout protection
- Retrieval-aware file selection so prompts include only relevant codebase context
- Optional streaming progress updates (`--stream`) for incremental visibility

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Prerequisites

```bash
ollama serve
ollama pull deepseek-coder
ollama pull mistral
ollama pull llama3
ollama pull gemma:2b
```

## Usage

```bash
kautuk-agent "Build a FastAPI todo app with tests" --workspace ./output_project --max-iters 5 --stream
```

Optional memory file:

```bash
kautuk-agent "Improve existing project" --workspace ./output_project --memory-file ./agent-memory.json
```

## Model output format

```xml
<spec>
Requirements, constraints, and architecture summary.
</spec>

<plan>
1. Analyze...
2. Implement...
</plan>

<reflection>
Plan quality is acceptable; improve test coverage.
</reflection>

<codebase_analysis>
Current project contains CLI, parser, and tests modules.
</codebase_analysis>

<files>
<file path="app.py">
# full code
</file>
</files>

<commands>
python -m pytest -q
</commands>

<iteration_log>
Generated initial project scaffold and tests.
</iteration_log>
```

The CLI prints JSON with selected models, planner output, review notes, generated files, iteration logs, and memory path.
