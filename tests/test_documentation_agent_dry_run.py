import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.documentation_agent_dry_run import validate_documentation_agent_dry_run
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


def _seed_item(config: AppConfig, *, item_id: str = "m100-doc-dry-run") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M100 Documentation Agent Dry-Run Review Workflow",
        description="Review source-of-truth docs and reconciliation warnings without applying documentation changes.",
        status="ready",
        priority="high",
        item_type="documentation",
        tags=["milestone:m100", "documentation", "local-only"],
        notes="Acceptance criteria:\n- Dry-run only\n- No documentation mutation",
    )["ok"] is True


def _plan(*, lane: str = "documentation_agent_dry_run") -> dict[str, object]:
    return {
        "ok": True,
        "local_only": True,
        "dispatch_plan_version": "m97.1",
        "item_id": "m100-doc-dry-run",
        "title": "M100 Documentation Agent Dry-Run Review Workflow",
        "status": "ready",
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "milestone": "m100",
        "selected_lane": lane,
        "routing_confidence": {"score": 81, "level": "high", "reason": "documentation item"},
        "lane_selection_reason": "Queue item is documentation oriented.",
        "planned_artifact_intent": {
            "artifact_type": "documentation_agent_dry_run_plan",
            "generator_milestone": "M100",
            "intent": "Prepare a future non-mutating documentation review plan.",
            "full_prompt_generated": False,
        },
        "blocked": False,
        "blocked_reasons": [],
        "execution_allowed": False,
    }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_produces_ready_result_for_documentation_agent_dry_run(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(validate_documentation_agent_dry_run(config, item_id="m100-doc-dry-run"))

    assert payload["dry_run"] is True
    assert payload["ready_for_future_documentation_review"] is True
    assert payload["blocked"] is False
    assert payload["item_id"] == "m100-doc-dry-run"
    assert payload["title"] == "M100 Documentation Agent Dry-Run Review Workflow"
    assert payload["selected_lane"] == "documentation_agent_dry_run"
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_blocks_non_documentation_lanes() -> None:
    config = _config(Path("."))

    for lane in (
        "codex_prompt_artifact",
        "local_llm_advisory",
        "local_llm_coding_draft",
        "human_only_manual",
    ):
        payload = _payload(
            validate_documentation_agent_dry_run(
                config,
                item_id="m100-doc-dry-run",
                dispatch_plan=_plan(lane=lane),
            )
        )
        assert payload["ready_for_future_documentation_review"] is False
        assert payload["blocked"] is True
        assert any("M100 only validates documentation_agent_dry_run" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_dispatch_plan_has_blocked_reasons() -> None:
    config = _config(Path("."))
    plan = _plan()
    plan["blocked"] = True
    plan["blocked_reasons"] = ["Docs evidence is incomplete."]

    payload = _payload(validate_documentation_agent_dry_run(config, item_id="m100-doc-dry-run", dispatch_plan=plan))

    assert payload["blocked"] is True
    assert "Docs evidence is incomplete." in payload["blocked_reasons"]
    assert "Dispatch plan is blocked." in payload["blocked_reasons"]


def test_blocks_unsafe_local_only_and_execution_flags() -> None:
    config = _config(Path("."))
    non_local = _plan()
    non_local["local_only"] = False
    execution_allowed = _plan()
    execution_allowed["execution_allowed"] = True

    non_local_payload = _payload(
        validate_documentation_agent_dry_run(config, item_id="m100-doc-dry-run", dispatch_plan=non_local)
    )
    execution_payload = _payload(
        validate_documentation_agent_dry_run(config, item_id="m100-doc-dry-run", dispatch_plan=execution_allowed)
    )

    assert "Dispatch plan local_only must be true." in non_local_payload["blocked_reasons"]
    assert "Dispatch plan execution_allowed must be false." in execution_payload["blocked_reasons"]


def test_ready_result_includes_docs_to_review_and_stale_doc_checks() -> None:
    config = _config(Path("."))

    payload = _payload(
        validate_documentation_agent_dry_run(
            config,
            item_id="m100-doc-dry-run",
            dispatch_plan=_plan(),
        )
    )

    assert payload["source_docs_to_review"]
    assert "docs/context/BUILD_STATE.md" in payload["source_docs_to_review"]
    assert payload["expected_doc_updates"]
    assert payload["stale_doc_checks"]
    assert payload["reconciliation_scope"]
    assert payload["operator_approval_gates"]
    assert payload["validation_expectations"]
    assert payload["next_safe_action"]


def test_json_stdout_contains_stable_fields() -> None:
    config = _config(Path("."))

    result = validate_documentation_agent_dry_run(
        config,
        item_id="m100-doc-dry-run",
        dispatch_plan=_plan(),
        output_format="json",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["dry_run"] is True
    assert parsed["ready_for_future_documentation_review"] is True
    assert parsed["blocked"] is False
    assert parsed["item_id"] == "m100-doc-dry-run"
    assert parsed["selected_lane"] == "documentation_agent_dry_run"
    assert parsed["documentation_review_intent"]
    assert parsed["source_docs_to_review"]
    assert parsed["stale_doc_checks"]
    assert parsed["local_only"] is True
    assert parsed["execution_allowed"] is False


def test_optional_output_file_writes_safely_and_force_overwrites(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output_path = tmp_path / "artifacts" / "documentation_agent" / "dry_runs" / "m100.md"

    first = _payload(
        validate_documentation_agent_dry_run(
            config,
            item_id="m100-doc-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
        )
    )
    duplicate = _payload(
        validate_documentation_agent_dry_run(
            config,
            item_id="m100-doc-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
        )
    )
    forced = _payload(
        validate_documentation_agent_dry_run(
            config,
            item_id="m100-doc-dry-run",
            dispatch_plan=_plan(),
            output=output_path,
            force=True,
        )
    )

    assert first["ready_for_future_documentation_review"] is True
    assert Path(first["output_path"]).exists()
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["ready_for_future_documentation_review"] is True
    assert "Documentation Agent Dry-Run Validator" in output_path.read_text(encoding="utf-8")
