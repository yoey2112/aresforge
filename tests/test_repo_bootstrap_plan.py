from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import repo_bootstrap_plan


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


def test_plan_repo_bootstrap_generates_default_repo_plan(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {
                    "repository_slug": "yoey2112/aresforge",
                    "is_default": True,
                    "local_path": str(tmp_path),
                    "project_key": "project-aresforge",
                    "repo_role": "platform_self_managed",
                    "warnings": [],
                    "disabled": False,
                    "archived": False,
                }
            ],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"available": True, "missing": []},
            "optional_platform_labels": {"available": True, "missing": ["aresforge-generated"]},
            "automation_trigger_labels": {"available": True, "missing": ["aresforge-automerge"]},
            "milestone_naming_status": {
                "available": True,
                "missing_platform_milestones": ["M2 - Local Automation Foundation"],
                "unknown_platform_like_milestones": [],
                "project_specific_milestones": ["Backlog - Product"],
            },
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {
            "area_evaluation": [
                {
                    "area": "pr_linking_conventions",
                    "requirement_level": "recommended",
                    "status": "advisory",
                    "summary": "PR linking should be explicit.",
                }
            ]
        },
    )

    payload = repo_bootstrap_plan.plan_repo_bootstrap(config)

    assert payload["ok"] is True
    assert payload["plan_only"] is True
    assert payload["setup_performed"] is False
    assert payload["repository_count"] == 1
    repo_plan = payload["repositories"][0]
    assert repo_plan["repository_slug"] == "yoey2112/aresforge"
    assert any(
        action["title"] == "Create automation trigger label aresforge-automerge"
        for action in repo_plan["actions"]
    )
    assert any(
        action["title"] == "Create canonical milestone M2 - Local Automation Foundation"
        for action in repo_plan["actions"]
    )
    assert any(
        action["title"] == "Document project-specific milestone mapping"
        for action in repo_plan["actions"]
    )


def test_plan_repo_bootstrap_handles_disabled_and_archived(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        repo_bootstrap_plan,
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
        repo_bootstrap_plan,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"available": True, "missing": []},
            "optional_platform_labels": {"available": True, "missing": []},
            "automation_trigger_labels": {"available": True, "missing": []},
            "milestone_naming_status": {
                "available": True,
                "missing_platform_milestones": [],
                "unknown_platform_like_milestones": [],
                "project_specific_milestones": [],
            },
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"area_evaluation": []},
    )

    payload = repo_bootstrap_plan.plan_repo_bootstrap(config)

    assert payload["repository_count"] == 2
    assert any(
        action["title"] == "Repository is disabled"
        for action in payload["repositories"][0]["actions"]
    )
    assert any(
        action["title"] == "Repository is archived"
        for action in payload["repositories"][1]["actions"]
    )


def test_plan_repo_bootstrap_degrades_when_data_unavailable(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    missing_repo = tmp_path / "missing"

    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {
                    "repository_slug": "example/degraded",
                    "local_path": str(missing_repo),
                    "warnings": ["registry warning"],
                    "disabled": False,
                    "archived": False,
                }
            ],
            "warnings": ["global registry warning"],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": None,
            "required_platform_labels": {"available": False, "missing": []},
            "optional_platform_labels": {"available": False, "missing": []},
            "automation_trigger_labels": {"available": False, "missing": []},
            "milestone_naming_status": {"available": False},
            "warnings": ["gh command unavailable"],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {
            "area_evaluation": [
                {
                    "area": "documentation_expectations",
                    "requirement_level": "required",
                    "status": "unavailable",
                    "summary": "Documentation posture unavailable.",
                }
            ]
        },
    )

    payload = repo_bootstrap_plan.plan_repo_bootstrap(config)

    repo_plan = payload["repositories"][0]
    assert any("Local path is registered but not available on disk." in warning for warning in repo_plan["warnings"])
    assert any(action["category"] == "required" for action in repo_plan["actions"])
    assert any("global registry warning" in warning for warning in payload["warnings"])


def test_plan_repo_bootstrap_includes_per_repository_actions_for_default_and_fixture(
    monkeypatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    missing_repo = "C:/Projects/aresforge-demo-managed-repo"
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_managed_repos",
        lambda _cfg: {
            "managed_repositories": [
                {
                    "repository_slug": "yoey2112/aresforge",
                    "is_default": True,
                    "local_path": str(tmp_path),
                    "project_key": "project-aresforge",
                    "repo_role": "platform_self_managed",
                    "disabled": False,
                    "archived": False,
                },
                {
                    "repository_slug": "yoey2112/aresforge-demo-managed-repo",
                    "is_default": False,
                    "local_path": missing_repo,
                    "project_key": "project-aresforge-demo",
                    "repo_role": "demo_managed_repository",
                    "disabled": False,
                    "archived": False,
                },
            ],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"available": True, "missing": []},
            "optional_platform_labels": {"available": True, "missing": []},
            "automation_trigger_labels": {"available": True, "missing": []},
            "milestone_naming_status": {
                "available": True,
                "missing_platform_milestones": [],
                "unknown_platform_like_milestones": [],
                "project_specific_milestones": [],
            },
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        repo_bootstrap_plan,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"area_evaluation": []},
    )

    payload = repo_bootstrap_plan.plan_repo_bootstrap(config)
    assert payload["repository_count"] == 2
    assert all(isinstance(repo["actions"], list) for repo in payload["repositories"])
    fixture = next(
        repo for repo in payload["repositories"] if repo["repository_slug"] == "yoey2112/aresforge-demo-managed-repo"
    )
    assert any(action["title"] == "Confirm local path alignment" for action in fixture["actions"])
