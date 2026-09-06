"""
Ollama connectivity client.

Scope right now: check whether a local Ollama instance is reachable and
list the models it has installed. This module intentionally does NOT send
quiz questions or generate answers yet — that lands in Phase 3
(ai/verifier.py + ai/prompts.py) once Phase 2's quiz detector exists to
feed it real question/option data.

No Qt dependency here on purpose, so this stays trivially unit-testable
(see tests/test_ollama.py) and reusable outside the UI layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import requests

from utils.logger import get_logger

logger = get_logger(__name__)

_STATUS_TIMEOUT_SECONDS = 2.0


@dataclass
class OllamaStatus:
    """Result of a single connectivity check against a local Ollama server."""

    online: bool
    models: list[str] = field(default_factory=list)
    error: str | None = None


def get_ollama_status(base_url: str) -> OllamaStatus:
    """
    Query a local Ollama server's `/api/tags` endpoint for health + models.

    Never raises: any network error, timeout, or malformed response is
    captured and returned as an offline OllamaStatus with a short,
    UI-friendly error message rather than propagating an exception.
    """
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        response = requests.get(url, timeout=_STATUS_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()

        models = [
            model.get("name", "")
            for model in data.get("models", [])
            if isinstance(model, dict) and model.get("name")
        ]
        logger.info("Ollama reachable at %s (%d model(s))", base_url, len(models))
        return OllamaStatus(online=True, models=models)

    except requests.exceptions.ConnectionError:
        logger.info("Ollama not reachable at %s", base_url)
        return OllamaStatus(online=False, error="Not running")

    except requests.exceptions.Timeout:
        logger.warning("Ollama status check timed out at %s", base_url)
        return OllamaStatus(online=False, error="Connection timed out")

    except (requests.exceptions.RequestException, ValueError) as exc:
        # ValueError covers response.json() failing on non-JSON bodies.
        logger.warning("Ollama status check failed: %s", exc)
        return OllamaStatus(online=False, error="Unexpected response")

def generate_response(base_url: str, model: str, prompt: str) -> str:
    """
    Send a prompt to the local Ollama server and return the response text.

    Returns an error message if the request fails.
    """
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": f"Provide only the correct and concise answer for the following text. Do not provide explanations or conversational filler:\n\n{prompt}",
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=120.0)
        response.raise_for_status()
        return response.json().get("response", "No response received from model.")
    except Exception as exc:
        logger.error("Ollama generation failed: %s", exc)
        return f"Error: {str(exc)}"
