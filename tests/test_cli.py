import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from aresforge.artifacts.store import ArtifactBundle
from aresforge.config import AppConfig
from aresforge import cli
from aresforge.cli import (
    build_parser,
    command_requires_directories,
    parse_details_input,
    parse_details_json,
    parse_json_object,
    parse_metadata,
    parse_metadata_pairs,
)
from aresforge.validation import ValidationFinding, ValidationReport


def test_cli_has_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for command in (
        "validate-config",
        "validate-registries",
        "migrate",
        "init-roadmap-schema",
        "seed-aresforge-roadmap",
        "inspect-roadmap-db",
        "update-roadmap-task-status",
        "update-roadmap-milestone-status",
        "update-roadmap-area-status",
        "add-roadmap-event",
        "inspect-roadmap-events",
        "add-roadmap-task-dependency",
        "remove-roadmap-task-dependency",
        "inspect-roadmap-task-dependencies",
        "create-work-item-from-roadmap-task",
        "update-work-item-status",
        "start-work-item",
        "complete-work-item-if-ready",
        "plan-work-item-queue-transition",
        "move-work-item-queue",
        "request-work-item-queue-approval",
        "approve-work-item-queue-approval",
        "inspect-work-item-queue-approval",
        "handoff-work-item-to-implementation",
        "inspect-work-item-lifecycle",
        "build-work-item-execution-dossier",
        "export-work-item-operator-prompt",
        "archive-work-item-operator-packet",
        "recommend-next-work-item-action",
        "complete-local-queue-item",
        "generate-local-queue-item-codex-prompt",
        "inspect-codex-dispatch-contract",
        "prepare-codex-dispatch-dry-run",
        "prepare-queue-item-dispatch",
        "inspect-queue-dispatch-plan",
        "generate-codex-dispatch-artifact",
        "generate-local-llm-advisory-artifact",
        "run-local-llm-advisory",
        "validate-documentation-agent-dry-run",
        "generate-doc-agent-patch-proposal",
        "recommend-agent-route",
        "create-dispatch-approval-gate",
        "inspect-dispatch-approval-gate",
        "update-dispatch-approval-gate",
        "inspect-dispatch-artifacts",
        "inspect-artifact-registry",
        "inspect-approval-ledger",
        "inspect-queue-transaction-log",
        "record-artifact-review",
        "prepare-manual-codex-dispatch",
        "intake-patch-proposal",
        "parse-dispatch-result-evidence",
        "recommend-queue-completion",
        "inspect-agent-runtime-boundary",
        "inspect-agent-registry",
        "recommend-llm-decision",
        "run-agent-dry-run",
        "run-agent",
        "evaluate-machine-safety-gates",
        "auto-complete-safe-queue-item",
        "apply-docs-only-patch",
        "probe-local-ollama-provider",
        "inspect-llm-decision-matrix",
        "inspect-local-llm-provider-contract",
        "run-single-ready-codex-queue-item",
        "approve-codex-dispatch",
        "run-codex-dispatch",
        "ingest-codex-result-and-validate",
        "run-github-sync-agent",
        "run-agent-orchestration",
        "generate-autonomous-sprint-closeout",
        "inspect-orchestrator-state-machine",
        "inspect-codex-dispatch-run",
        "list-codex-dispatch-runs",
        "cancel-codex-dispatch-run",
        "recover-codex-dispatch-run",
        "inspect-queue-work-state",
        "inspect-work-item-readiness",
        "inspect-queue-readiness",
        "inspect-project-queue-dashboard",
        "inspect-roadmap-work-item-links",
        "inspect-project-state",
        "inspect-db-state",
        "inspect-project",
        "inspect-registries",
        "list-artifacts",
        "list-review-packages",
        "run-local-review",
        "list-evidence-packages",
        "list-ready-issues",
        "inspect-ready-issue",
        "plan-ready-issue",
        "run-ready-issue-pipeline",
        "run-ready-issue-batch",
        "automation-readiness-report",
        "project-state-summary",
        "inspect-repo-governance",
        "assess-repo",
        "inspect-evidence-bundle-automation-contract",
        "inspect-milestone-closeout-preflight-contract",
        "inspect-canonical-evidence-marker-contract",
        "inspect-repo-bootstrap-contract",
        "inspect-managed-repos",
        "managed-repo-readiness-report",
        "plan-repo-bootstrap",
        "demo-managed-repo-governance",
        "plan-batch-closeout",
        "plan-sprint-issues",
        "plan-self-managed-milestone",
        "inspect-self-managed-milestone-execution-contract",
        "simulate-self-managed-milestone-execution",
        "generate-self-managed-milestone-handoff",
        "generate-self-managed-issue-script",
        "generate-child-closeout-script",
        "generate-child-closeout-evidence-bundle",
        "generate-child-evidence-marker-template",
        "generate-parent-closeout-evidence-bundle",
        "generate-parent-closeout-marker-template",
        "generate-pr-evidence-bundle",
        "generate-pr-evidence-marker-template",
        "simulate-evidence-bundle-generation",
        "generate-evidence-comment-template",
        "run-autonomous-cycle",
        "inspect-autonomous-run",
        "inspect-milestone-state",
        "plan-milestone-execution-queue",
        "check-issue-evidence-readiness",
        "check-milestone-evidence-readiness",
        "plan-milestone-final-reconciliation",
        "inspect-milestone-dashboard",
        "inspect-parent-closeout-readiness",
        "inspect-parent-child-linkage-preflight",
        "inspect-child-evidence-marker-preflight",
        "inspect-pr-mapping-preflight",
        "generate-closeout-preflight-repair-guidance",
        "inspect-milestone-closeout-preflight",
        "check-closeout-readiness-by-construction",
        "generate-offline-closeout-state-template",
        "generate-handoff-package",
        "generate-safe-dispatch-handoff",
        "generate-local-milestone-template",
        "inspect-local-milestone",
        "check-local-milestone-readiness",
        "generate-local-milestone-closeout",
        "plan-github-sync",
        "plan-agent-orchestration",
        "init-project-state",
        "add-local-queue-item",
        "inspect-queue-consistency",
        "inspect-local-queue-item-readiness",
        "start-local-queue-item",
        "update-project-state",
        "append-operation-log",
        "inspect-operation-log",
        "init-managed-project-registry",
        "register-managed-project",
        "register-managed-repo",
        "inspect-managed-project-registry",
        "inspect-managed-project",
        "inspect-managed-repo",
        "seed-aresforge-self-project",
        "inspect-local-project-dashboard",
        "list-local-projects",
        "inspect-local-project-readiness",
        "inspect-local-queue-agent-summary",
        "inspect-local-project-report",
        "inspect-self-managed-project",
        "generate-preflight-baseline-snapshot",
        "diff-preflight-snapshots",
        "inspect-child-execution-gates",
        "inspect-sequential-run-state",
        "plan-sequential-run-recovery",
        "generate-sequential-handoff-package",
        "run-sequential-child-closeout-flow",
        "generate-sequential-closeout-execution-package",
        "inspect-closeout-planning-drift",
        "plan-github-mutation",
        "execute-github-issue-comment",
        "execute-github-issue-close",
        "prepare-pr-body-update",
        "inspect-github-mutation-audit-log",
        "qa-review-pr",
        "qa-closeout-pr",
        "validate-pr-end-to-end",
        "inspect-review-package",
        "inspect-artifact",
        "inspect-evidence-package",
        "inspect-model",
        "inspect-queue",
        "inspect-work-item",
        "list-projects",
        "list-agents",
        "list-models",
        "list-queues",
        "create-work-item",
        "list-work-items",
        "generate-prompt-package",
        "record-evidence-package",
        "test-ollama",
        "inspect-ollama-health",
        "prepare-local-llm-advisory-run",
        "prepare-local-coding-draft",
        "inspect-human-gated-patch-application-contract",
        "inspect-model-usage-report",
        "inspect-sprint-batch-report",
        "plan-operator-batch",
        "plan-operator-batch-v2",
        "inspect-documentation-agent-contract",
        "plan-doc-reconciliation",
        "prepare-codex-handoff",
    ):
        assert command in help_text


def test_parse_metadata_requires_object() -> None:
    assert parse_metadata('{"priority_hint": "high"}') == {"priority_hint": "high"}


def test_parse_metadata_pairs() -> None:
    assert parse_metadata_pairs(["issue=81", "protected_issue=39"]) == {
        "issue": "81",
        "protected_issue": "39",
    }


def test_parse_json_object_accepts_object() -> None:
    assert parse_json_object('{"previous_status": "planned"}') == {"previous_status": "planned"}


def test_parse_json_object_rejects_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        parse_json_object("{not json}")


def test_parse_json_object_rejects_non_object_json() -> None:
    with pytest.raises(ValueError, match="details must decode to a JSON object."):
        parse_json_object('["not", "an", "object"]')


def test_parse_json_object_accepts_wrapped_json_string() -> None:
    assert parse_json_object('"{\\"source\\":\\"unit-test\\",\\"mode\\":\\"local-only\\"}"') == {
        "source": "unit-test",
        "mode": "local-only",
    }


def test_parse_details_json_returns_empty_dict_when_omitted() -> None:
    parsed, error = parse_details_json(None)
    assert error is None
    assert parsed == {}


def test_parse_details_json_rejects_non_object_json() -> None:
    parsed, error = parse_details_json('["not","object"]')
    assert parsed is None
    assert error == {"ok": False, "error": "invalid_details_json"}


def test_parse_details_input_returns_empty_dict_when_omitted() -> None:
    parsed, error = parse_details_input(None, None)
    assert error is None
    assert parsed == {}


def test_parse_details_input_rejects_conflicting_inputs() -> None:
    parsed, error = parse_details_input('{"source":"unit-test"}', "details.json")
    assert parsed is None
    assert error == {"ok": False, "error": "conflicting_details_input"}


def test_parse_details_input_reads_json_file(tmp_path: Path) -> None:
    details_path = tmp_path / "details.json"
    details_path.write_text('{"source":"unit-test","mode":"local-only"}', encoding="utf-8")
    parsed, error = parse_details_input(None, str(details_path))
    assert error is None
    assert parsed == {"source": "unit-test", "mode": "local-only"}


def test_parse_details_input_reads_bom_prefixed_json_file(tmp_path: Path) -> None:
    details_path = tmp_path / "details-bom.json"
    details_path.write_text(
        '\ufeff{"source":"unit-test","mode":"local-only"}',
        encoding="utf-8",
    )
    parsed, error = parse_details_input(None, str(details_path))
    assert error is None
    assert parsed == {"source": "unit-test", "mode": "local-only"}


def test_parse_details_input_rejects_invalid_json_file(tmp_path: Path) -> None:
    details_path = tmp_path / "details.json"
    details_path.write_text("{not-json}", encoding="utf-8")
    parsed, error = parse_details_input(None, str(details_path))
    assert parsed is None
    assert error == {"ok": False, "error": "invalid_details_json"}


def test_parse_details_input_rejects_non_object_json_file(tmp_path: Path) -> None:
    details_path = tmp_path / "details.json"
    details_path.write_text('["not","object"]', encoding="utf-8")
    parsed, error = parse_details_input(None, str(details_path))
    assert parsed is None
    assert error == {"ok": False, "error": "invalid_details_json"}


def test_cli_route_status_defaults_use_canonical_vocabulary() -> None:
    parser = build_parser()

    create_args = parser.parse_args(["create-work-item", "--title", "Test", "--queue-id", "queue-intake"])
    assert create_args.route_status == "queued"

    prompt_args = parser.parse_args(
        ["generate-prompt-package", "--title", "Prompt", "--objective", "Objective"]
    )
    assert prompt_args.route_status == "ready"

    handoff_args = parser.parse_args(
        [
            "prepare-codex-handoff",
            "--title",
            "Handoff",
            "--summary",
            "Summary",
            "--requested-output",
            "Output",
        ]
    )
    assert handoff_args.route_status == "ready"


def test_cli_seed_aresforge_self_project_returns_stable_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)

    exit_code = cli.main(
        [
            "seed-aresforge-self-project",
            "--root-path",
            str(tmp_path),
            "--set-active",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["repo_id"] == "aresforge-main"
    assert payload["active_project_status"]["active_project_id"] == "aresforge"
    assert len(payload["seeded_queue_items"]) == 6
    assert all(item["status"] == "proposed" for item in payload["seeded_queue_items"])
    assert any("No GitHub API calls." == item for item in payload["boundary_confirmations"])


def test_cli_update_roadmap_task_status_dispatch_parses_details_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_update_roadmap_task_status(
        _conn: object,
        *,
        task_id: str,
        status: str,
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["task_id"] = task_id
        seen["status"] = status
        seen["summary"] = summary
        seen["details"] = details
        return {"ok": True, "changed": True, "task": {"id": task_id, "status": status}, "event_id": "roadmap-event-abc123"}

    monkeypatch.setattr(cli, "update_roadmap_task_status", fake_update_roadmap_task_status)

    exit_code = cli.main(
        [
            "update-roadmap-task-status",
            "--task-id",
            "rt-02-starter",
            "--status",
            "active",
            "--summary",
            "Begin state authority lifecycle contract work",
            "--details-json",
            '{"source":"unit-test","mode":"local-only"}',
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test", "mode": "local-only"}
    assert payload["ok"] is True


def test_cli_add_roadmap_event_dispatch_parses_details_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_add_roadmap_event(
        _conn: object,
        project_id: str,
        event_type: str,
        actor: str = "aresforge-cli",
        summary: str = "",
        details: dict[str, object] | None = None,
        area_id: str | None = None,
        milestone_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        seen["project_id"] = project_id
        seen["event_type"] = event_type
        seen["summary"] = summary
        seen["details"] = details
        seen["task_id"] = task_id
        return {"ok": True, "event_id": "roadmap-event-def456", "event": {"id": "roadmap-event-def456"}}

    monkeypatch.setattr(cli, "add_roadmap_event", fake_add_roadmap_event)

    exit_code = cli.main(
        [
            "add-roadmap-event",
            "--event-type",
            "roadmap_operator_note",
            "--summary",
            "M2 smoke test event",
            "--task-id",
            "rt-02-starter",
            "--details-json",
            '{"source":"unit-test"}',
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test"}
    assert seen["task_id"] == "rt-02-starter"
    assert payload["ok"] is True


def test_cli_update_roadmap_task_status_dispatch_defaults_details_to_empty_dict_when_omitted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_update_roadmap_task_status(
        _conn: object,
        *,
        task_id: str,
        status: str,
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["details"] = details
        return {"ok": True, "changed": True, "task": {"id": task_id, "status": status}, "event_id": "roadmap-event-abc123"}

    monkeypatch.setattr(cli, "update_roadmap_task_status", fake_update_roadmap_task_status)

    exit_code = cli.main(
        [
            "update-roadmap-task-status",
            "--task-id",
            "rt-02-starter",
            "--status",
            "active",
            "--summary",
            "Unit test status update",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["details"] == {}
    assert payload["ok"] is True


def test_cli_update_roadmap_task_status_dispatch_parses_details_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    details_path = tmp_path / "details.json"
    details_path.write_text('{"source":"unit-test","mode":"local-only"}', encoding="utf-8")
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_update_roadmap_task_status(
        _conn: object,
        *,
        task_id: str,
        status: str,
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["details"] = details
        return {"ok": True, "changed": True, "task": {"id": task_id, "status": status}, "event_id": "roadmap-event-abc123"}

    monkeypatch.setattr(cli, "update_roadmap_task_status", fake_update_roadmap_task_status)
    exit_code = cli.main(
        [
            "update-roadmap-task-status",
            "--task-id",
            "rt-02-starter",
            "--status",
            "active",
            "--summary",
            "Unit test status update",
            "--details-file",
            str(details_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test", "mode": "local-only"}
    assert payload["ok"] is True


def test_cli_update_roadmap_task_status_dispatch_parses_bom_details_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    details_path = tmp_path / "details-bom.json"
    details_path.write_text(
        '\ufeff{"source":"unit-test","mode":"local-only"}',
        encoding="utf-8",
    )
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_update_roadmap_task_status(
        _conn: object,
        *,
        task_id: str,
        status: str,
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["details"] = details
        return {"ok": True, "changed": True, "task": {"id": task_id, "status": status}, "event_id": "roadmap-event-abc123"}

    monkeypatch.setattr(cli, "update_roadmap_task_status", fake_update_roadmap_task_status)
    exit_code = cli.main(
        [
            "update-roadmap-task-status",
            "--task-id",
            "rt-03-starter",
            "--status",
            "active",
            "--summary",
            "Unit test status update",
            "--details-file",
            str(details_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test", "mode": "local-only"}
    assert payload["ok"] is True


def test_cli_update_work_item_status_dispatch_parses_details_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    details_path = tmp_path / "details.json"
    details_path.write_text('{"source":"unit-test","mode":"local-only"}', encoding="utf-8")
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_update_work_item_status(
        _conn: object,
        work_item_id: str,
        status: str,
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["work_item_id"] = work_item_id
        seen["status"] = status
        seen["summary"] = summary
        seen["details"] = details
        return {"ok": True, "changed": True, "work_item_id": work_item_id, "status": status}

    monkeypatch.setattr(cli, "update_work_item_status", fake_update_work_item_status)

    exit_code = cli.main(
        [
            "update-work-item-status",
            "--work-item-id",
            "work-1",
            "--status",
            "active",
            "--summary",
            "Advance local queue",
            "--details-file",
            str(details_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test", "mode": "local-only"}
    assert payload["ok"] is True


def test_cli_add_roadmap_event_dispatch_parses_details_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    details_path = tmp_path / "details.json"
    details_path.write_text('{"source":"unit-test"}', encoding="utf-8")
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_add_roadmap_event(
        _conn: object,
        project_id: str,
        event_type: str,
        actor: str = "aresforge-cli",
        summary: str = "",
        details: dict[str, object] | None = None,
        area_id: str | None = None,
        milestone_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, object]:
        seen["details"] = details
        return {"ok": True, "event_id": "roadmap-event-def456", "event": {"id": "roadmap-event-def456"}}

    monkeypatch.setattr(cli, "add_roadmap_event", fake_add_roadmap_event)
    exit_code = cli.main(
        [
            "add-roadmap-event",
            "--event-type",
            "roadmap_operator_note",
            "--summary",
            "Unit test event",
            "--task-id",
            "rt-02-starter",
            "--details-file",
            str(details_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen["details"] == {"source": "unit-test"}
    assert payload["ok"] is True


def test_cli_create_work_item_from_roadmap_task_dispatch_parses_details_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    details_path = tmp_path / "details.json"
    details_path.write_text('{"source":"unit-test","mode":"local-only"}', encoding="utf-8")
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "apply_migrations", lambda _conn, _dir: [])
    monkeypatch.setattr(cli, "bootstrap_reference_data", lambda _conn, _config: None)

    def fake_create_work_item_from_roadmap_task(
        _conn: object,
        roadmap_task_id: str,
        queue_id: str | None = None,
        priority: str = "normal",
        actor: str = "aresforge-cli",
        summary: str | None = None,
        details: dict[str, object] | None = None,
    ) -> dict[str, object]:
        seen["roadmap_task_id"] = roadmap_task_id
        seen["queue_id"] = queue_id
        seen["priority"] = priority
        seen["summary"] = summary
        seen["details"] = details
        return {
            "ok": True,
            "created": True,
            "existing": False,
            "roadmap_task_id": roadmap_task_id,
            "work_item_id": "work-123",
            "link_id": "rwil-123",
            "queue_id": queue_id or "queue-planning",
            "event_id": "roadmap-event-123",
            "work_item": {"id": "work-123"},
            "link": {"id": "rwil-123"},
        }

    monkeypatch.setattr(cli, "create_work_item_from_roadmap_task", fake_create_work_item_from_roadmap_task)
    exit_code = cli.main(
        [
            "create-work-item-from-roadmap-task",
            "--task-id",
            "rt-02-starter",
            "--queue-id",
            "queue-planning",
            "--priority",
            "high",
            "--summary",
            "Bridge roadmap task into local work queue.",
            "--details-file",
            str(details_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen["roadmap_task_id"] == "rt-02-starter"
    assert seen["queue_id"] == "queue-planning"
    assert seen["priority"] == "high"
    assert seen["details"] == {"source": "unit-test", "mode": "local-only"}
    assert payload["ok"] is True


def test_cli_roadmap_mutation_rejects_invalid_details_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("invalid details json must fail before database connection"),
    )
    exit_code = cli.main(
        [
            "update-roadmap-task-status",
            "--task-id",
            "rt-02-starter",
            "--status",
            "active",
            "--details-json",
            "{not json}",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload == {"ok": False, "error": "invalid_details_json"}


def test_cli_roadmap_mutation_rejects_non_object_details_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("non-object details json must fail before database connection"),
    )
    exit_code = cli.main(
        [
            "add-roadmap-event",
            "--event-type",
            "roadmap_operator_note",
            "--summary",
            "M2 smoke test event",
            "--details-json",
            '["not", "object"]',
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload == {"ok": False, "error": "invalid_details_json"}


def test_cli_inspection_commands_require_expected_ids() -> None:
    parser = build_parser()

    inspect_project_args = parser.parse_args(["inspect-project", "--project-id", "project-aresforge"])
    assert inspect_project_args.project_id == "project-aresforge"
    inspect_registries_args = parser.parse_args(["inspect-registries"])
    assert inspect_registries_args.command == "inspect-registries"
    list_artifacts_args = parser.parse_args(["list-artifacts"])
    assert list_artifacts_args.command == "list-artifacts"
    list_review_packages_args = parser.parse_args(["list-review-packages"])
    assert list_review_packages_args.command == "list-review-packages"
    run_local_review_args = parser.parse_args(["run-local-review"])
    assert run_local_review_args.command == "run-local-review"
    assert run_local_review_args.project_id == "project-aresforge"
    assert run_local_review_args.model_id == "model-ollama-default"
    assert run_local_review_args.include_artifacts is False
    assert run_local_review_args.include_evidence_packages is False
    assert run_local_review_args.write_review_package is False
    list_evidence_args = parser.parse_args(["list-evidence-packages"])
    assert list_evidence_args.command == "list-evidence-packages"
    list_ready_args = parser.parse_args(["list-ready-issues"])
    assert list_ready_args.command == "list-ready-issues"
    inspect_ready_args = parser.parse_args(["inspect-ready-issue", "--issue-number", "114"])
    assert inspect_ready_args.issue_number == 114
    plan_ready_args = parser.parse_args(["plan-ready-issue", "--issue-number", "114"])
    assert plan_ready_args.issue_number == 114
    run_pipeline_plan_args = parser.parse_args(
        ["run-ready-issue-pipeline", "--issue-number", "120", "--plan-only"]
    )
    assert run_pipeline_plan_args.issue_number == 120
    assert run_pipeline_plan_args.pr_number is None
    assert run_pipeline_plan_args.plan_only is True
    assert run_pipeline_plan_args.execute_closeout is False
    assert run_pipeline_plan_args.write_review_package is False
    assert run_pipeline_plan_args.write_evidence_package is False
    assert run_pipeline_plan_args.write_implementation_handoff is False
    run_batch_plan_args = parser.parse_args(
        ["run-ready-issue-batch", "--plan-only"]
    )
    assert run_batch_plan_args.plan_only is True
    assert run_batch_plan_args.write_selected_handoffs is False
    assert run_batch_plan_args.timestamp_override is None
    readiness_report_args = parser.parse_args(["automation-readiness-report"])
    assert readiness_report_args.command == "automation-readiness-report"
    project_state_summary_args = parser.parse_args(["project-state-summary"])
    assert project_state_summary_args.command == "project-state-summary"
    governance_args = parser.parse_args(["inspect-repo-governance"])
    assert governance_args.command == "inspect-repo-governance"
    assess_repo_args = parser.parse_args(["assess-repo"])
    assert assess_repo_args.command == "assess-repo"
    assert assess_repo_args.output == "docs/audit"
    assert assess_repo_args.format == "both"
    assert assess_repo_args.include_tests is True
    assert assess_repo_args.include_docs is True
    assert assess_repo_args.force is False
    evidence_contract_args = parser.parse_args(["inspect-evidence-bundle-automation-contract"])
    assert evidence_contract_args.command == "inspect-evidence-bundle-automation-contract"
    milestone_preflight_contract_args = parser.parse_args(["inspect-milestone-closeout-preflight-contract"])
    assert milestone_preflight_contract_args.command == "inspect-milestone-closeout-preflight-contract"
    canonical_marker_contract_args = parser.parse_args(["inspect-canonical-evidence-marker-contract"])
    assert canonical_marker_contract_args.command == "inspect-canonical-evidence-marker-contract"
    bootstrap_contract_args = parser.parse_args(["inspect-repo-bootstrap-contract"])
    assert bootstrap_contract_args.command == "inspect-repo-bootstrap-contract"
    managed_repos_args = parser.parse_args(["inspect-managed-repos"])
    assert managed_repos_args.command == "inspect-managed-repos"
    readiness_args = parser.parse_args(["managed-repo-readiness-report"])
    assert readiness_args.command == "managed-repo-readiness-report"
    plan_bootstrap_args = parser.parse_args(["plan-repo-bootstrap"])
    assert plan_bootstrap_args.command == "plan-repo-bootstrap"
    demo_governance_args = parser.parse_args(["demo-managed-repo-governance"])
    assert demo_governance_args.command == "demo-managed-repo-governance"
    plan_batch_closeout_args = parser.parse_args(["plan-batch-closeout", "--parent-issue", "172"])
    assert plan_batch_closeout_args.command == "plan-batch-closeout"
    assert plan_batch_closeout_args.parent_issue == 172
    plan_sprint_issues_args = parser.parse_args(
        ["plan-sprint-issues", "--definition", "tests/fixtures/m12-sprint-definition.json"]
    )
    assert plan_sprint_issues_args.command == "plan-sprint-issues"
    assert plan_sprint_issues_args.definition == "tests/fixtures/m12-sprint-definition.json"
    plan_self_managed_args = parser.parse_args(["plan-self-managed-milestone"])
    assert plan_self_managed_args.command == "plan-self-managed-milestone"
    assert plan_self_managed_args.mode == "read-only"
    inspect_contract_args = parser.parse_args(["inspect-self-managed-milestone-execution-contract"])
    assert inspect_contract_args.command == "inspect-self-managed-milestone-execution-contract"
    simulate_self_managed_args = parser.parse_args(
        ["simulate-self-managed-milestone-execution", "--parent-issue", "345"]
    )
    assert simulate_self_managed_args.command == "simulate-self-managed-milestone-execution"
    assert simulate_self_managed_args.parent_issue == 345
    handoff_args = parser.parse_args(
        ["generate-self-managed-milestone-handoff", "--parent-issue", "345", "--completed-child", "349"]
    )
    assert handoff_args.command == "generate-self-managed-milestone-handoff"
    assert handoff_args.parent_issue == 345
    assert handoff_args.completed_child == 349
    generate_self_managed_script_args = parser.parse_args(["generate-self-managed-issue-script"])
    assert generate_self_managed_script_args.command == "generate-self-managed-issue-script"
    assert generate_self_managed_script_args.mode == "read-only"
    assert generate_self_managed_script_args.run_id is None
    assert generate_self_managed_script_args.target_issue is None
    generate_child_closeout_script_args = parser.parse_args(
        ["generate-child-closeout-script", "--issue", "296"]
    )
    assert generate_child_closeout_script_args.command == "generate-child-closeout-script"
    assert generate_child_closeout_script_args.issue == 296
    generate_child_closeout_bundle_args = parser.parse_args(
        [
            "generate-child-closeout-evidence-bundle",
            "--parent-issue",
            "362",
            "--child-issue",
            "365",
        ]
    )
    assert generate_child_closeout_bundle_args.command == "generate-child-closeout-evidence-bundle"
    assert generate_child_closeout_bundle_args.parent_issue == 362
    assert generate_child_closeout_bundle_args.child_issue == 365
    generate_child_marker_template_args = parser.parse_args(
        [
            "generate-child-evidence-marker-template",
            "--parent-issue",
            "400",
            "--child-issue",
            "403",
        ]
    )
    assert generate_child_marker_template_args.command == "generate-child-evidence-marker-template"
    assert generate_child_marker_template_args.parent_issue == 400
    assert generate_child_marker_template_args.child_issue == 403
    generate_parent_closeout_bundle_args = parser.parse_args(
        [
            "generate-parent-closeout-evidence-bundle",
            "--parent-issue",
            "362",
        ]
    )
    assert generate_parent_closeout_bundle_args.command == "generate-parent-closeout-evidence-bundle"
    assert generate_parent_closeout_bundle_args.parent_issue == 362
    assert generate_parent_closeout_bundle_args.state_file is None
    generate_parent_closeout_bundle_state_file_args = parser.parse_args(
        [
            "generate-parent-closeout-evidence-bundle",
            "--parent-issue",
            "362",
            "--state-file",
            "artifacts/offline-state/m25-421.json",
        ]
    )
    assert generate_parent_closeout_bundle_state_file_args.command == "generate-parent-closeout-evidence-bundle"
    assert generate_parent_closeout_bundle_state_file_args.parent_issue == 362
    assert generate_parent_closeout_bundle_state_file_args.state_file == "artifacts/offline-state/m25-421.json"
    generate_parent_marker_template_args = parser.parse_args(
        [
            "generate-parent-closeout-marker-template",
            "--parent-issue",
            "400",
        ]
    )
    assert generate_parent_marker_template_args.command == "generate-parent-closeout-marker-template"
    assert generate_parent_marker_template_args.parent_issue == 400
    generate_pr_evidence_bundle_args = parser.parse_args(
        [
            "generate-pr-evidence-bundle",
            "--issue",
            "367",
            "--pr",
            "376",
        ]
    )
    assert generate_pr_evidence_bundle_args.command == "generate-pr-evidence-bundle"
    assert generate_pr_evidence_bundle_args.issue == 367
    assert generate_pr_evidence_bundle_args.pr == 376
    generate_pr_marker_template_args = parser.parse_args(
        [
            "generate-pr-evidence-marker-template",
            "--issue",
            "404",
            "--pr",
            "414",
        ]
    )
    assert generate_pr_marker_template_args.command == "generate-pr-evidence-marker-template"
    assert generate_pr_marker_template_args.issue == 404
    assert generate_pr_marker_template_args.pr == 414
    simulate_evidence_bundle_args = parser.parse_args(
        [
            "simulate-evidence-bundle-generation",
            "--parent-issue",
            "362",
        ]
    )
    assert simulate_evidence_bundle_args.command == "simulate-evidence-bundle-generation"
    assert simulate_evidence_bundle_args.parent_issue == 362
    generate_evidence_comment_template_args = parser.parse_args(
        ["generate-evidence-comment-template", "--issue", "297"]
    )
    assert generate_evidence_comment_template_args.command == "generate-evidence-comment-template"
    assert generate_evidence_comment_template_args.issue == 297
    autonomous_cycle_args = parser.parse_args(
        [
            "run-autonomous-cycle",
            "--mode",
            "dry-run",
            "--parent-issue",
            "258",
            "--target-issue",
            "259",
        ]
    )
    assert autonomous_cycle_args.mode == "dry-run"
    assert autonomous_cycle_args.parent_issue == 258
    assert autonomous_cycle_args.target_issue == 259
    assert autonomous_cycle_args.validation_command == []
    assert autonomous_cycle_args.allow_empty_commit is False
    inspect_autonomous_run_args = parser.parse_args(
        ["inspect-autonomous-run", "--run-id", "run-m16-259-abc123"]
    )
    assert inspect_autonomous_run_args.run_id == "run-m16-259-abc123"
    inspect_milestone_state_args = parser.parse_args(
        ["inspect-milestone-state", "--parent-issue", "269"]
    )
    assert inspect_milestone_state_args.command == "inspect-milestone-state"
    assert inspect_milestone_state_args.parent_issue == 269
    assert inspect_milestone_state_args.state_file is None
    inspect_milestone_state_state_file_args = parser.parse_args(
        ["inspect-milestone-state", "--parent-issue", "269", "--state-file", "artifacts/offline-state/m25-421.json"]
    )
    assert inspect_milestone_state_state_file_args.command == "inspect-milestone-state"
    assert inspect_milestone_state_state_file_args.parent_issue == 269
    assert inspect_milestone_state_state_file_args.state_file == "artifacts/offline-state/m25-421.json"
    plan_milestone_execution_queue_args = parser.parse_args(
        ["plan-milestone-execution-queue", "--parent-issue", "269"]
    )
    assert plan_milestone_execution_queue_args.command == "plan-milestone-execution-queue"
    assert plan_milestone_execution_queue_args.parent_issue == 269
    check_issue_evidence_args = parser.parse_args(
        ["check-issue-evidence-readiness", "--issue", "270"]
    )
    assert check_issue_evidence_args.command == "check-issue-evidence-readiness"
    assert check_issue_evidence_args.issue == 270
    check_milestone_evidence_args = parser.parse_args(
        ["check-milestone-evidence-readiness", "--parent-issue", "269"]
    )
    assert check_milestone_evidence_args.command == "check-milestone-evidence-readiness"
    assert check_milestone_evidence_args.parent_issue == 269
    assert check_milestone_evidence_args.state_file is None
    check_milestone_evidence_state_file_args = parser.parse_args(
        ["check-milestone-evidence-readiness", "--parent-issue", "269", "--state-file", "artifacts/offline-state/m25-421.json"]
    )
    assert check_milestone_evidence_state_file_args.command == "check-milestone-evidence-readiness"
    assert check_milestone_evidence_state_file_args.parent_issue == 269
    assert check_milestone_evidence_state_file_args.state_file == "artifacts/offline-state/m25-421.json"
    check_closeout_readiness_args = parser.parse_args(
        ["check-closeout-readiness-by-construction", "--parent-issue", "421"]
    )
    assert check_closeout_readiness_args.command == "check-closeout-readiness-by-construction"
    assert check_closeout_readiness_args.parent_issue == 421
    assert check_closeout_readiness_args.state_file is None
    check_closeout_readiness_state_file_args = parser.parse_args(
        [
            "check-closeout-readiness-by-construction",
            "--parent-issue",
            "421",
            "--state-file",
            "artifacts/offline-state/m25-421.json",
        ]
    )
    assert check_closeout_readiness_state_file_args.command == "check-closeout-readiness-by-construction"
    assert check_closeout_readiness_state_file_args.parent_issue == 421
    assert check_closeout_readiness_state_file_args.state_file == "artifacts/offline-state/m25-421.json"
    offline_template_args = parser.parse_args(
        [
            "generate-offline-closeout-state-template",
            "--parent-issue",
            "421",
            "--children",
            "422,423,424",
            "--output",
            "artifacts/offline-state/m25-421.template.json",
        ]
    )
    assert offline_template_args.command == "generate-offline-closeout-state-template"
    assert offline_template_args.parent_issue == 421
    assert offline_template_args.children == "422,423,424"
    assert offline_template_args.output == "artifacts/offline-state/m25-421.template.json"
    assert offline_template_args.force is False
    plan_final_reconciliation_args = parser.parse_args(
        ["plan-milestone-final-reconciliation", "--parent-issue", "269"]
    )
    assert plan_final_reconciliation_args.command == "plan-milestone-final-reconciliation"
    assert plan_final_reconciliation_args.parent_issue == 269
    inspect_milestone_dashboard_args = parser.parse_args(
        ["inspect-milestone-dashboard", "--parent-issue", "269"]
    )
    assert inspect_milestone_dashboard_args.command == "inspect-milestone-dashboard"
    assert inspect_milestone_dashboard_args.parent_issue == 269
    inspect_parent_closeout_readiness_args = parser.parse_args(
        ["inspect-parent-closeout-readiness", "--parent-issue", "269"]
    )
    assert inspect_parent_closeout_readiness_args.command == "inspect-parent-closeout-readiness"
    assert inspect_parent_closeout_readiness_args.parent_issue == 269
    assert inspect_parent_closeout_readiness_args.state_file is None
    inspect_parent_closeout_readiness_state_file_args = parser.parse_args(
        [
            "inspect-parent-closeout-readiness",
            "--parent-issue",
            "269",
            "--state-file",
            "artifacts/offline-state/m25-421.json",
        ]
    )
    assert inspect_parent_closeout_readiness_state_file_args.command == "inspect-parent-closeout-readiness"
    assert inspect_parent_closeout_readiness_state_file_args.parent_issue == 269
    assert inspect_parent_closeout_readiness_state_file_args.state_file == "artifacts/offline-state/m25-421.json"
    inspect_parent_child_linkage_preflight_args = parser.parse_args(
        ["inspect-parent-child-linkage-preflight", "--parent-issue", "381"]
    )
    assert inspect_parent_child_linkage_preflight_args.command == "inspect-parent-child-linkage-preflight"
    assert inspect_parent_child_linkage_preflight_args.parent_issue == 381
    inspect_child_evidence_marker_preflight_args = parser.parse_args(
        ["inspect-child-evidence-marker-preflight", "--parent-issue", "381"]
    )
    assert inspect_child_evidence_marker_preflight_args.command == "inspect-child-evidence-marker-preflight"
    assert inspect_child_evidence_marker_preflight_args.parent_issue == 381
    inspect_pr_mapping_preflight_args = parser.parse_args(
        ["inspect-pr-mapping-preflight", "--parent-issue", "381"]
    )
    assert inspect_pr_mapping_preflight_args.command == "inspect-pr-mapping-preflight"
    assert inspect_pr_mapping_preflight_args.parent_issue == 381
    generate_closeout_repair_guidance_args = parser.parse_args(
        ["generate-closeout-preflight-repair-guidance", "--parent-issue", "381"]
    )
    assert generate_closeout_repair_guidance_args.command == "generate-closeout-preflight-repair-guidance"
    assert generate_closeout_repair_guidance_args.parent_issue == 381
    inspect_milestone_closeout_preflight_args = parser.parse_args(
        ["inspect-milestone-closeout-preflight", "--parent-issue", "381"]
    )
    assert inspect_milestone_closeout_preflight_args.command == "inspect-milestone-closeout-preflight"
    assert inspect_milestone_closeout_preflight_args.parent_issue == 381
    generate_preflight_snapshot_args = parser.parse_args(
        ["generate-preflight-baseline-snapshot", "--parent-issue", "400"]
    )
    assert generate_preflight_snapshot_args.command == "generate-preflight-baseline-snapshot"
    assert generate_preflight_snapshot_args.parent_issue == 400
    assert generate_preflight_snapshot_args.output is None
    diff_preflight_snapshots_args = parser.parse_args(
        [
            "diff-preflight-snapshots",
            "--before",
            "artifacts/evidence/generated/before.json",
            "--after",
            "artifacts/evidence/generated/after.json",
        ]
    )
    assert diff_preflight_snapshots_args.command == "diff-preflight-snapshots"
    assert diff_preflight_snapshots_args.before == "artifacts/evidence/generated/before.json"
    assert diff_preflight_snapshots_args.after == "artifacts/evidence/generated/after.json"
    inspect_child_execution_gates_args = parser.parse_args(
        ["inspect-child-execution-gates", "--issue", "312", "--parent-issue", "309"]
    )
    assert inspect_child_execution_gates_args.command == "inspect-child-execution-gates"
    assert inspect_child_execution_gates_args.issue == 312
    assert inspect_child_execution_gates_args.parent_issue == 309
    inspect_closeout_planning_drift_args = parser.parse_args(
        ["inspect-closeout-planning-drift", "--parent-issue", "172"]
    )
    assert inspect_closeout_planning_drift_args.command == "inspect-closeout-planning-drift"
    assert inspect_closeout_planning_drift_args.parent_issue == 172
    plan_github_mutation_args = parser.parse_args(
        [
            "plan-github-mutation",
            "--mutation-type",
            "issue_comment",
            "--planned-action",
            "post validation evidence",
            "--target-issue",
            "328",
        ]
    )
    assert plan_github_mutation_args.command == "plan-github-mutation"
    assert plan_github_mutation_args.mutation_type == "issue_comment"
    assert plan_github_mutation_args.target_issue == 328
    assert plan_github_mutation_args.target_pr is None
    execute_github_issue_comment_args = parser.parse_args(
        [
            "execute-github-issue-comment",
            "--issue",
            "329",
            "--comment-body",
            "Evidence scoped to child issue only.",
        ]
    )
    assert execute_github_issue_comment_args.command == "execute-github-issue-comment"
    assert execute_github_issue_comment_args.issue == 329
    assert execute_github_issue_comment_args.execute is False
    assert execute_github_issue_comment_args.allow_parent_target is False
    execute_github_issue_close_args = parser.parse_args(
        [
            "execute-github-issue-close",
            "--issue-target",
            "330",
            "--parent-issue",
            "326",
        ]
    )
    assert execute_github_issue_close_args.command == "execute-github-issue-close"
    assert execute_github_issue_close_args.issue_target == "330"
    assert execute_github_issue_close_args.parent_issue == 326
    assert execute_github_issue_close_args.execute is False
    prepare_pr_body_update_args = parser.parse_args(
        [
            "prepare-pr-body-update",
            "--pr-number",
            "339",
            "--target-issue",
            "331",
            "--scope-summary",
            "Summarize M20 child implementation.",
            "--file-changed",
            "src/aresforge/cli.py",
            "--validation-result",
            "python -m pytest -> pass",
            "--safety-note",
            "Dry-run by default.",
        ]
    )
    assert prepare_pr_body_update_args.command == "prepare-pr-body-update"
    assert prepare_pr_body_update_args.pr_number == 339
    assert prepare_pr_body_update_args.target_issue == 331
    assert prepare_pr_body_update_args.execute is False
    inspect_github_mutation_audit_log_args = parser.parse_args(
        ["inspect-github-mutation-audit-log", "--limit", "5"]
    )
    assert inspect_github_mutation_audit_log_args.command == "inspect-github-mutation-audit-log"
    assert inspect_github_mutation_audit_log_args.limit == 5
    inspect_sequential_run_state_args = parser.parse_args(
        ["inspect-sequential-run-state", "--parent-issue", "309"]
    )
    assert inspect_sequential_run_state_args.command == "inspect-sequential-run-state"
    assert inspect_sequential_run_state_args.parent_issue == 309
    sequential_child_closeout_args = parser.parse_args(
        [
            "run-sequential-child-closeout-flow",
            "--parent-issue",
            "345",
            "--child-issue",
            "348",
            "--comment-body",
            "evidence",
        ]
    )
    assert sequential_child_closeout_args.command == "run-sequential-child-closeout-flow"
    assert sequential_child_closeout_args.execute is False
    sequential_closeout_package_args = parser.parse_args(
        [
            "generate-sequential-closeout-execution-package",
            "--parent-issue",
            "345",
            "--child-issue",
            "349",
        ]
    )
    assert sequential_closeout_package_args.command == "generate-sequential-closeout-execution-package"
    assert inspect_sequential_run_state_args.write_local_state is False
    plan_sequential_run_recovery_args = parser.parse_args(
        ["plan-sequential-run-recovery", "--parent-issue", "309"]
    )
    assert plan_sequential_run_recovery_args.command == "plan-sequential-run-recovery"
    assert plan_sequential_run_recovery_args.parent_issue == 309
    generate_sequential_handoff_args = parser.parse_args(
        ["generate-sequential-handoff-package", "--parent-issue", "309", "--issue", "314"]
    )
    assert generate_sequential_handoff_args.command == "generate-sequential-handoff-package"
    assert generate_sequential_handoff_args.parent_issue == 309
    assert generate_sequential_handoff_args.issue == 314
    qa_review_args = parser.parse_args(["qa-review-pr", "--pr-number", "118"])
    assert qa_review_args.pr_number == 118
    qa_closeout_args = parser.parse_args(["qa-closeout-pr", "--pr-number", "119"])
    assert qa_closeout_args.pr_number == 119
    assert qa_closeout_args.execute is False
    assert qa_closeout_args.dry_run is False
    validate_end_to_end_args = parser.parse_args(
        ["validate-pr-end-to-end", "--pr-number", "149"]
    )
    assert validate_end_to_end_args.pr_number == 149
    inspect_review_args = parser.parse_args(
        ["inspect-review-package", "--review-path", "20260520T120003Z-local-review.json"]
    )
    assert inspect_review_args.review_path == "20260520T120003Z-local-review.json"
    inspect_artifact_args = parser.parse_args(
        ["inspect-artifact", "--artifact-path", "prompts/generated/artifact.md"]
    )
    assert inspect_artifact_args.artifact_path == "prompts/generated/artifact.md"
    inspect_evidence_args = parser.parse_args(
        ["inspect-evidence-package", "--evidence-path", "20260520T120001Z-issue-109-evidence.json"]
    )
    assert inspect_evidence_args.evidence_path == "20260520T120001Z-issue-109-evidence.json"

    inspect_model_args = parser.parse_args(["inspect-model", "--model-id", "model-ollama-default"])
    assert inspect_model_args.model_id == "model-ollama-default"

    inspect_queue_args = parser.parse_args(["inspect-queue", "--queue-id", "queue-implementation"])
    assert inspect_queue_args.queue_id == "queue-implementation"
    assert inspect_queue_args.write_artifact is False

    inspect_work_item_args = parser.parse_args(
        ["inspect-work-item", "--work-item-id", "work-123"]
    )
    assert inspect_work_item_args.work_item_id == "work-123"
    assert inspect_work_item_args.write_artifact is False


def test_cli_inspect_project_requires_project_id() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-project"])


def test_cli_inspect_model_requires_model_id() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-model"])


def test_cli_inspect_artifact_requires_artifact_path() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-artifact"])


def test_cli_inspect_review_package_requires_review_path() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-review-package"])


def test_cli_inspect_ready_issue_requires_issue_number() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-ready-issue"])


def test_cli_plan_ready_issue_requires_issue_number() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["plan-ready-issue"])


def test_cli_run_ready_issue_pipeline_requires_mode() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["run-ready-issue-pipeline", "--issue-number", "120"])


def test_cli_qa_review_pr_requires_pr_number() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["qa-review-pr"])


def test_cli_qa_closeout_pr_requires_pr_number() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["qa-closeout-pr"])


def test_cli_validate_pr_end_to_end_requires_pr_number() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["validate-pr-end-to-end"])


def test_cli_qa_closeout_pr_execute_flag_is_optional_and_explicit() -> None:
    parser = build_parser()

    dry_args = parser.parse_args(["qa-closeout-pr", "--pr-number", "119"])
    assert dry_args.execute is False

    execute_args = parser.parse_args(["qa-closeout-pr", "--pr-number", "119", "--execute"])
    assert execute_args.execute is True


def test_cli_inspect_evidence_package_requires_evidence_path() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["inspect-evidence-package"])


def test_cli_inspection_commands_accept_write_artifact_flag() -> None:
    parser = build_parser()

    inspect_queue_args = parser.parse_args(
        ["inspect-queue", "--queue-id", "queue-implementation", "--write-artifact"]
    )
    assert inspect_queue_args.write_artifact is True

    inspect_work_item_args = parser.parse_args(
        ["inspect-work-item", "--work-item-id", "work-123", "--write-artifact"]
    )
    assert inspect_work_item_args.write_artifact is True


def test_command_requires_directories_only_for_commands_that_write_artifacts() -> None:
    parser = build_parser()

    assert command_requires_directories(parser.parse_args(["validate-config"])) is True
    assert (
        command_requires_directories(
            parser.parse_args(["generate-prompt-package", "--title", "Prompt", "--objective", "Goal"])
        )
        is True
    )
    assert (
        command_requires_directories(
            parser.parse_args(["inspect-queue", "--queue-id", "queue-implementation"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["inspect-queue", "--queue-id", "queue-implementation", "--write-artifact"])
        )
        is True
    )
    assert command_requires_directories(parser.parse_args(["list-artifacts"])) is False
    assert command_requires_directories(parser.parse_args(["list-review-packages"])) is False
    assert command_requires_directories(parser.parse_args(["run-local-review"])) is False
    assert (
        command_requires_directories(
            parser.parse_args(["run-local-review", "--write-review-package"])
        )
        is True
    )
    assert command_requires_directories(parser.parse_args(["list-evidence-packages"])) is False
    assert (
        command_requires_directories(
            parser.parse_args(
                ["inspect-review-package", "--review-path", "20260520T120003Z-local-review.json"]
            )
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["inspect-artifact", "--artifact-path", "prompts/generated/artifact.md"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["inspect-evidence-package", "--evidence-path", "artifact.json"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["qa-review-pr", "--pr-number", "118"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["qa-closeout-pr", "--pr-number", "119"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["validate-pr-end-to-end", "--pr-number", "149"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["run-ready-issue-pipeline", "--issue-number", "120", "--plan-only"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["run-ready-issue-batch", "--plan-only"])
        )
        is True
    )
    assert command_requires_directories(parser.parse_args(["automation-readiness-report"])) is False
    assert command_requires_directories(parser.parse_args(["inspect-repo-governance"])) is False
    assert command_requires_directories(parser.parse_args(["assess-repo"])) is False
    assert command_requires_directories(parser.parse_args(["inspect-milestone-closeout-preflight-contract"])) is False
    assert command_requires_directories(parser.parse_args(["inspect-canonical-evidence-marker-contract"])) is False
    assert command_requires_directories(parser.parse_args(["inspect-repo-bootstrap-contract"])) is False
    assert command_requires_directories(parser.parse_args(["inspect-managed-repos"])) is False
    assert command_requires_directories(parser.parse_args(["managed-repo-readiness-report"])) is False
    assert command_requires_directories(parser.parse_args(["plan-repo-bootstrap"])) is False
    assert command_requires_directories(parser.parse_args(["demo-managed-repo-governance"])) is False
    assert (
        command_requires_directories(
            parser.parse_args(["plan-batch-closeout", "--parent-issue", "172"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["plan-sprint-issues", "--definition", "tests/fixtures/m12-sprint-definition.json"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["plan-self-managed-milestone", "--mode", "local-write"])
        )
        is False
    )
    assert (
        command_requires_directories(
            parser.parse_args(["inspect-closeout-planning-drift", "--parent-issue", "172"])
        )
        is False
    )


def test_validate_registries_command_emits_ok_json_and_zero_exit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "validate_registry_seed_data",
        lambda: ValidationReport(ok=True, findings=()),
    )

    exit_code = cli.main(["validate-registries"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "findings": []}


def test_validate_registries_command_returns_one_for_error_findings(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "validate_registry_seed_data",
        lambda: ValidationReport(
            ok=False,
            findings=(
                ValidationFinding(
                    severity="error",
                    code="queue.invalid_allowed_next_queue",
                    message="Queue references unknown next queue 'queue-not-real'.",
                    location="queues[queue-intake].metadata.allowed_next_queues",
                ),
            ),
        ),
    )

    exit_code = cli.main(["validate-registries"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["findings"] == [
        {
            "severity": "error",
            "code": "queue.invalid_allowed_next_queue",
            "message": "Queue references unknown next queue 'queue-not-real'.",
            "location": "queues[queue-intake].metadata.allowed_next_queues",
        }
    ]


@contextmanager
def fake_connect(_config: object):
    yield object()


def test_inspect_queue_preserves_json_shape_without_write_artifact(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    queue_payload = {"id": "queue-implementation", "name": "implementation"}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_queue", lambda _conn, _queue_id: queue_payload)

    exit_code = cli.main(["inspect-queue", "--queue-id", "queue-implementation"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "queue": queue_payload}


def test_cli_dispatches_qa_review_pr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(cli, "qa_review_pr", lambda _config, _pr_number: {"ok": True})

    exit_code = cli.main(["qa-review-pr", "--pr-number", "118"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True}


def test_cli_dispatches_validate_pr_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "validate_pr_end_to_end",
        lambda _config, _pr_number: {"command": "validate-pr-end-to-end", "ok": True},
    )

    exit_code = cli.main(["validate-pr-end-to-end", "--pr-number", "149"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "validate-pr-end-to-end", "ok": True}


def test_cli_validate_pr_end_to_end_does_not_call_mutation_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "qa_closeout_pr",
        lambda *_args, **_kwargs: pytest.fail(
            "validate-pr-end-to-end must not call qa-closeout-pr mutation path"
        ),
    )
    monkeypatch.setattr(
        cli,
        "validate_pr_end_to_end",
        lambda _config, _pr_number: {"command": "validate-pr-end-to-end", "ok": False},
    )

    exit_code = cli.main(["validate-pr-end-to-end", "--pr-number", "149"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == {"command": "validate-pr-end-to-end", "ok": False}


def test_cli_dispatches_project_state_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "project_state_summary",
        lambda _config: {"command": "project-state-summary", "ok": True},
    )

    exit_code = cli.main(["project-state-summary"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "project-state-summary", "ok": True}


def test_cli_dispatches_demo_managed_repo_governance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "demo_managed_repo_governance",
        lambda _config: {"command": "demo-managed-repo-governance", "ok": True},
    )

    exit_code = cli.main(["demo-managed-repo-governance"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "demo-managed-repo-governance", "ok": True}


def test_cli_dispatches_inspect_repo_governance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_repo_governance",
        lambda _config: {"command": "inspect-repo-governance", "ok": True},
    )

    exit_code = cli.main(["inspect-repo-governance"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "inspect-repo-governance", "ok": True}


def test_cli_dispatches_inspect_repo_bootstrap_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_repo_bootstrap_contract",
        lambda _config: {"command": "inspect-repo-bootstrap-contract", "ok": True},
    )

    exit_code = cli.main(["inspect-repo-bootstrap-contract"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "inspect-repo-bootstrap-contract", "ok": True}


def test_cli_dispatches_inspect_parent_child_linkage_preflight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_parent_child_linkage_preflight",
        lambda _config, parent_issue: {
            "command": "inspect-parent-child-linkage-preflight",
            "ok": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["inspect-parent-child-linkage-preflight", "--parent-issue", "381"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "inspect-parent-child-linkage-preflight",
        "ok": True,
        "parent_issue": 381,
    }


def test_cli_dispatches_inspect_child_evidence_marker_preflight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_child_evidence_marker_preflight",
        lambda _config, parent_issue: {
            "command": "inspect-child-evidence-marker-preflight",
            "ok": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["inspect-child-evidence-marker-preflight", "--parent-issue", "381"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "inspect-child-evidence-marker-preflight",
        "ok": True,
        "parent_issue": 381,
    }


def test_cli_dispatches_inspect_pr_mapping_preflight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_pr_mapping_preflight",
        lambda _config, parent_issue: {
            "command": "inspect-pr-mapping-preflight",
            "ok": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["inspect-pr-mapping-preflight", "--parent-issue", "381"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "inspect-pr-mapping-preflight",
        "ok": True,
        "parent_issue": 381,
    }


def test_cli_dispatches_generate_closeout_preflight_repair_guidance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_closeout_preflight_repair_guidance",
        lambda _config, parent_issue: {
            "command": "generate-closeout-preflight-repair-guidance",
            "ok": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["generate-closeout-preflight-repair-guidance", "--parent-issue", "381"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-closeout-preflight-repair-guidance",
        "ok": True,
        "parent_issue": 381,
    }


def test_cli_dispatches_inspect_milestone_closeout_preflight(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_milestone_closeout_preflight",
        lambda _config, parent_issue: {
            "command": "inspect-milestone-closeout-preflight",
            "ok": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["inspect-milestone-closeout-preflight", "--parent-issue", "381"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "inspect-milestone-closeout-preflight",
        "ok": True,
        "parent_issue": 381,
    }


def test_cli_dispatches_generate_preflight_baseline_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_preflight_baseline_snapshot",
        lambda _config, parent_issue, output_path: {
            "command": "generate-preflight-baseline-snapshot",
            "ok": True,
            "parent_issue": parent_issue,
            "snapshot_path": output_path,
        },
    )

    exit_code = cli.main([
        "generate-preflight-baseline-snapshot",
        "--parent-issue",
        "400",
        "--output",
        "artifacts/evidence/generated/m24-400-snapshot.json",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-preflight-baseline-snapshot",
        "ok": True,
        "parent_issue": 400,
        "snapshot_path": "artifacts/evidence/generated/m24-400-snapshot.json",
    }


def test_cli_dispatches_diff_preflight_snapshots(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "diff_preflight_snapshots",
        lambda before_path, after_path: {
            "command": "diff-preflight-snapshots",
            "ok": True,
            "before_path": before_path,
            "after_path": after_path,
            "classification": "improved",
        },
    )

    exit_code = cli.main(
        [
            "diff-preflight-snapshots",
            "--before",
            "artifacts/evidence/generated/before.json",
            "--after",
            "artifacts/evidence/generated/after.json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "diff-preflight-snapshots",
        "ok": True,
        "before_path": "artifacts/evidence/generated/before.json",
        "after_path": "artifacts/evidence/generated/after.json",
        "classification": "improved",
    }


def test_cli_dispatches_inspect_milestone_closeout_preflight_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_milestone_closeout_preflight_contract",
        lambda _config: {"command": "inspect-milestone-closeout-preflight-contract", "ok": True},
    )

    exit_code = cli.main(["inspect-milestone-closeout-preflight-contract"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "inspect-milestone-closeout-preflight-contract", "ok": True}


def test_cli_dispatches_inspect_canonical_evidence_marker_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_canonical_evidence_marker_contract",
        lambda _config: {"command": "inspect-canonical-evidence-marker-contract", "ok": True},
    )

    exit_code = cli.main(["inspect-canonical-evidence-marker-contract"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "inspect-canonical-evidence-marker-contract", "ok": True}


def test_cli_dispatches_inspect_managed_repos(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "inspect_managed_repos",
        lambda _config: {"command": "inspect-managed-repos", "ok": True},
    )

    exit_code = cli.main(["inspect-managed-repos"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "inspect-managed-repos", "ok": True}


def test_cli_dispatches_managed_repo_readiness_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "managed_repo_readiness_report",
        lambda _config: {"command": "managed-repo-readiness-report", "ok": True},
    )

    exit_code = cli.main(["managed-repo-readiness-report"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "managed-repo-readiness-report", "ok": True}


def test_cli_dispatches_plan_repo_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "plan_repo_bootstrap",
        lambda _config: {"command": "plan-repo-bootstrap", "ok": True},
    )

    exit_code = cli.main(["plan-repo-bootstrap"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"command": "plan-repo-bootstrap", "ok": True}


def test_cli_dispatches_plan_batch_closeout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "plan_batch_closeout",
        lambda _config, parent_issue, write_planning_snapshot=False, planning_state_path=None: {
            "command": "plan-batch-closeout",
            "ok": True,
            "parent_issue": parent_issue,
            "write_planning_snapshot": write_planning_snapshot,
            "planning_state_path": planning_state_path,
        },
    )

    exit_code = cli.main(["plan-batch-closeout", "--parent-issue", "172"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "plan-batch-closeout",
        "ok": True,
        "parent_issue": 172,
        "write_planning_snapshot": False,
        "planning_state_path": None,
    }


def test_cli_dispatches_generate_parent_closeout_evidence_bundle(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_parent_closeout_evidence_bundle",
        lambda _config, parent_issue, state_file=None: {
            "command": "generate-parent-closeout-evidence-bundle",
            "ok": True,
            "read_only": True,
            "parent_issue": parent_issue,
            "state_file": state_file,
        },
    )

    exit_code = cli.main(
        [
            "generate-parent-closeout-evidence-bundle",
            "--parent-issue",
            "362",
            "--state-file",
            "artifacts/offline-state/m25-421.json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-parent-closeout-evidence-bundle",
        "ok": True,
        "read_only": True,
        "parent_issue": 362,
        "state_file": "artifacts/offline-state/m25-421.json",
    }


def test_cli_dispatches_generate_parent_closeout_marker_template(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_parent_closeout_marker_template",
        lambda _config, parent_issue: {
            "command": "generate-parent-closeout-marker-template",
            "ok": True,
            "read_only": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["generate-parent-closeout-marker-template", "--parent-issue", "400"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-parent-closeout-marker-template",
        "ok": True,
        "read_only": True,
        "parent_issue": 400,
    }


def test_cli_dispatches_generate_child_evidence_marker_template(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_child_evidence_marker_template",
        lambda _config, parent_issue, child_issue: {
            "command": "generate-child-evidence-marker-template",
            "ok": True,
            "read_only": True,
            "parent_issue": parent_issue,
            "child_issue": child_issue,
        },
    )

    exit_code = cli.main(
        [
            "generate-child-evidence-marker-template",
            "--parent-issue",
            "400",
            "--child-issue",
            "403",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-child-evidence-marker-template",
        "ok": True,
        "read_only": True,
        "parent_issue": 400,
        "child_issue": 403,
    }


def test_cli_dispatches_generate_pr_evidence_bundle(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_pr_evidence_bundle",
        lambda _config, issue_number, pr_number: {
            "command": "generate-pr-evidence-bundle",
            "ok": True,
            "read_only": True,
            "issue": issue_number,
            "pr": pr_number,
        },
    )

    exit_code = cli.main(["generate-pr-evidence-bundle", "--issue", "367", "--pr", "376"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-pr-evidence-bundle",
        "ok": True,
        "read_only": True,
        "issue": 367,
        "pr": 376,
    }


def test_cli_dispatches_generate_pr_evidence_marker_template(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "generate_pr_evidence_marker_template",
        lambda _config, issue_number, pr_number: {
            "command": "generate-pr-evidence-marker-template",
            "ok": True,
            "read_only": True,
            "issue": issue_number,
            "pr": pr_number,
        },
    )

    exit_code = cli.main(["generate-pr-evidence-marker-template", "--issue", "404", "--pr", "414"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "generate-pr-evidence-marker-template",
        "ok": True,
        "read_only": True,
        "issue": 404,
        "pr": 414,
    }


def test_cli_dispatches_simulate_evidence_bundle_generation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "simulate_evidence_bundle_generation",
        lambda _config, parent_issue: {
            "command": "simulate-evidence-bundle-generation",
            "ok": True,
            "read_only": True,
            "dry_run": True,
            "parent_issue": parent_issue,
        },
    )

    exit_code = cli.main(["simulate-evidence-bundle-generation", "--parent-issue", "362"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        "command": "simulate-evidence-bundle-generation",
        "ok": True,
        "read_only": True,
        "dry_run": True,
        "parent_issue": 362,
    }


def test_cli_dispatches_qa_closeout_pr(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "qa_closeout_pr",
        lambda _config, _pr_number, execute=False: {
            "failed_gates": [] if execute else ["qa_decision_pass"],
            "mode": "execute" if execute else "dry_run",
        },
    )

    dry_exit_code = cli.main(["qa-closeout-pr", "--pr-number", "119"])
    dry_payload = json.loads(capsys.readouterr().out)
    assert dry_exit_code == 1
    assert dry_payload["mode"] == "dry_run"

    execute_exit_code = cli.main(["qa-closeout-pr", "--pr-number", "119", "--execute"])
    execute_payload = json.loads(capsys.readouterr().out)
    assert execute_exit_code == 0
    assert execute_payload["mode"] == "execute"


def test_cli_dispatches_run_ready_issue_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config = AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    monkeypatch.setattr(
        cli,
        "run_ready_issue_pipeline",
        lambda _config, **_kwargs: {
            "command": "run-ready-issue-pipeline",
            "failed_gates": [],
            "mode": "plan-only",
        },
    )

    exit_code = cli.main(["run-ready-issue-pipeline", "--issue-number", "120", "--plan-only"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["command"] == "run-ready-issue-pipeline"


def test_inspect_project_preserves_json_shape_when_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project_payload = {
        "id": "project-aresforge",
        "slug": "aresforge",
        "name": "AresForge",
        "status": "active",
        "repo_owner": "yoey2112",
        "repo_name": "aresforge",
        "default_branch": "main",
        "local_path": "C:\\Projects\\aresforge",
        "metadata": {
            "autonomy_level": "human_triggered_local_only",
            "protected_issue": 39,
            "active_issue": 97,
            "completed_issue": 96,
        },
        "autonomy_level": "human_triggered_local_only",
        "protected_issue": 39,
        "active_issue": 97,
        "completed_issue": 96,
        "updated_at": "2026-05-20T00:00:00Z",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_project", lambda _conn, _project_id: project_payload)

    exit_code = cli.main(["inspect-project", "--project-id", "project-aresforge"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "project": project_payload}


def test_inspect_registries_emits_summary_and_exit_zero_when_ok(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_payload = {
        "ok": True,
        "inspection_mode": "local_repo_only",
        "summary": {"registry_count": 5, "ok": 5, "problem_registry_count": 0},
        "registries": [{"registry": "project_registry", "status": "ok"}],
    }
    monkeypatch.setattr(cli, "inspect_local_registries", lambda _repo_root: registry_payload)

    exit_code = cli.main(["inspect-registries"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == registry_payload


def test_inspect_registries_returns_exit_one_when_any_registry_has_problem(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    registry_payload = {
        "ok": False,
        "inspection_mode": "local_repo_only",
        "summary": {"registry_count": 5, "ok": 4, "problem_registry_count": 1},
        "registries": [{"registry": "queue_registry", "status": "missing"}],
    }
    monkeypatch.setattr(cli, "inspect_local_registries", lambda _repo_root: registry_payload)

    exit_code = cli.main(["inspect-registries"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == registry_payload


def test_inspect_project_returns_not_found_with_exit_code_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_project", lambda _conn, _project_id: None)

    exit_code = cli.main(["inspect-project", "--project-id", "project-missing"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == {
        "ok": False,
        "error": "project_not_found",
        "project_id": "project-missing",
    }


def test_inspect_project_is_read_only_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_project", lambda _conn, _project_id: {"id": _project_id})
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-project must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-project must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-project must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-project must not bootstrap state"),
    )

    exit_code = cli.main(["inspect-project", "--project-id", "project-aresforge"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "project": {"id": "project-aresforge"}}


def test_inspect_registries_is_read_only_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "inspect_local_registries",
        lambda _repo_root: {
            "ok": True,
            "inspection_mode": "local_repo_only",
            "summary": {"registry_count": 5, "ok": 5, "problem_registry_count": 0},
            "registries": [],
        },
    )
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("inspect-registries must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-registries must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-registries must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-registries must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-registries must not bootstrap state"),
    )

    exit_code = cli.main(["inspect-registries"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True


def test_plan_ready_issue_dispatches_without_mutation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_payload = {
        "issue_number": 114,
        "issue_title": "Plan routing",
        "issue_url": "https://github.com/example/114",
        "labels": ["aresforge-ready"],
        "automation_eligible": True,
        "selected_primary_agent": "implementation-agent",
        "selected_qa_agent": "qa-agent",
        "selected_documentation_agent": "documentation-agent",
        "selected_model_tier": "local",
        "model_routing_reason": "Local-first default for routine scope.",
        "lower_tiers_sufficient": True,
        "codex_justified": False,
        "paid_use_blocked": True,
        "confidence": "medium",
        "blocked": False,
        "blocked_reason": None,
        "recommended_next_command": "python -m aresforge list-ready-issues",
    }

    monkeypatch.setattr(cli, "plan_ready_issue", lambda _config, _issue_number: plan_payload)
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("plan-ready-issue must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("plan-ready-issue must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("plan-ready-issue must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("plan-ready-issue must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("plan-ready-issue must not bootstrap state"),
    )

    exit_code = cli.main(["plan-ready-issue", "--issue-number", "114"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == plan_payload


def test_list_artifacts_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    discovery_payload = {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": "C:/Projects/aresforge/artifacts",
        "artifact_root_exists": False,
        "artifact_count": 0,
        "artifacts": [],
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(
        cli,
        "discover_local_artifacts",
        lambda _config: discovery_payload,
    )
    monkeypatch.setattr(
        cli.AppConfig,
        "ensure_directories",
        lambda _self: ensure_calls.append(True),
    )
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("list-artifacts must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("list-artifacts must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("list-artifacts must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("list-artifacts must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("list-artifacts must not bootstrap state"),
    )

    exit_code = cli.main(["list-artifacts"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == discovery_payload


def test_list_review_packages_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    discovery_payload = {
        "ok": True,
        "inspection_mode": "local_review_package_root_only",
        "review_package_root": "C:/Projects/aresforge/artifacts/local_reviews/generated",
        "review_package_root_exists": False,
        "review_package_count": 0,
        "review_packages": [],
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(cli, "discover_local_review_packages", lambda _config: discovery_payload)
    monkeypatch.setattr(cli.AppConfig, "ensure_directories", lambda _self: ensure_calls.append(True))
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not bootstrap state"),
    )
    monkeypatch.setattr(
        cli,
        "render_evidence_package",
        lambda *_args, **_kwargs: pytest.fail("list-review-packages must not mutate evidence files"),
    )

    exit_code = cli.main(["list-review-packages"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == discovery_payload


def test_run_local_review_dispatches_without_ollama_routing_or_mutation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    review_payload = {
        "ok": True,
        "command": "run-local-review",
        "status": "passed",
        "requested_options": {
            "project_id": "project-aresforge",
            "model_id": "model-ollama-default",
            "include_artifacts": False,
            "artifact_path": None,
            "include_evidence_packages": False,
            "evidence_path": None,
            "write_review_package": False,
        },
        "checks_run": [],
        "checks_skipped": [],
        "skip_reasons": {},
        "artifact_summary": None,
        "evidence_package_summary": None,
        "boundary_confirmations": ["Protected historical references were not modified by this command."],
        "output_package_path": None,
        "output_package_markdown_path": None,
    }

    monkeypatch.setattr(cli, "run_local_review", lambda _config, options: review_payload)
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("run-local-review must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("run-local-review must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("run-local-review must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("run-local-review must not bootstrap state"),
    )
    monkeypatch.setattr(
        cli,
        "render_evidence_package",
        lambda *_args, **_kwargs: pytest.fail("run-local-review must not write evidence packages"),
    )

    exit_code = cli.main(["run-local-review"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == review_payload


def test_inspect_artifact_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": "C:/Projects/aresforge/artifacts",
        "artifact_root_exists": True,
        "artifact": {
            "artifact_path": "prompts/generated/artifact.md",
            "filename": "artifact.md",
            "size_bytes": 12,
            "modified_at": "2026-05-20T00:00:00+00:00",
            "artifact_type": "prompt_package",
            "command_source_hint": "generate-prompt-package",
            "extension": ".md",
            "text_readable": True,
            "text_preview": "# Artifact",
        },
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(
        cli,
        "inspect_local_artifact",
        lambda _config, _artifact_path: inspection_payload,
    )
    monkeypatch.setattr(
        cli.AppConfig,
        "ensure_directories",
        lambda _self: ensure_calls.append(True),
    )
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("inspect-artifact must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-artifact must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-artifact must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-artifact must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-artifact must not bootstrap state"),
    )

    exit_code = cli.main(["inspect-artifact", "--artifact-path", "prompts/generated/artifact.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == inspection_payload


def test_inspect_review_package_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": True,
        "inspection_mode": "local_review_package_root_only",
        "review_package_root": "C:/Projects/aresforge/artifacts/local_reviews/generated",
        "review_package_root_exists": True,
        "review_package": {
            "review_path": "20260520T120003Z-local-review.json",
            "filename": "20260520T120003Z-local-review.json",
            "size_bytes": 12,
            "modified_at": "2026-05-20T00:00:00+00:00",
            "artifact_type": "local_review_package",
            "command_source_hint": "run-local-review --write-review-package",
            "extension": ".json",
            "text_readable": True,
            "text_preview": '{"ok": true}',
            "parsed_summary": {
                "command": "run-local-review",
                "status": "passed",
                "project_id": "project-aresforge",
                "model_id": "model-ollama-default",
                "checks_run_count": 1,
                "checks_skipped_count": 0,
                "has_artifact_summary": False,
                "has_evidence_package_summary": False,
                "write_review_package_requested": True,
            },
        },
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(cli, "inspect_local_review_package", lambda _config, _review_path: inspection_payload)
    monkeypatch.setattr(cli.AppConfig, "ensure_directories", lambda _self: ensure_calls.append(True))
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("inspect-review-package must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-review-package must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-review-package must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-review-package must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-review-package must not bootstrap state"),
    )

    exit_code = cli.main(["inspect-review-package", "--review-path", "20260520T120003Z-local-review.json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == inspection_payload


def test_inspect_review_package_returns_exit_one_when_helper_reports_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": False,
        "inspection_mode": "local_review_package_root_only",
        "review_package_root": "C:/Projects/aresforge/artifacts/local_reviews/generated",
        "review_package_root_exists": True,
        "error": "review_package_not_found",
        "review_path": "missing.json",
    }
    monkeypatch.setattr(
        cli, "inspect_local_review_package", lambda _config, _review_path: inspection_payload
    )

    exit_code = cli.main(["inspect-review-package", "--review-path", "missing.json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == inspection_payload


def test_inspect_artifact_returns_exit_one_when_helper_reports_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": False,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": "C:/Projects/aresforge/artifacts",
        "artifact_root_exists": True,
        "error": "artifact_not_found",
        "artifact_path": "prompts/generated/missing.md",
    }
    monkeypatch.setattr(cli, "inspect_local_artifact", lambda _config, _artifact_path: inspection_payload)

    exit_code = cli.main(["inspect-artifact", "--artifact-path", "prompts/generated/missing.md"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == inspection_payload


def test_list_evidence_packages_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    discovery_payload = {
        "ok": True,
        "inspection_mode": "local_evidence_root_only",
        "evidence_root": "C:/Projects/aresforge/artifacts/evidence/generated",
        "evidence_root_exists": False,
        "evidence_package_count": 0,
        "evidence_packages": [],
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(cli, "discover_local_evidence_packages", lambda _config: discovery_payload)
    monkeypatch.setattr(cli.AppConfig, "ensure_directories", lambda _self: ensure_calls.append(True))
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not bootstrap state"),
    )
    monkeypatch.setattr(
        cli,
        "render_evidence_package",
        lambda *_args, **_kwargs: pytest.fail("list-evidence-packages must not mutate evidence files"),
    )

    exit_code = cli.main(["list-evidence-packages"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == discovery_payload


def test_inspect_evidence_package_emits_json_and_skips_directory_creation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": True,
        "inspection_mode": "local_evidence_root_only",
        "evidence_root": "C:/Projects/aresforge/artifacts/evidence/generated",
        "evidence_root_exists": True,
        "evidence_package": {
            "evidence_path": "artifact.json",
            "filename": "artifact.json",
            "size_bytes": 12,
            "modified_at": "2026-05-20T00:00:00+00:00",
            "artifact_type": "evidence_package",
            "command_source_hint": "record-evidence-package",
            "extension": ".json",
            "text_readable": True,
            "text_preview": '{"ok": true}',
        },
    }
    ensure_calls: list[bool] = []

    monkeypatch.setattr(cli, "inspect_local_evidence_package", lambda _config, _evidence_path: inspection_payload)
    monkeypatch.setattr(cli.AppConfig, "ensure_directories", lambda _self: ensure_calls.append(True))
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not connect to PostgreSQL"),
    )
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not bootstrap state"),
    )
    monkeypatch.setattr(
        cli,
        "render_evidence_package",
        lambda *_args, **_kwargs: pytest.fail("inspect-evidence-package must not mutate evidence files"),
    )

    exit_code = cli.main(["inspect-evidence-package", "--evidence-path", "artifact.json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert ensure_calls == []
    assert payload == inspection_payload


def test_inspect_evidence_package_returns_exit_one_when_helper_reports_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspection_payload = {
        "ok": False,
        "inspection_mode": "local_evidence_root_only",
        "evidence_root": "C:/Projects/aresforge/artifacts/evidence/generated",
        "evidence_root_exists": True,
        "error": "evidence_package_not_found",
        "evidence_path": "missing.json",
    }
    monkeypatch.setattr(cli, "inspect_local_evidence_package", lambda _config, _evidence_path: inspection_payload)

    exit_code = cli.main(["inspect-evidence-package", "--evidence-path", "missing.json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == inspection_payload


def test_list_models_emits_valid_json_without_ollama(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    models_payload = [
        {
            "id": "model-ollama-default",
            "name": "qwen2.5:32b",
            "display_name": "qwen2.5:32b",
            "provider": "ollama",
            "runtime": None,
            "status": "configured",
            "endpoint": "http://127.0.0.1:11434",
            "local_endpoint": "http://127.0.0.1:11434",
            "model_key": None,
            "execution_location": None,
            "metadata": {"default": True},
            "updated_at": "2026-05-20T00:00:00Z",
        }
    ]

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "list_models", lambda _conn: models_payload)
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("list-models must not call Ollama"),
    )

    exit_code = cli.main(["list-models"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"models": models_payload}


def test_list_models_is_read_only_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "list_models", lambda _conn: [])
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("list-models must not bootstrap state"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("list-models must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("list-models must not route work"),
    )

    exit_code = cli.main(["list-models"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"models": []}


def test_inspect_model_preserves_json_shape_when_found(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    model_payload = {
        "id": "model-ollama-default",
        "name": "qwen2.5:32b",
        "display_name": "Qwen 2.5 32B",
        "provider": "ollama",
        "runtime": "ollama_local",
        "status": "configured",
        "endpoint": "http://127.0.0.1:11434",
        "local_endpoint": "http://127.0.0.1:11434",
        "model_key": "ollama/qwen2.5:32b",
        "execution_location": "local_machine",
        "hosting_posture": "local_only",
        "purpose": "Local drafting, documentation support, and bounded validation evidence review.",
        "allowed_task_classes": [
            "documentation_support",
            "implementation_support",
        ],
        "default_routing_priority": "primary",
        "fallback_rules": [
            "If unavailable, try another approved local model for the same task class.",
        ],
        "approval_requirements": [
            "Human review remains required for all output.",
        ],
        "approval_posture": "local_human_review_required",
        "validation_suitability": "bounded_validation_support",
        "evidence_expectations": ["record selected model key"],
        "known_limitations": ["Must not be treated as approval authority."],
        "restricted_task_classes": ["governance_decision", "merge_authority"],
        "governance_sensitive_task_posture": "advisory_only_human_approval_required",
        "source_document": "docs/architecture/MODEL_REGISTRY_SCHEMA.md",
        "metadata": {"default": True},
        "updated_at": "2026-05-20T00:00:00Z",
    }

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_model", lambda _conn, _model_id: model_payload)

    exit_code = cli.main(["inspect-model", "--model-id", "model-ollama-default"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "model": model_payload}


def test_inspect_model_returns_not_found_with_exit_code_one(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_model", lambda _conn, _model_id: None)

    exit_code = cli.main(["inspect-model", "--model-id", "missing-model-id"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == {
        "ok": False,
        "error": "model_not_found",
        "model_id": "missing-model-id",
    }


def test_inspect_model_is_read_only_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_model", lambda _conn, _model_id: {"id": _model_id})
    monkeypatch.setattr(
        cli,
        "test_generate",
        lambda *_args, **_kwargs: pytest.fail("inspect-model must not call Ollama"),
    )
    monkeypatch.setattr(
        cli,
        "create_work_item",
        lambda *_args, **_kwargs: pytest.fail("inspect-model must not create work items"),
    )
    monkeypatch.setattr(
        cli,
        "build_route_plan",
        lambda *_args, **_kwargs: pytest.fail("inspect-model must not route work"),
    )
    monkeypatch.setattr(
        cli,
        "bootstrap_reference_data",
        lambda *_args, **_kwargs: pytest.fail("inspect-model must not bootstrap state"),
    )

    exit_code = cli.main(["inspect-model", "--model-id", "model-ollama-default"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "model": {"id": "model-ollama-default"}}


def test_inspect_queue_write_artifact_renders_report_and_emits_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    queue_payload = {"id": "queue-implementation", "name": "implementation"}
    markdown_path = tmp_path / "queue-report.md"
    json_path = tmp_path / "queue-report.json"
    calls: list[tuple[object, dict[str, str]]] = []

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_queue", lambda _conn, _queue_id: queue_payload)

    def fake_render_queue_inspection_report(*, config: object, inspection_payload: dict[str, str]) -> ArtifactBundle:
        calls.append((config, inspection_payload))
        return ArtifactBundle(
            markdown_path=markdown_path,
            json_path=json_path,
            payload={"inspection_payload": inspection_payload},
        )

    monkeypatch.setattr(cli, "render_queue_inspection_report", fake_render_queue_inspection_report)

    exit_code = cli.main(["inspect-queue", "--queue-id", "queue-implementation", "--write-artifact"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls
    assert calls[0][1] == queue_payload
    assert payload == {
        "ok": True,
        "queue": queue_payload,
        "inspection_payload": queue_payload,
        "markdown_path": str(markdown_path),
        "json_path": str(json_path),
    }


def test_inspect_work_item_preserves_json_shape_without_write_artifact(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    work_item_payload = {"id": "work-123", "title": "Inspect me"}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_work_item", lambda _conn, _work_item_id: work_item_payload)

    exit_code = cli.main(["inspect-work-item", "--work-item-id", "work-123"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {"ok": True, "work_item": work_item_payload}


def test_inspect_work_item_write_artifact_renders_report_and_emits_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    work_item_payload = {"id": "work-123", "title": "Inspect me"}
    markdown_path = tmp_path / "work-item-report.md"
    json_path = tmp_path / "work-item-report.json"
    calls: list[tuple[object, dict[str, str]]] = []

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_work_item", lambda _conn, _work_item_id: work_item_payload)

    def fake_render_work_item_inspection_report(
        *, config: object, inspection_payload: dict[str, str]
    ) -> ArtifactBundle:
        calls.append((config, inspection_payload))
        return ArtifactBundle(
            markdown_path=markdown_path,
            json_path=json_path,
            payload={"inspection_payload": inspection_payload},
        )

    monkeypatch.setattr(
        cli,
        "render_work_item_inspection_report",
        fake_render_work_item_inspection_report,
    )

    exit_code = cli.main(
        ["inspect-work-item", "--work-item-id", "work-123", "--write-artifact"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls
    assert calls[0][1] == work_item_payload
    assert payload == {
        "ok": True,
        "work_item": work_item_payload,
        "inspection_payload": work_item_payload,
        "markdown_path": str(markdown_path),
        "json_path": str(json_path),
    }


def test_record_evidence_package_does_not_capture_artifact_discovery_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    calls: list[dict[str, object | None]] = []
    bundle = ArtifactBundle(
        markdown_path=tmp_path / "evidence.md",
        json_path=tmp_path / "evidence.json",
        payload={"ok": True},
    )

    monkeypatch.setattr(
        cli,
        "discover_local_artifacts",
        lambda _config: pytest.fail("record-evidence-package must not capture artifact discovery unless opted in"),
    )
    monkeypatch.setattr(
        cli,
        "latest_local_review_package_summary",
        lambda _config: pytest.fail("record-evidence-package must not capture latest review package unless opted in"),
    )

    def fake_render_evidence_package(**kwargs: object) -> ArtifactBundle:
        calls.append(
            {
                "artifact_discovery": kwargs["artifact_discovery"],
                "latest_review_package": kwargs["latest_review_package"],
            }
        )
        return bundle

    monkeypatch.setattr(cli, "render_evidence_package", fake_render_evidence_package)

    exit_code = cli.main(["record-evidence-package", "--title", "Evidence"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [{"artifact_discovery": None, "latest_review_package": None}]
    assert payload == {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def test_record_evidence_package_can_capture_artifact_discovery_when_opted_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    artifact_discovery_payload = {
        "ok": True,
        "inspection_mode": "local_artifact_root_only",
        "artifact_root": "C:/Projects/aresforge/artifacts",
        "artifact_root_exists": True,
        "artifact_count": 1,
        "artifacts": [{"artifact_path": "prompts/generated/example.md"}],
    }
    calls: list[dict[str, object | None]] = []
    bundle = ArtifactBundle(
        markdown_path=tmp_path / "evidence.md",
        json_path=tmp_path / "evidence.json",
        payload={"ok": True},
    )

    monkeypatch.setattr(cli, "discover_local_artifacts", lambda _config: artifact_discovery_payload)

    def fake_render_evidence_package(**kwargs: object) -> ArtifactBundle:
        calls.append({"artifact_discovery": kwargs["artifact_discovery"]})
        return bundle

    monkeypatch.setattr(cli, "render_evidence_package", fake_render_evidence_package)

    exit_code = cli.main(
        ["record-evidence-package", "--title", "Evidence", "--include-artifact-discovery"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [{"artifact_discovery": artifact_discovery_payload}]
    assert payload == {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def test_record_evidence_package_can_capture_latest_review_package_when_opted_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    latest_review_payload = {
        "ok": True,
        "selection_mode": "latest_review_package",
        "review_package_root": "C:/Projects/aresforge/artifacts/local_reviews/generated",
        "review_package_root_exists": True,
        "review_package_count": 1,
        "selected_review_path": "20260520T120003Z-local-review.json",
        "selected_review_package": {"review_path": "20260520T120003Z-local-review.json"},
    }
    calls: list[dict[str, object | None]] = []
    bundle = ArtifactBundle(
        markdown_path=tmp_path / "evidence.md",
        json_path=tmp_path / "evidence.json",
        payload={"ok": True},
    )

    monkeypatch.setattr(
        cli,
        "latest_local_review_package_summary",
        lambda _config: latest_review_payload,
    )

    def fake_render_evidence_package(**kwargs: object) -> ArtifactBundle:
        calls.append({"latest_review_package": kwargs["latest_review_package"]})
        return bundle

    monkeypatch.setattr(cli, "render_evidence_package", fake_render_evidence_package)

    exit_code = cli.main(
        ["record-evidence-package", "--title", "Evidence", "--include-latest-review-package"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [{"latest_review_package": latest_review_payload}]
    assert payload == {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def test_prepare_codex_handoff_does_not_capture_latest_review_package_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    bundle = ArtifactBundle(
        markdown_path=tmp_path / "handoff.md",
        json_path=tmp_path / "handoff.json",
        payload={"ok": True},
    )
    calls: list[dict[str, object | None]] = []

    monkeypatch.setattr(cli, "build_route_plan", lambda **_kwargs: object())
    monkeypatch.setattr(
        cli,
        "latest_local_review_package_summary",
        lambda _config: pytest.fail("prepare-codex-handoff must not capture latest review package unless opted in"),
    )

    def fake_render_codex_handoff(**kwargs: object) -> ArtifactBundle:
        calls.append({"latest_review_package": kwargs["latest_review_package"]})
        return bundle

    monkeypatch.setattr(cli, "render_codex_handoff", fake_render_codex_handoff)

    exit_code = cli.main(
        [
            "prepare-codex-handoff",
            "--title",
            "Handoff",
            "--summary",
            "Summary",
            "--requested-output",
            "Output",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [{"latest_review_package": None}]
    assert payload == {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def test_prepare_codex_handoff_can_capture_latest_review_package_when_opted_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    latest_review_payload = {
        "ok": True,
        "selection_mode": "latest_review_package",
        "review_package_root": "C:/Projects/aresforge/artifacts/local_reviews/generated",
        "review_package_root_exists": True,
        "review_package_count": 1,
        "selected_review_path": "20260520T120003Z-local-review.json",
        "selected_review_package": {"review_path": "20260520T120003Z-local-review.json"},
    }
    bundle = ArtifactBundle(
        markdown_path=tmp_path / "handoff.md",
        json_path=tmp_path / "handoff.json",
        payload={"ok": True},
    )
    calls: list[dict[str, object | None]] = []

    monkeypatch.setattr(cli, "build_route_plan", lambda **_kwargs: object())
    monkeypatch.setattr(
        cli,
        "latest_local_review_package_summary",
        lambda _config: latest_review_payload,
    )

    def fake_render_codex_handoff(**kwargs: object) -> ArtifactBundle:
        calls.append({"latest_review_package": kwargs["latest_review_package"]})
        return bundle

    monkeypatch.setattr(cli, "render_codex_handoff", fake_render_codex_handoff)

    exit_code = cli.main(
        [
            "prepare-codex-handoff",
            "--title",
            "Handoff",
            "--summary",
            "Summary",
            "--requested-output",
            "Output",
            "--include-latest-review-package",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert calls == [{"latest_review_package": latest_review_payload}]
    assert payload == {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def test_inspect_work_item_readiness_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    readiness_payload = {
        "ok": True,
        "work_item_id": "work-1",
        "project_id": "project-aresforge",
        "readiness_status": "ready",
        "ready": True,
        "next_safe_action": "Start work item or assign to operator.",
        "blockers": [],
        "warnings": [],
        "work_item": {"id": "work-1", "status": "queued"},
        "roadmap_links": [],
        "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
        "related_events": {"audit_event_count": 0, "roadmap_event_count": 0},
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "inspect_work_item_readiness", lambda _conn, _work_item_id: readiness_payload)

    exit_code = cli.main(["inspect-work-item-readiness", "--work-item-id", "work-1", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == readiness_payload


def test_build_work_item_execution_dossier_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dossier_payload = {
        "ok": True,
        "work_item_id": "work-1",
        "dossier_status": "active",
        "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "build_work_item_execution_dossier", lambda _conn, _work_item_id: dossier_payload)

    exit_code = cli.main(
        ["build-work-item-execution-dossier", "--work-item-id", "work-1", "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == dossier_payload


def test_build_work_item_execution_dossier_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dossier_payload = {
        "ok": False,
        "work_item_id": "work-missing",
        "dossier_status": "missing",
        "next_safe_action": "Create or inspect the local work item before starting.",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "build_work_item_execution_dossier", lambda _conn, _work_item_id: dossier_payload)
    monkeypatch.setattr(
        cli,
        "render_work_item_execution_dossier_markdown",
        lambda _payload: "# Work Item Execution Dossier\n",
    )

    exit_code = cli.main(
        ["build-work-item-execution-dossier", "--work-item-id", "work-missing", "--format", "markdown"]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Work Item Execution Dossier\n\n"


def test_inspect_queue_readiness_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    readiness_payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "queue_id": None,
        "total_items": 0,
        "counts": {
            "ready": 0,
            "not_ready": 0,
            "blocked": 0,
            "already_active": 0,
            "already_complete": 0,
            "cancelled": 0,
            "missing": 0,
        },
        "work_items": [],
        "next_ready_work_items": [],
        "blocked_work_items": [],
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "inspect_queue_readiness",
        lambda _conn, queue_id=None, project_id="project-aresforge": readiness_payload,
    )
    monkeypatch.setattr(cli, "render_queue_readiness_markdown", lambda payload: "# Queue Readiness\n")

    exit_code = cli.main(["inspect-queue-readiness", "--format", "markdown"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Queue Readiness\n\n"


def test_start_work_item_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "previous_status": "queued",
        "new_status": "active",
        "readiness_status": "ready",
        "reason": "started",
        "next_safe_action": "Continue or inspect active work item.",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "start_work_item_if_ready", lambda _conn, _work_item_id, actor, details: payload)
    exit_code = cli.main(["start-work-item", "--work-item-id", "work-1", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_start_work_item_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": False,
        "changed": False,
        "work_item_id": "work-1",
        "readiness_status": "blocked",
        "reason": "work_item_not_ready",
        "next_safe_action": "Resolve blockers before starting.",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "start_work_item_if_ready", lambda _conn, _work_item_id, actor, details: payload)
    monkeypatch.setattr(cli, "render_start_work_item_markdown", lambda _payload: "# Start Work Item\n")
    exit_code = cli.main(["start-work-item", "--work-item-id", "work-1", "--format", "markdown"])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Start Work Item\n\n"


def test_start_work_item_dispatch_parses_bom_details_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    details_path = tmp_path / "details-bom.json"
    details_path.write_text('\ufeff{"source":"unit-test"}', encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_start_work_item_if_ready(
        _conn: object, _work_item_id: str, actor: str, details: dict[str, object]
    ) -> dict[str, object]:
        seen["actor"] = actor
        seen["details"] = details
        return {"ok": True, "changed": False, "work_item_id": _work_item_id}

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "start_work_item_if_ready", fake_start_work_item_if_ready)
    exit_code = cli.main(
        [
            "start-work-item",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--details-file",
            str(details_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen == {"actor": "local-test", "details": {"source": "unit-test"}}
    assert payload["ok"] is True


def test_complete_work_item_if_ready_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "complete_work_item_if_ready",
        lambda _conn, _work_item_id, actor, details: {
            "ok": True,
            "mutated": True,
            "work_item_id": _work_item_id,
            "completion_status": "completed",
        },
    )
    monkeypatch.setattr(
        cli,
        "render_work_item_completion_markdown",
        lambda _payload: "# Complete Work Item\n",
    )
    exit_code = cli.main(
        [
            "complete-work-item-if-ready",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Complete Work Item\n\n"


def test_complete_work_item_if_ready_dispatch_parses_bom_details_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    details_path = tmp_path / "details-bom.json"
    details_path.write_text('\ufeff{"source":"unit-test"}', encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_complete_work_item_if_ready(
        _conn: object, _work_item_id: str, actor: str, details: dict[str, object]
    ) -> dict[str, object]:
        seen["actor"] = actor
        seen["details"] = details
        return {"ok": True, "mutated": True, "work_item_id": _work_item_id}

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "complete_work_item_if_ready", fake_complete_work_item_if_ready)
    exit_code = cli.main(
        [
            "complete-work-item-if-ready",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--details-file",
            str(details_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen == {"actor": "local-test", "details": {"source": "unit-test"}}
    assert payload["ok"] is True


def test_plan_work_item_queue_transition_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_payload = {
        "ok": True,
        "work_item_id": "work-1",
        "can_transition": True,
        "transition_status": "ready",
        "reason": "transition_allowed",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "plan_work_item_queue_transition",
        lambda _conn, _work_item_id, _target_queue_id: plan_payload,
    )
    monkeypatch.setattr(
        cli,
        "render_work_item_queue_transition_plan_markdown",
        lambda _payload: "# Queue Transition Plan\n",
    )

    exit_code = cli.main(
        [
            "plan-work-item-queue-transition",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-triage",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Queue Transition Plan\n\n"


def test_move_work_item_queue_dispatch_parses_bom_details_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    details_path = tmp_path / "details-bom.json"
    details_path.write_text('\ufeff{"source":"unit-test"}', encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_move_work_item_queue_if_allowed(
        _conn: object,
        _work_item_id: str,
        _target_queue_id: str,
        actor: str,
        details: dict[str, object],
    ) -> dict[str, object]:
        seen["actor"] = actor
        seen["details"] = details
        return {"ok": True, "changed": True, "work_item_id": _work_item_id}

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "move_work_item_queue_if_allowed", fake_move_work_item_queue_if_allowed)

    exit_code = cli.main(
        [
            "move-work-item-queue",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-triage",
            "--actor",
            "local-test",
            "--details-file",
            str(details_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen == {"actor": "local-test", "details": {"source": "unit-test"}}
    assert payload["ok"] is True


def test_request_work_item_queue_approval_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "request_work_item_queue_approval",
        lambda _conn, work_item_id, target_queue_id, actor, details: {
            "ok": True,
            "work_item_id": work_item_id,
            "target_queue_id": target_queue_id,
            "approval_status": "pending",
        },
    )
    exit_code = cli.main(
        [
            "request-work-item-queue-approval",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-implementation",
            "--actor",
            "local-test",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["approval_status"] == "pending"


def test_approve_work_item_queue_approval_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "approve_work_item_queue_approval",
        lambda _conn, work_item_id, target_queue_id, actor, details: {
            "ok": True,
            "work_item_id": work_item_id,
            "target_queue_id": target_queue_id,
            "approval_status": "approved",
        },
    )
    monkeypatch.setattr(
        cli,
        "render_work_item_queue_approval_markdown",
        lambda _payload: "# Work Item Queue Approval\n",
    )
    exit_code = cli.main(
        [
            "approve-work-item-queue-approval",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-implementation",
            "--actor",
            "local-test",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Work Item Queue Approval\n\n"


def test_inspect_work_item_queue_approval_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "inspect_work_item_queue_approval_state",
        lambda _conn, work_item_id, target_queue_id: {
            "ok": True,
            "work_item_id": work_item_id,
            "target_queue_id": target_queue_id,
            "approval_status": "pending",
        },
    )
    exit_code = cli.main(
        [
            "inspect-work-item-queue-approval",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-implementation",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["approval_status"] == "pending"


def test_handoff_work_item_to_implementation_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    handoff_payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "previous_queue_id": "queue-triage",
        "new_queue_id": "queue-implementation",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "handoff_work_item_to_implementation",
        lambda _conn, _work_item_id, actor, details: handoff_payload,
    )
    exit_code = cli.main(
        ["handoff-work-item-to-implementation", "--work-item-id", "work-1", "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == handoff_payload


def test_handoff_work_item_to_implementation_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    handoff_payload = {
        "ok": False,
        "changed": False,
        "work_item_id": "work-missing",
        "reason": "work_item_not_found",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "handoff_work_item_to_implementation",
        lambda _conn, _work_item_id, actor, details: handoff_payload,
    )
    monkeypatch.setattr(
        cli,
        "render_implementation_handoff_markdown",
        lambda _payload: "# Implementation Handoff\n",
    )
    exit_code = cli.main(
        ["handoff-work-item-to-implementation", "--work-item-id", "work-missing", "--format", "markdown"]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Implementation Handoff\n\n"


def test_handoff_work_item_to_implementation_dispatch_parses_bom_details_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    details_path = tmp_path / "details-bom.json"
    details_path.write_text('\ufeff{"source":"unit-test"}', encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_handoff_work_item_to_implementation(
        _conn: object, _work_item_id: str, actor: str, details: dict[str, object]
    ) -> dict[str, object]:
        seen["actor"] = actor
        seen["details"] = details
        return {"ok": True, "changed": False, "work_item_id": _work_item_id}

    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "handoff_work_item_to_implementation", fake_handoff_work_item_to_implementation)
    exit_code = cli.main(
        [
            "handoff-work-item-to-implementation",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--details-file",
            str(details_path),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert seen == {"actor": "local-test", "details": {"source": "unit-test"}}
    assert payload["ok"] is True


def test_inspect_project_queue_dashboard_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dashboard_payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "dashboard_status": "ready",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "inspect_project_queue_dashboard",
        lambda _conn, project_id="project-aresforge": dashboard_payload,
    )
    exit_code = cli.main(["inspect-project-queue-dashboard", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == dashboard_payload


def test_inspect_project_queue_dashboard_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dashboard_payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "dashboard_status": "ready",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "inspect_project_queue_dashboard",
        lambda _conn, project_id="project-aresforge": dashboard_payload,
    )
    monkeypatch.setattr(
        cli,
        "render_project_queue_dashboard_markdown",
        lambda _payload: "# Project Queue Dashboard\n",
    )
    exit_code = cli.main(["inspect-project-queue-dashboard", "--format", "markdown"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Project Queue Dashboard\n\n"


def test_inspect_local_project_dashboard_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "local_only": True,
        "total_projects": 0,
        "active_project": None,
    }
    monkeypatch.setattr(cli, "summarize_local_project_dashboard", lambda _config: payload)
    exit_code = cli.main(["inspect-local-project-dashboard"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_list_local_projects_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "project_count": 0, "projects": []}
    monkeypatch.setattr(cli, "list_local_projects", lambda _config: payload)
    exit_code = cli.main(["list-local-projects"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_local_project_readiness_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "project_id": "p1", "readiness_status": "ready"}
    monkeypatch.setattr(cli, "inspect_local_project_readiness", lambda _config, project_id: payload)
    exit_code = cli.main(["inspect-local-project-readiness", "--project-id", "p1"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_local_queue_agent_summary_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "queue_totals": {"item_count": 0}}
    monkeypatch.setattr(cli, "inspect_local_queue_agent_summary", lambda _config: payload)
    exit_code = cli.main(["inspect-local-queue-agent-summary"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_local_queue_item_readiness_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "item_id": "q1", "readiness_status": "ready"}
    monkeypatch.setattr(cli, "inspect_local_queue_item_readiness", lambda _config, item_id, queue_path=None, registry_path=None: payload)
    exit_code = cli.main(["inspect-local-queue-item-readiness", "--item-id", "q1"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_queue_consistency_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps({"item_count": 1, "blocked_items": []}),
    }
    monkeypatch.setattr(
        cli,
        "inspect_queue_consistency",
        lambda _config, queue_path=None, project_id=None, repo_id=None, output_format="json": payload,
    )
    exit_code = cli.main(["inspect-queue-consistency", "--project-id", "p1", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == {"item_count": 1, "blocked_items": []}


def test_start_local_queue_item_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "item_id": "q1", "status": "in_progress"}
    monkeypatch.setattr(cli, "start_local_queue_item", lambda _config, item_id, queue_path=None, registry_path=None: payload)
    exit_code = cli.main(["start-local-queue-item", "--item-id", "q1"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_local_project_report_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "report_type": "local_project_report_summary"}
    monkeypatch.setattr(cli, "inspect_local_project_report", lambda _config: payload)
    exit_code = cli.main(["inspect-local-project-report"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_self_managed_project_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "wrote_output_file": False, "stdout": "# Self-Managed Project Review\n"}
    monkeypatch.setattr(
        cli,
        "inspect_self_managed_project",
        lambda _config, project_id, output_format="markdown": payload,
    )
    exit_code = cli.main(["inspect-self-managed-project", "--project-id", "aresforge"])
    assert exit_code == 0
    assert "Self-Managed Project Review" in capsys.readouterr().out


def test_inspect_self_managed_project_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps({"project_id": "aresforge", "read_only": True}),
    }
    monkeypatch.setattr(
        cli,
        "inspect_self_managed_project",
        lambda _config, project_id, output_format="markdown": payload,
    )
    exit_code = cli.main(["inspect-self-managed-project", "--project-id", "aresforge", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == {"project_id": "aresforge", "read_only": True}


def test_export_work_item_operator_prompt_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "output_path": "artifacts/work-1.txt",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "export_work_item_operator_prompt",
        lambda _conn, _work_item_id, _output, force=False: payload,
    )
    exit_code = cli.main(
        [
            "export-work-item-operator-prompt",
            "--work-item-id",
            "work-1",
            "--output",
            "artifacts/work-1.txt",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_export_work_item_operator_prompt_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": False, "changed": False, "reason": "output_file_exists"}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "export_work_item_operator_prompt",
        lambda _conn, _work_item_id, _output, force=False: payload,
    )
    monkeypatch.setattr(
        cli,
        "render_export_work_item_operator_prompt_markdown",
        lambda _payload: "# Export Work Item Operator Prompt\n",
    )
    exit_code = cli.main(
        [
            "export-work-item-operator-prompt",
            "--work-item-id",
            "work-1",
            "--output",
            "artifacts/work-1.txt",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Export Work Item Operator Prompt\n\n"


def test_generate_local_queue_item_codex_prompt_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "item_id": "work-1",
        "prompt": "# Codex Prompt Package",
        "readiness_status": "ready",
        "warnings": [],
    }
    monkeypatch.setattr(
        cli,
        "generate_local_queue_item_codex_prompt",
        lambda _config, item_id, queue_path=None, registry_path=None, output=None, force=False, commit_message=None: payload,
    )
    exit_code = cli.main(
        [
            "generate-local-queue-item-codex-prompt",
            "--item-id",
            "work-1",
            "--commit-message",
            "queue prompt commit",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_inspect_codex_dispatch_contract_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "dry_run_only": True,
                "dispatch_allowed": False,
                "codex_cli_invocation_allowed": False,
            }
        ),
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "inspect_codex_dispatch_contract",
        lambda _config, item_id, queue_path=None, registry_path=None, output_format="json": payload,
    )
    exit_code = cli.main(["inspect-codex-dispatch-contract", "--item-id", "m77", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dry_run_only"] is True
    assert parsed["dispatch_allowed"] is False


def test_prepare_codex_dispatch_dry_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "dry_run_only": True,
                "execution_mode": "dry_run_no_execute",
                "codex_cli_invocation_allowed": False,
            }
        ),
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "prepare_codex_dispatch_dry_run",
        lambda _config, item_id, queue_path=None, registry_path=None, output=None, force=False, output_format="json": payload,
    )
    exit_code = cli.main(["prepare-codex-dispatch-dry-run", "--item-id", "m77", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_mode"] == "dry_run_no_execute"
    assert parsed["codex_cli_invocation_allowed"] is False


def test_prepare_queue_item_dispatch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "item_id": "m78-5",
                "target": "codex",
                "dispatch_allowed": False,
                "automatic_next_item_execution_allowed": False,
                "queue_completion_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_prepare(
        _config,
        item_id,
        target="codex",
        queue_path=None,
        registry_path=None,
        output=None,
        start_if_ready=False,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["target"] = target
        seen["start_if_ready"] = start_if_ready
        seen["force"] = force
        return payload

    monkeypatch.setattr(cli, "prepare_queue_item_dispatch", fake_prepare)
    exit_code = cli.main(
        [
            "prepare-queue-item-dispatch",
            "--item-id",
            "m78-5",
            "--target",
            "codex",
            "--start-if-ready",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dispatch_allowed"] is False
    assert parsed["automatic_next_item_execution_allowed"] is False
    assert parsed["queue_completion_allowed"] is False
    assert seen["item_id"] == "m78-5"
    assert seen["target"] == "codex"
    assert seen["start_if_ready"] is True
    assert seen["force"] is True


def test_inspect_llm_decision_matrix_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "advisory_only": True,
                "item_id": "m80",
                "routing_confidence": {
                    "score": 72,
                    "recommended_lane": "local_llm_advisory",
                    "warnings": [],
                },
                "execution_allowed": False,
                "automatic_next_item_execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, item_id, queue_path=None, registry_path=None, output_format="json"):
        seen["item_id"] = item_id
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_llm_decision_matrix", fake_inspect)
    exit_code = cli.main(["inspect-llm-decision-matrix", "--item-id", "m80", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["advisory_only"] is True
    assert parsed["routing_confidence"]["score"] == 72
    assert parsed["routing_confidence"]["recommended_lane"] == "local_llm_advisory"
    assert parsed["execution_allowed"] is False
    assert parsed["automatic_next_item_execution_allowed"] is False
    assert seen["item_id"] == "m80"
    assert seen["output_format"] == "json"


def test_inspect_local_llm_advisory_lane_readiness_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "advisory_only": True,
                "item_id": "m81",
                "execution_allowed": False,
                "local_llm_invocation_allowed": False,
                "repo_mutation_allowed": False,
                "queue_mutation_allowed": False,
                "automatic_next_item_execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, item_id, queue_path=None, registry_path=None, output_format="json"):
        seen["item_id"] = item_id
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_local_llm_advisory_lane_readiness", fake_inspect)
    exit_code = cli.main(
        ["inspect-local-llm-advisory-lane-readiness", "--item-id", "m81", "--format", "json"]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["advisory_only"] is True
    assert parsed["execution_allowed"] is False
    assert parsed["local_llm_invocation_allowed"] is False
    assert parsed["repo_mutation_allowed"] is False
    assert parsed["queue_mutation_allowed"] is False
    assert parsed["automatic_next_item_execution_allowed"] is False
    assert seen["item_id"] == "m81"
    assert seen["output_format"] == "json"


def test_inspect_local_llm_provider_contract_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "read_only": True,
                "provider": "ollama",
                "initial_provider_target": "ollama",
                "safety_boundary": {
                    "provider_invocation_allowed_from_this_command": False,
                    "repo_mutation_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                    "github_api_allowed": False,
                    "gh_allowed": False,
                },
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output_format="json"):
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_local_llm_provider_contract", fake_inspect)
    exit_code = cli.main(["inspect-local-llm-provider-contract", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["provider"] == "ollama"
    assert parsed["initial_provider_target"] == "ollama"
    assert parsed["safety_boundary"]["provider_invocation_allowed_from_this_command"] is False
    assert parsed["safety_boundary"]["repo_mutation_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    assert parsed["safety_boundary"]["github_api_allowed"] is False
    assert parsed["safety_boundary"]["gh_allowed"] is False
    assert seen["output_format"] == "json"


def test_inspect_ollama_health_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "available": False,
                "provider": "ollama",
                "endpoint": "http://127.0.0.1:11434/api/tags",
                "models": [],
                "error_summary": "offline",
                "next_safe_action": "continue without blocking readiness",
                "safety_boundary": {
                    "generation_allowed": False,
                    "repo_mutation_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                },
            }
        ),
        "payload": {},
    }

    monkeypatch.setattr(cli, "inspect_ollama_health_and_models", lambda _config, output_format="json": payload)
    exit_code = cli.main(["inspect-ollama-health", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["available"] is False
    assert parsed["provider"] == "ollama"
    assert parsed["models"] == []
    assert parsed["safety_boundary"]["generation_allowed"] is False
    assert parsed["safety_boundary"]["repo_mutation_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False


def test_probe_local_ollama_provider_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "probe_type": "local_ollama_provider_probe",
                "probed": True,
                "blocked": False,
                "ollama_expected": True,
                "ollama_detected": False,
                "probe_method": "config_only_no_network",
                "configured_model_profiles": [],
                "available_models": [],
                "advisory_execution_allowed": False,
                "prompt_execution_performed": False,
                "coding_execution_performed": False,
                "reasoning_execution_performed": False,
                "network_execution_performed": False,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_probe(
        _config,
        output=None,
        force=False,
        no_network=False,
        config_path=None,
        output_format="markdown",
    ):
        seen["output"] = output
        seen["force"] = force
        seen["no_network"] = no_network
        seen["config_path"] = config_path
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "probe_local_ollama_provider", fake_probe)
    exit_code = cli.main(
        [
            "probe-local-ollama-provider",
            "--format",
            "json",
            "--output",
            "artifacts/probes/ollama.json",
            "--force",
            "--no-network",
            "--config",
            ".aresforge/local_llm_environment.json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["probe_type"] == "local_ollama_provider_probe"
    assert parsed["prompt_execution_performed"] is False
    assert parsed["network_execution_performed"] is False
    assert seen == {
        "output": "artifacts/probes/ollama.json",
        "force": True,
        "no_network": True,
        "config_path": ".aresforge/local_llm_environment.json",
        "output_format": "json",
    }


def test_recommend_llm_decision_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "recommendation_type": "llm_decision_policy_v1",
                "item_id": "m127",
                "agent_id": "validation-agent",
                "recommended_lane": "validation_agent",
                "recommended_provider": "agent_registry",
                "recommended_model_profile": "deterministic_validation_plan",
                "alternatives": [],
                "decision_reasons": ["validation"],
                "risk_assessment": {"effective_risk_level": "medium"},
                "autonomy_allowed": True,
                "machine_gate_required": True,
                "human_review_required": True,
                "execution_performed": False,
                "local_only": True,
                "next_safe_action": "Review only.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_recommend(
        _config,
        *,
        item_id,
        agent_id=None,
        task_type=None,
        risk_level=None,
        mutation_scope=None,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["agent_id"] = agent_id
        seen["task_type"] = task_type
        seen["risk_level"] = risk_level
        seen["mutation_scope"] = mutation_scope
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "recommend_llm_decision", fake_recommend)
    exit_code = cli.main(
        [
            "recommend-llm-decision",
            "--item-id",
            "m127",
            "--agent-id",
            "validation-agent",
            "--task-type",
            "validation",
            "--risk-level",
            "medium",
            "--mutation-scope",
            "none",
            "--queue-path",
            ".aresforge/queue/work_items.json",
            "--output",
            "artifacts/llm-decisions/m127.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["recommendation_type"] == "llm_decision_policy_v1"
    assert parsed["execution_performed"] is False
    assert seen == {
        "item_id": "m127",
        "agent_id": "validation-agent",
        "task_type": "validation",
        "risk_level": "medium",
        "mutation_scope": "none",
        "queue_path": ".aresforge/queue/work_items.json",
        "output": "artifacts/llm-decisions/m127.json",
        "force": True,
        "output_format": "json",
    }


def test_build_agent_orchestration_plan_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "plan_type": "agent_orchestration_plan",
                "generated": True,
                "item_id": "m128",
                "requested_execution_target": "dry-run",
                "recommended_execution_target": "dry-run",
                "steps": [],
                "execution_performed": False,
                "local_only": True,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_build(
        _config,
        *,
        item_id,
        agent_id=None,
        execution_target="dry-run",
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["agent_id"] = agent_id
        seen["execution_target"] = execution_target
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "build_agent_orchestration_plan", fake_build)
    exit_code = cli.main(
        [
            "build-agent-orchestration-plan",
            "--item-id",
            "m128",
            "--agent-id",
            "documentation-agent",
            "--execution-target",
            "dry-run",
            "--queue-path",
            ".aresforge/queue/work_items.json",
            "--output",
            "artifacts/orchestration-plans/m128.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["plan_type"] == "agent_orchestration_plan"
    assert parsed["execution_performed"] is False
    assert seen == {
        "item_id": "m128",
        "agent_id": "documentation-agent",
        "execution_target": "dry-run",
        "queue_path": ".aresforge/queue/work_items.json",
        "output": "artifacts/orchestration-plans/m128.json",
        "force": True,
        "output_format": "json",
    }


def test_run_agent_dry_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "execution_record_type": "single_agent_dry_run",
                "agent_id": "artifact-registry-agent",
                "item_id": "m129",
                "dry_run": True,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        *,
        agent_id,
        item_id,
        plan_path=None,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["agent_id"] = agent_id
        seen["item_id"] = item_id
        seen["plan_path"] = plan_path
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "run_single_agent_dry_run", fake_run)
    exit_code = cli.main(
        [
            "run-agent-dry-run",
            "--agent-id",
            "artifact-registry-agent",
            "--item-id",
            "m129",
            "--plan-path",
            "plan.json",
            "--queue-path",
            "queue.json",
            "--output",
            "record.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "single_agent_dry_run"
    assert parsed["dry_run"] is True
    assert seen == {
        "agent_id": "artifact-registry-agent",
        "item_id": "m129",
        "plan_path": "plan.json",
        "queue_path": "queue.json",
        "output": "record.json",
        "force": True,
        "output_format": "json",
    }


def test_run_agent_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "stdout": json.dumps(
            {
                "execution_record_type": "single_agent_real_execution",
                "agent_id": "artifact-registry-agent",
                "item_id": "m130",
                "dry_run": False,
                "real_execution": True,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        *,
        agent_id,
        item_id,
        queue_path=None,
        output=None,
        force=False,
        require_machine_gates=False,
        output_format="json",
    ):
        seen["agent_id"] = agent_id
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["require_machine_gates"] = require_machine_gates
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "run_single_agent_real_execution", fake_run)
    exit_code = cli.main(
        [
            "run-agent",
            "--agent-id",
            "artifact-registry-agent",
            "--item-id",
            "m130",
            "--queue-path",
            "queue.json",
            "--output",
            "record.json",
            "--force",
            "--require-machine-gates",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "single_agent_real_execution"
    assert parsed["real_execution"] is True
    assert seen == {
        "agent_id": "artifact-registry-agent",
        "item_id": "m130",
        "queue_path": "queue.json",
        "output": "record.json",
        "force": True,
        "require_machine_gates": True,
        "output_format": "json",
    }


def test_evaluate_machine_safety_gates_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "gate_result_type": "machine_safety_gate_evaluation",
                "item_id": "m131",
                "gate_profile": "docs_only_patch_apply",
                "passed": True,
                "blocked": False,
                "execution_performed": False,
                "mutation_performed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_evaluate(
        _config,
        *,
        item_id,
        gate_profile="read_only_agent",
        artifact_path=None,
        patch_path=None,
        execution_record=None,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["gate_profile"] = gate_profile
        seen["artifact_path"] = artifact_path
        seen["patch_path"] = patch_path
        seen["execution_record"] = execution_record
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "evaluate_machine_safety_gates", fake_evaluate)
    exit_code = cli.main(
        [
            "evaluate-machine-safety-gates",
            "--item-id",
            "m131",
            "--gate-profile",
            "docs_only_patch_apply",
            "--artifact-path",
            "artifacts/m131.json",
            "--patch-path",
            "artifacts/m131.patch",
            "--execution-record",
            "artifacts/m131-record.json",
            "--queue-path",
            "queue.json",
            "--output",
            "gates.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["gate_result_type"] == "machine_safety_gate_evaluation"
    assert parsed["execution_performed"] is False
    assert parsed["mutation_performed"] is False
    assert seen == {
        "item_id": "m131",
        "gate_profile": "docs_only_patch_apply",
        "artifact_path": "artifacts/m131.json",
        "patch_path": "artifacts/m131.patch",
        "execution_record": "artifacts/m131-record.json",
        "queue_path": "queue.json",
        "output": "gates.json",
        "force": True,
        "output_format": "json",
    }


def test_auto_complete_safe_queue_item_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "action_type": "auto_complete_safe_queue_item",
                "item_id": "m132",
                "auto_completed": False,
                "dry_run": True,
                "queue_mutation_performed": False,
                "external_execution_performed": False,
                "model_execution_performed": False,
                "github_execution_performed": False,
                "patch_application_performed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_auto_complete(
        _config,
        *,
        item_id,
        evidence_path=None,
        gate_profile="queue_status_mutation",
        queue_path=None,
        dry_run=False,
        force=False,
        output=None,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["evidence_path"] = evidence_path
        seen["gate_profile"] = gate_profile
        seen["queue_path"] = queue_path
        seen["dry_run"] = dry_run
        seen["force"] = force
        seen["output"] = output
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "auto_complete_safe_queue_item", fake_auto_complete)
    exit_code = cli.main(
        [
            "auto-complete-safe-queue-item",
            "--item-id",
            "m132",
            "--evidence-path",
            "artifacts/dispatch_result_evidence/m132.json",
            "--gate-profile",
            "queue_status_mutation",
            "--queue-path",
            "queue.json",
            "--dry-run",
            "--output",
            "auto-complete.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["action_type"] == "auto_complete_safe_queue_item"
    assert parsed["external_execution_performed"] is False
    assert seen == {
        "item_id": "m132",
        "evidence_path": "artifacts/dispatch_result_evidence/m132.json",
        "gate_profile": "queue_status_mutation",
        "queue_path": "queue.json",
        "dry_run": True,
        "force": True,
        "output": "auto-complete.json",
        "output_format": "json",
    }


def test_apply_docs_only_patch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "action_type": "docs_only_patch_apply",
                "item_id": "m133",
                "patch_path": "artifacts/manual/docs.patch",
                "dry_run": True,
                "applied": False,
                "blocked": False,
                "source_code_changed": False,
                "tests_changed": False,
                "external_execution_performed": False,
                "model_execution_performed": False,
                "github_execution_performed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_apply(
        _config,
        *,
        item_id,
        patch_path,
        queue_path=None,
        dry_run=False,
        force=False,
        output=None,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["patch_path"] = patch_path
        seen["queue_path"] = queue_path
        seen["dry_run"] = dry_run
        seen["force"] = force
        seen["output"] = output
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "apply_docs_only_patch", fake_apply)
    exit_code = cli.main(
        [
            "apply-docs-only-patch",
            "--item-id",
            "m133",
            "--patch-path",
            "artifacts/manual/docs.patch",
            "--queue-path",
            "queue.json",
            "--dry-run",
            "--output",
            "docs-apply.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["action_type"] == "docs_only_patch_apply"
    assert parsed["source_code_changed"] is False
    assert parsed["tests_changed"] is False
    assert seen == {
        "item_id": "m133",
        "patch_path": "artifacts/manual/docs.patch",
        "queue_path": "queue.json",
        "dry_run": True,
        "force": True,
        "output": "docs-apply.json",
        "output_format": "json",
    }


def test_run_local_llm_advisory_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "execution_record_type": "local_llm_advisory_execution",
                "item_id": "m134",
                "artifact_path": "artifacts/manual/sample-local-llm-advisory.json",
                "provider": "ollama",
                "dry_run": True,
                "executed": False,
                "blocked": False,
                "advisory_only": True,
                "patch_application_performed": False,
                "queue_mutation_performed": False,
                "github_execution_performed": False,
                "codex_execution_performed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        *,
        item_id,
        artifact_path,
        provider="ollama",
        model=None,
        queue_path=None,
        dry_run=False,
        output=None,
        force=False,
        timeout_seconds=None,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["artifact_path"] = artifact_path
        seen["provider"] = provider
        seen["model"] = model
        seen["queue_path"] = queue_path
        seen["dry_run"] = dry_run
        seen["output"] = output
        seen["force"] = force
        seen["timeout_seconds"] = timeout_seconds
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "run_local_llm_advisory_execution", fake_run)
    exit_code = cli.main(
        [
            "run-local-llm-advisory",
            "--item-id",
            "m134",
            "--artifact-path",
            "artifacts/manual/sample-local-llm-advisory.json",
            "--provider",
            "ollama",
            "--model",
            "qwen2.5:32b",
            "--queue-path",
            "queue.json",
            "--dry-run",
            "--output",
            "local-llm-execution.json",
            "--force",
            "--timeout-seconds",
            "45",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "local_llm_advisory_execution"
    assert parsed["advisory_only"] is True
    assert parsed["patch_application_performed"] is False
    assert seen == {
        "item_id": "m134",
        "artifact_path": "artifacts/manual/sample-local-llm-advisory.json",
        "provider": "ollama",
        "model": "qwen2.5:32b",
        "queue_path": "queue.json",
        "dry_run": True,
        "output": "local-llm-execution.json",
        "force": True,
        "timeout_seconds": 45,
        "output_format": "json",
    }


def test_prepare_local_llm_advisory_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "run_requested": False,
                "run_status": "prepared_not_run",
                "prompt_path": "artifacts/local_llm_advisory/generated/m85-prompt.md",
                "response_path": "",
                "provider_model_metadata": {"provider": "ollama", "model": "qwen"},
                "safety_boundary": {
                    "repo_mutation_allowed": False,
                    "queue_completion_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                },
                "next_safe_action": "review prompt",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_prepare(_config, **kwargs):
        seen.update(kwargs)
        return payload

    monkeypatch.setattr(cli, "prepare_local_llm_advisory_run_artifact", fake_prepare)
    exit_code = cli.main(["prepare-local-llm-advisory-run", "--item-id", "m85", "--run-id", "dry", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["item_id"] == "m85"
    assert seen["run"] is False
    assert parsed["run_status"] == "prepared_not_run"
    assert parsed["response_path"] == ""
    assert parsed["safety_boundary"]["repo_mutation_allowed"] is False
    assert parsed["safety_boundary"]["queue_completion_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False


def test_prepare_local_coding_draft_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "draft_only": True,
                "non_applied": True,
                "run_requested": False,
                "run_status": "prepared_not_run",
                "prompt_path": "artifacts/local_coding_drafts/generated/m87-prompt.md",
                "draft_path": "",
                "draft_contract": {
                    "draft_is_authoritative": False,
                    "automatic_patch_application_allowed": False,
                },
                "safety_boundary": {
                    "repo_mutation_allowed": False,
                    "automatic_file_mutation_allowed": False,
                    "automatic_patch_application_allowed": False,
                    "queue_completion_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                },
                "next_safe_action": "review prompt",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_prepare(_config, **kwargs):
        seen.update(kwargs)
        return payload

    monkeypatch.setattr(cli, "prepare_local_coding_draft_artifact", fake_prepare)
    exit_code = cli.main(["prepare-local-coding-draft", "--item-id", "m87", "--run-id", "dry", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["item_id"] == "m87"
    assert seen["run"] is False
    assert parsed["draft_only"] is True
    assert parsed["non_applied"] is True
    assert parsed["draft_contract"]["automatic_patch_application_allowed"] is False
    assert parsed["safety_boundary"]["automatic_file_mutation_allowed"] is False
    assert parsed["safety_boundary"]["automatic_patch_application_allowed"] is False
    assert parsed["safety_boundary"]["queue_completion_allowed"] is False


def test_inspect_human_gated_patch_application_contract_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "read_only": True,
                "dry_run_only": True,
                "patch_application_implemented": False,
                "operator_approval_requirements": {
                    "explicit_approval_required": True,
                    "approval_phrase": "APPROVE LOCAL PATCH APPLICATION",
                },
                "safety_boundary": {
                    "patch_application_allowed_from_this_command": False,
                    "automatic_patch_application_allowed": False,
                    "repo_mutation_allowed": False,
                    "automatic_file_mutation_allowed": False,
                    "queue_completion_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                    "github_api_allowed": False,
                    "gh_allowed": False,
                },
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output_format="json"):
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_human_gated_patch_application_contract", fake_inspect)
    exit_code = cli.main(["inspect-human-gated-patch-application-contract", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output_format"] == "json"
    assert parsed["dry_run_only"] is True
    assert parsed["patch_application_implemented"] is False
    assert parsed["operator_approval_requirements"]["explicit_approval_required"] is True
    assert parsed["safety_boundary"]["patch_application_allowed_from_this_command"] is False
    assert parsed["safety_boundary"]["automatic_patch_application_allowed"] is False
    assert parsed["safety_boundary"]["repo_mutation_allowed"] is False
    assert parsed["safety_boundary"]["queue_completion_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    assert parsed["safety_boundary"]["github_api_allowed"] is False
    assert parsed["safety_boundary"]["gh_allowed"] is False


def test_inspect_model_usage_report_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "read_only": True,
                "codex_dispatch": {
                    "run_count": 1,
                    "token_usage": {
                        "available_count": 0,
                        "unavailable_count": 1,
                        "total_tokens": 0,
                    },
                },
                "local_llm_advisory": {"artifact_count": 0},
                "local_coding_drafts": {"artifact_count": 0},
                "safety_boundary": {
                    "network_calls_allowed": False,
                    "provider_invocation_allowed": False,
                    "repo_mutation_allowed": False,
                    "queue_completion_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                    "github_api_allowed": False,
                    "gh_allowed": False,
                },
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output=None, output_format="json"):
        seen["output"] = output
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_model_usage_report", fake_inspect)
    exit_code = cli.main(["inspect-model-usage-report", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output"] is None
    assert seen["output_format"] == "json"
    assert parsed["codex_dispatch"]["run_count"] == 1
    assert parsed["codex_dispatch"]["token_usage"]["unavailable_count"] == 1
    assert parsed["safety_boundary"]["network_calls_allowed"] is False
    assert parsed["safety_boundary"]["provider_invocation_allowed"] is False
    assert parsed["safety_boundary"]["repo_mutation_allowed"] is False
    assert parsed["safety_boundary"]["queue_completion_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    assert parsed["safety_boundary"]["github_api_allowed"] is False
    assert parsed["safety_boundary"]["gh_allowed"] is False


def test_inspect_sprint_batch_report_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "read_only_by_default": True,
                "commit_window": {"count": 2},
                "items_completed": {"count": 1},
                "validation_evidence": {"tests_recorded_count": 3},
                "dispatch_runs": {"run_count": 4, "recovered_count": 2},
                "queue_posture": {"status_counts": {"done": 27}},
                "next_recommended_milestone": {"item_id": "m95-next"},
                "safety_boundary": {
                    "github_api_allowed": False,
                    "gh_allowed": False,
                    "external_workflow_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                },
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, since_commit=None, commit_count=20, output=None, output_format="json"):
        seen["since_commit"] = since_commit
        seen["commit_count"] = commit_count
        seen["output"] = output
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_sprint_batch_report", fake_inspect)
    exit_code = cli.main(
        ["inspect-sprint-batch-report", "--since-commit", "abc123", "--commit-count", "7", "--format", "json"]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["since_commit"] == "abc123"
    assert seen["commit_count"] == 7
    assert seen["output"] is None
    assert seen["output_format"] == "json"
    assert parsed["commit_window"]["count"] == 2
    assert parsed["items_completed"]["count"] == 1
    assert parsed["dispatch_runs"]["recovered_count"] == 2
    assert parsed["safety_boundary"]["github_api_allowed"] is False
    assert parsed["safety_boundary"]["gh_allowed"] is False
    assert parsed["safety_boundary"]["external_workflow_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False


def test_plan_operator_batch_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "wrote_output_file": False, "stdout": "# Operator Batch Plan\n"}
    monkeypatch.setattr(
        cli,
        "plan_operator_batch",
        lambda _config, project_id, queue_path=None, registry_path=None, limit=10, output_format="markdown": payload,
    )

    exit_code = cli.main(["plan-operator-batch", "--project-id", "aresforge", "--limit", "3"])

    assert exit_code == 0
    assert "Operator Batch Plan" in capsys.readouterr().out


def test_plan_operator_batch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps({"project_id": "aresforge", "execution_allowed": False}),
    }
    monkeypatch.setattr(
        cli,
        "plan_operator_batch",
        lambda _config, project_id, queue_path=None, registry_path=None, limit=10, output_format="markdown": payload,
    )

    exit_code = cli.main(["plan-operator-batch", "--project-id", "aresforge", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed == {"project_id": "aresforge", "execution_allowed": False}


def test_plan_operator_batch_v2_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "plan_type": "operator_batch_sequence_v2",
                "project_id": "aresforge",
                "execution_allowed": False,
            }
        ),
    }

    def fake_plan(
        _config,
        *,
        project_id,
        queue_path=None,
        registry_path=None,
        approval_path=None,
        limit=10,
        include_blocked=False,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen.update(
            {
                "project_id": project_id,
                "queue_path": queue_path,
                "registry_path": registry_path,
                "approval_path": approval_path,
                "limit": limit,
                "include_blocked": include_blocked,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "plan_operator_batch_v2", fake_plan)

    exit_code = cli.main(
        [
            "plan-operator-batch-v2",
            "--project-id",
            "aresforge",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "registry.json",
            "--approval-path",
            "approvals.json",
            "--limit",
            "4",
            "--include-blocked",
            "--output",
            "batch.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["plan_type"] == "operator_batch_sequence_v2"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "project_id": "aresforge",
        "queue_path": "queue.json",
        "registry_path": "registry.json",
        "approval_path": "approvals.json",
        "limit": 4,
        "include_blocked": True,
        "output": "batch.json",
        "force": True,
        "output_format": "json",
    }


def test_inspect_documentation_agent_contract_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "read_only": True,
                "contract_name": "documentation_agent_v1_contract",
                "source_docs_to_update": [
                    "docs/context/BUILD_STATE.md",
                    "docs/context/AGENT_CONTEXT.md",
                    "docs/roadmap/ROADMAP.md",
                ],
                "plan_mode": {"available_now": True, "mutates_files": False},
                "future_gated_apply_mode": {
                    "available_now": False,
                    "explicit_operator_approval_required": True,
                },
                "safety_boundary": {
                    "automatic_doc_updates_allowed": False,
                    "model_output_can_mutate_docs": False,
                    "queue_completion_allowed": False,
                    "automatic_next_item_execution_allowed": False,
                    "github_api_allowed": False,
                    "gh_allowed": False,
                },
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output_format="json"):
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_documentation_agent_contract", fake_inspect)
    exit_code = cli.main(["inspect-documentation-agent-contract", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output_format"] == "json"
    assert parsed["contract_name"] == "documentation_agent_v1_contract"
    assert "docs/context/BUILD_STATE.md" in parsed["source_docs_to_update"]
    assert parsed["plan_mode"]["mutates_files"] is False
    assert parsed["future_gated_apply_mode"]["available_now"] is False
    assert parsed["future_gated_apply_mode"]["explicit_operator_approval_required"] is True
    assert parsed["safety_boundary"]["automatic_doc_updates_allowed"] is False
    assert parsed["safety_boundary"]["model_output_can_mutate_docs"] is False
    assert parsed["safety_boundary"]["queue_completion_allowed"] is False
    assert parsed["safety_boundary"]["automatic_next_item_execution_allowed"] is False
    assert parsed["safety_boundary"]["github_api_allowed"] is False
    assert parsed["safety_boundary"]["gh_allowed"] is False


def test_inspect_agent_runtime_boundary_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "contract_type": "agent_runtime_boundary",
                "generated": True,
                "agent_boundary_version": "m125.1",
                "supported_execution_modes": ["inspect_only", "plan_only"],
                "supported_autonomy_levels": ["manual_only", "recommendation_only"],
                "supported_safety_classes": ["read_only"],
                "allowed_capability_catalog": {"read_local_queue": {}},
                "forbidden_capability_catalog": {"execute_codex": "blocked"},
                "mutation_scope_catalog": {"none": {}},
                "network_scope_catalog": {"none": {}},
                "model_scope_catalog": {"none": {}},
                "evidence_requirements": {"required_before_runtime_handoff": ["agent_id"]},
                "default_runtime_limits": {"execution_allowed_by_this_contract": False},
                "local_only": True,
                "execution_performed": False,
                "next_safe_action": "Use the boundary before future agent execution.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output_format="json"):
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_agent_runtime_boundary", fake_inspect)
    exit_code = cli.main(["inspect-agent-runtime-boundary", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output_format"] == "json"
    assert parsed["contract_type"] == "agent_runtime_boundary"
    assert parsed["generated"] is True
    assert parsed["agent_boundary_version"] == "m125.1"
    assert parsed["execution_performed"] is False


def test_inspect_agent_registry_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "registry_type": "agent_registry",
                "generated": True,
                "agent_count": 1,
                "agents": [{"agent_id": "documentation-agent"}],
                "agents_by_type": {"documentation": ["documentation-agent"]},
                "agents_by_safety_class": {"external_mutation_prohibited": ["documentation-agent"]},
                "agents_by_autonomy_level": {"recommendation_only": ["documentation-agent"]},
                "blocked_agents": ["documentation-agent"],
                "executable_agents": [],
                "dry_run_only_agents": ["documentation-agent"],
                "local_only": True,
                "execution_performed": False,
                "next_safe_action": "Review only.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(
        _config,
        *,
        agent_id=None,
        safety_class=None,
        autonomy_level=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["agent_id"] = agent_id
        seen["safety_class"] = safety_class
        seen["autonomy_level"] = autonomy_level
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_agent_registry", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-agent-registry",
            "--agent-id",
            "documentation-agent",
            "--safety-class",
            "external_mutation_prohibited",
            "--autonomy-level",
            "recommendation_only",
            "--output",
            "artifacts/agent-registry.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen == {
        "agent_id": "documentation-agent",
        "safety_class": "external_mutation_prohibited",
        "autonomy_level": "recommendation_only",
        "output": "artifacts/agent-registry.json",
        "force": True,
        "output_format": "json",
    }
    assert parsed["registry_type"] == "agent_registry"
    assert parsed["execution_performed"] is False


def test_plan_doc_reconciliation_dispatch_preserves_m92_boundaries(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
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
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs",
        github_owner="local",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    seen: dict[str, object] = {}

    def fake_generate(_config, **kwargs):
        seen.update(kwargs)
        return {
            "ok": True,
            "wrote_output_file": False,
            "stdout": json.dumps(
                {
                    "ok": True,
                    "local_only": True,
                    "plan_only": True,
                    "read_only_by_default": True,
                    "source_docs": [],
                    "queue_items": {"detected": True, "total": 1},
                    "recent_commits": {"items": ["abc123 M92 add docs plan"]},
                    "changed_source_docs": {"changed_paths": []},
                    "safety_boundary": {
                        "writes_docs": False,
                        "writes_queue": False,
                        "invokes_local_llm": False,
                        "invokes_codex": False,
                        "auto_starts_next_item": False,
                        "uses_github_api": False,
                        "uses_gh": False,
                    },
                }
            ),
        }

    monkeypatch.setattr(cli, "generate_doc_reconciliation_plan", fake_generate)
    exit_code = cli.main(["plan-doc-reconciliation", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output_format"] == "json"
    assert seen["include_git_state"] is False
    assert parsed["local_only"] is True
    assert parsed["plan_only"] is True
    assert parsed["read_only_by_default"] is True
    assert parsed["safety_boundary"]["writes_docs"] is False
    assert parsed["safety_boundary"]["writes_queue"] is False
    assert parsed["safety_boundary"]["invokes_local_llm"] is False
    assert parsed["safety_boundary"]["invokes_codex"] is False
    assert parsed["safety_boundary"]["auto_starts_next_item"] is False
    assert parsed["safety_boundary"]["uses_github_api"] is False
    assert parsed["safety_boundary"]["uses_gh"] is False


def test_generate_handoff_package_dispatch_preserves_m93_boundaries(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    config = AppConfig(
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
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs",
        github_owner="local",
        github_repo="aresforge",
    )
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: config)
    seen: dict[str, object] = {}

    def fake_generate(_config, **kwargs):
        seen.update(kwargs)
        return {
            "ok": True,
            "wrote_output_file": False,
            "stdout": json.dumps(
                {
                    "handoff_package_version": "m93.v2",
                    "local_only": True,
                    "read_only_by_default": True,
                    "current_head": "abc123",
                    "queue_v2_summary": {"status_counts": {"proposed": 1}},
                    "active_or_ready_items": [{"item_id": "m93-operator-handoff-package-v2"}],
                    "recovered_dispatch_summary": {"recovered_count": 1},
                    "model_routing_summary": {"execution_allowed": False},
                    "safe_command_suggestions": ["python -m aresforge inspect-local-project-report"],
                    "safety_boundary": {
                        "executes_codex": False,
                        "invokes_local_llm": False,
                        "mutates_github": False,
                        "auto_starts_next_item": False,
                    },
                }
            ),
        }

    monkeypatch.setattr(cli, "generate_handoff_package", fake_generate)
    exit_code = cli.main(["generate-handoff-package", "--format", "json"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["output_format"] == "json"
    assert seen["include_doc_excerpts"] is False
    assert parsed["handoff_package_version"] == "m93.v2"
    assert parsed["local_only"] is True
    assert parsed["read_only_by_default"] is True
    assert parsed["model_routing_summary"]["execution_allowed"] is False
    assert parsed["safety_boundary"]["executes_codex"] is False
    assert parsed["safety_boundary"]["invokes_local_llm"] is False
    assert parsed["safety_boundary"]["mutates_github"] is False
    assert parsed["safety_boundary"]["auto_starts_next_item"] is False


def test_generate_safe_dispatch_handoff_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Safe Dispatch Handoff Package\n\n- execution_allowed: False\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "generate_safe_dispatch_handoff",
        lambda _config, project_id="aresforge", queue_path=None, registry_path=None, artifact_root=None, approval_path=None, output=None, force=False, output_format="markdown": payload,
    )

    exit_code = cli.main(["generate-safe-dispatch-handoff"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Safe Dispatch Handoff Package" in output
    assert "execution_allowed: False" in output


def test_generate_safe_dispatch_handoff_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "handoff_type": "safe_dispatch_handoff",
                "project_id": "aresforge",
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }

    def fake_generate(
        _config: AppConfig,
        *,
        project_id: str = "aresforge",
        queue_path=None,
        registry_path=None,
        artifact_root=None,
        approval_path=None,
        output=None,
        force: bool = False,
        output_format: str = "markdown",
    ):
        seen.update(
            {
                "project_id": project_id,
                "queue_path": queue_path,
                "registry_path": registry_path,
                "artifact_root": artifact_root,
                "approval_path": approval_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "generate_safe_dispatch_handoff", fake_generate)
    exit_code = cli.main(
        [
            "generate-safe-dispatch-handoff",
            "--project-id",
            "aresforge",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--artifact-root",
            "artifacts",
            "--approval-path",
            ".aresforge/gates.json",
            "--output",
            "artifacts/handoff.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["handoff_type"] == "safe_dispatch_handoff"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "project_id": "aresforge",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "artifact_root": "artifacts",
        "approval_path": ".aresforge/gates.json",
        "output": "artifacts/handoff.json",
        "force": True,
        "output_format": "json",
    }


def test_test_ollama_uses_health_inspection_without_generation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "available": True, "models": [{"name": "qwen"}]}),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, output_format="json"):
        seen["called"] = True
        return payload

    monkeypatch.setattr(cli, "inspect_ollama_health_and_models", fake_inspect)
    monkeypatch.setattr(cli, "test_generate", lambda *_args, **_kwargs: pytest.fail("test-ollama must not invoke generation"))

    exit_code = cli.main(["test-ollama", "--prompt", "ignored"])
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert seen["called"] is True
    assert parsed["available"] is True
    assert parsed["models"][0]["name"] == "qwen"


def test_run_single_ready_codex_queue_item_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "workflow_state": "completed",
                "item_id": "m79-2",
                "automatic_next_item_execution_allowed": False,
                "next_item_started": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        item_id=None,
        queue_path=None,
        registry_path=None,
        prompt_output=None,
        force_prompt=False,
        approved_by="local_operator",
        approval_phrase="",
        run_id=None,
        command=None,
        timeout_seconds=300,
        validation_commands=None,
        implementation_commit_message="M79.2 add single-item ready Codex automation",
        queue_evidence_commit_message="Record M79.2 queue evidence",
        closed_by="local_operator",
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["command"] = command
        seen["validation_commands"] = validation_commands
        seen["approval_phrase"] = approval_phrase
        seen["implementation_commit_message"] = implementation_commit_message
        return payload

    monkeypatch.setattr(cli, "run_single_ready_codex_queue_item", fake_run)
    exit_code = cli.main(
        [
            "run-single-ready-codex-queue-item",
            "--item-id",
            "m79-2",
            "--approval-phrase",
            "APPROVE CODEX DISPATCH",
            "--command-arg",
            "codex",
            "--validation-command",
            "git diff --check",
            "--implementation-commit-message",
            "M79.2 add single-item ready Codex automation",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["workflow_state"] == "completed"
    assert parsed["automatic_next_item_execution_allowed"] is False
    assert parsed["next_item_started"] is False
    assert seen["item_id"] == "m79-2"
    assert seen["command"] == ["codex"]
    assert seen["validation_commands"] == ["git diff --check"]
    assert seen["approval_phrase"] == "APPROVE CODEX DISPATCH"


def test_inspect_queue_dispatch_plan_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "local_only": True,
                "item_id": "m97",
                "selected_lane": "codex_prompt_artifact",
                "execution_allowed": False,
                "next_safe_action": "Review this plan, then use the future M98 artifact generator.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(_config, item_id, queue_path=None, registry_path=None, output_format="markdown"):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["registry_path"] = registry_path
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "inspect_queue_agent_dispatch_plan", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-queue-dispatch-plan",
            "--item-id",
            "m97",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["selected_lane"] == "codex_prompt_artifact"
    assert parsed["execution_allowed"] is False
    assert parsed["local_only"] is True
    assert seen == {
        "item_id": "m97",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "output_format": "json",
    }


def test_inspect_queue_dispatch_plan_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Queue-to-Agent Dispatch Plan\n\n- selected_lane: documentation_agent_dry_run\n- next_safe_action: Review this plan.\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "inspect_queue_agent_dispatch_plan",
        lambda _config, item_id, queue_path=None, registry_path=None, output_format="markdown": payload,
    )

    exit_code = cli.main(["inspect-queue-dispatch-plan", "--item-id", "m100"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "selected_lane: documentation_agent_dry_run" in output
    assert "next_safe_action: Review this plan." in output


def test_generate_codex_dispatch_artifact_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "generated": True,
                "blocked": False,
                "item_id": "m98",
                "selected_lane": "codex_prompt_artifact",
                "output_path": "",
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": "Review the generated prompt.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_generate(
        _config,
        item_id,
        queue_path=None,
        registry_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["registry_path"] = registry_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "generate_codex_prompt_dispatch_artifact", fake_generate)
    exit_code = cli.main(
        [
            "generate-codex-dispatch-artifact",
            "--item-id",
            "m98",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--output",
            "artifacts/codex_prompt_dispatch/generated/m98.txt",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["generated"] is True
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m98",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "output": "artifacts/codex_prompt_dispatch/generated/m98.txt",
        "force": True,
        "output_format": "json",
    }


def test_generate_codex_dispatch_artifact_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Codex Dispatch Artifact Generator\n\n- generated: True\n- selected_lane: codex_prompt_artifact\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "generate_codex_prompt_dispatch_artifact",
        lambda _config, item_id, queue_path=None, registry_path=None, output=None, force=False, output_format="markdown": payload,
    )

    exit_code = cli.main(["generate-codex-dispatch-artifact", "--item-id", "m98"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "generated: True" in output
    assert "selected_lane: codex_prompt_artifact" in output


def test_validate_local_llm_advisory_dry_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "dry_run": True,
                "ready_for_future_advisory_run": True,
                "blocked": False,
                "item_id": "m99",
                "selected_lane": "local_llm_advisory",
                "advisory_intent": "Prepare a future local advisory dry-run validation plan.",
                "recommended_model_role": "reasoning/advisory",
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": "Review the dry-run output.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_validate(
        _config,
        item_id,
        queue_path=None,
        registry_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["registry_path"] = registry_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "validate_local_llm_advisory_dry_run", fake_validate)
    exit_code = cli.main(
        [
            "validate-local-llm-advisory-dry-run",
            "--item-id",
            "m99",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--output",
            "artifacts/local_llm_advisory/dry_runs/m99.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dry_run"] is True
    assert parsed["selected_lane"] == "local_llm_advisory"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m99",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "output": "artifacts/local_llm_advisory/dry_runs/m99.json",
        "force": True,
        "output_format": "json",
    }


def test_validate_local_llm_advisory_dry_run_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Local LLM Advisory Dry-Run Validator\n\n- ready_for_future_advisory_run: True\n- selected_lane: local_llm_advisory\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "validate_local_llm_advisory_dry_run",
        lambda _config, item_id, queue_path=None, registry_path=None, output=None, force=False, output_format="markdown": payload,
    )

    exit_code = cli.main(["validate-local-llm-advisory-dry-run", "--item-id", "m99"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ready_for_future_advisory_run: True" in output
    assert "selected_lane: local_llm_advisory" in output


def test_generate_local_llm_advisory_artifact_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "stdout": json.dumps(
            {
                "artifact_type": "local_llm_advisory_request",
                "generated": True,
                "blocked": False,
                "item_id": "m110",
                "selected_lane": "local_llm_advisory",
                "requested_model_profile": "reasoning-fast",
                "reasoning_scope": "safety_review",
                "local_only": True,
                "execution_allowed": False,
                "local_llm_execution_performed": False,
                "codex_execution_performed": False,
                "network_execution_performed": False,
                "patch_application_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_generate(
        _config,
        item_id,
        queue_path=None,
        registry_path=None,
        output=None,
        force=False,
        output_format="markdown",
        model_profile=None,
        reasoning_scope=None,
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["registry_path"] = registry_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        seen["model_profile"] = model_profile
        seen["reasoning_scope"] = reasoning_scope
        return payload

    monkeypatch.setattr(cli, "generate_local_llm_advisory_artifact", fake_generate)
    exit_code = cli.main(
        [
            "generate-local-llm-advisory-artifact",
            "--item-id",
            "m110",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--output",
            "artifacts/local_llm_advisory/requests/m110.json",
            "--force",
            "--model-profile",
            "reasoning-fast",
            "--reasoning-scope",
            "safety_review",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["artifact_type"] == "local_llm_advisory_request"
    assert parsed["selected_lane"] == "local_llm_advisory"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m110",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "output": "artifacts/local_llm_advisory/requests/m110.json",
        "force": True,
        "output_format": "json",
        "model_profile": "reasoning-fast",
        "reasoning_scope": "safety_review",
    }


def test_generate_local_llm_advisory_artifact_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": True,
        "stdout": "# Local LLM Advisory Request Artifact\n\n- generated: True\n- selected_lane: local_llm_advisory\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "generate_local_llm_advisory_artifact",
        lambda _config,
        item_id,
        queue_path=None,
        registry_path=None,
        output=None,
        force=False,
        output_format="markdown",
        model_profile=None,
        reasoning_scope=None: payload,
    )

    exit_code = cli.main(["generate-local-llm-advisory-artifact", "--item-id", "m110"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "generated: True" in output
    assert "selected_lane: local_llm_advisory" in output


def test_generate_doc_agent_patch_proposal_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "artifact_type": "documentation_agent_patch_proposal",
                "generated": True,
                "blocked": False,
                "item_id": "m116",
                "source_documents_reviewed": [],
                "detected_doc_gaps": [],
                "proposed_doc_changes": [],
                "proposed_patch_path": "artifacts/documentation_agent/patch_proposals/m116.patch",
                "approval_required": True,
                "patch_application_allowed": False,
                "patch_application_performed": False,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_generate(
        _config,
        item_id,
        queue_path=None,
        output=None,
        force=False,
        include_roadmap=False,
        include_context=False,
        include_operator_docs=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["include_roadmap"] = include_roadmap
        seen["include_context"] = include_context
        seen["include_operator_docs"] = include_operator_docs
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "generate_documentation_agent_patch_proposal", fake_generate)
    exit_code = cli.main(
        [
            "generate-doc-agent-patch-proposal",
            "--item-id",
            "m116",
            "--queue-path",
            "queue.json",
            "--output",
            "artifacts/documentation_agent/patch_proposals/m116.json",
            "--force",
            "--include-roadmap",
            "--include-context",
            "--include-operator-docs",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["artifact_type"] == "documentation_agent_patch_proposal"
    assert parsed["approval_required"] is True
    assert parsed["patch_application_allowed"] is False
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m116",
        "queue_path": "queue.json",
        "output": "artifacts/documentation_agent/patch_proposals/m116.json",
        "force": True,
        "include_roadmap": True,
        "include_context": True,
        "include_operator_docs": True,
        "output_format": "json",
    }


def test_recommend_agent_route_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "recommendation_type": "agent_route_recommendation",
                "item_id": "m117",
                "recommended_lane": "codex_prompt_artifact",
                "alternative_lanes": [],
                "routing_reasons": ["dashboard"],
                "required_artifacts_before_dispatch": [],
                "approval_requirements": [],
                "local_llm_suitable": False,
                "codex_suitable": True,
                "documentation_agent_suitable": False,
                "human_operator_required": True,
                "dispatch_performed": False,
                "execution_allowed": False,
                "local_only": True,
                "next_safe_action": "Review only.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_recommend(
        _config,
        *,
        item_id,
        queue_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "recommend_agent_route", fake_recommend)
    exit_code = cli.main(
        [
            "recommend-agent-route",
            "--item-id",
            "m117",
            "--queue-path",
            "queue.json",
            "--output",
            "artifacts/agent_routes/m117.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["recommendation_type"] == "agent_route_recommendation"
    assert parsed["dispatch_performed"] is False
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m117",
        "queue_path": "queue.json",
        "output": "artifacts/agent_routes/m117.json",
        "force": True,
        "output_format": "json",
    }


def test_intake_patch_proposal_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "intake_record_type": "patch_proposal_intake",
                "accepted_for_review": True,
                "blocked": False,
                "item_id": "m111",
                "patch_artifact_path": "artifacts/manual/test.patch",
                "approval_gate_id": "approval-1",
                "approval_status": "approved_for_manual_handoff",
                "operator_review_required": True,
                "patch_application_allowed": False,
                "patch_application_performed": False,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_intake(
        _config,
        item_id,
        patch_artifact,
        approval_id=None,
        queue_path=None,
        approval_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["patch_artifact"] = patch_artifact
        seen["approval_id"] = approval_id
        seen["queue_path"] = queue_path
        seen["approval_path"] = approval_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "intake_patch_proposal", fake_intake)
    exit_code = cli.main(
        [
            "intake-patch-proposal",
            "--item-id",
            "m111",
            "--patch-artifact",
            "artifacts/manual/test.patch",
            "--approval-id",
            "approval-1",
            "--queue-path",
            "queue.json",
            "--approval-path",
            "approvals.json",
            "--output",
            "artifacts/patch_intake/m111.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["intake_record_type"] == "patch_proposal_intake"
    assert parsed["patch_application_allowed"] is False
    assert seen == {
        "item_id": "m111",
        "patch_artifact": "artifacts/manual/test.patch",
        "approval_id": "approval-1",
        "queue_path": "queue.json",
        "approval_path": "approvals.json",
        "output": "artifacts/patch_intake/m111.json",
        "force": True,
        "output_format": "json",
    }


def test_intake_patch_proposal_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Patch Proposal Intake\n\n- accepted_for_review: True\n- patch_application_allowed: False\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "intake_patch_proposal",
        lambda _config,
        item_id,
        patch_artifact,
        approval_id=None,
        queue_path=None,
        approval_path=None,
        output=None,
        force=False,
        output_format="markdown": payload,
    )

    exit_code = cli.main(
        ["intake-patch-proposal", "--item-id", "m111", "--patch-artifact", "artifacts/manual/test.patch"]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "accepted_for_review: True" in output
    assert "patch_application_allowed: False" in output


def test_parse_dispatch_result_evidence_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "evidence_record_type": "dispatch_result_evidence",
                "parsed": True,
                "blocked": False,
                "item_id": "m112",
                "result_path": "artifacts/manual/sample-codex-result.md",
                "result_exists": True,
                "files_changed": ["src/aresforge/cli.py"],
                "tests_reported": ["python -m pytest tests/test_cli.py -> passed"],
                "smoke_checks_reported": ["smoke -> passed"],
                "commit_hash": "abc1234",
                "validation_confidence": "high",
                "completion_recommendation": "ready_for_human_completion_review",
                "human_review_required": True,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_parse(
        _config,
        item_id,
        result_path,
        queue_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["result_path"] = result_path
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "parse_dispatch_result_evidence", fake_parse)
    exit_code = cli.main(
        [
            "parse-dispatch-result-evidence",
            "--item-id",
            "m112",
            "--result-path",
            "artifacts/manual/sample-codex-result.md",
            "--queue-path",
            "queue.json",
            "--output",
            "artifacts/dispatch_result_evidence/m112.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["evidence_record_type"] == "dispatch_result_evidence"
    assert parsed["human_review_required"] is True
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m112",
        "result_path": "artifacts/manual/sample-codex-result.md",
        "queue_path": "queue.json",
        "output": "artifacts/dispatch_result_evidence/m112.json",
        "force": True,
        "output_format": "json",
    }


def test_parse_dispatch_result_evidence_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Dispatch Result Evidence\n\n- parsed: True\n- validation_confidence: high\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "parse_dispatch_result_evidence",
        lambda _config,
        item_id,
        result_path,
        queue_path=None,
        output=None,
        force=False,
        output_format="markdown": payload,
    )

    exit_code = cli.main(
        [
            "parse-dispatch-result-evidence",
            "--item-id",
            "m112",
            "--result-path",
            "artifacts/manual/sample-codex-result.md",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "parsed: True" in output
    assert "validation_confidence: high" in output


def test_recommend_queue_completion_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "recommendation_record_type": "queue_completion_recommendation",
                "recommended_complete": True,
                "blocked": False,
                "item_id": "m113",
                "operator_decision_required": True,
                "queue_mutation_performed": False,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_recommend(
        _config,
        *,
        item_id,
        evidence_path,
        queue_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["evidence_path"] = evidence_path
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "recommend_queue_completion", fake_recommend)
    exit_code = cli.main(
        [
            "recommend-queue-completion",
            "--item-id",
            "m113",
            "--evidence-path",
            "artifacts/manual/sample-dispatch-evidence.json",
            "--queue-path",
            "queue.json",
            "--output",
            "artifacts/queue_completion_recommendations/m113.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["recommendation_record_type"] == "queue_completion_recommendation"
    assert parsed["operator_decision_required"] is True
    assert parsed["queue_mutation_performed"] is False
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m113",
        "evidence_path": "artifacts/manual/sample-dispatch-evidence.json",
        "queue_path": "queue.json",
        "output": "artifacts/queue_completion_recommendations/m113.json",
        "force": True,
        "output_format": "json",
    }


def test_recommend_queue_completion_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Queue Completion Recommendation\n\n- recommended_complete: True\n- confidence: high\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "recommend_queue_completion",
        lambda _config,
        item_id,
        evidence_path,
        queue_path=None,
        output=None,
        force=False,
        output_format="markdown": payload,
    )

    exit_code = cli.main(
        [
            "recommend-queue-completion",
            "--item-id",
            "m113",
            "--evidence-path",
            "artifacts/manual/sample-dispatch-evidence.json",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "recommended_complete: True" in output
    assert "confidence: high" in output


def test_validate_documentation_agent_dry_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "dry_run": True,
                "ready_for_future_documentation_review": True,
                "blocked": False,
                "item_id": "m100",
                "selected_lane": "documentation_agent_dry_run",
                "documentation_review_intent": "Prepare a future non-mutating documentation review plan.",
                "source_docs_to_review": ["docs/context/BUILD_STATE.md"],
                "local_only": True,
                "execution_allowed": False,
                "next_safe_action": "Review the documentation dry-run output.",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_validate(
        _config,
        item_id,
        queue_path=None,
        registry_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen["item_id"] = item_id
        seen["queue_path"] = queue_path
        seen["registry_path"] = registry_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "validate_documentation_agent_dry_run", fake_validate)
    exit_code = cli.main(
        [
            "validate-documentation-agent-dry-run",
            "--item-id",
            "m100",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--output",
            "artifacts/documentation_agent/dry_runs/m100.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dry_run"] is True
    assert parsed["selected_lane"] == "documentation_agent_dry_run"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m100",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "output": "artifacts/documentation_agent/dry_runs/m100.json",
        "force": True,
        "output_format": "json",
    }


def test_validate_documentation_agent_dry_run_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Documentation Agent Dry-Run Validator\n\n- ready_for_future_documentation_review: True\n- selected_lane: documentation_agent_dry_run\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "validate_documentation_agent_dry_run",
        lambda _config, item_id, queue_path=None, registry_path=None, output=None, force=False, output_format="markdown": payload,
    )

    exit_code = cli.main(["validate-documentation-agent-dry-run", "--item-id", "m100"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "ready_for_future_documentation_review: True" in output
    assert "selected_lane: documentation_agent_dry_run" in output


def test_create_dispatch_approval_gate_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "execution_allowed": False,
                "approval_gate": {"approval_id": "approval-1", "status": "pending_review"},
            }
        ),
        "payload": {},
    }

    def fake_create(
        _config: AppConfig,
        *,
        item_id: str,
        artifact_type: str,
        artifact_path=None,
        dispatch_lane=None,
        reviewer=None,
        review_notes=None,
        checklist=None,
        approval_path=None,
        queue_path=None,
        registry_path=None,
        output_format="markdown",
    ):
        seen.update(
            {
                "item_id": item_id,
                "artifact_type": artifact_type,
                "artifact_path": artifact_path,
                "dispatch_lane": dispatch_lane,
                "reviewer": reviewer,
                "review_notes": review_notes,
                "checklist": checklist,
                "approval_path": approval_path,
                "queue_path": queue_path,
                "registry_path": registry_path,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "create_dispatch_approval_gate", fake_create)
    exit_code = cli.main(
        [
            "create-dispatch-approval-gate",
            "--item-id",
            "m101",
            "--artifact-type",
            "codex_prompt_artifact",
            "--artifact-path",
            "artifact.txt",
            "--dispatch-lane",
            "codex_prompt_artifact",
            "--reviewer",
            "operator",
            "--review-notes",
            "Looks safe.",
            "--checklist",
            "reviewed",
            "--approval-path",
            ".aresforge/gates.json",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_allowed"] is False
    assert parsed["approval_gate"]["status"] == "pending_review"
    assert seen["item_id"] == "m101"
    assert seen["artifact_type"] == "codex_prompt_artifact"
    assert seen["checklist"] == ["reviewed"]
    assert seen["output_format"] == "json"


def test_inspect_dispatch_approval_gate_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Dispatch Approval Gate\n\n- approval_id: approval-1\n- status: pending_review\n- execution_allowed: False\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "inspect_dispatch_approval_gate",
        lambda _config, approval_id=None, item_id=None, approval_path=None, limit=None, output_format="markdown": payload,
    )

    exit_code = cli.main(["inspect-dispatch-approval-gate", "--approval-id", "approval-1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "approval_id: approval-1" in output
    assert "execution_allowed: False" in output


def test_update_dispatch_approval_gate_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ok": True,
                "execution_allowed": False,
                "approval_gate": {"approval_id": "approval-1", "status": "approved_for_manual_handoff"},
            }
        ),
        "payload": {},
    }

    def fake_update(
        _config: AppConfig,
        *,
        approval_id: str,
        status: str,
        reviewer=None,
        review_notes=None,
        checklist=None,
        approval_path=None,
        output_format="markdown",
    ):
        seen.update(
            {
                "approval_id": approval_id,
                "status": status,
                "reviewer": reviewer,
                "review_notes": review_notes,
                "checklist": checklist,
                "approval_path": approval_path,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "update_dispatch_approval_gate", fake_update)
    exit_code = cli.main(
        [
            "update-dispatch-approval-gate",
            "--approval-id",
            "approval-1",
            "--status",
            "approved_for_manual_handoff",
            "--reviewer",
            "operator",
            "--review-notes",
            "Approved for manual handoff only.",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_allowed"] is False
    assert parsed["approval_gate"]["status"] == "approved_for_manual_handoff"
    assert seen["approval_id"] == "approval-1"
    assert seen["status"] == "approved_for_manual_handoff"
    assert seen["output_format"] == "json"


def test_inspect_dispatch_artifacts_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Dispatch Artifact Index\n\n- artifact_count: 1\n- execution_allowed: False\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "inspect_dispatch_artifacts",
        lambda _config, project_id="aresforge", artifact_root=None, approval_path=None, output_format="markdown": payload,
    )

    exit_code = cli.main(["inspect-dispatch-artifacts"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Dispatch Artifact Index" in output
    assert "execution_allowed: False" in output


def test_inspect_dispatch_artifacts_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "report_type": "dispatch_artifact_index",
                "project_id": "aresforge",
                "artifact_count": 1,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }

    def fake_inspect(
        _config: AppConfig,
        *,
        project_id: str = "aresforge",
        artifact_root=None,
        approval_path=None,
        output_format: str = "markdown",
    ):
        seen.update(
            {
                "project_id": project_id,
                "artifact_root": artifact_root,
                "approval_path": approval_path,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "inspect_dispatch_artifacts", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-dispatch-artifacts",
            "--project-id",
            "aresforge",
            "--artifact-root",
            "artifacts",
            "--approval-path",
            ".aresforge/gates.json",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["report_type"] == "dispatch_artifact_index"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "project_id": "aresforge",
        "artifact_root": "artifacts",
        "approval_path": ".aresforge/gates.json",
        "output_format": "json",
    }


def test_inspect_artifact_registry_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "registry_type": "dispatch_artifact_registry_v2",
                "generated": True,
                "artifact_count": 0,
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }

    def fake_inspect(
        _config: AppConfig,
        *,
        project_id: str = "aresforge",
        item_id=None,
        artifact_type=None,
        output=None,
        force: bool = False,
        output_format: str = "json",
    ):
        seen.update(
            {
                "project_id": project_id,
                "item_id": item_id,
                "artifact_type": artifact_type,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "inspect_artifact_registry", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-artifact-registry",
            "--project-id",
            "aresforge",
            "--item-id",
            "m119",
            "--artifact-type",
            "dispatch_result_evidence",
            "--output",
            "artifacts/registry/m119.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["registry_type"] == "dispatch_artifact_registry_v2"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "project_id": "aresforge",
        "item_id": "m119",
        "artifact_type": "dispatch_result_evidence",
        "output": "artifacts/registry/m119.json",
        "force": True,
        "output_format": "json",
    }


def test_inspect_approval_ledger_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ledger_type": "human_approval_review_ledger",
                "generated": True,
                "project_id": "aresforge",
                "local_only": True,
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }

    def fake_inspect(
        _config: AppConfig,
        *,
        project_id: str,
        item_id=None,
        artifact_path=None,
        output=None,
        force: bool = False,
        output_format: str = "markdown",
    ):
        seen.update(
            {
                "project_id": project_id,
                "item_id": item_id,
                "artifact_path": artifact_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "inspect_approval_ledger", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-approval-ledger",
            "--project-id",
            "aresforge",
            "--item-id",
            "m121",
            "--artifact-path",
            "artifacts/review.json",
            "--output",
            "artifacts/ledger.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["ledger_type"] == "human_approval_review_ledger"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "project_id": "aresforge",
        "item_id": "m121",
        "artifact_path": "artifacts/review.json",
        "output": "artifacts/ledger.json",
        "force": True,
        "output_format": "json",
    }


def test_record_artifact_review_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ledger_type": "human_approval_review_ledger",
                "review_record": {"decision": "approved"},
                "execution_allowed": False,
            }
        ),
        "payload": {},
    }

    def fake_record(
        _config: AppConfig,
        *,
        item_id: str,
        artifact_path: str,
        decision: str,
        reviewer=None,
        review_notes=None,
        output=None,
        force: bool = False,
        output_format: str = "markdown",
    ):
        seen.update(
            {
                "item_id": item_id,
                "artifact_path": artifact_path,
                "decision": decision,
                "reviewer": reviewer,
                "review_notes": review_notes,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "record_artifact_review", fake_record)
    exit_code = cli.main(
        [
            "record-artifact-review",
            "--item-id",
            "m121",
            "--artifact-path",
            "artifacts/review.json",
            "--decision",
            "approved",
            "--reviewer",
            "operator",
            "--review-notes",
            "looks good",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["review_record"]["decision"] == "approved"
    assert parsed["execution_allowed"] is False
    assert seen == {
        "item_id": "m121",
        "artifact_path": "artifacts/review.json",
        "decision": "approved",
        "reviewer": "operator",
        "review_notes": "looks good",
        "output": None,
        "force": False,
        "output_format": "json",
    }


def test_prepare_manual_codex_dispatch_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "markdown",
        "wrote_output_file": False,
        "stdout": "# Manual Codex Dispatch Preparation\n\n- prepared: True\n- codex_execution_performed: False\n",
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "prepare_manual_codex_dispatch",
        lambda _config, item_id, artifact_path=None, approval_id=None, queue_path=None, registry_path=None, artifact_root=None, approval_path=None, output=None, force=False, output_format="markdown": payload,
    )

    exit_code = cli.main(["prepare-manual-codex-dispatch", "--item-id", "m109-target"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Manual Codex Dispatch Preparation" in output
    assert "codex_execution_performed: False" in output


def test_prepare_manual_codex_dispatch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: dict[str, object] = {}
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "prepared": True,
                "item_id": "m109-target",
                "execution_allowed": False,
                "codex_execution_performed": False,
            }
        ),
        "payload": {},
    }

    def fake_prepare(
        _config: AppConfig,
        *,
        item_id: str,
        artifact_path=None,
        approval_id=None,
        queue_path=None,
        registry_path=None,
        artifact_root=None,
        approval_path=None,
        output=None,
        force=False,
        output_format="markdown",
    ):
        seen.update(
            {
                "item_id": item_id,
                "artifact_path": artifact_path,
                "approval_id": approval_id,
                "queue_path": queue_path,
                "registry_path": registry_path,
                "artifact_root": artifact_root,
                "approval_path": approval_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "prepare_manual_codex_dispatch", fake_prepare)
    exit_code = cli.main(
        [
            "prepare-manual-codex-dispatch",
            "--item-id",
            "m109-target",
            "--artifact-path",
            "artifact.txt",
            "--approval-id",
            "approval-1",
            "--queue-path",
            "queue.json",
            "--registry-path",
            "projects.json",
            "--artifact-root",
            "artifacts",
            "--approval-path",
            ".aresforge/gates.json",
            "--output",
            "prepared.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_allowed"] is False
    assert parsed["codex_execution_performed"] is False
    assert seen == {
        "item_id": "m109-target",
        "artifact_path": "artifact.txt",
        "approval_id": "approval-1",
        "queue_path": "queue.json",
        "registry_path": "projects.json",
        "artifact_root": "artifacts",
        "approval_path": ".aresforge/gates.json",
        "output": "prepared.json",
        "force": True,
        "output_format": "json",
    }


def test_approve_codex_dispatch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "run_id": "run-one", "dispatch_state": "approved_pending_dispatch"}),
        "payload": {},
    }
    monkeypatch.setattr(
        cli,
        "approve_codex_dispatch",
        lambda _config, item_id, approved_by, approval_phrase, queue_path=None, registry_path=None, run_id=None, output_format="json": payload,
    )
    exit_code = cli.main(
        [
            "approve-codex-dispatch",
            "--item-id",
            "m78",
            "--approved-by",
            "local_operator",
            "--approval-phrase",
            "APPROVE CODEX DISPATCH",
            "--run-id",
            "run-one",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dispatch_state"] == "approved_pending_dispatch"


def test_run_codex_dispatch_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "run_id": "run-one", "dispatch_state": "review_required"}),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(_config, item_id, run_id, command, timeout_seconds=300, output_format="json"):
        seen["command"] = command
        seen["timeout_seconds"] = timeout_seconds
        return payload

    monkeypatch.setattr(cli, "run_operator_gated_codex_dispatch", fake_run)
    exit_code = cli.main(
        [
            "run-codex-dispatch",
            "--item-id",
            "m78",
            "--run-id",
            "run-one",
            "--command",
            "python -c \"print('smoke')\"",
            "--command-arg",
            "python",
            "--command-arg=-c",
            "--command-arg",
            "print('smoke')",
            "--timeout-seconds",
            "12",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["dispatch_state"] == "review_required"
    assert seen["command"] == ["python", "-c", "print('smoke')"]
    assert seen["timeout_seconds"] == 12


def test_run_codex_dispatch_executor_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "stdout": json.dumps(
            {
                "execution_record_type": "codex_dispatch_execution_v1",
                "item_id": "m135",
                "dry_run": True,
                "blocked": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        item_id,
        artifact_path,
        dry_run=False,
        force=False,
        output=None,
        timeout_seconds=300,
        require_clean_worktree=False,
        execution_enabled=False,
        queue_path=None,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["artifact_path"] = artifact_path
        seen["dry_run"] = dry_run
        seen["execution_enabled"] = execution_enabled
        seen["require_clean_worktree"] = require_clean_worktree
        seen["timeout_seconds"] = timeout_seconds
        seen["output"] = output
        return payload

    monkeypatch.setattr(cli, "run_codex_dispatch_executor", fake_run)
    exit_code = cli.main(
        [
            "run-codex-dispatch",
            "--item-id",
            "m135",
            "--artifact-path",
            "artifacts/manual/sample-codex-dispatch.json",
            "--dry-run",
            "--execution-enabled",
            "--require-clean-worktree",
            "--timeout-seconds",
            "15",
            "--output",
            "artifacts/codex_dispatch/executions/m135.json",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "codex_dispatch_execution_v1"
    assert seen["item_id"] == "m135"
    assert seen["artifact_path"] == "artifacts/manual/sample-codex-dispatch.json"
    assert seen["dry_run"] is True
    assert seen["execution_enabled"] is True
    assert seen["require_clean_worktree"] is True
    assert seen["timeout_seconds"] == 15
    assert seen["output"] == "artifacts/codex_dispatch/executions/m135.json"


def test_ingest_codex_result_and_validate_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "ingestion_record_type": "codex_result_ingestion_validation",
                "item_id": "m136",
                "execution_record_path": "artifacts/manual/sample-codex-execution-record.json",
                "dry_run": True,
                "validation_profile": "queue_system",
                "blocked": False,
                "queue_mutation_performed": False,
                "github_execution_performed": False,
                "local_only": True,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_ingest(
        _config,
        item_id,
        execution_record,
        validation_profile="code_unit_tests",
        dry_run=False,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["execution_record"] = execution_record
        seen["validation_profile"] = validation_profile
        seen["dry_run"] = dry_run
        seen["queue_path"] = queue_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "ingest_codex_result_and_validate", fake_ingest)
    exit_code = cli.main(
        [
            "ingest-codex-result-and-validate",
            "--item-id",
            "m136",
            "--execution-record",
            "artifacts/manual/sample-codex-execution-record.json",
            "--validation-profile",
            "queue_system",
            "--dry-run",
            "--queue-path",
            "queue.json",
            "--output",
            "artifacts/codex_result_ingestion/m136.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["ingestion_record_type"] == "codex_result_ingestion_validation"
    assert parsed["queue_mutation_performed"] is False
    assert parsed["github_execution_performed"] is False
    assert seen == {
        "item_id": "m136",
        "execution_record": "artifacts/manual/sample-codex-execution-record.json",
        "validation_profile": "queue_system",
        "dry_run": True,
        "queue_path": "queue.json",
        "output": "artifacts/codex_result_ingestion/m136.json",
        "force": True,
        "output_format": "json",
    }


def test_run_github_sync_agent_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "execution_record_type": "github_sync_agent_v1",
                "item_id": "m137",
                "dry_run": True,
                "github_enabled": False,
                "sync_mode": "issue-comment",
                "repo": "yoey2112/aresforge",
                "issue_number": 1,
                "blocked": False,
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        item_id,
        sync_mode="issue-comment",
        dry_run=False,
        github_enabled=False,
        repo=None,
        issue_number=None,
        pr_number=None,
        artifact_path=None,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen["item_id"] = item_id
        seen["sync_mode"] = sync_mode
        seen["dry_run"] = dry_run
        seen["github_enabled"] = github_enabled
        seen["repo"] = repo
        seen["issue_number"] = issue_number
        seen["artifact_path"] = artifact_path
        seen["output"] = output
        seen["force"] = force
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "run_github_sync_agent", fake_run)
    exit_code = cli.main(
        [
            "run-github-sync-agent",
            "--item-id",
            "m137",
            "--dry-run",
            "--sync-mode",
            "issue-comment",
            "--repo",
            "yoey2112/aresforge",
            "--issue-number",
            "1",
            "--artifact-path",
            "artifacts/manual/github-sync-comment.json",
            "--output",
            "artifacts/github_sync_agent/m137.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "github_sync_agent_v1"
    assert seen == {
        "item_id": "m137",
        "sync_mode": "issue-comment",
        "dry_run": True,
        "github_enabled": False,
        "repo": "yoey2112/aresforge",
        "issue_number": 1,
        "artifact_path": "artifacts/manual/github-sync-comment.json",
        "output": "artifacts/github_sync_agent/m137.json",
        "force": True,
        "output_format": "json",
    }


def test_run_agent_orchestration_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "stdout": json.dumps({"execution_record_type": "multi_agent_orchestration_v1", "item_id": "m138"}),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_run(
        _config,
        *,
        item_id,
        plan_path=None,
        dry_run=False,
        max_steps=None,
        allow_low_risk_real=False,
        allow_local_llm=False,
        allow_codex=False,
        allow_github_sync=False,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen.update(
            {
                "item_id": item_id,
                "plan_path": plan_path,
                "dry_run": dry_run,
                "max_steps": max_steps,
                "allow_low_risk_real": allow_low_risk_real,
                "allow_local_llm": allow_local_llm,
                "allow_codex": allow_codex,
                "allow_github_sync": allow_github_sync,
                "queue_path": queue_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "run_multi_agent_orchestration", fake_run)
    exit_code = cli.main(
        [
            "run-agent-orchestration",
            "--item-id",
            "m138",
            "--plan-path",
            "artifacts/orchestration/plan.json",
            "--dry-run",
            "--max-steps",
            "2",
            "--allow-low-risk-real",
            "--allow-local-llm",
            "--allow-codex",
            "--allow-github-sync",
            "--queue-path",
            ".aresforge/queue/work_items.json",
            "--output",
            "artifacts/multi-agent-orchestration/m138.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["execution_record_type"] == "multi_agent_orchestration_v1"
    assert seen == {
        "item_id": "m138",
        "plan_path": "artifacts/orchestration/plan.json",
        "dry_run": True,
        "max_steps": 2,
        "allow_low_risk_real": True,
        "allow_local_llm": True,
        "allow_codex": True,
        "allow_github_sync": True,
        "queue_path": ".aresforge/queue/work_items.json",
        "output": "artifacts/multi-agent-orchestration/m138.json",
        "force": True,
        "output_format": "json",
    }


def test_generate_autonomous_sprint_closeout_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": True,
        "stdout": json.dumps({"closeout_type": "autonomous_sprint_closeout_v1", "project_id": "aresforge"}),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_generate(
        _config,
        *,
        project_id,
        sprint_start="M125",
        sprint_end="M139",
        dry_run=False,
        apply_docs_only=False,
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen.update(
            {
                "project_id": project_id,
                "sprint_start": sprint_start,
                "sprint_end": sprint_end,
                "dry_run": dry_run,
                "apply_docs_only": apply_docs_only,
                "queue_path": queue_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "generate_autonomous_sprint_closeout", fake_generate)
    exit_code = cli.main(
        [
            "generate-autonomous-sprint-closeout",
            "--project-id",
            "aresforge",
            "--sprint-start",
            "M125",
            "--sprint-end",
            "M139",
            "--dry-run",
            "--apply-docs-only",
            "--queue-path",
            ".aresforge/queue/work_items.json",
            "--output",
            "artifacts/autonomous-sprint-closeout/m139.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["closeout_type"] == "autonomous_sprint_closeout_v1"
    assert seen == {
        "project_id": "aresforge",
        "sprint_start": "M125",
        "sprint_end": "M139",
        "dry_run": True,
        "apply_docs_only": True,
        "queue_path": ".aresforge/queue/work_items.json",
        "output": "artifacts/autonomous-sprint-closeout/m139.json",
        "force": True,
        "output_format": "json",
    }


def test_inspect_orchestrator_state_machine_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps(
            {
                "record_type": "orchestrator_execution_state_machine_v1",
                "item_id": "m140",
                "project_id": "aresforge",
            }
        ),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_inspect(
        _config,
        *,
        item_id="m140-orchestrator-execution-state-machine-v1",
        project_id="aresforge",
        queue_path=None,
        output=None,
        force=False,
        output_format="json",
    ):
        seen.update(
            {
                "item_id": item_id,
                "project_id": project_id,
                "queue_path": queue_path,
                "output": output,
                "force": force,
                "output_format": output_format,
            }
        )
        return payload

    monkeypatch.setattr(cli, "inspect_orchestrator_state_machine", fake_inspect)
    exit_code = cli.main(
        [
            "inspect-orchestrator-state-machine",
            "--item-id",
            "m140",
            "--project-id",
            "aresforge",
            "--queue-path",
            ".aresforge/queue/work_items.json",
            "--output",
            ".aresforge/orchestrator/state-machine.json",
            "--force",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["record_type"] == "orchestrator_execution_state_machine_v1"
    assert seen == {
        "item_id": "m140",
        "project_id": "aresforge",
        "queue_path": ".aresforge/queue/work_items.json",
        "output": ".aresforge/orchestrator/state-machine.json",
        "force": True,
        "output_format": "json",
    }


def test_inspect_and_list_codex_dispatch_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inspect_payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "run_id": "run-one"}),
        "payload": {},
    }
    list_payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "run_count": 1}),
        "payload": {},
    }
    monkeypatch.setattr(cli, "inspect_codex_dispatch_run", lambda _config, run_id, output_format="json": inspect_payload)
    monkeypatch.setattr(cli, "list_codex_dispatch_runs", lambda _config, output_format="json": list_payload)

    inspect_exit = cli.main(["inspect-codex-dispatch-run", "--run-id", "run-one", "--format", "json"])
    inspected = json.loads(capsys.readouterr().out)
    list_exit = cli.main(["list-codex-dispatch-runs", "--format", "json"])
    listed = json.loads(capsys.readouterr().out)

    assert inspect_exit == 0
    assert inspected["run_id"] == "run-one"
    assert list_exit == 0
    assert listed["run_count"] == 1


def test_recover_codex_dispatch_run_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "format": "json",
        "wrote_output_file": False,
        "stdout": json.dumps({"ok": True, "run_id": "run-one", "recovery_required": True}),
        "payload": {},
    }
    seen: dict[str, object] = {}

    def fake_recover(_config, run_id, recovery_note="", output_format="json"):
        seen["run_id"] = run_id
        seen["recovery_note"] = recovery_note
        seen["output_format"] = output_format
        return payload

    monkeypatch.setattr(cli, "recover_codex_dispatch_run", fake_recover)
    exit_code = cli.main(
        [
            "recover-codex-dispatch-run",
            "--run-id",
            "run-one",
            "--recovery-note",
            "manual recovery after interruption",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert parsed["recovery_required"] is True
    assert seen["run_id"] == "run-one"
    assert seen["recovery_note"] == "manual recovery after interruption"
    assert seen["output_format"] == "json"


def test_complete_local_queue_item_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {
        "ok": True,
        "local_only": True,
        "item_id": "work-1",
        "previous_status": "in_progress",
        "status": "done",
        "completion_commit": "abc123def",
        "validation_summary": "Targeted tests passed locally.",
        "next_safe_action": "Inspect queue summary.",
        "warnings": [],
    }
    monkeypatch.setattr(
        cli,
        "complete_local_queue_item",
        lambda _config, item_id, commit_hash, validation_summary, evidence_note=None, tests_run=None, changed_files=None, artifact_paths=None, completed_by='local_operator', queue_path=None: payload,
    )
    exit_code = cli.main(
        [
            "complete-local-queue-item",
            "--item-id",
            "work-1",
            "--commit-hash",
            "abc123def",
            "--validation-summary",
            "Targeted tests passed locally.",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_archive_work_item_operator_packet_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    packet_payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "packet_dir": "artifacts/local-smoke/operator-packets/work-1/abc123",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "archive_work_item_operator_packet",
        lambda _conn, _work_item_id, _output_dir, actor, force: packet_payload,
    )
    exit_code = cli.main(
        [
            "archive-work-item-operator-packet",
            "--work-item-id",
            "work-1",
            "--output-dir",
            "artifacts/local-smoke/operator-packets",
            "--actor",
            "local-test",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == packet_payload


def test_archive_work_item_operator_packet_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    packet_payload = {
        "ok": False,
        "changed": False,
        "work_item_id": "work-missing",
        "reason": "work_item_not_found",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "archive_work_item_operator_packet",
        lambda _conn, _work_item_id, _output_dir, actor, force: packet_payload,
    )
    monkeypatch.setattr(
        cli,
        "render_archive_work_item_operator_packet_markdown",
        lambda _payload: "# Archive Work Item Operator Packet\n",
    )
    exit_code = cli.main(
        [
            "archive-work-item-operator-packet",
            "--work-item-id",
            "work-missing",
            "--output-dir",
            "artifacts/local-smoke/operator-packets",
            "--actor",
            "local-test",
            "--force",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Archive Work Item Operator Packet\n\n"


def test_recommend_next_work_item_action_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    recommendation_payload = {
        "ok": True,
        "read_only": True,
        "work_item_id": "work-1",
        "primary_recommendation": "inspect-work-item-readiness --work-item-id work-1 --format markdown",
        "recommended_commands": [],
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "recommend_next_work_item_action",
        lambda _conn, _work_item_id: recommendation_payload,
    )
    exit_code = cli.main(
        [
            "recommend-next-work-item-action",
            "--work-item-id",
            "work-1",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == recommendation_payload


def test_recommend_next_work_item_action_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    recommendation_payload = {
        "ok": False,
        "read_only": True,
        "work_item_id": "work-missing",
    }
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "recommend_next_work_item_action",
        lambda _conn, _work_item_id: recommendation_payload,
    )
    monkeypatch.setattr(
        cli,
        "render_next_work_item_action_recommendation_markdown",
        lambda _payload: "# Next Work Item Action Recommendation\n",
    )
    exit_code = cli.main(
        [
            "recommend-next-work-item-action",
            "--work-item-id",
            "work-missing",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 1
    assert output == "# Next Work Item Action Recommendation\n\n"


def test_add_roadmap_task_dependency_dispatch_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "changed": True, "task_id": "rt-04-starter", "depends_on_task_id": "rt-03-starter"}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "add_roadmap_task_dependency",
        lambda _conn, task_id, depends_on_task_id, dependency_type, actor, details: payload,
    )
    exit_code = cli.main(
        [
            "add-roadmap-task-dependency",
            "--task-id",
            "rt-04-starter",
            "--depends-on-task-id",
            "rt-03-starter",
            "--format",
            "json",
        ]
    )
    parsed = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert parsed == payload


def test_remove_roadmap_task_dependency_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "changed": False, "reason": "dependency_not_found"}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "remove_roadmap_task_dependency",
        lambda _conn, task_id, depends_on_task_id, actor, details: payload,
    )
    monkeypatch.setattr(
        cli,
        "render_remove_roadmap_task_dependency_markdown",
        lambda _payload: "# Remove Roadmap Task Dependency\n",
    )
    exit_code = cli.main(
        [
            "remove-roadmap-task-dependency",
            "--task-id",
            "rt-04-starter",
            "--depends-on-task-id",
            "rt-03-starter",
            "--format",
            "markdown",
        ]
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Remove Roadmap Task Dependency\n\n"


def test_inspect_roadmap_task_dependencies_dispatch_markdown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payload = {"ok": True, "dependency_count": 0, "dependencies": []}
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(
        cli,
        "inspect_roadmap_task_dependencies",
        lambda _conn, task_id=None, project_id="project-aresforge": payload,
    )
    monkeypatch.setattr(
        cli,
        "render_roadmap_task_dependencies_markdown",
        lambda _payload: "# Roadmap Task Dependencies\n",
    )
    exit_code = cli.main(["inspect-roadmap-task-dependencies", "--format", "markdown"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert output == "# Roadmap Task Dependencies\n\n"
