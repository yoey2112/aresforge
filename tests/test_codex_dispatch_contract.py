import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_dispatch_contract import (
    build_codex_dispatch_contract,
    inspect_codex_dispatch_contract,
    prepare_codex_dispatch_dry_run,
    validate_codex_dispatch_contract_payload,
)
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
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


def _seed_project_and_item(config: AppConfig, tmp_path: Path, *, status: str = "in_progress") -> None:
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=tmp_path,
        status="active",
        primary_repo_id="aresforge-main",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-main",
        name="AresForge Main",
        path=tmp_path,
        role="primary",
        status="active",
    )["ok"] is True
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m77-codex-cli-dispatch-contract",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M77 Codex CLI Dispatch Contract",
        description="Define the local dry-run/no-execute Codex dispatch contract.",
        status=status,
        priority="high",
        item_type="architecture",
    )["ok"] is True


def test_contract_payload_shape_is_stable_and_m77_blocks_dispatch(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    payload = build_codex_dispatch_contract(
        config,
        item_id="m77-codex-cli-dispatch-contract",
    )
    validation = validate_codex_dispatch_contract_payload(payload)

    assert payload["ok"] is True
    assert validation["valid"] is True
    assert payload["dry_run_only"] is True
    assert payload["dispatch_allowed"] is False
    assert payload["codex_cli_invocation_allowed"] is False
    assert payload["automatic_next_item_execution_allowed"] is False
    assert payload["operator_approval_required"] is True
    assert payload["operator_approval_status"] == "not_requested"
    assert payload["execution_mode"] == "contract_only"
    assert payload["item_ready_for_dispatch_contract"] is True
    assert payload["working_directory"] == str(tmp_path)
    assert "PREVIEW ONLY - NOT EXECUTABLE IN M77" in payload["codex_cli_command_preview"]
    assert "codex --cd" in payload["codex_cli_command_preview"]
    assert payload["expected_run_state_shape"]["dispatch_state"] == "not_requested"
    assert "running" in payload["allowed_dispatch_states"]
    assert any(gate["gate"] == "explicit_operator_approval_present" for gate in payload["safety_gates"])
    assert any("No Codex CLI process is invoked." == item for item in payload["boundary_confirmations"])


def test_missing_item_returns_safe_blocked_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = build_codex_dispatch_contract(config, item_id="missing-item")

    assert payload["ok"] is False
    assert payload["local_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["dispatch_allowed"] is False
    assert payload["codex_cli_invocation_allowed"] is False
    assert payload["item_ready_for_dispatch_contract"] is False
    assert any("Queue item not found" in blocker for blocker in payload["blockers"])


def test_done_and_cancelled_items_are_not_dispatchable(tmp_path: Path) -> None:
    for status in ("done", "cancelled"):
        config = _config(tmp_path / status)
        config.repo_root.mkdir(parents=True)
        _seed_project_and_item(config, config.repo_root, status=status)

        payload = build_codex_dispatch_contract(
            config,
            item_id="m77-codex-cli-dispatch-contract",
        )

        assert payload["ok"] is True
        assert payload["queue_item_status"] == status
        assert payload["item_ready_for_dispatch_contract"] is False
        assert payload["dispatch_allowed"] is False
        assert any("done/cancelled" in blocker for blocker in payload["blockers"])


def test_contract_inspects_registered_project_repo_binding(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    payload = build_codex_dispatch_contract(config, item_id="m77-codex-cli-dispatch-contract")

    assert payload["project_id"] == "aresforge"
    assert payload["repo_id"] == "aresforge-main"
    assert payload["working_directory"] == str(tmp_path)
    assert payload["safety_gates"][1]["gate"] == "queue_item_belongs_to_registered_managed_project_repo"
    assert payload["safety_gates"][1]["passed"] is True


def test_contract_blocks_when_registered_binding_is_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m77-codex-cli-dispatch-contract",
        project_id="missing-project",
        repo_id="missing-repo",
        title="M77",
        status="in_progress",
    )["ok"] is True
    assert init_managed_project_registry(config)["ok"] is True

    payload = build_codex_dispatch_contract(config, item_id="m77-codex-cli-dispatch-contract")

    assert payload["ok"] is False
    assert payload["item_ready_for_dispatch_contract"] is False
    assert any("Managed project not found" in blocker for blocker in payload["blockers"])


def test_artifact_paths_stay_under_local_codex_dispatch_root(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    payload = build_codex_dispatch_contract(config, item_id="m77-codex-cli-dispatch-contract")

    for key in (
        "expected_contract_path",
        "prompt_artifact_path",
        "expected_run_state_path",
        "expected_stdout_path",
        "expected_stderr_path",
        "expected_artifact_dir",
    ):
        assert str(tmp_path / ".aresforge" / "codex_dispatch") in payload[key]


def test_prepare_dry_run_does_not_mutate_queue_status_or_execute(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"

    payload = prepare_codex_dispatch_dry_run(
        config,
        item_id="m77-codex-cli-dispatch-contract",
        output=tmp_path / ".aresforge" / "codex_dispatch" / "contracts" / "m77.json",
    )
    parsed = json.loads(queue_path.read_text(encoding="utf-8"))
    item = next(item for item in parsed["work_items"] if item["item_id"] == "m77-codex-cli-dispatch-contract")

    assert payload["ok"] is True
    assert payload["wrote_output_file"] is True
    assert item["status"] == "in_progress"
    assert payload["payload"]["execution_mode"] == "dry_run_no_execute"
    assert payload["payload"]["expected_run_state_shape"]["dispatch_state"] == "dry_run_prepared"
    assert payload["payload"]["codex_cli_invocation_allowed"] is False


def test_prepare_dry_run_refuses_output_outside_codex_dispatch_root(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    payload = prepare_codex_dispatch_dry_run(
        config,
        item_id="m77-codex-cli-dispatch-contract",
        output=tmp_path / "outside.json",
    )

    assert payload["ok"] is False
    assert "under .aresforge/codex_dispatch" in json.dumps(payload)


def test_inspect_contract_cli_style_result_returns_stable_json_stdout(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_project_and_item(config, tmp_path)

    result = inspect_codex_dispatch_contract(
        config,
        item_id="m77-codex-cli-dispatch-contract",
        output_format="json",
    )
    parsed = json.loads(result["stdout"])

    assert result["ok"] is True
    assert parsed["item_id"] == "m77-codex-cli-dispatch-contract"
    assert parsed["dry_run_only"] is True
    assert parsed["dispatch_allowed"] is False
    assert parsed["codex_cli_invocation_allowed"] is False


def test_docs_mention_m77_no_execute_boundary() -> None:
    doc_paths = [
        Path("docs/context/BUILD_STATE.md"),
        Path("docs/context/AGENT_CONTEXT.md"),
        Path("docs/roadmap/ROADMAP.md"),
        Path("docs/architecture/RUNNABLE_SKELETON.md"),
        Path("docs/operator/LOCAL_OPERATOR_USAGE.md"),
        Path("docs/architecture/CODEX_CLI_MODEL_PROFILE_CONTRACT.md"),
    ]

    for path in doc_paths:
        text = path.read_text(encoding="utf-8")
        assert "M77" in text
        assert "no-execute" in text.lower() or "No Codex CLI process invocation" in text
        assert "M78" in text
