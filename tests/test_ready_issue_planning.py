import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator.ready_issue_intake import READY_TRIGGER_LABEL
from aresforge.operator.ready_issue_planning import plan_ready_issue
from aresforge.operator import ready_issue_intake


def make_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts" / "generated",
        evidence_dir=tmp_path / "artifacts" / "evidence" / "generated",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex_handoffs" / "generated",
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def _issue_payload(*, number: int, title: str, labels: list[str], body: str = "") -> dict[str, object]:
    return {
        "number": number,
        "title": title,
        "state": "OPEN",
        "url": f"https://github.com/example/{number}",
        "labels": [{"name": label} for label in labels],
        "createdAt": "2026-05-20T00:00:00Z",
        "updatedAt": "2026-05-20T01:00:00Z",
        "author": {"login": "yoey2112"},
        "assignees": [],
        "milestone": None,
        "body": body,
    }


def test_plan_ready_issue_routes_documentation_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=114,
        title="Documentation: update local operator usage",
        labels=[READY_TRIGGER_LABEL, "documentation"],
        body="Update docs and source of truth references.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 114)

    assert payload["selected_primary_agent"] == "documentation-agent"
    assert payload["selected_model_tier"] == "local"
    assert payload["automation_eligible"] is True
    assert payload["blocked"] is False
    assert payload["paid_use_blocked"] is True


def test_plan_ready_issue_routes_implementation_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=115,
        title="Add CLI command for routing",
        labels=[READY_TRIGGER_LABEL, "enhancement"],
        body="Implement new operator command.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 115)

    assert payload["selected_primary_agent"] == "implementation-agent"
    assert payload["selected_model_tier"] == "local"


def test_plan_ready_issue_routes_qa_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=116,
        title="Validation: ensure CLI output is deterministic",
        labels=[READY_TRIGGER_LABEL, "qa"],
        body="Review validation output for deterministic JSON.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 116)

    assert payload["selected_primary_agent"] == "qa-agent"


def test_plan_ready_issue_routes_model_routing_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=117,
        title="Model routing strategy update",
        labels=[READY_TRIGGER_LABEL, "architecture"],
        body="Refine model tier strategy and routing guidance.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 117)

    assert payload["selected_primary_agent"] == "model-routing-agent"
    assert payload["selected_model_tier"] == "copilot"


def test_plan_ready_issue_blocks_unflagged_issue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=118,
        title="Add operator command",
        labels=["enhancement"],
        body="Missing ready label.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 118)

    assert payload["blocked"] is True
    assert payload["automation_eligible"] is False
    assert payload["blocked_reason"] == "missing_ready_label:aresforge-ready"


def test_plan_ready_issue_blocks_protected_issue(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = plan_ready_issue(config, 39)

    assert payload["blocked"] is True
    assert payload["blocked_reason"] == "protected_issue"


def test_plan_ready_issue_is_deterministic_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=119,
        title="Documentation sync update",
        labels=[READY_TRIGGER_LABEL, "documentation-sync"],
        body="Sync docs.",
    )

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", lambda _args: (0, json.dumps(raw_issue), ""))

    payload = plan_ready_issue(config, 119)

    assert json.loads(json.dumps(payload)) == payload


def test_plan_ready_issue_uses_read_only_issue_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = _issue_payload(
        number=120,
        title="Implementation work",
        labels=[READY_TRIGGER_LABEL],
        body="Implement change.",
    )
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        calls.append(args)
        return 0, json.dumps(raw_issue), ""

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", fake_run)

    payload = plan_ready_issue(config, 120)

    assert payload["issue_number"] == 120
    assert calls
    assert calls[0][:2] == ["issue", "view"]
