from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import repo_governance


def make_config(tmp_path: Path) -> AppConfig:
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


def test_inspect_repo_governance_reports_contract_health(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    def fake_run(args: list[str], _cwd: Path) -> tuple[bool, int | None, str, str]:
        command = " ".join(args)
        if command.startswith("gh repo view"):
            return True, 0, '{"defaultBranchRef": {"name": "main"}}', ""
        if command.startswith("gh label list"):
            return (
                True,
                0,
                "["
                '{"name":"aresforge-ready"},'
                '{"name":"aresforge-automerge"},'
                '{"name":"aresforge-blocked"},'
                '{"name":"aresforge-needs-evidence"},'
                '{"name":"aresforge-needs-docs"},'
                '{"name":"aresforge-closeout-ready"},'
                '{"name":"aresforge-managed"},'
                '{"name":"aresforge-generated"}'
                "]",
                "",
            )
        if command.startswith("gh api repos/yoey2112/aresforge/milestones"):
            return (
                True,
                0,
                "["
                '{"title":"M0 - Foundation","state":"closed","number":1},'
                '{"title":"M1 - Validation","state":"closed","number":2},'
                '{"title":"M2 - Local Automation Foundation","state":"closed","number":3},'
                '{"title":"M3 - Registry And Routing Deepening","state":"open","number":4},'
                '{"title":"M4 - Local Operator Expansion","state":"open","number":5},'
                '{"title":"Product - Backlog","state":"open","number":6}'
                "]",
                "",
            )
        if command.startswith("gh issue list"):
            return (
                True,
                0,
                "["
                '{"number":131,"title":"Governance","url":"https://example/131",'
                '"labels":[{"name":"aresforge-ready"}],"milestone":{"title":"M3 - Registry And Routing Deepening"}}'
                "]",
                "",
            )
        if command.startswith("gh pr list"):
            return (
                True,
                0,
                "["
                '{"number":210,"title":"M3 governance","url":"https://example/210",'
                '"labels":[{"name":"aresforge-automerge"}]}'
                "]",
                "",
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(repo_governance, "_run_command", fake_run)

    payload = repo_governance.inspect_repo_governance(config)

    assert payload["repository_slug"] == "yoey2112/aresforge"
    assert payload["default_branch"] == "main"
    assert payload["required_platform_labels"]["all_present"] is True
    assert payload["optional_platform_labels"]["all_present"] is True
    assert payload["automation_trigger_labels"]["all_present"] is True
    assert payload["milestone_naming_status"]["naming_ok"] is True
    assert payload["open_issue_readiness_signal"]["ready_issue_numbers"] == [131]
    assert payload["open_pr_readiness_signal"]["automerge_intent_pr_numbers"] == [210]
    assert payload["warnings"] == []
    assert "run-ready-issue-batch --plan-only" in payload["recommended_next_action"]


def test_inspect_repo_governance_degrades_when_gh_unavailable(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        repo_governance,
        "_run_command",
        lambda _args, _cwd: (False, None, "", "command_not_found"),
    )

    payload = repo_governance.inspect_repo_governance(config)

    assert payload["default_branch"] is None
    assert payload["required_platform_labels"]["available"] is False
    assert payload["milestone_naming_status"]["available"] is False
    assert payload["open_issue_readiness_signal"]["signal"] == "unavailable"
    assert payload["open_pr_readiness_signal"]["signal"] == "unavailable"
    assert any("gh command unavailable" in warning for warning in payload["warnings"])
    assert "Resolve environment or GitHub CLI warnings" in payload["recommended_next_action"]
