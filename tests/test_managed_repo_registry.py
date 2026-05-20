from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import managed_repo_registry


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


def test_inspect_managed_repos_includes_default_repo_first(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"missing": []},
            "automation_trigger_labels": {"missing": []},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 0}},
    )

    payload = managed_repo_registry.inspect_managed_repos(config)

    assert payload["ok"] is True
    assert payload["managed_repository_count"] == 1
    first = payload["managed_repositories"][0]
    assert first["repository_slug"] == "yoey2112/aresforge"
    assert first["is_default"] is True
    assert first["bootstrap_status"] == "ready_read_only"
    assert first["automation_status"] == "ready_read_only"


def test_inspect_managed_repos_merges_optional_registry_entries(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    registry_path = tmp_path / "config" / "managed_repositories.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """
{
  "managed_repositories": [
    {
      "repository_slug": "yoey2112/aresforge",
      "project_key": "project-aresforge",
      "repo_role": "platform_self_managed",
      "governance_profile": "aresforge-default"
    },
    {
      "repository_slug": "example-org/demo-repo",
      "project_key": "project-demo",
      "repo_role": "managed_external",
      "default_branch": "main",
      "documentation_roots": ["docs/"],
      "artifact_roots": ["artifacts/evidence/generated/"],
      "allowed_automation_capabilities": ["read_only_inspection"],
      "disabled": true,
      "archived": false
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"missing": []},
            "automation_trigger_labels": {"missing": []},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 1}},
    )

    payload = managed_repo_registry.inspect_managed_repos(config)

    assert payload["managed_repository_count"] == 2
    assert payload["managed_repositories"][0]["repository_slug"] == "yoey2112/aresforge"
    assert payload["managed_repositories"][1]["repository_slug"] == "example-org/demo-repo"
    assert payload["managed_repositories"][1]["project_key"] == "project-demo"
    assert payload["managed_repositories"][1]["disabled"] is True
    assert payload["managed_repositories"][1]["bootstrap_status"] == "degraded"


def test_inspect_managed_repos_preserves_fixture_status_and_single_default(monkeypatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    registry_path = tmp_path / "config" / "managed_repositories.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """
{
  "managed_repositories": [
    {
      "repository_slug": "yoey2112/aresforge-demo-managed-repo",
      "project_key": "project-aresforge-demo",
      "repo_role": "demo_managed_repository",
      "local_path": "C:/Projects/aresforge-demo-managed-repo",
      "default_branch": "main",
      "governance_profile": "aresforge-default",
      "automation_status": "fixture_read_only",
      "bootstrap_status": "fixture_only",
      "allowed_automation_capabilities": ["human_triggered_validation", "read_only_inspection"],
      "disabled": false,
      "archived": false
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_governance",
        lambda _cfg: {
            "default_branch": "main",
            "required_platform_labels": {"missing": []},
            "automation_trigger_labels": {"missing": []},
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        managed_repo_registry,
        "inspect_repo_bootstrap_contract",
        lambda _cfg: {"summary": {"required_attention_needed": 0, "unavailable": 0}},
    )

    payload = managed_repo_registry.inspect_managed_repos(config)
    defaults = [row for row in payload["managed_repositories"] if row["is_default"]]
    fixture = next(
        row for row in payload["managed_repositories"] if row["repository_slug"] == "yoey2112/aresforge-demo-managed-repo"
    )

    assert len(defaults) == 1
    assert defaults[0]["repository_slug"] == "yoey2112/aresforge"
    assert fixture["automation_status"] == "fixture_read_only"
    assert fixture["bootstrap_status"] == "fixture_only"
    assert fixture["local_path_exists"] is False
