import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import automation_readiness_report
from aresforge.operator import ready_issue_batch
from aresforge.operator.ready_issue_batch import run_ready_issue_batch


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


def _ready_list_payload() -> dict[str, object]:
    return {
        "ok": True,
        "issues": [
            {
                "number": 120,
                "title": "Implementation issue",
                "labels": ["aresforge-ready", "aresforge-automerge"],
            },
            {
                "number": 121,
                "title": "Blocked issue",
                "labels": ["aresforge-ready"],
            },
            {
                "number": 39,
                "title": "Protected audit issue",
                "labels": ["aresforge-ready", "aresforge-automerge"],
            },
        ],
    }


def test_batch_excludes_protected_issue_and_summarizes_multiple_ready_issues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(ready_issue_batch, "list_ready_issues", lambda _config: _ready_list_payload())

    def fake_inspect(_config: AppConfig, issue_number: int) -> dict[str, object]:
        return {
            "ok": True,
            "issue": {
                "number": issue_number,
                "title": f"Issue {issue_number}",
                "labels": ["aresforge-ready", "aresforge-automerge"]
                if issue_number == 120
                else ["aresforge-ready"],
            },
        }

    def fake_plan(_config: AppConfig, issue_number: int) -> dict[str, object]:
        if issue_number == 121:
            return {
                "issue_title": "Blocked issue",
                "blocked": True,
                "blocked_reason": "missing_automerge_label",
                "selected_primary_agent": "implementation-agent",
                "selected_qa_agent": "qa-agent",
                "selected_documentation_agent": "documentation-agent",
                "selected_model_tier": "local",
                "model_routing_reason": "Local-first default for routine scope.",
                "confidence": "medium",
                "recommended_next_command": "python -m aresforge list-ready-issues",
            }
        return {
            "issue_title": "Implementation issue",
            "blocked": False,
            "blocked_reason": None,
            "selected_primary_agent": "implementation-agent",
            "selected_qa_agent": "qa-agent",
            "selected_documentation_agent": "documentation-agent",
            "selected_model_tier": "local",
            "model_routing_reason": "Local-first default for routine scope.",
            "confidence": "medium",
            "recommended_next_command": "python -m aresforge run-ready-issue-pipeline --issue-number 120 --plan-only",
        }

    monkeypatch.setattr(ready_issue_batch, "inspect_ready_issue", fake_inspect)
    monkeypatch.setattr(ready_issue_batch, "plan_ready_issue", fake_plan)

    payload = run_ready_issue_batch(
        config,
        plan_only=True,
        timestamp_override="20260520T190000Z",
    )

    assert payload["ready_issue_count"] == 2
    assert [issue["issue_number"] for issue in payload["issues"]] == [120, 121]
    assert payload["excluded_issues"] == [{"number": 39, "reason": "protected_issue"}]
    assert payload["issues"][0]["closeout_automation_eligible"] is True
    assert payload["issues"][1]["blocked"] is True
    assert payload["issues"][1]["blocked_reasons"] == ["missing_automerge_label"]
    assert json.loads(json.dumps(payload))


def test_batch_handles_empty_ready_issue_set(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(ready_issue_batch, "list_ready_issues", lambda _config: {"ok": True, "issues": []})
    monkeypatch.setattr(
        ready_issue_batch,
        "inspect_ready_issue",
        lambda *_args, **_kwargs: pytest.fail("No issues should be inspected for empty ready set"),
    )

    payload = run_ready_issue_batch(config, plan_only=True, timestamp_override="20260520T191500Z")

    assert payload["ready_issue_count"] == 0
    assert payload["issues"] == []
    assert payload["selected_handoffs"] == []


def test_batch_writes_json_and_markdown_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        ready_issue_batch,
        "list_ready_issues",
        lambda _config: {"ok": True, "issues": [{"number": 120, "title": "Issue", "labels": ["aresforge-ready"]}]},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "inspect_ready_issue",
        lambda _config, _issue_number: {"ok": True, "issue": {"labels": ["aresforge-ready"]}},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "plan_ready_issue",
        lambda _config, _issue_number: {
            "issue_title": "Issue",
            "blocked": False,
            "blocked_reason": None,
            "selected_primary_agent": "implementation-agent",
            "selected_qa_agent": "qa-agent",
            "selected_documentation_agent": "documentation-agent",
            "selected_model_tier": "local",
            "model_routing_reason": "Local-first default for routine scope.",
            "confidence": "medium",
            "recommended_next_command": "python -m aresforge plan-ready-issue --issue-number 120",
        },
    )

    payload = run_ready_issue_batch(config, plan_only=True, timestamp_override="20260520T192500Z")

    json_path = Path(payload["json_path"])
    markdown_path = Path(payload["markdown_path"])
    assert json_path.exists()
    assert markdown_path.exists()
    assert "20260520T192500Z-ready-issue-batch" in json_path.name
    assert "Ready Issue Batch Plan" in markdown_path.read_text(encoding="utf-8")


def test_optional_handoff_generation_for_copilot_or_codex(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        ready_issue_batch,
        "list_ready_issues",
        lambda _config: {"ok": True, "issues": [{"number": 120, "title": "Complex issue", "labels": ["aresforge-ready"]}]},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "inspect_ready_issue",
        lambda _config, _issue_number: {"ok": True, "issue": {"labels": ["aresforge-ready"]}},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "plan_ready_issue",
        lambda _config, _issue_number: {
            "issue_title": "Complex issue",
            "blocked": False,
            "blocked_reason": None,
            "selected_primary_agent": "implementation-agent",
            "selected_qa_agent": "qa-agent",
            "selected_documentation_agent": "documentation-agent",
            "selected_model_tier": "copilot",
            "model_routing_reason": "Complex multi-document scope.",
            "confidence": "high",
            "recommended_next_command": "python -m aresforge prepare-codex-handoff --title \"Issue 120 handoff\" --summary \"Issue 120\" --requested-output \"Prepare output\"",
        },
    )

    payload = run_ready_issue_batch(
        config,
        plan_only=True,
        write_selected_handoffs=True,
        timestamp_override="20260520T193500Z",
    )

    assert len(payload["selected_handoffs"]) == 1
    handoff_path = Path(payload["selected_handoffs"][0]["handoff_json_path"])
    assert handoff_path.exists()


def test_batch_non_mutating_default_does_not_render_handoffs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        ready_issue_batch,
        "list_ready_issues",
        lambda _config: {"ok": True, "issues": [{"number": 120, "title": "Issue", "labels": ["aresforge-ready"]}]},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "inspect_ready_issue",
        lambda _config, _issue_number: {"ok": True, "issue": {"labels": ["aresforge-ready"]}},
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "plan_ready_issue",
        lambda _config, _issue_number: {
            "issue_title": "Issue",
            "blocked": False,
            "blocked_reason": None,
            "selected_primary_agent": "implementation-agent",
            "selected_qa_agent": "qa-agent",
            "selected_documentation_agent": "documentation-agent",
            "selected_model_tier": "codex",
            "model_routing_reason": "Agentic scope.",
            "confidence": "high",
            "recommended_next_command": "python -m aresforge run-ready-issue-pipeline --issue-number 120 --plan-only",
        },
    )
    monkeypatch.setattr(
        ready_issue_batch,
        "render_codex_handoff",
        lambda *_args, **_kwargs: pytest.fail("handoff generation should be opt-in"),
    )

    payload = run_ready_issue_batch(
        config,
        plan_only=True,
        write_selected_handoffs=False,
        timestamp_override="20260520T194500Z",
    )

    assert payload["selected_handoffs"] == []


def test_automation_readiness_report_content(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        automation_readiness_report,
        "list_ready_issues",
        lambda _config: {
            "ok": True,
            "issues": [
                {"number": 120},
                {"number": 121},
            ],
        },
    )

    payload = automation_readiness_report.automation_readiness_report(config)

    assert payload["command"] == "automation-readiness-report"
    assert payload["ready_issue_count"] == 2
    assert payload["protected_issue_handling"]["issue_number"] == 39
    assert payload["required_labels"]["ready_intake"] == "aresforge-ready"
    assert any("run-ready-issue-batch --plan-only" in cmd for cmd in payload["available_automation_commands"])
    assert json.loads(json.dumps(payload)) == payload
