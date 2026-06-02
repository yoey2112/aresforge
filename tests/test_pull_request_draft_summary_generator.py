import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.pull_request_draft_summary_generator import (
    RECORD_TYPE,
    generate_pr_draft_summary,
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m165-github-issue-closure-recommendation-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M165 GitHub Issue Closure Recommendation Gate",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m166-pull-request-draft-summary-generator",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M166 Pull Request Draft Summary Generator",
        description="Generate draft PR summaries from local evidence.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m166", "pr-draft-summary", "local-only"],
        dependencies=["m165-github-issue-closure-recommendation-gate"],
        notes="Summary artifact generation only; no PR creation.",
    )["ok"] is True
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m166-pull-request-draft-summary-generator":
            item["github_issue"] = {
                "number": 166,
                "url": "https://github.com/local/aresforge/issues/166",
                "state": "open",
            }
            item["completion_commit"] = "def4567"
            item["completed_at"] = "2026-06-02T03:00:00Z"
            item["completed_by"] = "local_operator"
            item["validation_summary"] = "M166 targeted validation passed."
            item["tests_run"] = [
                "python -m pytest tests/test_pull_request_draft_summary_generator.py -> passed",
                "python -m aresforge generate-pr-draft-summary --item-id m166-pull-request-draft-summary-generator --format json -> passed",
            ]
            item["evidence_note"] = "Queue, validation, changed files, and artifact evidence support PR summary review."
            item["changed_files"] = [
                "src/aresforge/operator/pull_request_draft_summary_generator.py",
                "tests/test_pull_request_draft_summary_generator.py",
            ]
            item["artifact_paths"] = [".aresforge/pr_draft_summaries/m166.json"]
            item["completion_evidence"] = {
                "record_type": "pull_request_draft_summary_generator_v1",
                "artifacts_created": [".aresforge/pr_draft_summaries/m166.json"],
            }
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


def _write_evidence_bundle(tmp_path: Path) -> Path:
    path = tmp_path / ".aresforge" / "codex_loop_validation_evidence" / "m166-pull-rator" / "run-1"
    path.mkdir(parents=True)
    bundle = path / "codex-loop-validation-evidence-bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "record_type": "codex_loop_validation_evidence_bundle_v1",
                "status": "evidence_bundle_created",
                "blocked": False,
                "blocked_reasons": [],
                "warnings": [],
                "run_id": "run-166",
                "artifacts_created": [str(bundle)],
                "changed_files": {
                    "bundled_changed_files": ["docs/operator/LOCAL_OPERATOR_USAGE.md"],
                    "workspace_changed_files": [],
                },
                "validation_evidence": {
                    "validation_summary": "Codex evidence bundle validation passed.",
                    "validation_commands": ["python -m pytest tests/test_codex_loop_validation_evidence_bundle.py"],
                    "validation_passed": True,
                },
                "validation_command_execution_performed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return bundle


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_generates_pr_draft_summary_from_queue_and_codex_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    evidence = _write_evidence_bundle(tmp_path)

    payload = _payload(
        generate_pr_draft_summary(
            config,
            item_id="m166-pull-request-draft-summary-generator",
            evidence_bundle=evidence,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "draft_summary_created"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["pr_creation_allowed"] is False
    assert payload["pull_request_created"] is False
    assert "src/aresforge/operator/pull_request_draft_summary_generator.py" in payload["changed_files"]
    assert "docs/operator/LOCAL_OPERATOR_USAGE.md" in payload["changed_files"]
    assert any("pytest" in test for test in payload["tests"])
    assert any("generate-pr-draft-summary" in check for check in payload["smoke_checks"])
    assert payload["linked_issue_references"][0] == "#166"
    assert payload["artifact_paths"]
    assert "## Summary" in payload["draft_pr_body_markdown"]
    assert Path(str(payload["artifacts_created"][0])).exists()
    assert Path(str(payload["artifacts_created"][1])).exists()


def test_blocks_complete_summary_when_validation_and_artifacts_are_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m166-pull-request-draft-summary-generator":
            item["validation_summary"] = ""
            item["tests_run"] = []
            item["artifact_paths"] = []
            item["completion_evidence"] = {}
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

    payload = _payload(
        generate_pr_draft_summary(
            config,
            item_id="m166-pull-request-draft-summary-generator",
        )
    )

    assert payload["status"] == "blocked"
    assert payload["github_execution_performed"] is False
    assert any("Validation evidence is required" in reason for reason in payload["blocked_reasons"])
    assert any("artifact path" in reason for reason in payload["blocked_reasons"])


def test_output_path_writes_json_and_markdown_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "pr_draft_summaries" / "m166.json"

    first = generate_pr_draft_summary(
        config,
        item_id="m166-pull-request-draft-summary-generator",
        output=output,
    )
    second = generate_pr_draft_summary(
        config,
        item_id="m166-pull-request-draft-summary-generator",
        output=output,
    )

    assert first["ok"] is True
    assert output.exists()
    assert output.with_suffix(".md").exists()
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
