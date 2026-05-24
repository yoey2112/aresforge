from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_dashboard import summarize_docs_status, summarize_local_project_dashboard

SERVICE_NAME = "aresforge-hub"


def get_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "local_only": True,
        "boundary_confirmations": [
            "Local-only hub endpoint.",
            "No GitHub calls.",
            "No gh calls.",
            "No network service calls.",
            "No local LLM calls.",
            "No cloud LLM calls.",
            "No Codex calls.",
            "No ChatGPT calls.",
            "No Ollama calls.",
            "No external API calls.",
            "Default bind host is 127.0.0.1.",
        ],
    }


def get_summary(config: AppConfig) -> dict[str, Any]:
    payload = summarize_local_project_dashboard(config)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
        }
    )
    return payload


def get_docs_status(config: AppConfig) -> dict[str, Any]:
    payload = summarize_docs_status(config.repo_root)
    payload.update(
        {
            "ok": True,
            "service": SERVICE_NAME,
            "boundary_confirmations": [
                "Local-only docs status inspection.",
                "No network calls.",
                "No GitHub calls.",
            ],
        }
    )
    return payload
