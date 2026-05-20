import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import local_review
from aresforge.operator.local_review import LocalReviewOptions
from aresforge.validation import ValidationReport


def make_config(tmp_path: Path) -> AppConfig:
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


@contextmanager
def fake_connect(_config: object):
    yield object()


def test_run_local_review_happy_path_is_deterministic_and_json_serializable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(local_review, "connect", fake_connect)
    monkeypatch.setattr(
        local_review,
        "validate_registry_seed_data",
        lambda: ValidationReport(ok=True, findings=()),
    )
    monkeypatch.setattr(local_review, "list_projects", lambda _conn: [{"id": "project-aresforge"}])
    monkeypatch.setattr(local_review, "list_agents", lambda _conn: [{"id": "agent-local-operator"}])
    monkeypatch.setattr(local_review, "list_models", lambda _conn: [{"id": "model-ollama-default"}])
    monkeypatch.setattr(local_review, "list_queues", lambda _conn: [{"id": "queue-implementation"}])
    monkeypatch.setattr(
        local_review,
        "inspect_project",
        lambda _conn, _project_id: {"id": "project-aresforge"},
    )
    monkeypatch.setattr(
        local_review,
        "inspect_model",
        lambda _conn, _model_id: {"id": "model-ollama-default"},
    )
    monkeypatch.setattr(
        local_review,
        "inspect_local_registries",
        lambda _repo_root: {
            "ok": True,
            "inspection_mode": "local_repo_only",
            "summary": {"registry_count": 5, "ok": 5, "problem_registry_count": 0},
            "registries": [],
        },
    )
    monkeypatch.setattr(
        local_review,
        "discover_local_artifacts",
        lambda _config: {
            "ok": True,
            "inspection_mode": "local_artifact_root_only",
            "artifact_root": str(config.artifact_root),
            "artifact_root_exists": True,
            "artifact_count": 1,
            "artifacts": [{"artifact_path": "prompts/generated/example.md"}],
        },
    )
    monkeypatch.setattr(
        local_review,
        "inspect_local_artifact",
        lambda _config, _artifact_path: {
            "ok": True,
            "artifact": {"artifact_path": "prompts/generated/example.md"},
        },
    )
    monkeypatch.setattr(
        local_review,
        "discover_local_evidence_packages",
        lambda _config: {
            "ok": True,
            "inspection_mode": "local_evidence_root_only",
            "evidence_root": str(config.evidence_dir),
            "evidence_root_exists": True,
            "evidence_package_count": 1,
            "evidence_packages": [{"evidence_path": "issue-109.json"}],
        },
    )
    monkeypatch.setattr(
        local_review,
        "inspect_local_evidence_package",
        lambda _config, _evidence_path: {
            "ok": True,
            "evidence_package": {"evidence_path": "issue-109.json"},
        },
    )

    payload = local_review.run_local_review(
        config,
        options=LocalReviewOptions(
            project_id="project-aresforge",
            model_id="model-ollama-default",
            include_artifacts=True,
            artifact_path="prompts/generated/example.md",
            include_evidence_packages=True,
            evidence_path="issue-109.json",
        ),
    )

    assert payload["ok"] is True
    assert [check["name"] for check in payload["checks_run"]] == [
        "validate-config",
        "validate-registries",
        "list-projects",
        "list-agents",
        "list-models",
        "list-queues",
        "inspect-project",
        "inspect-model",
        "inspect-registries",
        "list-artifacts",
        "inspect-artifact",
        "list-evidence-packages",
        "inspect-evidence-package",
    ]
    assert payload["checks_skipped"] == []
    assert payload["artifact_summary"] == {
        "list_artifacts": {
            "ok": True,
            "inspection_mode": "local_artifact_root_only",
            "artifact_root": str(config.artifact_root),
            "artifact_root_exists": True,
            "artifact_count": 1,
            "artifacts": [{"artifact_path": "prompts/generated/example.md"}],
        },
        "inspect_artifact": {
            "ok": True,
            "artifact": {"artifact_path": "prompts/generated/example.md"},
        },
    }
    assert payload["evidence_package_summary"] == {
        "list_evidence_packages": {
            "ok": True,
            "inspection_mode": "local_evidence_root_only",
            "evidence_root": str(config.evidence_dir),
            "evidence_root_exists": True,
            "evidence_package_count": 1,
            "evidence_packages": [{"evidence_path": "issue-109.json"}],
        },
        "inspect_evidence_package": {
            "ok": True,
            "evidence_package": {"evidence_path": "issue-109.json"},
        },
    }
    assert payload["output_package_path"] is None
    assert json.loads(json.dumps(payload)) == payload


def test_run_local_review_reports_skips_for_unrequested_and_unavailable_optional_checks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(local_review, "connect", fake_connect)
    monkeypatch.setattr(
        local_review,
        "validate_registry_seed_data",
        lambda: ValidationReport(ok=True, findings=()),
    )
    monkeypatch.setattr(local_review, "list_projects", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_agents", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_models", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_queues", lambda _conn: [])
    monkeypatch.setattr(local_review, "inspect_project", lambda _conn, _project_id: {"id": _project_id})
    monkeypatch.setattr(local_review, "inspect_model", lambda _conn, _model_id: {"id": _model_id})
    monkeypatch.setattr(
        local_review,
        "inspect_local_registries",
        lambda _repo_root: {"ok": True, "summary": {}, "registries": []},
    )
    monkeypatch.setattr(
        local_review,
        "discover_local_evidence_packages",
        lambda _config: (_ for _ in ()).throw(NotImplementedError("capability_unavailable")),
    )

    payload = local_review.run_local_review(
        config,
        options=LocalReviewOptions(include_evidence_packages=True, project_id="project-aresforge", model_id="model-ollama-default"),
    )

    assert payload["ok"] is True
    assert payload["checks_skipped"] == [
        {"name": "list-artifacts", "reason": "artifacts_not_requested"},
        {"name": "inspect-artifact", "reason": "artifact_path_not_requested"},
        {"name": "list-evidence-packages", "reason": "capability_unavailable"},
        {"name": "inspect-evidence-package", "reason": "evidence_path_not_requested"},
    ]
    assert payload["skip_reasons"]["list-evidence-packages"] == "capability_unavailable"


def test_run_local_review_reports_failed_check_without_hiding_later_results(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(local_review, "connect", fake_connect)
    monkeypatch.setattr(
        local_review,
        "validate_registry_seed_data",
        lambda: ValidationReport(ok=True, findings=()),
    )
    monkeypatch.setattr(local_review, "list_projects", lambda _conn: [{"id": "project-aresforge"}])
    monkeypatch.setattr(local_review, "list_agents", lambda _conn: [{"id": "agent-local-operator"}])
    monkeypatch.setattr(local_review, "list_models", lambda _conn: [{"id": "model-ollama-default"}])
    monkeypatch.setattr(local_review, "list_queues", lambda _conn: [{"id": "queue-implementation"}])
    monkeypatch.setattr(local_review, "inspect_project", lambda _conn, _project_id: {"id": _project_id})
    monkeypatch.setattr(local_review, "inspect_model", lambda _conn, _model_id: None)
    monkeypatch.setattr(
        local_review,
        "inspect_local_registries",
        lambda _repo_root: {
            "ok": False,
            "error": "registry_problem",
            "summary": {"problem_registry_count": 1},
            "registries": [{"registry": "queue_registry", "status": "missing"}],
        },
    )
    monkeypatch.setattr(
        local_review,
        "discover_local_artifacts",
        lambda _config: {
            "ok": True,
            "artifact_root": str(config.artifact_root),
            "artifact_root_exists": False,
            "artifact_count": 0,
            "artifacts": [],
        },
    )

    payload = local_review.run_local_review(
        config,
        options=LocalReviewOptions(
            project_id="project-aresforge",
            model_id="missing-model-id",
            include_artifacts=True,
        ),
    )

    assert payload["ok"] is False
    assert payload["checks_run"][7]["name"] == "inspect-model"
    assert payload["checks_run"][7]["status"] == "failed"
    assert payload["checks_run"][7]["error"] == "model_not_found"
    assert payload["checks_run"][8]["name"] == "inspect-registries"
    assert payload["checks_run"][8]["status"] == "failed"
    assert payload["checks_run"][9]["name"] == "list-artifacts"
    assert payload["checks_run"][9]["status"] == "passed"


def test_run_local_review_write_review_package_is_opt_in_and_writes_expected_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(local_review, "connect", fake_connect)
    monkeypatch.setattr(
        local_review,
        "validate_registry_seed_data",
        lambda: ValidationReport(ok=True, findings=()),
    )
    monkeypatch.setattr(local_review, "list_projects", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_agents", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_models", lambda _conn: [])
    monkeypatch.setattr(local_review, "list_queues", lambda _conn: [])
    monkeypatch.setattr(local_review, "inspect_project", lambda _conn, _project_id: {"id": _project_id})
    monkeypatch.setattr(local_review, "inspect_model", lambda _conn, _model_id: {"id": _model_id})
    monkeypatch.setattr(
        local_review,
        "inspect_local_registries",
        lambda _repo_root: {"ok": True, "summary": {}, "registries": []},
    )

    payload = local_review.run_local_review(
        config,
        options=LocalReviewOptions(
            project_id="project-aresforge",
            model_id="model-ollama-default",
            write_review_package=True,
        ),
    )

    review_dir = config.artifact_root / "local_reviews" / "generated"
    files = sorted(path.name for path in review_dir.iterdir())

    assert payload["ok"] is True
    assert payload["output_package_path"] is not None
    assert payload["output_package_markdown_path"] is not None
    assert Path(payload["output_package_path"]).exists()
    assert Path(payload["output_package_markdown_path"]).exists()
    assert len(files) == 2
    assert files[0].endswith(".json")
    assert files[1].endswith(".md")
