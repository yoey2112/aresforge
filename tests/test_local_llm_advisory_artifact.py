import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_llm_advisory_artifact import generate_local_llm_advisory_artifact
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


def _seed_item(config: AppConfig, *, item_id: str = "m110-advisory-artifact") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M110 Local LLM Advisory Artifact Generator",
        description="Prepare a local reasoning advisory request package without executing models.",
        status="ready",
        priority="high",
        item_type="architecture",
        tags=["milestone:m110", "local-only"],
        notes="Acceptance criteria:\n- Generate advisory request artifacts\n- Preserve execution_allowed=false",
    )["ok"] is True
    assert update_local_queue_item_routing_metadata(
        config,
        item_id=item_id,
        routing_metadata={
            "recommended_agent_lane": "architect_planner",
            "recommended_engine": "local_reasoning_llm",
            "routing_policy_source": "test",
            "routing_reason": "Reasoning advisory artifact preparation.",
            "risk_level": "low",
            "complexity_level": "low",
        },
    )["ok"] is True


def _plan(*, lane: str = "local_llm_advisory") -> dict[str, object]:
    return {
        "ok": True,
        "local_only": True,
        "dispatch_plan_version": "m97.1",
        "item_id": "m110-advisory-artifact",
        "title": "M110 Local LLM Advisory Artifact Generator",
        "status": "ready",
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "milestone": "m110",
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
        "decision_matrix_summary": {
            "recommended_engine": "local_reasoning_llm",
            "recommended_model": "qwen2.5:32b",
        },
    }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_generates_local_llm_advisory_artifact_in_default_folder(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(generate_local_llm_advisory_artifact(config, item_id="m110-advisory-artifact"))

    assert payload["artifact_type"] == "local_llm_advisory_request"
    assert payload["generated"] is True
    assert payload["blocked"] is False
    assert payload["item_id"] == "m110-advisory-artifact"
    assert payload["selected_lane"] == "local_llm_advisory"
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["local_llm_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["network_execution_performed"] is False
    assert payload["patch_application_allowed"] is False
    assert Path(payload["output_path"]).exists()
    assert "local_llm_advisory/requests" in str(payload["output_path"]).replace("\\", "/")


def test_blocks_non_advisory_lanes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    for lane in (
        "codex_prompt_artifact",
        "local_llm_coding_draft",
        "documentation_agent_dry_run",
        "human_only_manual",
    ):
        payload = _payload(
            generate_local_llm_advisory_artifact(
                config,
                item_id="m110-advisory-artifact",
                dispatch_plan=_plan(lane=lane),
            )
        )
        assert payload["generated"] is False
        assert payload["blocked"] is True
        assert payload["advisory_prompt"] == ""
        assert any("M110 only generates artifacts" in reason for reason in payload["blocked_reasons"])


def test_json_stdout_contains_contract_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    result = generate_local_llm_advisory_artifact(
        config,
        item_id="m110-advisory-artifact",
        output_format="json",
        model_profile="reasoning-fast",
        reasoning_scope="safety_review",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["artifact_type"] == "local_llm_advisory_request"
    assert parsed["generated"] is True
    assert parsed["requested_model_profile"] == "reasoning-fast"
    assert parsed["reasoning_scope"] == "safety_review"
    assert parsed["expected_response_shape"]["mutation_allowed"] is False
    assert parsed["execution_allowed"] is False


def test_explicit_output_path_writes_json_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    output_path = tmp_path / "artifacts" / "local_llm_advisory" / "requests" / "m110.json"

    payload = _payload(
        generate_local_llm_advisory_artifact(
            config,
            item_id="m110-advisory-artifact",
            output=output_path,
        )
    )
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["generated"] is True
    assert payload["output_path"] == str(output_path)
    assert written["artifact_type"] == "local_llm_advisory_request"
    assert written["advisory_prompt"]


def test_no_overwrite_without_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    output_path = tmp_path / "artifacts" / "local_llm_advisory" / "requests" / "m110.json"

    first = _payload(generate_local_llm_advisory_artifact(config, item_id="m110-advisory-artifact", output=output_path))
    duplicate = _payload(
        generate_local_llm_advisory_artifact(config, item_id="m110-advisory-artifact", output=output_path)
    )
    forced = _payload(
        generate_local_llm_advisory_artifact(
            config,
            item_id="m110-advisory-artifact",
            output=output_path,
            force=True,
        )
    )

    assert first["generated"] is True
    assert duplicate["generated"] is False
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["generated"] is True
