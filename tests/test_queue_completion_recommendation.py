import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.queue_completion_recommendation import recommend_queue_completion


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


def _seed_item(config: AppConfig, *, item_id: str = "m113-queue-item-auto-completion-recommendation-engine") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M113 Queue Item Auto-Completion Recommendation Engine",
        description="Recommend queue completion from parsed dispatch evidence.",
        status="in_progress",
        priority="high",
        item_type="architecture",
        tags=["milestone:m113", "queue-completion", "local-only"],
        completion_requires=["tests_run", "changed_files", "review_evidence"],
        evidence_required=["dispatch_result_evidence", "validation_results"],
        notes="Recommendation only; no queue mutation.",
    )["ok"] is True


def _evidence(**overrides: object) -> dict[str, object]:
    evidence: dict[str, object] = {
        "evidence_record_type": "dispatch_result_evidence",
        "parsed": True,
        "blocked": False,
        "blocked_reasons": [],
        "item_id": "m113-queue-item-auto-completion-recommendation-engine",
        "title": "M113 Queue Item Auto-Completion Recommendation Engine",
        "project_id": "aresforge",
        "milestone": "m113",
        "result_path": "artifacts/manual/sample-codex-result.md",
        "result_exists": True,
        "files_changed": ["src/aresforge/operator/queue_completion_recommendation.py"],
        "what_changed": ["Added a local-only recommendation engine."],
        "tests_reported": ["python -m pytest tests/test_queue_completion_recommendation.py -> passed"],
        "smoke_checks_reported": [
            "python -m aresforge recommend-queue-completion --item-id m113-queue-item-auto-completion-recommendation-engine --evidence-path artifacts/manual/sample-dispatch-evidence.json --format json -> passed"
        ],
        "warnings_or_blockers": ["No blockers."],
        "commit_hash": "abc1234",
        "validation_confidence": "high",
        "completion_recommendation": "ready_for_human_completion_review",
        "human_review_required": True,
        "local_only": True,
        "execution_allowed": False,
    }
    evidence.update(overrides)
    return evidence


def _write_evidence(config: AppConfig, data: dict[str, object], name: str = "evidence.json") -> Path:
    path = config.repo_root / "artifacts" / "manual" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_recommends_complete_when_required_evidence_is_present(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    evidence_path = _write_evidence(config, _evidence())

    payload = _payload(
        recommend_queue_completion(
            config,
            item_id="m113-queue-item-auto-completion-recommendation-engine",
            evidence_path=evidence_path,
        )
    )

    assert payload["recommendation_record_type"] == "queue_completion_recommendation"
    assert payload["recommended_complete"] is True
    assert payload["blocked"] is False
    assert payload["evidence_valid"] is True
    assert payload["required_evidence_present"] is True
    assert payload["missing_evidence"] == []
    assert payload["tests_passed_reported"] is True
    assert payload["smoke_checks_passed_reported"] is True
    assert payload["commit_hash_present"] is True
    assert payload["confidence"] == "high"
    assert payload["operator_decision_required"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_recommends_blocked_for_failed_validation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    evidence_path = _write_evidence(
        config,
        _evidence(
            tests_reported=["python -m pytest tests/test_queue_completion_recommendation.py -> failed"],
            smoke_checks_reported=["Smoke check -> passed"],
        ),
    )

    payload = _payload(
        recommend_queue_completion(
            config,
            item_id="m113-queue-item-auto-completion-recommendation-engine",
            evidence_path=evidence_path,
        )
    )

    assert payload["recommended_complete"] is False
    assert payload["blocked"] is True
    assert payload["tests_passed_reported"] is False
    assert "tests_passed_reported" in payload["missing_evidence"]
    assert any("Required evidence is missing" in reason for reason in payload["blocked_reasons"])
    assert payload["queue_mutation_performed"] is False


def test_missing_evidence_file_blocks_without_crashing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(
        recommend_queue_completion(
            config,
            item_id="m113-queue-item-auto-completion-recommendation-engine",
            evidence_path=tmp_path / "artifacts" / "manual" / "missing.json",
        )
    )

    assert payload["recommended_complete"] is False
    assert payload["blocked"] is True
    assert payload["evidence_valid"] is False
    assert "valid_dispatch_result_evidence" in payload["missing_evidence"]
    assert any("Evidence file is missing" in reason for reason in payload["blocked_reasons"])


def test_warning_or_blocker_prevents_completion_recommendation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    evidence_path = _write_evidence(config, _evidence(warnings_or_blockers=["Blocker: manual review found a risk."]))

    payload = _payload(
        recommend_queue_completion(
            config,
            item_id="m113-queue-item-auto-completion-recommendation-engine",
            evidence_path=evidence_path,
        )
    )

    assert payload["recommended_complete"] is False
    assert payload["blocked"] is True
    assert payload["required_evidence_present"] is True
    assert payload["confidence"] == "blocked"
    assert any("warning or blocker" in reason for reason in payload["blocked_reasons"])


def test_json_output_and_no_overwrite_behavior(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    evidence_path = _write_evidence(config, _evidence())
    output_path = tmp_path / "artifacts" / "queue_completion_recommendations" / "m113.json"

    first = recommend_queue_completion(
        config,
        item_id="m113-queue-item-auto-completion-recommendation-engine",
        evidence_path=evidence_path,
        output=output_path,
        output_format="json",
    )
    duplicate = _payload(
        recommend_queue_completion(
            config,
            item_id="m113-queue-item-auto-completion-recommendation-engine",
            evidence_path=evidence_path,
            output=output_path,
            output_format="json",
        )
    )
    forced = recommend_queue_completion(
        config,
        item_id="m113-queue-item-auto-completion-recommendation-engine",
        evidence_path=evidence_path,
        output=output_path,
        output_format="json",
        force=True,
    )
    written = json.loads(output_path.read_text(encoding="utf-8"))

    assert first["ok"] is True
    assert output_path.exists()
    assert written["recommendation_record_type"] == "queue_completion_recommendation"
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["ok"] is True
