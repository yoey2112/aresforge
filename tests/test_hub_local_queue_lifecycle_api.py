from __future__ import annotations

import json
import http.client
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading

from aresforge.config import AppConfig
from aresforge.hub.server import _build_handler
from aresforge.hub.api import (
    get_agent_route_recommendation,
    get_dispatch_review_panel,
    get_local_queue_routing_dashboard,
    post_active_project,
    post_local_queue_item_routing_metadata,
    post_project,
    post_project_repo,
    post_queue_item,
)
from aresforge.operator.local_ai_artifacts import register_ai_artifact
from aresforge.operator.local_execution_audit import append_execution_audit_entry
from aresforge.operator.local_project_queue import complete_local_queue_item


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


def _write_local_llm_environment(repo_root: Path, *, execution_enabled: bool = False) -> None:
    path = repo_root / ".aresforge" / "local_llm_environment.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "local_llm_provider": "ollama",
                "provider_base_url": "http://127.0.0.1:11434",
                "reasoning_model": "local-reason",
                "coding_model": "local-code",
                "fallback_model": "",
                "health_check_enabled": False,
                "execution_enabled": execution_enabled,
                "operator_gate_required": True,
                "notes": "",
                "updated_at": "",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_get_dispatch_review_panel_reads_local_review_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_dir = tmp_path / "artifacts" / "queue_completion_recommendations"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.joinpath("m114.json").write_text(
        json.dumps(
            {
                "recommendation_record_type": "queue_completion_recommendation",
                "recommended_complete": True,
                "blocked": False,
                "blocked_reasons": [],
                "item_id": "m114-hub-dispatch-review-panel",
                "title": "M114 Hub Dispatch Review Panel",
                "project_id": "aresforge",
                "milestone": "m114",
                "evidence_path": "artifacts/manual/sample-dispatch-evidence.json",
                "evidence_valid": True,
                "operator_decision_required": True,
                "queue_mutation_performed": False,
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": "Review locally before explicit completion.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = get_dispatch_review_panel(
        config,
        {"item_id": "m114-hub-dispatch-review-panel", "limit": "10"},
    )

    assert payload["ok"] is True
    assert payload["panel_type"] == "hub_dispatch_review_panel"
    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["patch_application_allowed"] is False
    assert payload["record_count"] == 1
    assert payload["records"][0]["artifact_type"] == "queue_completion_recommendation"
    assert payload["records"][0]["item_id"] == "m114-hub-dispatch-review-panel"


def test_get_agent_route_recommendation_is_read_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="m117-agent-routing-decision-dashboard",
        status="ready",
        title="M117 Agent Routing Decision Dashboard",
        description="Add a Hub dashboard and CLI for advisory routing decisions.",
    )

    payload = get_agent_route_recommendation(
        config,
        {"item_id": "m117-agent-routing-decision-dashboard"},
    )

    assert payload["recommendation_type"] == "agent_route_recommendation"
    assert payload["recommended_lane"] == "codex_prompt_artifact"
    assert payload["hub_read_only"] is True
    assert payload["local_only"] is True
    assert payload["dispatch_performed"] is False
    assert payload["execution_allowed"] is False


def test_agent_route_recommendation_http_route(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="m117-agent-routing-decision-dashboard",
        status="ready",
        title="M117 Agent Routing Decision Dashboard",
        description="Add a Hub dashboard and CLI for advisory routing decisions.",
    )
    server, thread = _start_server(config)
    try:
        port = server.server_address[1]
        status, payload = _request_json(
            port,
            "GET",
            "/api/agent-route-recommendation?item_id=m117-agent-routing-decision-dashboard",
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert payload["recommendation_type"] == "agent_route_recommendation"
    assert payload["dispatch_performed"] is False
    assert payload["execution_allowed"] is False


def test_dispatch_review_route_is_get_only_and_read_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(port, "GET", "/api/dispatch-review?limit=5")

        assert status == 200
        assert payload["ok"] is True
        assert payload["panel_type"] == "hub_dispatch_review_panel"
        assert payload["local_only"] is True
        assert payload["execution_allowed"] is False
        assert payload["execution_performed"] is False
        assert payload["queue_mutation_performed"] is False
        assert payload["patch_application_allowed"] is False
        assert "No execution endpoints are exposed by this panel." in payload["boundary_confirmations"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


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
        assert queue_item["item"]["routing_metadata"]["risk_level"] == "unknown"
        assert queue_item["item"]["routing_metadata"]["recommended_agent_lane"] == ""
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_routing_metadata_route_updates_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="m53-routing-api",
        status="ready",
        title="Routing API",
        description="Update routing metadata.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/m53-routing-api/routing-metadata",
            {
                "routing_metadata": {
                    "recommended_agent_lane": "reviewer_validator",
                    "recommended_engine": "local_reasoning_llm",
                    "fallback_engine": "codex_cli",
                    "routing_policy_source": "manual_contract_test",
                    "routing_reason": "Review validation evidence later.",
                    "risk_level": "medium",
                    "complexity_level": "low",
                    "operator_override": False,
                }
            },
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["routing_metadata"]["recommended_agent_lane"] == "reviewer_validator"
        assert payload["routing_metadata"]["recommended_engine"] == "local_reasoning_llm"
        assert payload["validation"]["routing_execution_status"] == "not_implemented"

        detail_status, detail_payload = _request_json(port, "GET", "/api/queue/m53-routing-api")
        assert detail_status == 200
        assert detail_payload["item"]["routing_metadata"]["fallback_engine"] == "codex_cli"
        assert detail_payload["item"]["status"] == "ready"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_routing_metadata_route_rejects_invalid_metadata(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="m53-routing-invalid-api",
        status="ready",
        title="Routing API Invalid",
        description="Reject invalid routing metadata.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        bad_lane_status, bad_lane = _request_json(
            port,
            "POST",
            "/api/local-queue/items/m53-routing-invalid-api/routing-metadata",
            {"recommended_agent_lane": "bad_lane"},
        )
        assert bad_lane_status == 400
        assert bad_lane["ok"] is False
        assert bad_lane["error"] == "invalid_recommended_agent_lane"

        bad_engine_status, bad_engine = _request_json(
            port,
            "POST",
            "/api/local-queue/items/m53-routing-invalid-api/routing-metadata",
            {"recommended_engine": "bad_engine"},
        )
        assert bad_engine_status == 400
        assert bad_engine["error"] == "invalid_recommended_engine"

        bad_level_status, bad_level = _request_json(
            port,
            "POST",
            "/api/local-queue/items/m53-routing-invalid-api/routing-metadata",
            {"risk_level": "extreme"},
        )
        assert bad_level_status == 400
        assert bad_level["error"] == "invalid_risk_level"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_local_queue_routed_views_route_returns_grouped_read_only_view(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="routed-api-item",
        status="ready",
        title="Routed API item",
        description="Routed view item.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/routed-api-item/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "risk_level": "low",
                "complexity_level": "medium",
                "project_ai_mode": "balanced",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "GET",
            "/api/local-queue/routed-views?agent_lane=coding&group_by=by_engine&include_unrouted=false",
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["execution_allowed"] is False
        assert payload["total_items"] == 1
        assert "local_coding_llm" in payload["groups"]
        assert payload["items"][0]["item_id"] == "routed-api-item"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_local_queue_routing_dashboard_returns_decision_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="routing-dashboard-api-item",
        status="proposed",
        title="Build routing dashboard data contract",
        description="Expose read-only routing confidence metadata.",
    )
    routed = post_local_queue_item_routing_metadata(
        config,
        "routing-dashboard-api-item",
        {
            "routing_metadata": {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "recommended_model": "qwen2.5-coder:32b",
                "risk_level": "low",
                "complexity_level": "low",
                "routing_policy_source": "api-test",
                "routing_reason": "Read-only dashboard data.",
            }
        },
    )
    assert routed["ok"] is True

    payload = get_local_queue_routing_dashboard(config, {"project_id": "aresforge", "status": "proposed"})

    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["contract_name"] == "hub_routing_dashboard_data_contract"
    assert payload["item_count"] == 1
    row = payload["items"][0]
    assert row["item_id"] == "routing-dashboard-api-item"
    assert row["status"] == "proposed"
    assert row["risk"] == "low"
    assert row["task_size"] == "small"
    assert row["recommended_engine"] == "local_coding_llm"
    assert row["recommended_lane"] == "coding"
    assert isinstance(row["confidence_score"], int)
    assert row["validation_burden"]
    assert isinstance(row["warnings"], list)
    assert isinstance(row["blockers"], list)
    assert row["prompt_dispatch_allowed"] is False
    assert row["local_llm_invocation_allowed"] is False
    assert row["codex_invocation_allowed"] is False
    assert row["automatic_next_item_execution_allowed"] is False
    assert payload["safety_boundary"]["mutation_endpoints_added"] is False
    assert payload["safety_boundary"]["github_api_allowed"] is False
    assert payload["safety_boundary"]["gh_allowed"] is False


def test_get_local_queue_routing_dashboard_route_is_read_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="routing-dashboard-http-item",
        status="proposed",
        title="Review routing dashboard data",
        description="Read-only API route contract.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "GET",
            "/api/local-queue/routing-dashboard?project_id=aresforge&status=proposed",
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["read_only"] is True
        assert payload["item_count"] == 1
        assert payload["items"][0]["item_id"] == "routing-dashboard-http-item"
        assert payload["items"][0]["prompt_dispatch_allowed"] is False
        assert payload["items"][0]["local_llm_invocation_allowed"] is False
        assert payload["items"][0]["codex_invocation_allowed"] is False
        assert payload["safety_boundary"]["automatic_next_item_execution_allowed"] is False
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
        status="in_progress",
        title="Done dependency",
        description="Already complete.",
    )
    assert complete_local_queue_item(
        config,
        item_id="dep-done",
        commit_hash="abc123def",
        validation_summary="Dependency validation passed.",
        evidence_note="Operator reviewed dependency evidence.",
    )["ok"] is True
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


def test_post_local_queue_item_codex_high_value_prompt_route_returns_preview_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="codex-high-value-api",
        status="ready",
        title="Codex high value prompt",
        description="Generate a Codex high-value lane prompt for an API route task.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        routing_status, routing_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/codex-high-value-api/routing-metadata",
            {
                "routing_metadata": {
                    "recommended_agent_lane": "high_value_codex",
                    "recommended_engine": "codex_cli",
                    "recommended_model": "gpt-5-codex",
                    "routing_policy_source": "api-test",
                    "routing_reason": "High-value backend API route work.",
                    "risk_level": "medium",
                    "complexity_level": "medium",
                    "project_ai_mode": "balanced",
                }
            },
        )
        assert routing_status == 200
        assert routing_payload["ok"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/codex-high-value-api/codex-high-value-prompt",
            {"include_context": True, "include_validation_expectations": True, "include_operating_rules": True},
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["eligible_for_codex_lane"] is True
        assert payload["recommended_engine"] == "codex_cli"
        assert payload["execution_allowed"] is False
        assert payload["executed"] is False
        assert payload["repo_mutation_allowed"] is False
        assert payload["external_mutation_allowed"] is False
        assert payload["automatic_execution_allowed"] is False
        assert payload["advisory_only"] is True
        assert "AresForge must not automatically execute Codex." in payload["prompt_preview"]
        assert "git diff --check" in payload["prompt_preview"]
        assert any("does not execute Codex" in entry for entry in payload["boundary_confirmations"])

        missing_status, missing_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/missing-codex/codex-high-value-prompt",
            {},
        )
        assert missing_status == 404
        assert missing_payload["ok"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_execution_audit_log_route_returns_filtered_entries(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert append_execution_audit_entry(
        config,
        action_type="local_llm_execute",
        item_id="audit-api-item",
        engine="local_coding_llm",
        dry_run=True,
        executed=False,
        execution_allowed=False,
        outcome="dry_run",
        summary="Dry run recorded.",
        source_function="test",
        timestamp="2026-05-29T00:00:00+00:00",
    )["ok"] is True
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "GET",
            "/api/execution-audit-log?item_id=audit-api-item&action_type=local_llm_execute&limit=5",
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["total_entries"] == 1
        assert payload["entries"][0]["item_id"] == "audit-api-item"
        assert payload["entries"][0]["executed"] is False
        assert payload["entries"][0]["repo_mutation_allowed"] is False
        assert payload["entries"][0]["external_mutation_allowed"] is False
        assert payload["entries"][0]["automatic_execution_allowed"] is False
        assert payload["filters"]["limit"] == 5
        assert any("read-only" in entry for entry in payload["boundary_confirmations"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_ai_action_safety_gate_route_returns_decision(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="safety-gate-api-item",
        status="ready",
        title="Safety gate API item",
        description="Preview safety gate decision.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/ai-action-safety-gate",
            {
                "action_type": "local_llm_execute",
                "item_id": "safety-gate-api-item",
                "engine": "local_coding_llm",
                "risk_level": "low",
                "complexity_level": "low",
                "confirm_operator_gate": True,
            },
        )
        bad_status, bad_payload = _request_json(
            port,
            "POST",
            "/api/ai-action-safety-gate",
            {"action_type": "local_llm_execute", "confirm_operator_gate": "yes"},
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["allowed"] is True
        assert payload["decision"] == "allowed"
        assert payload["execution_allowed"] is True
        assert payload["repo_mutation_allowed"] is False
        assert payload["external_mutation_allowed"] is False
        assert payload["automatic_execution_allowed"] is False
        assert any("decision/reporting" in entry for entry in payload["boundary_confirmations"])
        assert bad_status == 400
        assert bad_payload["ok"] is False
        assert bad_payload["error"] == "invalid_confirm_operator_gate"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_ai_artifacts_route_returns_filtered_registry(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = tmp_path / "artifacts" / "prompt_packs" / "api-pack.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("api prompt pack\n", encoding="utf-8")
    assert register_ai_artifact(
        config,
        artifact_type="prompt_pack",
        artifact_path=artifact_path,
        source_action="prompt_pack_generate",
        item_id="artifact-api-item",
        engine="prompt_pack",
        summary="API route artifact registry entry.",
        created_at="2026-05-29T00:00:00+00:00",
    )["ok"] is True
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "GET",
            "/api/ai-artifacts?item_id=artifact-api-item&artifact_type=prompt_pack&exists=true&limit=1",
        )
        bad_status, bad_payload = _request_json(port, "GET", "/api/ai-artifacts?exists=maybe")

        assert status == 200
        assert payload["ok"] is True
        assert payload["total_artifacts"] == 1
        assert payload["artifacts"][0]["artifact_type"] == "prompt_pack"
        assert payload["artifacts"][0]["artifact_path"] == str(artifact_path)
        assert payload["artifacts"][0]["exists"] is True
        assert payload["artifacts"][0]["advisory_only"] is True
        assert payload["artifacts"][0]["repo_mutation_allowed"] is False
        assert payload["artifacts"][0]["external_mutation_allowed"] is False
        assert payload["artifacts"][0]["automatic_execution_allowed"] is False
        assert any("read-only" in entry for entry in payload["boundary_confirmations"])
        assert bad_status == 400
        assert bad_payload["error"] == "invalid_exists"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_operator_run_history_route_returns_timeline(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = tmp_path / "artifacts" / "history" / "prompt.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("history prompt\n", encoding="utf-8")
    assert append_execution_audit_entry(
        config,
        action_type="codex_high_value_prompt",
        project_id="p-history",
        item_id="history-api-item",
        engine="codex_cli",
        outcome="prompt_generated",
        summary="Run history API audit entry.",
        source_function="test",
        timestamp="2026-05-29T00:00:01+00:00",
    )["ok"] is True
    assert register_ai_artifact(
        config,
        artifact_type="codex_high_value_prompt",
        artifact_path=artifact_path,
        source_action="codex_high_value_prompt",
        project_id="p-history",
        item_id="history-api-item",
        engine="codex_cli",
        summary="Run history API artifact entry.",
        created_at="2026-05-29T00:00:02+00:00",
    )["ok"] is True
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "GET",
            "/api/operator-run-history?project_id=p-history&item_id=history-api-item&limit=5",
        )
        bad_status, bad_payload = _request_json(port, "GET", "/api/operator-run-history?limit=zero")

        assert status == 200
        assert payload["ok"] is True
        assert payload["total_audit_entries"] == 1
        assert payload["total_artifacts"] == 1
        assert [entry["kind"] for entry in payload["timeline"]] == ["artifact", "audit"]
        assert payload["timeline"][0]["artifact_path"] == str(artifact_path)
        assert payload["timeline"][0]["execution_allowed"] is False
        assert payload["timeline"][0]["repo_mutation_allowed"] is False
        assert payload["timeline"][0]["external_mutation_allowed"] is False
        assert payload["timeline"][0]["automatic_execution_allowed"] is False
        assert any("read-only" in entry for entry in payload["boundary_confirmations"])
        assert bad_status == 400
        assert bad_payload["error"] == "invalid_limit"
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


def test_post_local_queue_item_evidence_route_records_without_completing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="evidence-route-item",
        status="in_progress",
        title="Evidence route item",
        description="Capture evidence through Hub API.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/evidence-route-item/evidence",
            {
                "evidence_summary": "Hub route evidence captured.",
                "validation_commands": ["python -m pytest tests/test_hub_local_queue_lifecycle_api.py"],
                "validation_results": ["passed"],
                "smoke_checks": ["inspect-local-queue-agent-summary -> ok"],
                "diff_check_result": "git diff --check -> pass",
                "files_changed": ["src/aresforge/hub/api.py"],
                "commit_hash": "abc123def",
                "push_result": "not pushed yet",
                "review_evidence": ["Operator reviewed Hub evidence route output."],
                "operator_notes": "Ready for closeout review.",
            },
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["status"] == "in_progress"
        assert payload["closeout_eligible"] is True
        assert payload["completion_evidence"]["evidence_summary"] == "Hub route evidence captured."
        assert payload["completion_evidence"]["captured_at"]
        assert any("does not complete the item" in entry for entry in payload["boundary_confirmations"])

        detail_status, detail_payload = _request_json(port, "GET", "/api/queue/evidence-route-item")
        assert detail_status == 200
        assert detail_payload["item"]["status"] == "in_progress"
        assert detail_payload["item"]["completion_evidence"]["commit_hash"] == "abc123def"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_evidence_route_returns_safe_failures(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="empty-evidence-route-item",
        status="in_progress",
        title="Empty evidence route item",
        description="Empty evidence should fail.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        missing_status, missing_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/missing-evidence-item/evidence",
            {"evidence_summary": "Evidence exists."},
        )
        assert missing_status == 404
        assert missing_payload["ok"] is False
        assert missing_payload["closeout_eligible"] is False

        empty_status, empty_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/empty-evidence-route-item/evidence",
            {
                "evidence_summary": "   ",
                "validation_commands": [],
                "validation_results": [],
                "smoke_checks": [],
                "files_changed": [],
            },
        )
        assert empty_status == 400
        assert empty_payload["ok"] is False
        assert empty_payload["status"] == "in_progress"
        assert any("meaningful evidence field" in warning for warning in empty_payload["warnings"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_closeout_route_closes_with_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="closeout-route-item",
        status="in_progress",
        title="Closeout route item",
        description="Close out through Hub API.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        evidence_status, evidence_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/closeout-route-item/evidence",
            {
                "evidence_summary": "Hub route evidence captured.",
                "validation_results": ["targeted tests passed"],
                "diff_check_result": "git diff --check -> pass",
                "review_evidence": ["Operator reviewed closeout route evidence."],
            },
        )
        assert evidence_status == 200
        assert evidence_payload["closeout_eligible"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/closeout-route-item/closeout",
            {
                "closeout_summary": "Evidence reviewed; closeout approved locally.",
                "closed_by": "local_operator",
            },
        )

        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["previous_status"] == "in_progress"
        assert payload["status"] == "done"
        assert payload["closed_at"]
        assert payload["closed_by"] == "local_operator"
        assert payload["item"]["completion_evidence"]["evidence_summary"] == "Hub route evidence captured."
        assert any("does not execute external actions" in entry for entry in payload["boundary_confirmations"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_queue_item_closeout_route_returns_safe_failures(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="no-evidence-route-closeout",
        status="in_progress",
        title="No evidence closeout",
        description="Missing evidence should fail.",
    )
    _seed_queue_item(
        config,
        item_id="wrong-status-route-closeout",
        status="proposed",
        title="Wrong status closeout",
        description="Wrong status should fail.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        missing_status, missing_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/missing-closeout-route/closeout",
            {"closeout_summary": "Close it."},
        )
        assert missing_status == 404
        assert missing_payload["ok"] is False

        no_evidence_status, no_evidence_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/no-evidence-route-closeout/closeout",
            {"closeout_summary": "Close it."},
        )
        assert no_evidence_status == 409
        assert no_evidence_payload["ok"] is False
        assert any("Completion evidence is required" in warning for warning in no_evidence_payload["warnings"])

        assert _request_json(
            port,
            "POST",
            "/api/local-queue/items/wrong-status-route-closeout/evidence",
            {
                "evidence_summary": "Evidence captured.",
                "validation_results": ["passed"],
                "diff_check_result": "pass",
            },
        )[0] == 200
        wrong_status, wrong_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/wrong-status-route-closeout/closeout",
            {"closeout_summary": "Close it."},
        )
        assert wrong_status == 409
        assert wrong_payload["ok"] is False
        assert wrong_payload["status"] == "proposed"
        assert any("in_progress" in warning for warning in wrong_payload["warnings"])
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
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/pack-ready/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "recommended_model": "local-code",
                "routing_policy_source": "m54_decision_matrix_v1",
                "routing_reason": "Simple local prompt-pack test.",
                "risk_level": "low",
                "complexity_level": "low",
                "project_ai_mode": "balanced",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/prompt-pack",
            {
                "statuses": ["ready"],
                "output": str(output_path),
                "include_routing": True,
                "group_by_routing": True,
                "routing_group_by": "by_engine",
            },
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["item_count"] == 1
        assert payload["execution_allowed"] is False
        assert payload["groups"] == ["by_engine: local_coding_llm"]
        assert payload["output_path"] == str(output_path)
        assert "Agent Prompt Pack (Local-Only)" in payload["prompt_pack"]
        assert "recommended_engine: local_coding_llm" in payload["prompt_pack"]
        assert "AresForge does not execute local LLMs" in payload["prompt_pack"]
        assert "No automatic execution." in payload["prompt_pack"]
        assert "No repo mutation from local LLM output." in payload["prompt_pack"]
        assert "recommendation_is_advisory_only: true" in payload["prompt_pack"]
        assert "Final response format:" in payload["prompt_pack"]
        assert "```" not in payload["prompt_pack"]
        assert any("does not execute Codex, local LLMs, agents" in entry for entry in payload["boundary_confirmations"])
        assert output_path.exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_ai_action_review_route_returns_read_only_operator_review(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _seed_queue_item(
        config,
        item_id="review-ai-action-api",
        status="ready",
        title="Review AI action metadata",
        description="Review existing local AI action metadata without executing anything.",
    )
    artifact_path = tmp_path / "artifacts" / "review" / "prompt.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("local advisory artifact", encoding="utf-8")
    append_execution_audit_entry(
        config,
        action_type="local_llm_execute",
        outcome="blocked",
        summary="Local LLM execution requires confirm_operator_gate=true for real execution.",
        source_function="test_get_ai_action_review_route_returns_read_only_operator_review",
        project_id="aresforge",
        item_id="review-ai-action-api",
        engine="local_coding_llm",
        model="local-code",
        agent_lane="coding",
        blockers=["Local LLM execution requires confirm_operator_gate=true for real execution."],
        safety_status="blocked",
        gate_status="missing_operator_approval",
        blocked_reason_category="missing_operator_approval",
    )
    register_ai_artifact(
        config,
        artifact_type="local_llm_prompt_preview",
        artifact_path=artifact_path,
        source_action="local_llm_prompt_preview",
        summary="Prompt preview artifact for review.",
        project_id="aresforge",
        item_id="review-ai-action-api",
        engine="local_coding_llm",
        model="local-code",
        agent_lane="coding",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/review-ai-action-api/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "recommended_model": "local-code",
                "routing_policy_source": "operator_review",
                "routing_reason": "AI-adjacent local review metadata.",
                "risk_level": "low",
                "complexity_level": "low",
                "project_ai_mode": "balanced",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "GET",
            "/api/ai-action-review?item_id=review-ai-action-api&limit=10",
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["local_only"] is True
        assert payload["read_only"] is True
        assert payload["review_only"] is True
        assert payload["counts"]["action_review_count"] >= 2
        assert payload["counts"]["blocked_action_count"] == 1
        assert payload["counts"]["artifact_reference_count"] == 1
        assert payload["counts"]["audit_reference_count"] >= 1
        assert payload["counts"]["queue_ai_action_count"] == 1
        blocked = payload["blocked_actions"][0]
        assert blocked["action_name"] == "local_llm_execute"
        assert blocked["safety_status"] == "blocked"
        assert blocked["gate_status"] == "missing_operator_approval"
        assert blocked["blocked_action"] == "local_llm_execute"
        assert blocked["blocked_reason_category"] == "missing_operator_approval"
        assert blocked["no_automatic_execution_flag"] is True
        assert blocked["no_repo_mutation_flag"] is True
        assert any("No execution controls are exposed" in entry for entry in payload["boundary_confirmations"])
        assert any("does not execute Codex, local LLMs, agents" in entry for entry in payload["boundary_confirmations"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_llm_prompt_preview_route_returns_preview_without_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _write_local_llm_environment(tmp_path)
    _seed_queue_item(
        config,
        item_id="local-preview-api",
        status="ready",
        title="Preview local LLM prompt",
        description="Generate the exact local LLM prompt preview without executing it.",
        notes="Acceptance criteria:\n- Preview only\nValidation notes:\n- Run targeted tests",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-preview-api/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "routing_policy_source": "m54_decision_matrix_v1",
                "routing_reason": "Low-risk local coding preview.",
                "risk_level": "low",
                "complexity_level": "low",
                "project_ai_mode": "balanced",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-preview-api/local-llm-prompt-preview",
            {
                "prompt_style": "implementation_planning",
                "include_context": True,
                "include_validation_expectations": True,
            },
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["preview_allowed"] is True
        assert payload["execution_allowed"] is False
        assert payload["recommended_engine"] == "local_coding_llm"
        assert payload["recommended_model"] == "local-code"
        assert "Local LLM Prompt Preview (No Execution)" in payload["prompt_preview"]
        assert "No GitHub API" in payload["prompt_preview"]
        assert "No local LLM inference or generation" in payload["prompt_preview"]
        assert "Local LLM prompt preview is local-only and non-executing." in payload["boundary_confirmations"][0]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_llm_prompt_preview_route_blocks_codex_routed_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _write_local_llm_environment(tmp_path)
    _seed_queue_item(
        config,
        item_id="codex-preview-api",
        status="ready",
        title="Preview Codex-routed prompt",
        description="Codex-routed work should not produce a local LLM prompt preview.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/codex-preview-api/routing-metadata",
            {
                "recommended_agent_lane": "high_value_codex",
                "recommended_engine": "codex_cli",
                "recommended_model": "default-codex",
                "routing_policy_source": "operator_override",
                "routing_reason": "High-value work.",
                "risk_level": "high",
                "complexity_level": "high",
                "project_ai_mode": "high_confidence",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/codex-preview-api/local-llm-prompt-preview",
            {},
        )
        assert status == 400
        assert payload["ok"] is False
        assert payload["preview_allowed"] is False
        assert payload["execution_allowed"] is False
        assert payload["prompt_preview"] == ""
        assert any("codex_cli" in blocker for blocker in payload["blockers"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_llm_execute_route_dry_run_returns_prompt_without_provider_call(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _write_local_llm_environment(tmp_path, execution_enabled=True)
    _seed_queue_item(
        config,
        item_id="local-execute-dry-run-api",
        status="ready",
        title="Dry run local LLM execution",
        description="Dry run should produce a gated execution payload without calling a provider.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        metadata_status, metadata_payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-execute-dry-run-api/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "recommended_model": "local-code",
                "routing_policy_source": "m54_decision_matrix_v1",
                "routing_reason": "Low-risk local execution dry run.",
                "risk_level": "low",
                "complexity_level": "low",
                "project_ai_mode": "balanced",
            },
        )
        assert metadata_status == 200
        assert metadata_payload["ok"] is True

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-execute-dry-run-api/local-llm-execute",
            {"dry_run": True, "confirm_operator_gate": False},
        )
        assert status == 200
        assert payload["ok"] is True
        assert payload["dry_run"] is True
        assert payload["executed"] is False
        assert payload["execution_allowed"] is False
        assert "Local LLM Prompt Preview" in payload["prompt_used"]
        assert payload["response_text"] == ""
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_post_local_llm_execute_route_requires_operator_confirmation_for_real_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_active_project(config, tmp_path)
    _write_local_llm_environment(tmp_path, execution_enabled=True)
    _seed_queue_item(
        config,
        item_id="local-execute-confirm-api",
        status="ready",
        title="Require confirmation",
        description="Real local execution should require explicit operator confirmation.",
    )
    server, thread = _start_server(config)

    try:
        port = int(server.server_address[1])
        assert _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-execute-confirm-api/routing-metadata",
            {
                "recommended_agent_lane": "coding",
                "recommended_engine": "local_coding_llm",
                "recommended_model": "local-code",
                "risk_level": "low",
                "complexity_level": "low",
                "project_ai_mode": "balanced",
            },
        )[0] == 200

        status, payload = _request_json(
            port,
            "POST",
            "/api/local-queue/items/local-execute-confirm-api/local-llm-execute",
            {"confirm_operator_gate": False, "dry_run": False},
        )
        assert status == 400
        assert payload["ok"] is False
        assert payload["executed"] is False
        assert any("confirm_operator_gate" in blocker for blocker in payload["blockers"])
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
