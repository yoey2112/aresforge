import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.sprint_issue_planner import (
    evaluate_issue_creation_verification,
    normalize_sprint_issue_plan,
    plan_sprint_issues,
    validate_sprint_issue_plan_definition,
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


def _load_fixture(name: str) -> dict[str, object]:
    root = Path(__file__).parent / "fixtures"
    return json.loads((root / name).read_text(encoding="utf-8-sig"))


def test_valid_definition_renders_expected_parent_and_child_plan(tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    result = plan_sprint_issues(definition_path=str(definition_path))

    assert result["ok"] is True
    assert result["plan"]["child_count"] == 7
    assert result["rendered"]["parent_issue_body"].startswith("## Safety Posture")
    assert len(result["rendered"]["child_issue_bodies"]) == 7


def test_invalid_definition_reports_clear_validation_errors() -> None:
    bad_definition = {
        "sprint_id": "M12",
        "repo": "yoey2112/aresforge",
        "parent": {"title": "Parent", "body": "missing sections"},
        "children": [{"title": "Child", "body": "Part of #{{PARENT_ISSUE_NUMBER}}\n```bad```"}],
    }

    errors = validate_sprint_issue_plan_definition(bad_definition)
    messages = "\n".join(item["message"] for item in errors)

    assert "Missing required '## Safety Posture' section." in messages
    assert "Nested markdown fences are not allowed" in messages


def test_generated_powershell_contains_required_phases(tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    result = plan_sprint_issues(definition_path=str(definition_path))
    script = result["rendered"]["powershell_issue_creation_block"]

    assert "gh issue create" in script
    assert "Parent child-index update" in script
    assert "Final Post-Creation Verification" in script
    assert "[FAILURE ACTION]" in script


def test_generated_issue_bodies_do_not_contain_markdown_fences_in_here_strings(tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    result = plan_sprint_issues(definition_path=str(definition_path))

    assert "```" not in result["rendered"]["powershell_issue_creation_block"]


def test_generated_output_includes_human_gated_mutation_warnings(tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    result = plan_sprint_issues(definition_path=str(definition_path))

    assert result["mutation_posture"] == "human_gated_output_only"
    warnings = "\n".join(result["safety_warnings"])
    assert "did not call gh" in warnings.lower()


def test_cli_plan_sprint_issues_dispatch_is_read_only(monkeypatch, capsys, tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "connect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("plan-sprint-issues must not connect to db")),
    )

    exit_code = cli.main(["plan-sprint-issues", "--definition", str(definition_path)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True


def test_regression_fixture_reports_verification_failure_pattern() -> None:
    definition = _load_fixture("m12-sprint-definition.json")
    observed = _load_fixture("m12-verification-failure-observed.json")
    plan = normalize_sprint_issue_plan(definition)

    report = evaluate_issue_creation_verification(
        plan=plan,
        actual_parent_title=observed["actual_parent_title"],
        actual_child_titles=observed["actual_child_titles"],
        parent_body_after_update=observed["parent_body_after_update"],
        body_by_child_title=observed["body_by_child_title"],
    )

    assert report["expected_child_count"] == 7
    assert report["actual_child_count"] == 6
    assert report["verification_status"] == "fail"
    assert "M12: Add regression fixtures for generated sprint issue scripts" in report["missing_expected_child_titles"]
    assert report["required_body_section_complete"] is False
    assert report["parent_child_index_complete"] is False
    assert "do not continue implementation" in report["failure_guidance"].lower()


def test_active_output_does_not_reintroduce_retired_issue_reference(tmp_path: Path) -> None:
    definition_payload = _load_fixture("m12-sprint-definition.json")
    definition_path = tmp_path / "m12.json"
    definition_path.write_text(json.dumps(definition_payload), encoding="utf-8")

    result = plan_sprint_issues(definition_path=str(definition_path))
    serialized = json.dumps(result)

    assert "#39" not in serialized
