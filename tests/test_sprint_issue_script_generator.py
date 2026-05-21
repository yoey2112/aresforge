import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.sprint_issue_script_generator import (
    generate_sprint_issue_script,
    validate_sprint_definition,
)


def _definition() -> dict[str, object]:
    return {
        "sprint_id": "M8",
        "repo": "yoey2112/aresforge",
        "parent": {
            "title": "M8 parent",
            "body": (
                "## Safety Posture\n"
                "- human-triggered operations only\n"
                "- read-only planning by default\n"
                "- no autonomous mutation\n"
                "## Acceptance Criteria\n"
                "- Parent issue captures sprint scope\n"
                "## Validation\n"
                "- python -m pytest\n"
            ),
        },
        "children": [
            {
                "title": "M8 child",
                "body": (
                    "Part of #{{PARENT_ISSUE_NUMBER}}\n"
                    "Implements sprint workflow improvements.\n"
                    "## Safety Posture\n"
                    "- human-triggered issue creation only\n"
                    "- read-only generation command\n"
                    "- no autonomous setup or mutation\n"
                    "## Acceptance Criteria\n"
                    "- Child issue body is complete\n"
                    "## Validation\n"
                    "- python -m pytest\n"
                ),
            }
        ],
    }


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


def test_generate_sprint_issue_script_writes_output(tmp_path: Path) -> None:
    definition = tmp_path / "m8-definition.json"
    definition.write_text(json.dumps(_definition()), encoding="utf-8")

    payload = generate_sprint_issue_script(definition_path=str(definition), output_path=str(tmp_path / "m8.ps1"))

    assert payload["ok"] is True
    script_path = Path(payload["script_path"])
    content = script_path.read_text(encoding="utf-8")
    assert "gh issue create" in content
    assert "{{PARENT_ISSUE_NUMBER}}" in content
    assert "```" not in content


def test_validate_sprint_definition_reports_actionable_failures() -> None:
    bad_definition = {
        "sprint_id": "M8",
        "repo": "yoey2112/aresforge",
        "parent": {"title": "Parent", "body": "No required sections"},
        "children": [
            {
                "title": "Child",
                "body": "Linked issue: #39\n```powershell\nWrite-Host unsafe\n```",
            }
        ],
    }

    errors = validate_sprint_definition(bad_definition)
    messages = "\n".join(item["message"] for item in errors)
    assert "Missing required '## Safety Posture' section." in messages
    assert "Nested markdown fences are not allowed" in messages
    assert "Retired or protected historical issue references must be explicitly classified" in messages


def test_cli_dispatch_generate_sprint_issue_script(monkeypatch, capsys, tmp_path: Path) -> None:
    definition = tmp_path / "m8-definition.json"
    definition.write_text(json.dumps(_definition()), encoding="utf-8")

    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    exit_code = cli.main(
        [
            "generate-sprint-issue-script",
            "--definition",
            str(definition),
            "--output",
            str(tmp_path / "generated.ps1"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["mutation_posture"] == "output_only_human_execution_required"


def test_generate_sprint_issue_script_does_not_write_planning_state_by_default(tmp_path: Path) -> None:
    definition = tmp_path / "m8-definition.json"
    definition.write_text(json.dumps(_definition()), encoding="utf-8")
    planning_state = tmp_path / ".aresforge" / "planning-state.json"

    payload = generate_sprint_issue_script(definition_path=str(definition), output_path=str(tmp_path / "m8.ps1"))

    assert payload["ok"] is True
    assert not planning_state.exists()


def test_generate_sprint_issue_script_can_write_planning_state_deterministically(tmp_path: Path) -> None:
    definition = tmp_path / "m8-definition.json"
    definition.write_text(json.dumps(_definition()), encoding="utf-8")
    planning_state = tmp_path / "state" / "planning-state.json"

    first = generate_sprint_issue_script(
        definition_path=str(definition),
        output_path=str(tmp_path / "m8.ps1"),
        write_planning_state=True,
        planning_state_path=str(planning_state),
        repo_root=tmp_path,
    )
    first_content = planning_state.read_text(encoding="utf-8")

    second = generate_sprint_issue_script(
        definition_path=str(definition),
        output_path=str(tmp_path / "m8.ps1"),
        write_planning_state=True,
        planning_state_path=str(planning_state),
        repo_root=tmp_path,
    )
    second_content = planning_state.read_text(encoding="utf-8")

    assert first["ok"] is True
    assert second["ok"] is True
    assert first_content == second_content
    assert "\"sprint_plans\"" in first_content
