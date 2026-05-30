import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.sprint_batch_report import inspect_sprint_batch_report


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


def test_sprint_batch_report_summarizes_commits_queue_tests_and_dispatch(monkeypatch, tmp_path: Path) -> None:
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-30T00:00:00+00:00",
                "work_items": [
                    {
                        "item_id": "m93-operator-handoff-package-v2",
                        "project_id": "aresforge",
                        "repo_id": "aresforge-main",
                        "title": "M93 Operator Handoff Package v2",
                        "status": "done",
                        "completed_at": "2026-05-30T01:00:00+00:00",
                        "completion_commit": "abc123456789",
                        "tests_run": ["python -m pytest tests/test_cli.py -> passed"],
                    },
                    {
                        "item_id": "m94-overnight-sprint-batch-report",
                        "title": "M94 Overnight Sprint Batch Report",
                        "status": "proposed",
                        "priority": "normal",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    run_state = tmp_path / ".aresforge" / "codex_dispatch" / "runs" / "run-1" / "run_state.json"
    run_state.parent.mkdir(parents=True, exist_ok=True)
    run_state.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "item_id": "m93-operator-handoff-package-v2",
                "dispatch_state": "failed",
                "recovery": {"recovered_at": "2026-05-30T00:00:00+00:00"},
                "review_required": True,
            }
        ),
        encoding="utf-8",
    )

    def fake_run(command, **_kwargs):
        assert command[:2] == ["git", "log"]
        return subprocess.CompletedProcess(command, 0, stdout="abc1234 M93 implementation\nfed9876 evidence\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = inspect_sprint_batch_report(_config(tmp_path), output_format="json")
    payload = result["payload"]

    assert result["ok"] is True
    assert payload["commit_window"]["count"] == 2
    assert payload["items_completed"]["count"] == 1
    assert payload["validation_evidence"]["tests_recorded_count"] == 1
    assert payload["dispatch_runs"]["recovered_count"] == 1
    assert payload["queue_posture"]["status_counts"]["proposed"] == 1
    assert payload["next_recommended_milestone"]["item_id"] == "m94-overnight-sprint-batch-report"
    assert payload["safety_boundary"]["github_api_allowed"] is False
    assert payload["safety_boundary"]["gh_allowed"] is False
    assert payload["safety_boundary"]["automatic_next_item_execution_allowed"] is False
