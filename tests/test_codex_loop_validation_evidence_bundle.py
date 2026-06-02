import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_loop_validation_evidence_bundle import (
    DEFAULT_ITEM_ID,
    bundle_codex_loop_validation_evidence,
)
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M161 Codex Loop Validation Evidence Bundle",
        description="Bundle Codex loop execution, validation, gates, classifications, and completion recommendation evidence.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m161", "codex-loop-validation-evidence", "machine-gated"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["codex_loop_execution_record", "validation_evidence", "completion_recommendation"],
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_bundle_codex_loop_validation_evidence_creates_durable_dry_run_bundle(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = bundle_codex_loop_validation_evidence(config, dry_run=True)
    payload = _payload(result)

    assert result["ok"] is True
    assert payload["record_type"] == "codex_loop_validation_evidence_bundle_v1"
    assert payload["status"] == "evidence_bundle_created"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == DEFAULT_ITEM_ID
    assert payload["dry_run"] is True
    assert payload["machine_gates_passed"] is True
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True

    output_path = Path(str(result["output"]))
    assert output_path.exists()
    assert (output_path.parent / "stdout-artifact.md").exists()
    assert (output_path.parent / "stderr-artifact.txt").exists()
    assert (output_path.parent / "source-patch-risk-classification.json").exists()
    assert (output_path.parent / "retry-classification.json").exists()
    assert payload["codex_loop_execution_record"]["record_type"] == "end_to_end_codex_loop_dry_run_v1"
    assert payload["validation_evidence"]["dry_run_validation_skipped"] is True
    assert payload["source_patch_risk_classification"]["status"] == "not_applicable_no_source_patch"
    assert payload["retry_classification"]["status"] == "not_applicable_no_failure"
    assert payload["safe_completion_recommendation"]["queue_completion_performed"] is False


def test_bundle_requires_dry_run_before_writing_live_execution_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(bundle_codex_loop_validation_evidence(config, dry_run=False))

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert any("--dry-run" in reason for reason in payload["blocked_reasons"])


def test_bundle_classifies_supplied_source_patch_without_applying_it(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = tmp_path / "artifacts" / "manual" / "sample.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(
        "\n".join(
            [
                "diff --git a/docs/example.md b/docs/example.md",
                "index 1111111..2222222 100644",
                "--- a/docs/example.md",
                "+++ b/docs/example.md",
                "@@ -1 +1 @@",
                "-old",
                "+new",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = _payload(bundle_codex_loop_validation_evidence(config, dry_run=True, patch_path=patch_path))

    classification = payload["source_patch_risk_classification"]
    assert classification["record_type"] == "source_patch_risk_classification_v1"
    assert classification["status"] == "classified"
    assert classification["risk_level"] == "low"
    assert classification["touched_files"] == ["docs/example.md"]
    assert classification["patch_application_performed"] is False
    assert payload["patch_application_performed"] is False


def test_bundle_blocks_when_queue_item_is_missing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = _payload(bundle_codex_loop_validation_evidence(config, dry_run=True))

    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert payload["queue_item_found"] is False
    assert any("Queue item was not found" in reason for reason in payload["blocked_reasons"])
    assert payload["codex_execution_performed"] is False
