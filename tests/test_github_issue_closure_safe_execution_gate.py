import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_issue_closure_safe_execution_gate import (
    RECORD_TYPE,
    gate_github_issue_closure,
)
from aresforge.operator.github_issue_creation_real_run_gate import LIVE_AUTONOMY_PROFILE
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


def _seed_queue(config: AppConfig) -> Path:
    result = init_project_queue(config)
    assert result["ok"] is True
    queue_path = Path(str(result["path"]))
    assert add_queue_item(
        config,
        item_id="m174-github-issue-state-reconciliation",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M174 GitHub Issue State Reconciliation",
        status="done",
        priority="high",
        item_type="sync",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m175-github-issue-closure-safe-execution-gate",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M175 GitHub Issue Closure Safe Execution Gate",
        description="Safely close a linked GitHub issue only after evidence and gates pass.",
        status="done",
        priority="high",
        item_type="sync",
        tags=["milestone:m175", "github-issue-sync", "issue-closure", "machine-gated"],
        dependencies=["m174-github-issue-state-reconciliation"],
        notes="Closure must be dry-run by default and real closure requires explicit enablement.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="blocked-item",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="Blocked item",
        description="Missing completion evidence.",
        status="in_progress",
        priority="normal",
        item_type="task",
    )["ok"] is True

    raw = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in raw["work_items"]:
        if item["item_id"] == "m175-github-issue-closure-safe-execution-gate":
            item["github_issue"] = {
                "number": 175,
                "url": "https://github.com/local/aresforge/issues/175",
                "state": "open",
            }
            item["completed_at"] = "2026-06-02T12:00:00Z"
            item["completed_by"] = "local_operator"
            item["completion_commit"] = "abc175"
            item["validation_summary"] = "Targeted validation passed."
            item["tests_run"] = ["python -m pytest tests/test_github_issue_closure_safe_execution_gate.py -> passed"]
            item["evidence_note"] = "Local validation and evidence bundle support safe closure."
            item["artifact_paths"] = [".aresforge/codex_loop_validation_evidence/m175/bundle.json"]
            item["completion_evidence"] = {
                "record_type": "github_issue_closure_safe_execution_gate_v1",
                "status": "dry_run_ready",
                "machine_gates_passed": True,
                "artifacts_created": [".aresforge/codex_loop_validation_evidence/m175/bundle.json"],
            }
        if item["item_id"] == "blocked-item":
            item["github_issue"] = {"number": 999, "state": "open"}
    queue_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    return queue_path


class _FakeGitHubClosureClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def close_issue(self, *, repo: str, issue_number: int, reason: str) -> dict[str, object]:
        self.calls.append({"repo": repo, "issue_number": issue_number, "reason": reason})
        return {
            "id": 175001,
            "number": issue_number,
            "html_url": f"https://github.test/{repo}/issues/{issue_number}",
            "state": "closed",
            "reason": reason,
        }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_dry_run_allows_closure_review_without_github_mutation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubClosureClient()

    payload = _payload(
        gate_github_issue_closure(
            config,
            item_id="m175-github-issue-closure-safe-execution-gate",
            dry_run=True,
            github_client=client,
        )
    )

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "dry_run_ready"
    assert payload["sync_status"] == "dry_run_ready"
    assert payload["blocked"] is False
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m175-github-issue-closure-safe-execution-gate"
    assert payload["repository"] == "local/aresforge"
    assert payload["issue_number"] == 175
    assert payload["issue_url"] == "https://github.com/local/aresforge/issues/175"
    assert payload["closure_recommended"] is True
    assert payload["issue_closure_allowed"] is False
    assert payload["issue_closed"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["registry_mutation_performed"] is False
    assert payload["queue_mutation_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["recovery_available"] is True
    assert payload["local_only"] is True
    assert payload["idempotency_key"].startswith("github-issue-closure:")
    assert payload["evidence_summary"]["validation_passed"] is True
    assert client.calls == []


def test_real_run_requires_live_autonomy_profile(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubClosureClient()

    payload = _payload(
        gate_github_issue_closure(
            config,
            item_id="m175-github-issue-closure-safe-execution-gate",
            dry_run=False,
            github_enabled=True,
            github_client=client,
        )
    )

    assert payload["blocked"] is True
    assert payload["status"] == "blocked"
    assert payload["sync_status"] == "blocked"
    assert payload["issue_closure_allowed"] is False
    assert payload["issue_closed"] is False
    assert payload["github_execution_performed"] is False
    assert any("github_issue_sync_enabled" in reason for reason in payload["blocked_reasons"])
    assert client.calls == []


def test_mocked_real_run_closes_issue_and_records_registry_sync(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubClosureClient()
    registry_path = tmp_path / ".aresforge" / "github_link_registry" / "links.json"

    payload = _payload(
        gate_github_issue_closure(
            config,
            item_id="m175-github-issue-closure-safe-execution-gate",
            registry_path=registry_path,
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            repo="local/aresforge",
            github_client=client,
        )
    )

    assert payload["blocked"] is False
    assert payload["status"] == "issue_closed"
    assert payload["sync_status"] == "issue_closed"
    assert payload["machine_gates_checked"][0]["gate_profile"] == "github_sync"
    assert payload["machine_gates_passed"] is True
    assert payload["issue_closure_allowed"] is True
    assert payload["issue_closed"] is True
    assert payload["github_execution_performed"] is True
    assert payload["mutation_performed"] is True
    assert payload["registry_mutation_performed"] is True
    assert payload["queue_mutation_performed"] is False
    assert payload["local_only"] is False
    assert payload["closed_issue"]["state"] == "closed"
    assert payload["local_registry_record"]["issue_number"] == 175
    assert Path(str(payload["github_preflight_record_path"])).exists()
    assert client.calls == [{"repo": "local/aresforge", "issue_number": 175, "reason": "completed"}]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["links"][0]["queue_item_id"] == "m175-github-issue-closure-safe-execution-gate"
    assert registry["links"][0]["sync_status"] == "synced"


def test_blocks_when_evidence_is_incomplete_or_issue_already_closed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    client = _FakeGitHubClosureClient()

    incomplete = _payload(
        gate_github_issue_closure(
            config,
            item_id="blocked-item",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )
    already_closed = _payload(
        gate_github_issue_closure(
            config,
            item_id="m175-github-issue-closure-safe-execution-gate",
            linked_issue_state="closed",
            dry_run=False,
            github_enabled=True,
            autonomy_profile=LIVE_AUTONOMY_PROFILE,
            github_client=client,
        )
    )

    assert incomplete["blocked"] is True
    assert any("status must be done" in reason for reason in incomplete["blocked_reasons"])
    assert any("Validation evidence" in reason for reason in incomplete["blocked_reasons"])
    assert already_closed["blocked"] is True
    assert any("already closed" in reason for reason in already_closed["blocked_reasons"])
    assert client.calls == []


def test_output_path_writes_local_artifact_and_refuses_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    output = tmp_path / ".aresforge" / "github_issue_closure_safe_execution_gate" / "m175.json"

    first = gate_github_issue_closure(
        config,
        item_id="m175-github-issue-closure-safe-execution-gate",
        dry_run=True,
        output=output,
    )
    second = gate_github_issue_closure(
        config,
        item_id="m175-github-issue-closure-safe-execution-gate",
        dry_run=True,
        output=output,
    )

    assert first["ok"] is True
    written = json.loads(output.read_text(encoding="utf-8"))
    assert str(output) in written["artifacts_created"]
    assert second["ok"] is False
    assert second["payload"]["blocked"] is True
    assert second["payload"]["github_execution_performed"] is False
    assert second["payload"]["mutation_performed"] is False
    assert any("Output file already exists" in reason for reason in second["payload"]["blocked_reasons"])
