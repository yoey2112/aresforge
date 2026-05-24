from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
import webbrowser

from aresforge.config import AppConfig
from aresforge.hub.api import get_docs_status, get_health, get_summary

_DEFAULT_MIME_TYPE = "application/octet-stream"


def _is_loopback_host(host: str) -> bool:
    value = host.strip().lower()
    return value in {"127.0.0.1", "localhost", "::1"}


def _render_json(handler: BaseHTTPRequestHandler, status_code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    return _DEFAULT_MIME_TYPE


def _build_handler(config: AppConfig, static_root: Path) -> type[BaseHTTPRequestHandler]:
    class HubRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/health":
                _render_json(self, HTTPStatus.OK, get_health())
                return
            if path == "/api/summary":
                _render_json(self, HTTPStatus.OK, get_summary(config))
                return
            if path == "/api/docs/status":
                _render_json(self, HTTPStatus.OK, get_docs_status(config))
                return
            if path.startswith("/api/"):
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "error": "unknown_api_endpoint",
                        "path": path,
                    },
                )
                return

            requested = "index.html" if path in {"", "/", "/index.html"} else unquote(path.lstrip("/"))
            candidate = (static_root / requested).resolve()
            if not str(candidate).startswith(str(static_root.resolve())) or not candidate.exists() or not candidate.is_file():
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "error": "static_asset_not_found",
                        "path": path,
                    },
                )
                return

            data = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", _guess_content_type(candidate))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return HubRequestHandler


def serve_hub(
    config: AppConfig,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
) -> dict[str, Any]:
    static_root = (Path(__file__).resolve().parent / "static").resolve()
    handler = _build_handler(config, static_root)
    server = ThreadingHTTPServer((host, port), handler)

    url_host = "127.0.0.1" if host == "0.0.0.0" else host
    hub_url = f"http://{url_host}:{port}/"

    browser_opened = False
    browser_warning: str | None = None
    if open_browser:
        if _is_loopback_host(url_host):
            browser_opened = bool(webbrowser.open(hub_url))
        else:
            browser_warning = "--open-browser ignored because host is not loopback/localhost."

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    payload = {
        "command": "serve-hub",
        "ok": True,
        "local_only": True,
        "host": host,
        "port": port,
        "url": hub_url,
        "open_browser": open_browser,
        "browser_opened": browser_opened,
        "boundary_confirmations": [
            "Local-only server for hub UI.",
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
    if browser_warning:
        payload["warning"] = browser_warning
    return payload
