import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from aresforge.artifacts.store import ArtifactBundle
from aresforge import cli
from aresforge.cli import build_parser, parse_metadata, parse_metadata_pairs
from aresforge.validation import ValidationFinding, ValidationReport


def test_cli_has_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for command in (
        "validate-config",
        "validate-registries",
        "migrate",
        "inspect-project-state",
        "inspect-project",
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


def test_cli_inspection_commands_require_expected_ids() -> None:
    parser = build_parser()

    inspect_project_args = parser.parse_args(["inspect-project", "--project-id", "project-aresforge"])
    assert inspect_project_args.project_id == "project-aresforge"

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
