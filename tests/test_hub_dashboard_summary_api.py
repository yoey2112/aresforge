from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import post_active_project, post_project, post_project_repo, post_queue_item
from aresforge.hub.server import _build_handler
from aresforge.operator.local_project_queue import capture_local_queue_completion_evidence
from aresforge.operator.local_project_report import read_local_project_reports


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


def test_get_project_progress_rollup_route_returns_read_only_counts(tmp_path: Path) -> None:
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
            "item_id": "rollup-ready",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Ready task",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "assigned_agent": "coding-agent",
        },
    )["ok"]
    assert post_queue_item(
        config,
        {
            "item_id": "rollup-blocked",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Blocked task",
            "status": "blocked",
            "priority": "high",
            "item_type": "bug",
            "assigned_agent": "reviewer-agent",
        },
    )["ok"]

    server, thread = _start_server(config)
    try:
        status, payload = _request_json(int(server.server_address[1]), "/api/projects/aresforge/progress-rollup")
        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["read_only"] is True
        assert payload["project_id"] == "aresforge"
        assert payload["active_project"] is True
        assert payload["total_queue_items"] == 2
        assert payload["items_by_status"]["ready"] == 1
        assert payload["items_by_status"]["blocked"] == 1
        assert payload["items_by_type"]["task"] == 1
        assert payload["items_by_lane"]["coding-agent"] == 1
        assert payload["ready_item_count"] == 1
        assert payload["blocked_item_count"] == 1
        assert payload["items_with_evidence_captured_count"] == 0
        assert payload["items_eligible_for_closeout_count"] == 0
        assert payload["closed_completed_item_count"] == 0
        assert payload["blockers"] == ["Queue item rollup-blocked is blocked: Blocked task"]
        assert payload["future_routing_metadata"]["implemented"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_project_progress_rollup_route_returns_not_found_for_missing_project(tmp_path: Path) -> None:
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

    server, thread = _start_server(config)
    try:
        status, payload = _request_json(int(server.server_address[1]), "/api/projects/missing/progress-rollup")
        assert status == 404
        assert payload["ok"] is False
        assert payload["error"] == "managed_project_not_found"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_read_local_project_reports_returns_reports_v1_with_progress_and_evidence(tmp_path: Path) -> None:
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
            "item_id": "reports-ready",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Ready report task",
            "status": "ready",
            "priority": "high",
            "item_type": "task",
            "assigned_agent": "coding-agent",
        },
    )["ok"]
    assert post_queue_item(
        config,
        {
            "item_id": "reports-closeout",
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": "Closeout report task",
            "status": "in_progress",
            "priority": "high",
            "item_type": "validation",
            "assigned_agent": "test-agent",
        },
    )["ok"]
    assert capture_local_queue_completion_evidence(
        config,
        item_id="reports-closeout",
        evidence_summary="Validation passed for Reports v1.",
        validation_results=["pytest -> passed"],
        diff_check_result="git diff --check -> pass",
    )["ok"]

    payload = read_local_project_reports(config)

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["report_type"] == "local_reports_v1"
    assert payload["overall_project_count"] == 1
    assert payload["active_project_summary"]["active_project_id"] == "aresforge"
    assert payload["queue_item_totals"]["total"] == 2
    assert payload["queue_item_totals"]["ready"] == 1
    assert payload["queue_item_totals"]["in_progress"] == 1
    assert payload["queue_item_counts_by_status"]["ready"] == 1
    assert payload["queue_item_counts_by_type"]["validation"] == 1
    assert payload["queue_item_counts_by_lane"]["test-agent"] == 1
    assert payload["evidence_summary"]["items_with_evidence_captured"] == 1
    assert payload["closeout_summary"]["items_eligible_for_closeout"] == 1
    assert payload["project_progress_rollup"]["project_id"] == "aresforge"
    assert payload["latest_activity_summary"]["available"] is True
    assert any("No local LLM execution" in item for item in payload["boundary_confirmations"])


def test_read_local_project_reports_handles_empty_state(tmp_path: Path) -> None:
    payload = read_local_project_reports(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["report_type"] == "local_reports_v1"
    assert payload["overall_project_count"] == 0
    assert payload["active_project_summary"]["active_project_selected"] is False
    assert payload["queue_item_totals"]["total"] == 0
    assert payload["evidence_summary"]["items_with_evidence_captured"] == 0
    assert payload["closeout_summary"]["items_eligible_for_closeout"] == 0
    assert payload["project_progress_rollup"] == {}
    assert payload["warnings"]


def test_get_reports_local_projects_route_returns_reports_v1(tmp_path: Path) -> None:
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
    assert post_active_project(config, {"project_id": "aresforge"})["ok"]

    server, thread = _start_server(config)
    try:
        status, payload = _request_json(int(server.server_address[1]), "/api/reports/local-projects")
        assert status == 200
        assert payload["ok"] is True
        assert payload["report_type"] == "local_reports_v1"
        assert payload["overall_project_count"] == 1
        assert payload["active_project_summary"]["active_project_id"] == "aresforge"
        assert "local_only_operating_boundary_summary" in payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
