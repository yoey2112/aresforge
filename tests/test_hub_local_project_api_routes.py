from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
import http.client
from pathlib import Path
import threading

from aresforge.config import AppConfig
from aresforge.hub.server import _build_handler
from aresforge.hub.api import post_active_project, post_project, post_project_repo, post_queue_item


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


def _seed_local_state(config: AppConfig, repo_root: Path) -> None:
    created_project = post_project(
        config,
        {
            "project_id": "aresforge",
            "name": "AresForge",
            "root_path": str(repo_root),
            "status": "active",
            "github_owner": "local",
            "github_repo": "aresforge",
        },
    )
    assert created_project["ok"] is True

    created_repo = post_project_repo(
        config,
        "aresforge",
        {
            "repo_id": "aresforge-primary",
            "name": "AresForge",
            "path": str(repo_root),
            "role": "primary",
            "status": "active",
        },
    )
    assert created_repo["ok"] is True

    selected = post_active_project(config, {"project_id": "aresforge"})
    assert selected["ok"] is True

    for index in range(1, 5):
        queued = post_queue_item(
            config,
            {
                "item_id": f"w{index}",
                "project_id": "aresforge",
                "repo_id": "aresforge-primary",
                "title": f"Work Item {index}",
                "status": "proposed",
                "priority": "normal",
                "item_type": "task",
            },
        )
        assert queued["ok"] is True


def _request_json(port: int, method: str, path: str) -> tuple[int, dict[str, object]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        return response.status, payload
    finally:
        connection.close()


def test_local_project_dashboard_and_report_routes_are_read_only_and_return_local_data(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_local_state(config, tmp_path)

    static_root = Path(__file__).resolve().parents[1] / "src" / "aresforge" / "hub" / "static"
    handler = _build_handler(config, static_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = int(server.server_address[1])

        dashboard_status, dashboard_payload = _request_json(port, "GET", "/api/local-project-dashboard")
        assert dashboard_status == 200
        assert dashboard_payload["local_only"] is True
        assert dashboard_payload["active_project_id"] == "aresforge"
        assert "queue_summary" in dashboard_payload

        report_status, report_payload = _request_json(port, "GET", "/api/local-project-report")
        assert report_status == 200
        assert report_payload["local_only"] is True
        assert report_payload["active_project"]["active_project_id"] == "aresforge"
        assert "queue_summary" in report_payload
        assert report_payload["report_type"] == "local_project_report_summary"

        post_status, post_payload = _request_json(port, "POST", "/api/local-project-dashboard")
        assert post_status == 404
        assert post_payload["ok"] is False
        assert post_payload["error"] == "unknown_api_endpoint"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
