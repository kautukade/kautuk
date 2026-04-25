# kautuk offline coding agent

A local-first autonomous coding assistant that uses Ollama models to:

- analyze natural language requests,
- create a step-by-step implementation plan,
- generate full project files,
- run commands,
- and attempt automatic fixes on failure.

## Model strategy

- `deepseek-coder` for code generation/fixing
- `mistral` (or `llama3` for simple tasks) for planning
- `gemma:2b` reserved for lightweight chat tasks

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Prerequisites

1. Install Ollama.
2. Start Ollama server:

```bash
ollama serve
```

3. Pull models:

```bash
ollama pull deepseek-coder
ollama pull mistral
ollama pull llama3
ollama pull gemma:2b
```

## Usage

```bash
kautuk-agent "Build a Flask todo API with tests" --workspace ./output_project
```

The agent prints JSON summary including selected models, generated files, and command execution results.

## Output contract from code model

The coder model is instructed to return blocks like:

```xml
<file path="app.py">
# full file content
</file>
<run>
python -m pytest -q
</run>
```

This keeps file writes deterministic and enables automated execution + repair loops.
