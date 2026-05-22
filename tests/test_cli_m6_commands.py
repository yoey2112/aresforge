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
    assert "plan-sprint-issues" in help_text
    assert "inspect-closeout-planning-drift" in help_text
    assert "inspect-milestone-state" in help_text
    assert "plan-milestone-execution-queue" in help_text
    assert "check-issue-evidence-readiness" in help_text
    assert "check-milestone-evidence-readiness" in help_text
    assert "plan-milestone-final-reconciliation" in help_text
    assert "inspect-milestone-dashboard" in help_text
    assert "inspect-child-execution-gates" in help_text
    assert "inspect-sequential-run-state" in help_text
    assert "generate-child-closeout-script" in help_text
    assert "generate-evidence-comment-template" in help_text


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


def test_cli_dispatch_inspect_closeout_planning_drift(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
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
    assert payload["parent_issue"] == 210


def test_cli_dispatch_inspect_milestone_state(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_milestone_state",
        lambda _config, parent_issue: {
            "command": "inspect-milestone-state",
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue},
        },
    )
    exit_code = cli.main(["inspect-milestone-state", "--parent-issue", "269"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "inspect-milestone-state"
    assert payload["read_only"] is True
    assert payload["parent_issue"]["issue_number"] == 269


def test_cli_dispatch_plan_milestone_execution_queue(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "plan_milestone_execution_queue",
        lambda _config, parent_issue: {
            "command": "plan-milestone-execution-queue",
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue},
            "safety_gates": {
                "execution_enabled": False,
                "close_issues": False,
                "bulk_closeout_allowed": False,
                "operator_review_required": True,
            },
        },
    )
    exit_code = cli.main(["plan-milestone-execution-queue", "--parent-issue", "269"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "plan-milestone-execution-queue"
    assert payload["read_only"] is True
    assert payload["safety_gates"]["execution_enabled"] is False


def test_cli_dispatch_check_issue_evidence_readiness(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "check_issue_evidence_readiness",
        lambda _config, issue_number: {
            "command": "check-issue-evidence-readiness",
            "ok": True,
            "read_only": True,
            "issue": {"number": issue_number},
            "safety": {"mutation_allowed": False},
        },
    )
    exit_code = cli.main(["check-issue-evidence-readiness", "--issue", "270"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "check-issue-evidence-readiness"
    assert payload["read_only"] is True


def test_cli_dispatch_check_milestone_evidence_readiness(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue: {
            "command": "check-milestone-evidence-readiness",
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue},
        },
    )
    exit_code = cli.main(["check-milestone-evidence-readiness", "--parent-issue", "269"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "check-milestone-evidence-readiness"


def test_cli_dispatch_plan_milestone_final_reconciliation(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {
            "command": "plan-milestone-final-reconciliation",
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue},
            "mutation_allowed": False,
        },
    )
    exit_code = cli.main(["plan-milestone-final-reconciliation", "--parent-issue", "269"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "plan-milestone-final-reconciliation"
    assert payload["read_only"] is True
    assert payload["mutation_allowed"] is False


def test_cli_dispatch_inspect_milestone_dashboard(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_milestone_dashboard",
        lambda _config, parent_issue: {
            "command": "inspect-milestone-dashboard",
            "ok": True,
            "read_only": True,
            "parent_issue": {"issue_number": parent_issue},
            "dashboard": {"recommended_next_child_issue": {"issue_number": 295}},
            "safety_gates": {"mutation_allowed": False},
        },
    )
    exit_code = cli.main(["inspect-milestone-dashboard", "--parent-issue", "294"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "inspect-milestone-dashboard"
    assert payload["read_only"] is True
    assert payload["dashboard"]["recommended_next_child_issue"]["issue_number"] == 295


def test_cli_dispatch_generate_child_closeout_script(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "generate_child_closeout_script",
        lambda _config, issue_number: {
            "command": "generate-child-closeout-script",
            "ok": True,
            "read_only": True,
            "target_issue": issue_number,
            "script": "Write-Host 'review'\n",
        },
    )
    exit_code = cli.main(["generate-child-closeout-script", "--issue", "296"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "generate-child-closeout-script"
    assert payload["read_only"] is True
    assert payload["target_issue"] == 296


def test_cli_dispatch_inspect_sequential_run_state(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_sequential_run_state",
        lambda _config, parent_issue, state_path, write_local_state: {
            "command": "inspect-sequential-run-state",
            "ok": True,
            "parent_issue": parent_issue,
            "sequential_run_state_path": str(state_path),
            "local_write": {"performed": write_local_state},
        },
    )
    exit_code = cli.main(["inspect-sequential-run-state", "--parent-issue", "309", "--write-local-state"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "inspect-sequential-run-state"
    assert payload["parent_issue"] == 309
    assert payload["local_write"]["performed"] is True


def test_cli_dispatch_inspect_child_execution_gates(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_child_execution_gates",
        lambda _config, issue_number, parent_issue: {
            "command": "inspect-child-execution-gates",
            "ok": True,
            "issue": {"number": issue_number},
            "parent_issue": parent_issue,
            "gate_status": {"blocked": False},
        },
    )
    exit_code = cli.main(["inspect-child-execution-gates", "--issue", "312", "--parent-issue", "309"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "inspect-child-execution-gates"
    assert payload["issue"]["number"] == 312
    assert payload["parent_issue"] == 309


def test_cli_dispatch_generate_evidence_comment_template(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "generate_evidence_comment_template",
        lambda _config, issue_number: {
            "command": "generate-evidence-comment-template",
            "ok": True,
            "read_only": True,
            "target_issue": {"number": issue_number},
            "template": "### Issue-Specific Evidence Mapping\n",
        },
    )
    exit_code = cli.main(["generate-evidence-comment-template", "--issue", "297"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["command"] == "generate-evidence-comment-template"
    assert payload["read_only"] is True
    assert payload["target_issue"]["number"] == 297
