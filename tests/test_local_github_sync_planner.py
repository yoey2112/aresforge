import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_github_sync_planner import generate_github_sync_plan


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


def test_sync_plan_from_offline_closeout_state(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/offline_state/parent_closeout_ready.json")
    state_path = tmp_path / "offline.json"
    state_path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    payload = generate_github_sync_plan(_config(tmp_path), state_file=state_path, output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert plan["github_operations_performed"] is False
    assert any(item["operation_type"] == "comment_candidate" for item in plan["operations"])
    assert any(item["operation_type"] == "milestone_candidate" for item in plan["operations"])
    assert any(item["operation_type"] == "validation_candidate" for item in plan["operations"])


def test_sync_plan_from_project_state_pending_sync(tmp_path: Path) -> None:
    state_dir = tmp_path / ".aresforge" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "project_state.json").write_text(
        json.dumps({"pending_sync": True, "documentation_status": "in_progress"}),
        encoding="utf-8",
    )

    payload = generate_github_sync_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert any(item["operation_type"] == "label_candidate" for item in plan["operations"])


def test_sync_plan_missing_files_warns_but_succeeds(tmp_path: Path) -> None:
    payload = generate_github_sync_plan(
        _config(tmp_path),
        state_file=tmp_path / "missing-offline.json",
        project_state=tmp_path / "missing-project.json",
        output_format="json",
    )
    assert payload["ok"] is True
    assert payload["payload"]["warnings"]


def test_sync_plan_overwrite_protection(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "github-sync" / "plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("old", encoding="utf-8")

    first = generate_github_sync_plan(_config(tmp_path), output=output, output_format="json")
    assert first["ok"] is False
    assert first["error"] == "output_exists"

    second = generate_github_sync_plan(_config(tmp_path), output=output, output_format="json", force=True)
    assert second["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["title"] == "AresForge Offline-to-GitHub Sync Plan"
