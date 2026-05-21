import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge import cli
from aresforge.operator.planning_state import (
    compare_planning_state,
    empty_planning_state,
    inspect_planning_state,
    persist_closeout_snapshot,
    persist_sprint_plan,
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_inspect_planning_state_missing(tmp_path: Path) -> None:
    payload = inspect_planning_state(path=tmp_path / ".aresforge" / "planning-state.json")
    assert payload["ok"] is True
    assert payload["summary"]["validation_status"] == "missing_state"


def test_inspect_planning_state_invalid(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("{bad", encoding="utf-8")
    payload = inspect_planning_state(path=state_path)
    assert payload["ok"] is False
    assert payload["summary"]["validation_status"] == "invalid"


def test_compare_planning_state_valid_and_drift(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    persist_sprint_plan(
        path=state_path,
        command_name="generate-sprint-issue-script",
        sprint_plan={
            "sprint_id": "M9",
            "parent_issue": {"number": 192, "title": "M9 parent"},
            "children": [{"number": 193, "title": "A"}, {"number": 193, "title": "A"}],
            "relationships": [],
        },
    )
    persist_closeout_snapshot(
        path=state_path,
        command_name="plan-batch-closeout",
        snapshot={
            "snapshot_id": "parent-999",
            "parent_issue": 999,
            "command": "plan-batch-closeout",
            "closeout_plan": {},
            "evidence_report": {},
            "observed_children": [],
        },
    )

    payload = compare_planning_state(path=state_path)
    assert payload["ok"] is True
    assert payload["drift_detected"] is True


def test_compare_planning_state_invalid_schema(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    payload = empty_planning_state()
    payload["schema_version"] = "0.1"
    state_path.write_text(json.dumps(payload), encoding="utf-8")
    result = compare_planning_state(path=state_path)
    assert result["ok"] is False


def test_cli_dispatch_inspect_and_compare_planning_state(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    state_path = tmp_path / "safe" / "planning-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(empty_planning_state()), encoding="utf-8")

    inspect_exit = cli.main(["inspect-planning-state", "--planning-state-path", str(state_path)])
    inspect_payload = json.loads(capsys.readouterr().out)
    assert inspect_exit == 0
    assert inspect_payload["ok"] is True

    compare_exit = cli.main(["compare-planning-state", "--planning-state-path", str(state_path)])
    compare_payload = json.loads(capsys.readouterr().out)
    assert compare_exit == 0
    assert compare_payload["ok"] is True


def test_cli_dispatch_inspect_closeout_planning_drift(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_closeout_planning_drift",
        lambda _config, parent_issue, planning_state_path: {
            "command": "inspect-closeout-planning-drift",
            "ok": True,
            "parent_issue": parent_issue,
            "planning_state_path": planning_state_path,
        },
    )
    exit_code = cli.main(["inspect-closeout-planning-drift", "--parent-issue", "210"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "inspect-closeout-planning-drift"
    assert payload["parent_issue"] == 210
