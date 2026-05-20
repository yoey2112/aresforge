import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import project_state_summary


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


def _write_doc(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_project_state_summary_parses_clean_repository_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    _write_doc(
        tmp_path / "docs" / "context" / "BUILD_STATE.md",
        "# Build\n\n## Current Phase\n\nM3 - Registry And Routing Deepening\n",
    )
    _write_doc(
        tmp_path / "docs" / "context" / "AGENT_CONTEXT.md",
        "# Agent Context\n",
    )
    _write_doc(
        tmp_path / "docs" / "roadmap" / "ROADMAP.md",
        "# Roadmap\n\n### M3 - Registry And Routing Deepening\nStatus: Active.\n\n"
        "## Planned Milestone Sequence\n\n### M4 - Local Operator Expansion\n",
    )
    _write_doc(tmp_path / "docs" / "operator" / "LOCAL_OPERATOR_USAGE.md", "# Local Operator\n")
    _write_doc(
        tmp_path / "docs" / "operator" / "BATCH_READY_ISSUE_OPERATIONS.md",
        "# Batch\n",
    )
    _write_doc(tmp_path / "docs" / "architecture" / "RUNNABLE_SKELETON.md", "# Skeleton\n")
    _write_doc(
        tmp_path / "docs" / "architecture" / "MODEL_ROUTING_STRATEGY.md",
        "# Routing\n",
    )
    _write_doc(
        tmp_path / "docs" / "architecture" / "ISSUE_LIFECYCLE_AGENT_PIPELINE.md",
        "# Pipeline\n",
    )
    _write_doc(tmp_path / "docs" / "planning" / "FUTURE_FEATURE_IDEAS.md", "# Ideas\n")

    def fake_run(args: list[str], _cwd: Path) -> tuple[bool, int | None, str, str]:
        command = " ".join(args)
        if command == "git branch --show-current":
            return True, 0, "main\n", ""
        if command == "git status --porcelain":
            return True, 0, "", ""
        if command == "git log -1 --pretty=format:%H%x09%s":
            return True, 0, "abc123\tlocal commit\n", ""
        if command == "git log -1 --pretty=format:%H%x09%s origin/main":
            return True, 0, "abc123\torigin commit\n", ""
        if command.startswith("gh issue list"):
            return True, 0, '[{"number":129,"title":"M3 planning","url":"https://example/129"}]', ""
        if command.startswith("gh pr list"):
            return True, 0, "[]", ""
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_state_summary, "_run_command", fake_run)

    payload = project_state_summary.project_state_summary(config)

    assert payload["repository"]["current_branch"] == "main"
    assert payload["repository"]["working_tree_clean"] is True
    assert payload["repository"]["latest_local_commit"]["sha"] == "abc123"
    assert payload["repository"]["head_matches_origin_main"] is True
    assert payload["github"]["open_issues_count"] == 1
    assert payload["github"]["open_prs_count"] == 0
    assert payload["milestone"]["current_phase"] == "M3 - Registry And Routing Deepening"
    assert payload["milestone"]["active_milestone"] == "M3 - Registry And Routing Deepening"
    assert payload["milestone"]["next_planned_milestone"] == "M4 - Local Operator Expansion"
    assert payload["warnings"] == []
    assert json.loads(json.dumps(payload)) == payload


def test_project_state_summary_degrades_when_git_and_gh_are_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    _write_doc(
        tmp_path / "docs" / "context" / "BUILD_STATE.md",
        "# Build\n\n## Current Phase\n\nM3 - Registry And Routing Deepening\n",
    )
    _write_doc(tmp_path / "docs" / "context" / "AGENT_CONTEXT.md", "# Agent\n")
    _write_doc(
        tmp_path / "docs" / "roadmap" / "ROADMAP.md",
        "# Roadmap\n\n### M3 - Registry And Routing Deepening\nStatus: Active.\n",
    )

    monkeypatch.setattr(
        project_state_summary,
        "_run_command",
        lambda _args, _cwd: (False, None, "", "command_not_found"),
    )

    payload = project_state_summary.project_state_summary(config)

    assert payload["repository"]["current_branch"] is None
    assert payload["repository"]["working_tree_clean"] is None
    assert payload["repository"]["latest_local_commit"] is None
    assert payload["repository"]["latest_origin_main_commit"] is None
    assert payload["github"]["open_issues_count"] is None
    assert payload["github"]["open_prs_count"] is None
    assert any("git command unavailable" in warning for warning in payload["warnings"])
    assert any("gh command unavailable" in warning for warning in payload["warnings"])
