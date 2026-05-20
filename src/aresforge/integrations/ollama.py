from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from urllib import error, request

from aresforge.config import AppConfig


@dataclass(frozen=True, slots=True)
class OllamaResult:
    ok: bool
    message: str
    response_text: str | None = None


def test_generate(config: AppConfig, prompt: str) -> OllamaResult:
    body = json.dumps(
        {
            "model": config.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{config.ollama_base_url}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        return OllamaResult(
            ok=False,
            message=(
                f"Unable to reach Ollama at {config.ollama_base_url}. "
                "Start Ollama locally or skip this check for now."
            ),
            response_text=str(exc),
        )
    except TimeoutError as exc:
        return OllamaResult(
            ok=False,
            message=(
                f"Ollama at {config.ollama_base_url} did not respond before timeout. "
                "Start or verify the local Ollama service, or skip this check for now."
            ),
            response_text=str(exc),
        )
    except socket.timeout as exc:
        return OllamaResult(
            ok=False,
            message=(
                f"Ollama at {config.ollama_base_url} did not respond before timeout. "
                "Start or verify the local Ollama service, or skip this check for now."
            ),
            response_text=str(exc),
        )
    except Exception as exc:
        return OllamaResult(ok=False, message="Ollama request failed.", response_text=str(exc))
    text = str(payload.get("response", "")).strip()
    return OllamaResult(
        ok=True,
        message=f"Ollama responded successfully with model {config.ollama_model}.",
        response_text=text,
    )
