import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.queue_agent_dispatch_plan import build_queue_agent_dispatch_plan


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


def _seed_item(
    config: AppConfig,
    *,
    item_id: str,
    title: str,
    description: str,
    status: str = "ready",
    item_type: str = "feature",
    blocked_by: list[str] | None = None,
) -> None:
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    if not queue_path.exists():
        assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title=title,
        description=description,
        status=status,
        priority="high",
        item_type=item_type,
        tags=[f"milestone:{item_id.split('-', 1)[0]}"],
        blocked_by=blocked_by,
        notes="Acceptance criteria:\n- Preserve local-only boundaries\n- Add focused tests",
    )["ok"] is True


def test_dispatch_plan_builds_for_ready_item_and_never_allows_execution(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(
        config,
        item_id="m97-implementation-contract",
        title="M97 Queue-to-Agent Dispatch Plan Contract",
        description="Implement the local operator-layer dispatch plan contract and CLI inspection command.",
    )

    plan = build_queue_agent_dispatch_plan(config, item_id="m97-implementation-contract")

    assert plan["ok"] is True
    assert plan["local_only"] is True
    assert plan["execution_allowed"] is False
    assert plan["prompt_dispatch_allowed"] is False
    assert plan["codex_execution_allowed"] is False
    assert plan["local_llm_invocation_allowed"] is False
    assert plan["github_api_allowed"] is False
    assert plan["gh_allowed"] is False
    assert plan["item_id"] == "m97-implementation-contract"
    assert plan["title"] == "M97 Queue-to-Agent Dispatch Plan Contract"
    assert plan["project_id"] == "aresforge"
    assert plan["milestone"] == "m97"
    assert plan["planned_artifact_intent"]["full_prompt_generated"] is False
    assert plan["generated_at"]


def test_dispatch_plan_selects_codex_prompt_artifact_for_implementation_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(
        config,
        item_id="m98-codex-prompt-generator",
        title="M98 Codex Prompt Dispatch Artifact Generator v1",
        description="Build a CLI generator for future Codex prompt dispatch artifacts.",
        item_type="feature",
    )

    plan = build_queue_agent_dispatch_plan(config, item_id="m98-codex-prompt-generator")

    assert plan["selected_lane"] == "codex_prompt_artifact"
    assert plan["routing_confidence"]["score"] >= 60
    assert "M98" in plan["planned_artifact_intent"]["generator_milestone"]
    assert any("operator_must_approve_m98" in gate for gate in plan["approval_gates"])


def test_dispatch_plan_selects_documentation_agent_dry_run_for_docs_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(
        config,
        item_id="m100-doc-reconciliation",
        title="M100 Documentation Agent Dry-Run Review Workflow",
        description="Review source-of-truth docs and reconciliation warnings without applying documentation changes.",
        item_type="documentation",
    )

    plan = build_queue_agent_dispatch_plan(config, item_id="m100-doc-reconciliation")

    assert plan["selected_lane"] == "documentation_agent_dry_run"
    assert plan["planned_artifact_intent"]["artifact_type"] == "documentation_agent_dry_run_plan"
    assert plan["execution_allowed"] is False


def test_dispatch_plan_uses_manual_fallback_for_unclear_or_blocked_items(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(
        config,
        item_id="unclear-blocked",
        title="Clarify future thing",
        description="",
        status="blocked",
        item_type="other",
        blocked_by=["missing-decision"],
    )

    plan = build_queue_agent_dispatch_plan(config, item_id="unclear-blocked")

    assert plan["ok"] is False
    assert plan["selected_lane"] == "human_only_manual"
    assert plan["blocked"] is True
    assert plan["blocked_reasons"]
    assert "Resolve blocked reasons" in plan["next_safe_action"]


def test_dispatch_plan_reports_missing_item_as_blocked_manual_only(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    plan = build_queue_agent_dispatch_plan(config, item_id="missing")

    assert plan["ok"] is False
    assert plan["selected_lane"] == "human_only_manual"
    assert plan["execution_allowed"] is False
    assert any("Queue item not found" in reason for reason in plan["blocked_reasons"])


def test_dispatch_plan_json_serializable(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(
        config,
        item_id="json-plan",
        title="Add local contract",
        description="Implement a local-only JSON-serializable contract.",
    )

    encoded = json.dumps(build_queue_agent_dispatch_plan(config, item_id="json-plan"), sort_keys=True)

    assert "codex_prompt_artifact" in encoded
    assert "execution_allowed" in encoded
