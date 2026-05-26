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
        "generate-local-milestone-template",
        "inspect-local-milestone",
        "check-local-milestone-readiness",
        "generate-local-milestone-closeout",
        "plan-github-sync",
        "plan-agent-orchestration",
        "init-project-state",
        "update-project-state",
        "append-operation-log",
        "inspect-operation-log",
        "init-managed-project-registry",
        "register-managed-project",
        "register-managed-repo",
        "inspect-managed-project-registry",
        "inspect-managed-project",
        "inspect-managed-repo",
        "inspect-local-project-dashboard",
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
