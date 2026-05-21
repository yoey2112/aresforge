import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig


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


def test_cli_help_includes_m6_commands() -> None:
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "plan-agent-queue" in help_text
    assert "report-batch-readiness" in help_text
    assert "plan-batch-closeout" in help_text


def test_cli_dispatch_plan_agent_queue(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "plan_agent_queue",
        lambda _config, issue_numbers, issues_file: {
            "command": "plan-agent-queue",
            "ok": True,
            "issue_numbers": issue_numbers,
            "issues_file": issues_file,
        },
    )
    exit_code = cli.main(["plan-agent-queue", "--issue-number", "165"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["issue_numbers"] == [165]


def test_cli_dispatch_report_batch_readiness(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "report_batch_readiness",
        lambda _config, issue_numbers, issues_file, changed_files, validations, pr_number: {
            "command": "report-batch-readiness",
            "ok": True,
            "issue_numbers": issue_numbers,
            "issues_file": issues_file,
            "changed_files": changed_files,
            "validations": validations,
            "pr_number": pr_number,
        },
    )
    exit_code = cli.main(
        [
            "report-batch-readiness",
            "--pr-number",
            "210",
            "--issue-number",
            "165",
            "--changed-file",
            "src/aresforge/cli.py",
            "--validation",
            "python -m pytest",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["pr_number"] == 210
    assert payload["issue_numbers"] == [165]


def test_cli_dispatch_plan_batch_closeout(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "plan_batch_closeout",
        lambda _config, parent_issue, write_planning_snapshot=False, planning_state_path=None: {
            "command": "plan-batch-closeout",
            "ok": True,
            "parent_issue": parent_issue,
            "write_planning_snapshot": write_planning_snapshot,
            "planning_state_path": planning_state_path,
        },
    )
    exit_code = cli.main(["plan-batch-closeout", "--parent-issue", "172"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["parent_issue"] == 172
    assert payload["write_planning_snapshot"] is False
