import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import ready_issue_intake
from aresforge.operator.ready_issue_intake import (
    PROTECTED_ISSUE_NUMBER,
    READY_TRIGGER_LABEL,
)


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


def test_list_ready_issues_filters_protected_issue_and_sorts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    raw_items = [
        {
            "number": 116,
            "title": "Ready intake",
            "url": "https://github.com/example/116",
            "labels": [{"name": READY_TRIGGER_LABEL}, {"name": "phase: m2"}],
            "createdAt": "2026-05-20T00:00:00Z",
            "updatedAt": "2026-05-20T01:00:00Z",
            "author": {"login": "yoey2112"},
        },
        {
            "number": PROTECTED_ISSUE_NUMBER,
            "title": "Protected",
            "url": "https://github.com/example/39",
            "labels": [{"name": READY_TRIGGER_LABEL}],
            "createdAt": "2026-05-19T00:00:00Z",
            "updatedAt": "2026-05-19T01:00:00Z",
            "author": {"login": "yoey2112"},
        },
        {
            "number": 114,
            "title": "Another",
            "url": "https://github.com/example/114",
            "labels": [{"name": READY_TRIGGER_LABEL}, {"name": "agent: devops"}],
            "createdAt": "2026-05-18T00:00:00Z",
            "updatedAt": "2026-05-18T01:00:00Z",
            "author": {"login": "octocat"},
        },
    ]

    def fake_run(_args: list[str]) -> tuple[int, str, str]:
        return 0, json.dumps(raw_items), ""

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", fake_run)

    payload = ready_issue_intake.list_ready_issues(config)

    assert payload["ok"] is True
    assert [issue["number"] for issue in payload["issues"]] == [114, 116]
    assert payload["excluded_issues"] == [{"number": PROTECTED_ISSUE_NUMBER, "reason": "protected_issue"}]
    assert payload["ready_label"] == READY_TRIGGER_LABEL
    assert json.loads(json.dumps(payload)) == payload


def test_list_ready_issues_skips_items_without_ready_label(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_items = [
        {
            "number": 120,
            "title": "Missing label",
            "url": "https://github.com/example/120",
            "labels": [{"name": "phase: m2"}],
            "createdAt": "2026-05-20T00:00:00Z",
            "updatedAt": "2026-05-20T01:00:00Z",
            "author": {"login": "yoey2112"},
        }
    ]

    def fake_run(_args: list[str]) -> tuple[int, str, str]:
        return 0, json.dumps(raw_items), ""

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", fake_run)

    payload = ready_issue_intake.list_ready_issues(config)

    assert payload["issues"] == []
    assert payload["issue_count"] == 0


def test_inspect_ready_issue_rejects_protected_issue(tmp_path: Path) -> None:
    config = make_config(tmp_path)

    payload = ready_issue_intake.inspect_ready_issue(config, PROTECTED_ISSUE_NUMBER)

    assert payload["ok"] is False
    assert payload["error"] == "protected_issue"


def test_inspect_ready_issue_requires_ready_label(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = {
        "number": 114,
        "title": "Ready intake",
        "state": "OPEN",
        "url": "https://github.com/example/114",
        "labels": [{"name": "phase: m2"}],
        "createdAt": "2026-05-20T00:00:00Z",
        "updatedAt": "2026-05-20T01:00:00Z",
        "author": {"login": "yoey2112"},
        "assignees": [],
        "milestone": None,
        "body": "Details",
    }

    def fake_run(_args: list[str]) -> tuple[int, str, str]:
        return 0, json.dumps(raw_issue), ""

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", fake_run)

    payload = ready_issue_intake.inspect_ready_issue(config, 114)

    assert payload["ok"] is False
    assert payload["error"] == "issue_not_ready"


def test_inspect_ready_issue_returns_issue_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    raw_issue = {
        "number": 114,
        "title": "Ready intake",
        "state": "OPEN",
        "url": "https://github.com/example/114",
        "labels": [{"name": READY_TRIGGER_LABEL}, {"name": "agent: devops"}],
        "createdAt": "2026-05-20T00:00:00Z",
        "updatedAt": "2026-05-20T01:00:00Z",
        "author": {"login": "yoey2112"},
        "assignees": [{"login": "octocat"}, {"login": "yoey2112"}],
        "milestone": {"number": 2, "title": "M2", "url": "https://github.com/example/m2"},
        "body": "Details",
    }

    def fake_run(_args: list[str]) -> tuple[int, str, str]:
        return 0, json.dumps(raw_issue), ""

    monkeypatch.setattr(ready_issue_intake, "_run_gh_command", fake_run)

    payload = ready_issue_intake.inspect_ready_issue(config, 114)

    assert payload["ok"] is True
    assert payload["issue"]["number"] == 114
    assert READY_TRIGGER_LABEL in payload["issue"]["labels"]
    assert payload["issue"]["assignees"] == ["octocat", "yoey2112"]
    assert payload["issue"]["milestone"]["number"] == 2
    assert json.loads(json.dumps(payload)) == payload
