import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.agent_orchestration_plan_builder import build_agent_orchestration_plan
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def _seed(
    config: AppConfig,
    *,
    item_id: str,
    item_type: str,
    title: str,
    notes: str = "",
    status: str = "ready",
    blocked_by: list[str] | None = None,
) -> None:
    if not (config.repo_root / ".aresforge" / "queue" / "work_items.json").exists():
        assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title=title,
        description=title,
        status=status,
        priority="high",
        item_type=item_type,
        tags=[f"milestone:{item_id.split('-', 1)[0]}", "local-only"],
        blocked_by=blocked_by,
        notes=notes,
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def _agent_ids(payload: dict[str, object]) -> list[str]:
    return [step["agent_id"] for step in payload["steps"]]  # type: ignore[index]


def test_docs_only_item_plan_uses_documentation_step(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m128-docs", item_type="documentation", title="Update source-of-truth docs")

    payload = _payload(build_agent_orchestration_plan(config, item_id="m128-docs"))

    assert payload["plan_type"] == "agent_orchestration_plan"
    assert payload["item_id"] == "m128-docs"
    assert payload["requested_execution_target"] == "dry-run"
    assert payload["recommended_execution_target"] == "dry-run"
    assert payload["execution_performed"] is False
    assert payload["local_only"] is True
    assert payload["blocked"] is False
    assert _agent_ids(payload) == [
        "queue-planner-agent",
        "documentation-agent",
        "validation-agent",
        "completion-recommendation-agent",
    ]


def test_coding_item_plan_uses_codex_handoff_for_high_risk_code(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(
        config,
        item_id="m128-code",
        item_type="feature",
        title="Implement agent runner guardrails in src/",
        notes="High-risk execution boundary code with tests/ coverage.",
    )

    payload = _payload(build_agent_orchestration_plan(config, item_id="m128-code"))

    assert "codex-dispatch-agent" in _agent_ids(payload)
    codex_step = next(step for step in payload["steps"] if step["agent_id"] == "codex-dispatch-agent")  # type: ignore[index]
    assert codex_step["decision_policy"]["recommended_lane"] == "codex_coding"
    assert codex_step["can_run_dry_run"] is True
    assert codex_step["can_run_real"] is False
    assert "execute_codex" in codex_step["forbidden_capabilities"]


def test_validation_only_item_plan_uses_validation_then_completion(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m128-validation", item_type="validation", title="Validate local reports")

    payload = _payload(build_agent_orchestration_plan(config, item_id="m128-validation"))

    assert _agent_ids(payload) == [
        "queue-planner-agent",
        "validation-agent",
        "completion-recommendation-agent",
    ]
    assert "validation_plan" in payload["required_artifacts"]
    assert payload["blocked"] is False


def test_real_execution_target_blocks_high_risk_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(
        config,
        item_id="m128-risk",
        item_type="feature",
        title="Implement real agent execution runner",
        notes="critical execution mutation",
    )

    payload = _payload(
        build_agent_orchestration_plan(
            config,
            item_id="m128-risk",
            execution_target="real",
        )
    )

    assert payload["blocked"] is True
    assert payload["requested_execution_target"] == "real"
    assert payload["recommended_execution_target"] == "dry-run"
    assert any("Real execution is blocked" in reason for reason in payload["blocked_reasons"])
    assert all(step["can_run_real"] is False for step in payload["steps"])  # type: ignore[index]


def test_output_path_writes_plan_json(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m128-output", item_type="documentation", title="Write docs")
    output = tmp_path / "artifacts" / "orchestration-plans" / "m128-output.json"

    result = build_agent_orchestration_plan(config, item_id="m128-output", output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["plan_type"] == "agent_orchestration_plan"
    assert written["execution_performed"] is False


def test_no_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m128-no-overwrite", item_type="documentation", title="Write docs")
    output = tmp_path / "plan.json"

    first = build_agent_orchestration_plan(config, item_id="m128-no-overwrite", output=output)
    duplicate = build_agent_orchestration_plan(config, item_id="m128-no-overwrite", output=output)
    forced = build_agent_orchestration_plan(config, item_id="m128-no-overwrite", output=output, force=True)

    assert first["ok"] is True
    assert duplicate["ok"] is False
    assert duplicate["error"] == "output_exists"
    assert forced["ok"] is True
