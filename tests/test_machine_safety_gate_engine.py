import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.machine_safety_gate_engine import (
    GATE_PROFILES,
    evaluate_machine_safety_gates,
)


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


def _seed(config: AppConfig, *, tests: bool = True, dependency_done: bool = True) -> None:
    assert init_project_queue(config)["ok"] is True
    if dependency_done:
        assert add_queue_item(
            config,
            item_id="m130-single-agent-real-executor-for-low-risk-agents",
            project_id="aresforge",
            repo_id="aresforge-main",
            title="M130 dependency",
            status="done",
            priority="high",
            item_type="feature",
        )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m131-machine-safety-gate-engine",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M131 Machine Safety Gate Engine",
        description="Create deterministic machine safety gates.",
        status="ready",
        priority="high",
        item_type="feature",
        tags=["milestone:m131", "local-only"],
        dependencies=["m130-single-agent-real-executor-for-low-risk-agents"],
        completion_requires=["tests_run"],
        evidence_required=["smoke_checks"],
        notes="Validation evidence present." if tests else "",
    )["ok"] is True
    if tests:
        queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        for item in queue["work_items"]:
            if item["item_id"] == "m131-machine-safety-gate-engine":
                item["tests_run"] = ["python -m pytest -> passed"]
                item["validation_summary"] = "Validation commands are runnable and reported as passed."
        queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")


def _write_json(path: Path, data: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _safe_artifact(config: AppConfig, profile: str) -> Path:
    if profile == "local_llm_execution":
        path = config.repo_root / "artifacts" / "local_llm_advisory" / "request.json"
    elif profile == "github_sync":
        path = config.repo_root / "artifacts" / "github-sync" / "sync.json"
    elif profile == "multi_agent_orchestration":
        path = config.repo_root / "artifacts" / "orchestration" / "plan.json"
    else:
        path = config.repo_root / "artifacts" / profile / "artifact.json"
    return _write_json(
        path,
        {
            "artifact_type": "machine_gate_fixture",
            "local_only": True,
            "execution_allowed": False,
            "execution_performed": False,
            "tests_reported": ["python -m pytest -> passed"],
            "validation_commands": ["python -m pytest"],
            "capabilities_used": ["read_local_queue"],
        },
    )


def _safe_execution_record(config: AppConfig, profile: str) -> Path:
    return _write_json(
        config.repo_root / "artifacts" / profile / "execution-record.json",
        {
            "execution_record_type": "machine_gate_fixture_execution",
            "local_only": True,
            "external_execution_performed": False,
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "queue_mutation_performed": False,
            "status": "completed",
            "tests_run": ["python -m pytest -> passed"],
            "capabilities_used": ["read_local_artifacts"],
        },
    )


def _docs_patch(config: AppConfig, target: str = "docs/operator/LOCAL_OPERATOR_USAGE.md") -> Path:
    path = config.repo_root / "artifacts" / "patches" / "docs.patch"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"diff --git a/{target} b/{target}",
                f"--- a/{target}",
                f"+++ b/{target}",
                "@@",
                "+M131 docs update",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _transaction_log(config: AppConfig) -> Path:
    return _write_json(
        config.repo_root / ".aresforge" / "queue" / "transaction_log.json",
        {"schema_version": "1.0", "transactions": []},
    )


def test_all_gate_profiles_can_pass_with_required_local_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    _transaction_log(config)

    for profile in GATE_PROFILES:
        kwargs: dict[str, object] = {"gate_profile": profile}
        if profile in {"local_llm_execution", "codex_dispatch", "github_sync", "multi_agent_orchestration"}:
            kwargs["artifact_path"] = _safe_artifact(config, profile)
            kwargs["execution_record"] = _safe_execution_record(config, profile)
        if profile == "docs_only_patch_apply":
            kwargs["patch_path"] = _docs_patch(config)
        if profile in {"codex_dispatch", "github_sync", "multi_agent_orchestration"}:
            kwargs["force"] = True

        result = evaluate_machine_safety_gates(
            config,
            item_id="m131-machine-safety-gate-engine",
            **kwargs,
        )
        payload = result["payload"]

        assert result["ok"] is True, profile
        assert payload["gate_result_type"] == "machine_safety_gate_evaluation"
        assert payload["gate_profile"] == profile
        assert payload["passed"] is True
        assert payload["blocked"] is False
        assert payload["autonomy_allowed"] is True
        assert payload["human_review_required"] is False
        assert payload["execution_performed"] is False
        assert payload["mutation_performed"] is False


def test_missing_queue_item_blocks_gate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    result = evaluate_machine_safety_gates(config, item_id="missing", gate_profile="read_only_agent")
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert any(check["check_id"] == "queue_item_exists" and not check["passed"] for check in payload["checks"])


def test_unsatisfied_dependency_blocks_gate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, dependency_done=False)

    result = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="read_only_agent",
    )
    payload = result["payload"]

    assert result["ok"] is False
    assert any(check["check_id"] == "dependencies_satisfied" and not check["passed"] for check in payload["checks"])


def test_docs_only_patch_allows_docs_and_blocks_source_targets(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    allowed = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="docs_only_patch_apply",
        patch_path=_docs_patch(config, "docs/context/BUILD_STATE.md"),
    )
    blocked = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="docs_only_patch_apply",
        patch_path=_docs_patch(config, "src/aresforge/cli.py"),
    )

    assert allowed["ok"] is True
    assert blocked["ok"] is False
    assert any(
        check["check_id"] == "docs_only_patch_check" and not check["passed"]
        for check in blocked["payload"]["checks"]
    )


def test_forbidden_capability_blocks_gate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _write_json(
        config.repo_root / "artifacts" / "bad" / "artifact.json",
        {
            "local_only": True,
            "execution_allowed": False,
            "execution_performed": False,
            "capabilities_used": ["call_github_api"],
        },
    )

    result = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="local_artifact_write",
        artifact_path=artifact,
    )

    assert result["ok"] is False
    assert any(
        check["check_id"] == "forbidden_capabilities_not_used" and not check["passed"]
        for check in result["payload"]["checks"]
    )


def test_missing_required_artifact_blocks_high_risk_profiles(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)

    result = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="local_llm_execution",
    )

    assert result["ok"] is False
    assert any(
        check["check_id"] == "required_artifacts_exist" and not check["passed"]
        for check in result["payload"]["checks"]
    )


def test_missing_evidence_blocks_tests_required_profiles(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, tests=False)
    artifact = _write_json(
        config.repo_root / "artifacts" / "local_llm_advisory" / "request.json",
        {"local_only": True, "execution_allowed": False, "execution_performed": False},
    )
    record = _write_json(
        config.repo_root / "artifacts" / "local_llm_execution" / "record.json",
        {
            "local_only": True,
            "external_execution_performed": False,
            "model_execution_performed": False,
            "github_execution_performed": False,
            "patch_application_performed": False,
            "queue_mutation_performed": False,
        },
    )

    result = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="local_llm_execution",
        artifact_path=artifact,
        execution_record=record,
    )

    assert result["ok"] is False
    assert any(
        check["check_id"] == "tests_reported_or_runnable" and not check["passed"]
        for check in result["payload"]["checks"]
    )


def test_external_profiles_require_explicit_allowance(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    artifact = _safe_artifact(config, "github_sync")
    record = _safe_execution_record(config, "github_sync")

    blocked = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="github_sync",
        artifact_path=artifact,
        execution_record=record,
    )
    passed = evaluate_machine_safety_gates(
        config,
        item_id="m131-machine-safety-gate-engine",
        gate_profile="github_sync",
        artifact_path=artifact,
        execution_record=record,
        force=True,
    )

    assert blocked["ok"] is False
    assert any(
        check["check_id"] == "external_execution_explicitly_allowed" and not check["passed"]
        for check in blocked["payload"]["checks"]
    )
    assert passed["ok"] is True
