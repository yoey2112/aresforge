import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_milestone_lifecycle import (
    check_local_milestone_readiness,
    generate_local_milestone_closeout,
    generate_local_milestone_template,
    inspect_local_milestone,
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


def test_generate_local_milestone_template_and_overwrite_protection(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output = tmp_path / ".aresforge" / "milestones" / "m30.json"
    first = generate_local_milestone_template(config, milestone_id="M30", output=output, title="M30")
    assert first["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["milestone_id"] == "M30"

    second = generate_local_milestone_template(config, milestone_id="M30", output=output)
    assert second["ok"] is False
    assert second["error"] == "output_exists"


def test_inspect_local_milestone(tmp_path: Path) -> None:
    config = _config(tmp_path)
    definition = tmp_path / "m30.json"
    definition.write_text(
        json.dumps(
            {
                "milestone_id": "M30",
                "title": "Lifecycle",
                "goal": "Connect M26-M29",
                "status": "in_progress",
                "parent_reference": "M30",
                "work_items": ["[x] local planning"],
                "required_docs": [],
                "required_artifacts": [],
                "validation_commands": ["python -m pytest tests/test_local_milestone_lifecycle.py"],
                "closeout_requirements": ["docs updated"],
                "risks": ["none"],
                "notes": ["local only"],
            }
        ),
        encoding="utf-8",
    )
    payload = inspect_local_milestone(config, definition=definition, output_format="json")
    assert payload["ok"] is True
    assert payload["payload"]["milestone_id"] == "M30"


def test_check_local_milestone_readiness(tmp_path: Path) -> None:
    config = _config(tmp_path)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "x.md").write_text("# x\n", encoding="utf-8")
    definition = tmp_path / "m30.json"
    definition.write_text(
        json.dumps(
            {
                "milestone_id": "M30",
                "title": "Lifecycle",
                "goal": "Connect M26-M29",
                "status": "in_progress",
                "parent_reference": "M30",
                "work_items": ["done: template"],
                "required_docs": [str(tmp_path / "docs" / "x.md")],
                "required_artifacts": [],
                "validation_commands": ["python -m pytest tests/test_local_milestone_lifecycle.py"],
                "closeout_requirements": ["docs updated"],
                "risks": ["none"],
                "notes": ["local only"],
            }
        ),
        encoding="utf-8",
    )
    state_path = tmp_path / ".aresforge" / "state"
    state_path.mkdir(parents=True, exist_ok=True)
    (state_path / "project_state.json").write_text(
        json.dumps({"documentation_status": "in_progress", "current_milestone": "M30"}),
        encoding="utf-8",
    )
    payload = check_local_milestone_readiness(config, definition=definition, output_format="json")
    assert payload["ok"] is True
    assert payload["payload"]["ready"] is True


def test_generate_local_milestone_closeout(tmp_path: Path) -> None:
    config = _config(tmp_path)
    definition = tmp_path / "m30.json"
    definition.write_text(
        json.dumps(
            {
                "milestone_id": "M30",
                "title": "Lifecycle",
                "goal": "Connect M26-M29",
                "status": "ready_for_closeout",
                "parent_reference": "M30",
                "work_items": ["done: template", "[x] docs"],
                "required_docs": [],
                "required_artifacts": [],
                "validation_commands": ["python -m pytest tests/test_local_milestone_lifecycle.py"],
                "closeout_requirements": ["docs updated"],
                "risks": ["none"],
                "notes": ["local only"],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "artifacts" / "closeout.md"
    first = generate_local_milestone_closeout(config, definition=definition, output=output)
    assert first["ok"] is True
    assert "Final Operator Checklist" in output.read_text(encoding="utf-8")

    second = generate_local_milestone_closeout(config, definition=definition, output=output)
    assert second["ok"] is False
    assert second["error"] == "output_exists"
