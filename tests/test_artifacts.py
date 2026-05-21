import json
from datetime import UTC, datetime
from pathlib import Path

from aresforge.artifacts.store import write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.inspection_reports import (
    render_queue_inspection_report,
    render_work_item_inspection_report,
)
from aresforge.operator.service import (
    render_codex_handoff,
    render_evidence_package,
    render_prompt_package,
)
from aresforge.routing.routes import build_route_plan


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts",
        evidence_dir=tmp_path / "artifacts" / "evidence",
        codex_handoffs_dir=tmp_path / "artifacts" / "handoffs",
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_generic_bundle_writer(tmp_path: Path) -> None:
    bundle = write_markdown_json_bundle(
        tmp_path, title="Example Prompt", markdown="# Test", payload={"ok": True}
    )
    assert bundle.markdown_path.exists()
    assert bundle.json_path.exists()


def test_generic_bundle_writer_serializes_datetimes(tmp_path: Path) -> None:
    bundle = write_markdown_json_bundle(
        tmp_path,
        title="Example Prompt",
        markdown="# Test",
        payload={"generated_at": datetime(2026, 5, 20, tzinfo=UTC)},
    )

    assert json.loads(bundle.json_path.read_text(encoding="utf-8")) == {
        "generated_at": "2026-05-20 00:00:00+00:00"
    }


def test_prompt_evidence_and_handoff_renderers(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    route_plan = build_route_plan(
        work_item_id="work-123",
        queue_id="queue-implementation",
        agent_id="agent-local-operator",
        model_id="model-ollama-default",
        prompt_package=None,
        route_status="ready",
    )
    prompt = render_prompt_package(
        config=config,
        title="Prompt Title",
        objective="Build the local skeleton.",
        work_item_id="work-123",
        route_plan=route_plan,
        notes="Keep it practical.",
    )
    evidence = render_evidence_package(
        config=config,
        title="Evidence Title",
        work_item_id="work-123",
        files_changed=["src/aresforge/cli.py"],
        validations_run=["python -m pytest"],
        skipped_checks=["Ollama not running"],
        protected_issue_checks=["Protected historical reference left unchanged."],
        automation_boundary_confirmation="No autonomous GitHub actions were used.",
        artifact_discovery={"ok": True, "artifact_count": 1, "artifacts": []},
        latest_review_package={"selected_review_path": "20260520T120003Z-local-review.json"},
    )
    handoff = render_codex_handoff(
        config=config,
        title="Codex Handoff",
        summary="Prepare a review prompt.",
        work_item_id="work-123",
        route_plan=route_plan,
        requested_output="Generate a human-reviewable implementation prompt.",
        latest_review_package={"selected_review_path": "20260520T120003Z-local-review.json"},
    )
    assert prompt.markdown_path.exists()
    assert evidence.json_path.exists()
    assert handoff.markdown_path.read_text(encoding="utf-8").startswith("# Codex Handoff")
    assert (
        json.loads(evidence.json_path.read_text(encoding="utf-8"))["artifact_discovery"]["artifact_count"]
        == 1
    )
    assert (
        json.loads(evidence.json_path.read_text(encoding="utf-8"))["latest_review_package"]["selected_review_path"]
        == "20260520T120003Z-local-review.json"
    )
    assert "Latest Local Review Package" in handoff.markdown_path.read_text(encoding="utf-8")


def test_queue_inspection_report_renderer_writes_markdown_and_json(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    inspection_payload = {
        "id": "queue-verification",
        "name": "verification",
        "status": "active",
        "purpose": "Confirm that implementation matches scope.",
        "lifecycle_stage_mapping": "verification",
        "accepted_work_item_types": ["github_issue", "verification_pass"],
        "allowed_next_queues": ["queue-testing", "queue-corrective", "queue-blocked"],
        "human_approval_requirement": "human_review_required",
        "local_operator_visibility_expectations": [
            "visible findings",
            "pass/fail posture",
        ],
        "source_document": "docs/architecture/QUEUE_REGISTRY_SCHEMA.md",
        "metadata": {
            "registry_version": "m2-v1",
            "notes": "Fixture payload for report rendering.",
        },
    }

    bundle = render_queue_inspection_report(
        config=config,
        inspection_payload=inspection_payload,
    )

    assert bundle.markdown_path.exists()
    assert bundle.json_path.exists()
    assert bundle.markdown_path.read_text(encoding="utf-8").startswith("# Queue Inspection Report")

    json_payload = json.loads(bundle.json_path.read_text(encoding="utf-8"))
    assert json_payload["inspection_payload"] == inspection_payload
    assert json_payload["report_metadata"]["report_type"] == "queue_inspection"
    assert json_payload["report_metadata"]["queue_id"] == "queue-verification"
    assert bundle.payload == json_payload


def test_work_item_inspection_report_renderer_writes_markdown_and_json(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    inspection_payload = {
        "id": "work-123",
        "title": "Implement inspection reports",
        "description": "Render read-only inspection output into review artifacts.",
        "status": "in_progress",
        "priority": "high",
        "route_status": "ready",
        "queue_id": "queue-implementation",
        "queue_name": "implementation",
        "queue_purpose": "Hold issue-scoped repository work while implementation changes are prepared.",
        "queue_lifecycle_stage_mapping": "implementation",
        "queue_allowed_next_queues": ["queue-verification", "queue-blocked"],
        "queue_human_approval_requirement": "human_review_required",
        "agent_id": "agent-worker",
        "agent_name": "worker-agent",
        "model_id": "model-ollama-default",
        "model_name": "qwen2.5:32b",
        "model_provider": "ollama",
        "prompt_id": "prompt-123",
        "metadata": {
            "issue": 93,
            "retry_or_correction_context": "Retain for metadata preservation.",
        },
        "lifecycle_state": "implementation_ready",
        "approval_state": "pending_human_review",
        "blocked_reason": None,
        "failure_reason": None,
        "retry_or_correction_context": "Return to verification if report output is incomplete.",
    }

    bundle = render_work_item_inspection_report(
        config=config,
        inspection_payload=inspection_payload,
    )

    assert bundle.markdown_path.exists()
    assert bundle.json_path.exists()
    assert bundle.markdown_path.read_text(encoding="utf-8").startswith(
        "# Work Item Inspection Report"
    )

    json_payload = json.loads(bundle.json_path.read_text(encoding="utf-8"))
    assert json_payload["inspection_payload"] == inspection_payload
    assert json_payload["report_metadata"]["report_type"] == "work_item_inspection"
    assert json_payload["report_metadata"]["work_item_id"] == "work-123"
    assert bundle.payload == json_payload
