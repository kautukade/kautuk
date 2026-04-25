from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class OllamaError(RuntimeError):
    """Raised when an Ollama call fails."""


@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 300

    def generate(self, model: str, prompt: str, system: str | None = None) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Could not reach Ollama. Ensure `ollama serve` is running on localhost:11434."
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned invalid JSON.") from exc

        text = body.get("response", "").strip()
        if not text:
            raise OllamaError("Ollama returned an empty response.")
        return text
