import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_llm_advisory_dry_run import validate_local_llm_advisory_dry_run
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue, update_local_queue_item_routing_metadata


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


def _seed_item(config: AppConfig, *, item_id: str = "m99-advisory-dry-run") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M99 Local LLM Advisory Execution Dry-Run Validator",
        description="Validate future local reasoning advisory readiness without executing models.",
        status="ready",
        priority="high",
        item_type="architecture",
        tags=["milestone:m99", "local-only"],
        notes="Acceptance criteria:\n- Dry-run only\n- execution_allowed=false",
    )["ok"] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id=item_id,
        routing_metadata={
            "recommended_agent_lane": "architect_planner",
            "recommended_engine": "local_reasoning_llm",
            "routing_policy_source": "test",
            "routing_reason": "Reasoning advisory dry-run readiness validation.",
            "risk_level": "low",
            "complexity_level": "low",
        },
    )["ok"] is True


def _plan(*, lane: str = "local_llm_advisory") -> dict[str, object]:
    return {
        "ok": True,
        "local_only": True,
        "dispatch_plan_version": "m97.1",
        "item_id": "m99-advisory-dry-run",
        "title": "M99 Local LLM Advisory Execution Dry-Run Validator",
        "status": "ready",
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "milestone": "m99",
        "selected_lane": lane,
        "routing_confidence": {"score": 78, "level": "medium", "reason": "reasoning advisory item"},
        "lane_selection_reason": "Decision matrix recommends local reasoning advisory review.",
        "planned_artifact_intent": {
            "artifact_type": "local_llm_advisory_plan",
            "generator_milestone": "M99",
            "intent": "Prepare a future local advisory dry-run validation plan.",
            "full_prompt_generated": False,
        },
        "blocked": False,
        "blocked_reasons": [],
        "execution_allowed": False,
    }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_produces_ready_dry_run_for_local_llm_advisory_lane(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(validate_local_llm_advisory_dry_run(config, item_id="m99-advisory-dry-run"))

    assert payload["dry_run"] is True
    assert payload["ready_for_future_advisory_run"] is True
    assert payload["blocked"] is False
    assert payload["item_id"] == "m99-advisory-dry-run"
    assert payload["title"] == "M99 Local LLM Advisory Execution Dry-Run Validator"
    assert payload["selected_lane"] == "local_llm_advisory"
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["recommended_model_role"] == "reasoning/advisory"


def test_blocks_non_advisory_lanes() -> None:
    config = _config(Path("."))

    for lane in (
        "codex_prompt_artifact",
        "local_llm_coding_draft",
        "documentation_agent_dry_run",
        "human_only_manual",
    ):
        payload = _payload(
            validate_local_llm_advisory_dry_run(
                config,
                item_id="m99-advisory-dry-run",
                dispatch_plan=_plan(lane=lane),
            )
        )
        assert payload["ready_for_future_advisory_run"] is False
        assert payload["blocked"] is True
        assert any("M99 only validates local_llm_advisory" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_dispatch_plan_has_blocked_reasons() -> None:
    config = _config(Path("."))
    plan = _plan()
    plan["blocked"] = True
    plan["blocked_reasons"] = ["Queue item requires manual clarification."]

    payload = _payload(validate_local_llm_advisory_dry_run(config, item_id="m99-advisory-dry-run", dispatch_plan=plan))

    assert payload["blocked"] is True
    assert "Queue item requires manual clarification." in payload["blocked_reasons"]
    assert "Dispatch plan is blocked." in payload["blocked_reasons"]


def test_blocks_if_local_only_is_false() -> None:
    config = _config(Path("."))
    plan = _plan()
    plan["local_only"] = False

    payload = _payload(validate_local_llm_advisory_dry_run(config, item_id="m99-advisory-dry-run", dispatch_plan=plan))

    assert payload["blocked"] is True
    assert "Dispatch plan local_only must be true." in payload["blocked_reasons"]


def test_blocks_if_execution_allowed_is_true() -> None:
    config = _config(Path("."))
    plan = _plan()
    plan["execution_allowed"] = True

    payload = _payload(validate_local_llm_advisory_dry_run(config, item_id="m99-advisory-dry-run", dispatch_plan=plan))

    assert payload["blocked"] is True
    assert "Dispatch plan execution_allowed must be false." in payload["blocked_reasons"]


def test_ready_dry_run_includes_required_structured_fields() -> None:
    config = _config(Path("."))

    payload = _payload(
        validate_local_llm_advisory_dry_run(
            config,
            item_id="m99-advisory-dry-run",
            dispatch_plan=_plan(),
        )
    )

    assert payload["item_id"] == "m99-advisory-dry-run"
    assert payload["title"] == "M99 Local LLM Advisory Execution Dry-Run Validator"
    assert payload["selected_lane"] == "local_llm_advisory"
    assert payload["advisory_intent"]
    assert payload["operator_approval_gates"]
    assert payload["validation_expectations"]
    assert payload["next_safe_action"]
    assert "future local LLM advisory artifact" in payload["prompt_outline"]


def test_json_stdout_contains_stable_fields() -> None:
    config = _config(Path("."))

    result = validate_local_llm_advisory_dry_run(
        config,
        item_id="m99-advisory-dry-run",
        dispatch_plan=_plan(),
        output_format="json",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["dry_run"] is True
    assert parsed["ready_for_future_advisory_run"] is True
    assert parsed["blocked"] is False
    assert parsed["item_id"] == "m99-advisory-dry-run"
    assert parsed["selected_lane"] == "local_llm_advisory"
    assert parsed["advisory_intent"]
    assert parsed["recommended_model_role"] == "reasoning/advisory"
    assert parsed["local_only"] is True
    assert parsed["execution_allowed"] is False
    assert parsed["next_safe_action"]


def test_optional_output_file_writes_safely_and_force_overwrites(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output_path = tmp_path / "artifacts" / "local_llm_advisory" / "dry_runs" / "m99.md"

    first = _payload(
        validate_local_llm_advisory_dry_run(
            config,
            item_id="m99-advisory-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
        )
    )
    duplicate = _payload(
        validate_local_llm_advisory_dry_run(
            config,
            item_id="m99-advisory-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
        )
    )
    forced = _payload(
        validate_local_llm_advisory_dry_run(
            config,
            item_id="m99-advisory-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
            force=True,
        )
    )

    assert first["ready_for_future_advisory_run"] is True
    assert Path(first["output_path"]).exists()
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["ready_for_future_advisory_run"] is True
    assert "Local LLM Advisory Dry-Run Validator" in output_path.read_text(encoding="utf-8")
