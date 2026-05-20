from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import managed_repo_readiness_report


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


def test_readiness_report_evaluates_default_repository(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {
                    "repository_slug": "yoey2112/aresforge",
                    "is_default": True,
                    "local_path": str(tmp_path),
                    "default_branch": "main",
                    "governance_profile": "aresforge-default",
                    "allowed_automation_capabilities": ["read_only_inspection"],
                    "warnings": [],
                    "disabled": False,
                    "archived": False,
                }
            ],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"available": True, "missing": []},
            "optional_platform_labels": {"available": True, "missing": ["aresforge-generated"]},
            "automation_trigger_labels": {"available": True, "missing": []},
            "milestone_naming_status": {"available": True, "missing_platform_milestones": []},
            "open_issue_readiness_signal": {"signal": "ready_issues_available", "ready_issue_count": 1},
            "open_pr_readiness_signal": {"signal": "no_open_prs_detected", "open_pr_count": 0},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {
            "summary": {"required_attention_needed": 0, "unavailable": 0},
            "area_evaluation": [
                {"area": "documentation_expectations", "status": "satisfied", "available": True, "summary": "ok"},
                {
                    "area": "generated_artifact_conventions",
                    "status": "satisfied",
                    "available": True,
                    "summary": "ok",
                },
                {
                    "area": "governance_profile_expectations",
                    "status": "satisfied",
                    "available": True,
                    "summary": "ok",
                },
                {
                    "area": "validation_evidence_expectations",
                    "status": "satisfied",
                    "available": True,
                    "summary": "ok",
                },
            ],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "_local_git_state",
        lambda _path, _exists: ("main", True, None),
    )

    payload = managed_repo_readiness_report.managed_repo_readiness_report(config)

    assert payload["ok"] is True
    assert payload["repository_count"] == 1
    row = payload["repositories"][0]
    assert row["repository_slug"] == "yoey2112/aresforge"
    assert row["readiness_level"] == "ready"
    assert row["current_branch"] == "main"
    assert row["working_tree_clean"] is True


def test_readiness_report_returns_disabled_and_archived_levels(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {"repository_slug": "example/repo-a", "disabled": True, "archived": False},
                {"repository_slug": "example/repo-b", "disabled": False, "archived": True},
            ],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"available": True, "missing": []},
            "optional_platform_labels": {"available": True, "missing": []},
            "automation_trigger_labels": {"available": True, "missing": []},
            "milestone_naming_status": {"available": True, "missing_platform_milestones": []},
            "open_issue_readiness_signal": {"signal": "no_ready_issues_detected"},
            "open_pr_readiness_signal": {"signal": "no_open_prs_detected"},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 0}, "area_evaluation": []},
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "_local_git_state",
        lambda _path, _exists: (None, None, None),
    )

    payload = managed_repo_readiness_report.managed_repo_readiness_report(config)
    assert payload["repositories"][0]["readiness_level"] == "disabled"
    assert payload["repositories"][1]["readiness_level"] == "archived"


def test_readiness_report_degrades_when_data_unavailable(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    missing_path = tmp_path / "missing-repo"
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {
                    "repository_slug": "example/degraded",
                    "local_path": str(missing_path),
                    "disabled": False,
                    "archived": False,
                    "warnings": ["upstream warning"],
                }
            ],
            "warnings": ["registry warning"],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": None,
            "required_platform_labels": {"available": False, "missing": []},
            "optional_platform_labels": {"available": False, "missing": []},
            "automation_trigger_labels": {"available": False, "missing": []},
            "milestone_naming_status": {"available": False},
            "open_issue_readiness_signal": {"signal": "unavailable"},
            "open_pr_readiness_signal": {"signal": "unavailable"},
            "warnings": ["gh command unavailable"],
        },
    )
    monkeypatch.setattr(
        managed_repo_readiness_report,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 2}, "area_evaluation": []},
    )

    payload = managed_repo_readiness_report.managed_repo_readiness_report(config)

    row = payload["repositories"][0]
    assert row["readiness_level"] == "unavailable"
    assert row["local_path_exists"] is False
    assert any("Local path is registered but not available on disk." in item for item in row["warnings"])
    assert any("registry warning" in item for item in payload["warnings"])
