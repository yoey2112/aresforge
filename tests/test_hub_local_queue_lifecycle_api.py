from __future__ import annotations

import json
import http.client
from http.server import ThreadingHTTPServer
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
    body: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
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


def _seed_queue_item(
    config: AppConfig,
    *,
    item_id: str,
    status: str,
    title: str,
    description: str,
    dependencies: list[str] | None = None,
    notes: str | None = None,
) -> None:
    payload = post_queue_item(
        config,
        {
            "item_id": item_id,
            "project_id": "aresforge",
            "repo_id": "aresforge-primary",
            "title": title,
            "description": description,
            "status": status,
            "priority": "high",
            "item_type": "task",
            "dependencies": dependencies or [],
            "notes": notes,
        },
    )
    assert payload["ok"] is True


def test_post_local_queue_item_route_adds_item_with_active_project_defaults(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items",
            {
                "title": "Build Hub queue lifecycle API foundation",
                "description": "Expose local-only Hub queue lifecycle endpoints.",
                "item_type": "feature",
                "priority": "high",
                "source": "active_project_workspace",
                "target_area": "hub-api queue-lifecycle",
                "acceptance_criteria": ["Stable JSON", "No execution"],
                "requested_outcome": "Queue intake provides a richer local-only payload.",
                "validation_notes": ["Run targeted pytest", "Keep queue item proposed"],
                "tags": ["m18", "hub-api"],
            },
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["project_id"] == "aresforge"
        assert payload["repo_id"] == "aresforge-primary"
        assert payload["source"] == "active_project_workspace"
        assert str(payload["item_id"]).startswith("local-build-hub-queue-lifecycle-api-foundation")
        assert payload["boundary_confirmations"]
        assert "initialized automatically" in " ".join(payload["warnings"])

        queue_status, queue_item = _request_json(
            port,
            "GET",
            f"/api/queue/{payload['item_id']}",
        )
        assert queue_status == 200
        assert queue_item["item"]["source"] == "active_project_workspace"
        assert "Requested outcome:" in queue_item["item"]["notes"]
        assert "Validation notes:" in queue_item["item"]["notes"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_active_project_workspace_route_returns_local_only_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="workspace-ready",
        status="ready",
        title="Workspace ready item",
        description="Ready for queue lifecycle.",
    )
    _seed_queue_item(
        config,
        item_id="workspace-done",
        status="done",
        title="Workspace done item",
        description="Completed recently.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(port, "GET", "/api/active-project/workspace")

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["report_only"] is True
        assert payload["active_project_selected"] is True
        assert payload["active_project_id"] == "aresforge"
        assert payload["current_queue_items"][0]["item_id"] == "workspace-ready"
        assert payload["recent_completed_queue_items"][0]["item_id"] == "workspace-done"
        assert payload["continue_actions"]["queue_lifecycle_section"] == "queue"
        assert payload["boundary_confirmations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_local_queue_item_readiness_route_returns_ready_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="dep-done",
        status="done",
        title="Done dependency",
        description="Already complete.",
    )
    _seed_queue_item(
        config,
        item_id="ready-item",
        status="ready",
        title="Ready item",
        description="Ready to start.",
        dependencies=["dep-done"],
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(port, "GET", "/api/local-queue/items/ready-item/readiness")

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["readiness_status"] == "ready"
        assert payload["can_start"] is True
        assert payload["dependency_summary"]["resolved_dependencies"] == ["dep-done"]
        assert payload["boundary_confirmations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_start_route_starts_ready_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="startable-item",
        status="ready",
        title="Startable item",
        description="Ready to begin local work.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(port, "POST", "/api/local-queue/items/startable-item/start", {})

        assert status == 200
        assert payload["ok"] is True
        assert payload["status"] == "in_progress"
        assert payload["previous_status"] == "ready"
        assert payload["item"]["status"] == "in_progress"
        assert payload["boundary_confirmations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_start_route_returns_gated_failures(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="blocked-item",
        status="blocked",
        title="Blocked item",
        description="Still blocked.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])

        blocked_status, blocked_payload = _request_json(port, "POST", "/api/local-queue/items/blocked-item/start", {})
        assert blocked_status == 409
        assert blocked_payload["ok"] is False
        assert blocked_payload["status"] == "blocked"
        assert blocked_payload["readiness"]["readiness_status"] == "blocked"

        missing_status, missing_payload = _request_json(port, "POST", "/api/local-queue/items/missing-item/start", {})
        assert missing_status == 404
        assert missing_payload["ok"] is False
        assert missing_payload["item_id"] == "missing-item"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_codex_prompt_route_returns_prompt_metadata_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="prompt-item",
        status="ready",
        title="Prepare queue prompt generation",
        description="Generate a Codex prompt from the local queue item.",
        notes="Acceptance criteria:\n- Prompt includes local-only constraints\n- Prompt includes validation commands",
    )
    output_path = tmp_path / "artifacts" / "local_queue_prompts" / "prompt-item.md"
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/prompt-item/codex-prompt",
            {
                "output": str(output_path),
                "commit_message": "M18 add Hub queue lifecycle API foundation",
            },
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["item_id"] == "prompt-item"
        assert payload["readiness_status"] == "ready"
        assert payload["output_path"] == str(output_path)
        assert "Queue item title: Prepare queue prompt generation" in payload["prompt"]
        assert any("does not execute Codex" in entry for entry in payload["boundary_confirmations"])
        assert output_path.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_complete_route_records_validation_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="complete-item",
        status="in_progress",
        title="Complete item",
        description="Complete local implementation with evidence.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/complete-item/complete",
            {
                "commit_hash": "abc123def",
                "validation_summary": "Targeted Hub queue lifecycle tests passed locally.",
                "evidence_note": "Manual smoke checks passed.",
                "tests_run": ["python -m pytest tests/test_hub_local_queue_lifecycle_api.py"],
                "changed_files": ["src/aresforge/hub/api.py", "src/aresforge/hub/server.py"],
                "artifact_paths": ["artifacts/evidence/hub-local-queue-api.md"],
            },
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["status"] == "done"
        assert payload["previous_status"] == "in_progress"
        assert payload["completion_commit"] == "abc123def"
        assert payload["validation_summary"] == "Targeted Hub queue lifecycle tests passed locally."
        assert payload["item"]["tests_run"] == ["python -m pytest tests/test_hub_local_queue_lifecycle_api.py"]
        assert payload["boundary_confirmations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



def test_post_local_queue_item_complete_route_rejects_missing_evidence_and_wrong_status(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="in-progress-item",
        status="in_progress",
        title="Evidence missing",
        description="Missing validation evidence should fail.",
    )
    _seed_queue_item(
        config,
        item_id="proposed-item",
        status="proposed",
        title="Wrong status",
        description="Not started yet.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])

        missing_status, missing_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/in-progress-item/complete",
            {
                "commit_hash": "abc123def",
                "validation_summary": "   ",
            },
        )
        assert missing_status == 409
        assert missing_payload["ok"] is False
        assert any("validation_summary is required" in warning for warning in missing_payload["warnings"])

        wrong_status, wrong_status_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/proposed-item/complete",
            {
                "commit_hash": "abc123def",
                "validation_summary": "Targeted tests passed locally.",
            },
        )
        assert wrong_status == 409
        assert wrong_status_payload["ok"] is False
        assert wrong_status_payload["status"] == "proposed"
        assert any("in_progress" in warning for warning in wrong_status_payload["warnings"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_prompt_pack_route_returns_local_copy_paste_payload(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="pack-ready",
        status="ready",
        title="Pack ready item",
        description="Ready for prompt pack generation.",
        notes="Acceptance criteria:\n- Keep local-only behavior",
    )
    output_path = tmp_path / "artifacts" / "prompt_packs" / "pack.txt"
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/prompt-pack",
            {
                "statuses": ["ready"],
                "output": str(output_path),
            },
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["item_count"] == 1
        assert payload["output_path"] == str(output_path)
        assert "Agent Prompt Pack (Local-Only)" in payload["prompt_pack"]
        assert any("does not execute Codex or agents" in entry for entry in payload["boundary_confirmations"])
        assert output_path.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
