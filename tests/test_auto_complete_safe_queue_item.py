import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.auto_complete_safe_queue_item import auto_complete_safe_queue_item
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


def _seed(config: AppConfig, *, item_id: str = "m132-safe", tags: list[str] | None = None) -> Path:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m131-machine-safety-gate-engine",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M131 dependency",
        status="done",
        priority="high",
        item_type="feature",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M132 safe auto completion",
        status="in_progress",
        priority="normal",
        item_type="feature",
        tags=["milestone:m132", *(tags or [])],
        dependencies=["m131-machine-safety-gate-engine"],
        completion_requires=["tests_run", "smoke_checks", "commit_hash"],
        evidence_required=["dispatch_result_evidence"],
    )["ok"] is True
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in queue["work_items"]:
        if item["item_id"] == item_id:
            item["tests_run"] = ["python -m pytest -> passed"]
            item["validation_summary"] = "Validation reported as passed."
    queue_path.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    return _write_evidence(config, item_id=item_id)


def _write_evidence(config: AppConfig, *, item_id: str = "m132-safe", tests: str = "python -m pytest -> passed") -> Path:
    path = config.artifact_root / "dispatch_result_evidence" / f"{item_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "evidence_record_type": "dispatch_result_evidence",
                "parsed": True,
                "blocked": False,
                "blocked_reasons": [],
                "item_id": item_id,
                "project_id": "aresforge",
                "files_changed": ["src/aresforge/operator/auto_complete_safe_queue_item.py"],
                "what_changed": ["Implemented safe auto-completion."],
                "tests_reported": [tests],
                "smoke_checks_reported": ["python -m aresforge auto-complete-safe-queue-item --dry-run -> passed"],
                "warnings_or_blockers": ["No blockers."],
                "commit_hash": "abc1234",
                "human_review_required": True,
                "local_only": True,
                "execution_allowed": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_auto_complete_safe_queue_item_dry_run_does_not_mutate(tmp_path: Path) -> None:
    config = _config(tmp_path)
    evidence_path = _seed(config)

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=evidence_path, dry_run=True)
    payload = json.loads(result["stdout"])
    queue = json.loads((tmp_path / ".aresforge" / "queue" / "work_items.json").read_text(encoding="utf-8"))
    item = next(entry for entry in queue["work_items"] if entry["item_id"] == "m132-safe")

    assert result["ok"] is True
    assert payload["action_type"] == "auto_complete_safe_queue_item"
    assert payload["auto_completed"] is False
    assert payload["dry_run"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["machine_gates_checked"] is True
    assert payload["machine_gates_passed"] is True
    assert item["status"] == "in_progress"


def test_auto_complete_safe_queue_item_successfully_completes_and_logs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    evidence_path = _seed(config)

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=evidence_path)
    payload = json.loads(result["stdout"])
    queue = json.loads((tmp_path / ".aresforge" / "queue" / "work_items.json").read_text(encoding="utf-8"))
    item = next(entry for entry in queue["work_items"] if entry["item_id"] == "m132-safe")
    log = json.loads((tmp_path / ".aresforge" / "queue" / "transaction_log.json").read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert payload["auto_completed"] is True
    assert payload["previous_status"] == "in_progress"
    assert payload["new_status"] == "done"
    assert item["status"] == "done"
    assert item["completed_by"] == "auto_complete_safe_queue_item"
    assert item["completion_commit"] == "abc1234"
    assert payload["transaction_log_entry"]["mutation_type"] == "auto_complete_safe_queue_item"
    assert log["transactions"][-1]["item_id"] == "m132-safe"
    assert log["transactions"][-1]["mutation_type"] == "auto_complete_safe_queue_item"


def test_auto_complete_safe_queue_item_blocks_high_risk_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    evidence_path = _seed(config, tags=["high-risk"])

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=evidence_path)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["auto_completed"] is False
    assert "Queue item is tagged high-risk." in payload["blocked_reasons"]


def test_auto_complete_safe_queue_item_blocks_missing_evidence(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config)
    missing = tmp_path / "artifacts" / "dispatch_result_evidence" / "missing.json"

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=missing)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert any("Evidence file is missing" in reason for reason in payload["blocked_reasons"])
    assert payload["queue_mutation_performed"] is False


def test_auto_complete_safe_queue_item_blocks_failed_gates(tmp_path: Path) -> None:
    config = _config(tmp_path)
    evidence_path = _seed(config)
    (tmp_path / ".aresforge" / "queue" / "transaction_log.json").unlink()

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=evidence_path)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert payload["machine_gates_passed"] is False
    assert "Machine safety gate profile queue_status_mutation did not pass." in payload["blocked_reasons"]


def test_auto_complete_safe_queue_item_blocks_failed_tests(tmp_path: Path) -> None:
    config = _config(tmp_path)
    evidence_path = _seed(config)
    _write_evidence(config, item_id="m132-safe", tests="python -m pytest -> failed")

    result = auto_complete_safe_queue_item(config, item_id="m132-safe", evidence_path=evidence_path)
    payload = json.loads(result["stdout"])

    assert result["ok"] is False
    assert payload["blocked"] is True
    assert "Required tests are not reported as passed." in payload["blocked_reasons"]
    assert payload["queue_mutation_performed"] is False
