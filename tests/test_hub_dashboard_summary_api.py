from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import post_active_project, post_project, post_project_repo, post_queue_item
from aresforge.hub.server import _build_handler


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def _start_server(config: AppConfig) -> tuple[ThreadingHTTPServer, threading.Thread]:
    static_root = Path(__file__).resolve().parents[1] / "src" / "aresforge" / "hub" / "static"
    handler = _build_handler(config, static_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request_json(port: int, path: str) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))
    finally:
        connection.close()


def test_get_dashboard_summary_route_returns_stable_read_only_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    server, thread = _start_server(config)
    try:
        status, payload = _request_json(int(server.server_address[1]), "/api/dashboard/summary")
        assert status == 200
        assert payload["ok"] is True
        assert payload["dashboard_type"] == "hub_home"
        assert payload["read_only"] is True
        assert "project_summary" in payload
        assert "queue_summary" in payload
        assert "agent_lane_summary" in payload
        assert "repo_summary" in payload
        assert isinstance(payload["blockers"], list)
        assert isinstance(payload["warnings"], list)
        assert isinstance(payload["next_safe_action"], str)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_dashboard_summary_route_includes_active_project_and_queue_counts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert post_project(
        config,
        {
            "project_id": "aresforge",
            "name": "AresForge",
            "root_path": str(tmp_path),
            "status": "active",
        },
    )["ok"]
    assert post_project_repo(
        config,
        "aresforge",
        {
            "repo_id": "aresforge-primary",
            "name": "AresForge Repo",
            "path": str(tmp_path),
            "role": "primary",
            "status": "active",
        },
    )["ok"]
    assert post_active_project(config, {"project_id": "aresforge"})["ok"]
    assert post_queue_item(
        config,
        {
            "item_id": "q1",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Task 1",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
        },
    )["ok"]

    server, thread = _start_server(config)
    try:
        status, payload = _request_json(int(server.server_address[1]), "/api/dashboard/summary")
        assert status == 200
        assert payload["ok"] is True
        assert payload["project_summary"]["active_project_id"] == "aresforge"
        assert payload["queue_summary"]["total_items"] == 1
        assert payload["queue_summary"]["counts_by_status"]["ready"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
