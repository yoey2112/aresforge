from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.hub.api import post_active_project, post_project, post_project_repo
from aresforge.hub.server import _build_handler
from aresforge.operator.local_project_queue import resolve_project_queue_path


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


def _request_json(
    port: int,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        payload = None if body is None else json.dumps(body)
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        decoded = json.loads(response.read().decode("utf-8"))
        return response.status, decoded
    finally:
        connection.close()


def _seed_active_project(config: AppConfig, repo_root: Path) -> None:
    assert post_project(
        config,
        {
            "project_id": "aresforge",
            "name": "AresForge",
            "root_path": str(repo_root),
            "status": "active",
        },
    )["ok"]
    assert post_project_repo(
        config,
        "aresforge",
        {
            "repo_id": "aresforge-primary",
            "name": "AresForge Primary",
            "path": str(repo_root),
            "role": "primary",
            "status": "active",
        },
    )["ok"]
    assert post_active_project(config, {"project_id": "aresforge"})["ok"]


def test_local_hub_operator_workflow_is_advisory_and_prompt_pack_safe(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])

        dashboard_status, dashboard = _request_json(port, "GET", "/api/dashboard/summary")
        assert dashboard_status == 200
        assert dashboard["ok"] is True
        assert dashboard["read_only"] is True
        assert dashboard["project_summary"]["active_project_id"] == "aresforge"

        active_status, active_project = _request_json(port, "GET", "/api/projects/active")
        assert active_status == 200
        assert active_project["ok"] is True
        assert active_project["active_project_selected"] is True
        assert active_project["active_repo_id"] == "aresforge-primary"

        create_status, created = _request_json(
            port,
            "POST",
            "/api/local-queue/items",
            {
                "title": "Validate local Hub operator workflow",
                "description": "Exercise the local-only Hub path from dashboard through reports.",
                "item_type": "validation",
                "priority": "high",
                "source": "m45_end_to_end_test",
                "requested_outcome": "The operator can inspect, review, and generate prompts without execution.",
                "acceptance_criteria": [
                    "Dashboard remains read-only",
                    "Readiness is advisory",
                    "Prompt pack generation does not start or complete queue work",
                ],
                "validation_notes": ["Run targeted Hub workflow tests"],
                "tags": ["m45", "operator-workflow"],
            },
        )
        assert create_status == 200
        assert created["ok"] is True
        assert created["local_only"] is True
        assert created["project_id"] == "aresforge"
        assert created["repo_id"] == "aresforge-primary"
        item_id = created["item_id"]

        detail_status, detail = _request_json(port, "GET", f"/api/queue/{item_id}")
        assert detail_status == 200
        assert detail["ok"] is True
        assert detail["item"]["status"] == "proposed"
        assert detail["item"]["source"] == "m45_end_to_end_test"
        assert "Requested outcome:" in detail["item"]["notes"]

        readiness_status, readiness = _request_json(port, "GET", f"/api/local-queue/items/{item_id}/readiness")
        assert readiness_status == 200
        assert readiness["ok"] is True
        assert readiness["local_only"] is True
        assert readiness["readiness_status"] == "ready"
        assert readiness["can_start"] is True
        assert any("No mutations performed" in entry for entry in readiness["boundary_confirmations"])

        queue_path = resolve_project_queue_path(config.repo_root, None)
        queue_before_prompt_pack = queue_path.read_text(encoding="utf-8")
        output_path = tmp_path / "artifacts" / "prompt_packs" / "m45-pack.txt"
        pack_status, prompt_pack = _request_json(
            port,
            "POST",
            "/api/local-queue/prompt-pack",
            {
                "item_ids": [item_id],
                "output": str(output_path),
            },
        )
        queue_after_prompt_pack = queue_path.read_text(encoding="utf-8")

        assert pack_status == 200
        assert prompt_pack["ok"] is True
        assert prompt_pack["local_only"] is True
        assert prompt_pack["item_count"] == 1
        assert prompt_pack["items"][0]["item_id"] == item_id
        assert prompt_pack["items"][0]["status"] == "proposed"
        assert "Agent Prompt Pack (Local-Only)" in prompt_pack["prompt_pack"]
        assert "It does not execute Codex, agents, models, GitHub actions, or network calls." in prompt_pack["prompt_pack"]
        assert output_path.exists()
        assert queue_after_prompt_pack == queue_before_prompt_pack

        detail_after_status, detail_after = _request_json(port, "GET", f"/api/queue/{item_id}")
        assert detail_after_status == 200
        assert detail_after["item"]["status"] == "proposed"
        persisted_queue = json.loads(queue_after_prompt_pack)
        persisted_item = next(item for item in persisted_queue["work_items"] if item["item_id"] == item_id)
        assert persisted_item["started_at"] == ""
        assert persisted_item["completed_at"] == ""
        assert persisted_item["completion_commit"] == ""

        report_status, report = _request_json(port, "GET", "/api/local-project-report")
        assert report_status == 200
        assert report["ok"] is True
        assert report["local_only"] is True
        assert report["queue_summary"]["item_count"] == 1
        assert report["queue_summary"]["counts_by_status"]["proposed"] == 1

        summary_status, summary = _request_json(port, "GET", "/api/local-queue-agent-summary")
        assert summary_status == 200
        assert summary["ok"] is True
        assert summary["local_only"] is True
        assert summary["queue_totals"]["item_count"] == 1
        assert summary["queue_totals"]["status_counts"]["proposed"] == 1
        assert summary["items_by_status"]["proposed"][0]["item_id"] == item_id
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
