import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_handoff_package import generate_handoff_package
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)
from aresforge.operator.local_project_state import init_project_state, update_project_state
from aresforge.operator.local_project_queue import init_project_queue, add_queue_item
from aresforge.operator.local_agent_profiles import init_agent_profiles, register_agent_profile


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
        github_owner="local",
        github_repo="aresforge",
    )


def _write_source_docs(repo_root: Path) -> None:
    (repo_root / "docs/context").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/roadmap").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/architecture").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/operator").mkdir(parents=True, exist_ok=True)

    (repo_root / "docs/context/BUILD_STATE.md").write_text(
        "# Build State\n\n## Current Phase\n\nM25 phase.\n\n## Current Goal\n\nComplete reconciliation.\n\n## Known Limitations\n\n- warning one\n",
        encoding="utf-8",
    )
    (repo_root / "docs/context/AGENT_CONTEXT.md").write_text(
        "# Agent Context\n\n## Known Limitations\n\n- warning two\n",
        encoding="utf-8",
    )
    (repo_root / "docs/roadmap/ROADMAP.md").write_text(
        "# Roadmap\n\n### M25 - Automatic Canonical Marker Emission Workflow\n\nDelivered M25 outcomes:\n\n- capability A\n- capability B\n",
        encoding="utf-8",
    )
    (repo_root / "docs/architecture/RUNNABLE_SKELETON.md").write_text("# Runnable\n", encoding="utf-8")
    (repo_root / "docs/operator/LOCAL_OPERATOR_USAGE.md").write_text("# Local usage\n", encoding="utf-8")


def test_generate_handoff_package_stdout_markdown(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)

    def fake_run(command, **_kwargs):
        key = " ".join(command)
        outputs = {
            "git branch --show-current": "main\n",
            "git rev-parse HEAD": "abc123\n",
            "git status --short": " M docs/context/BUILD_STATE.md\n",
            "git log -n 10 --oneline": "abc123 first\n",
        }
        return subprocess.CompletedProcess(command, 0, stdout=outputs.get(key, ""), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    payload = generate_handoff_package(_config(tmp_path), output_format="markdown")
    assert payload["ok"] is True
    assert payload["wrote_output_file"] is False
    assert payload["format"] == "markdown"
    assert "# AresForge Local Handoff Package" in payload["stdout"]


def test_generate_handoff_package_writes_json_and_refuses_overwrite(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="main\n" if "branch" in command else "x\n", stderr=""),
    )
    output = tmp_path / "handoff" / "package.json"
    first = generate_handoff_package(_config(tmp_path), output=output, output_format="json")
    assert first["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["title"] == "AresForge Local Handoff Package"

    second = generate_handoff_package(_config(tmp_path), output=output, output_format="json")
    assert second["ok"] is False
    assert second["error"] == "output_exists"


def test_generate_handoff_package_force_overwrite_and_missing_docs_warning(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "docs/context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/context/BUILD_STATE.md").write_text("# Build State\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="x\n", stderr=""),
    )
    output = tmp_path / "handoff.md"
    output.write_text("old", encoding="utf-8")
    payload = generate_handoff_package(_config(tmp_path), output=output, force=True)
    assert payload["ok"] is True
    assert any("Missing source-of-truth doc" in warning for warning in payload["warnings"])


def test_generate_handoff_package_includes_project_state_summary(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    config = _config(tmp_path)
    assert init_project_state(config)["ok"] is True
    assert update_project_state(config, current_milestone="M27", current_phase="Implementation")["ok"] is True
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="x\n", stderr=""),
    )
    payload = generate_handoff_package(config, output_format="json")
    assert payload["ok"] is True
    assert payload["payload"]["project_state_summary"]["current_milestone"] == "M27"
    assert payload["payload"]["active_local_milestone"] == "M27"


def test_generate_handoff_package_warns_when_project_state_missing(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="x\n", stderr=""),
    )
    payload = generate_handoff_package(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    assert any("Local project state ledger not found" in warning for warning in payload["payload"]["warnings"])


def test_generate_handoff_package_includes_latest_doc_reconciliation_plan(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    plan_path = tmp_path / "artifacts" / "doc-reconciliation" / "latest.md"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("# plan\n", encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="x\n", stderr=""),
    )
    payload = generate_handoff_package(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    latest = payload["payload"]["latest_doc_reconciliation_plan"]
    assert isinstance(latest, dict)
    assert latest["path"].endswith("artifacts\\doc-reconciliation\\latest.md")


def test_generate_handoff_package_includes_latest_github_sync_plan(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    plan_path = tmp_path / "artifacts" / "github-sync" / "latest.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text('{"ok":true}', encoding="utf-8")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout="x\n", stderr=""),
    )
    payload = generate_handoff_package(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    latest = payload["payload"]["latest_github_sync_plan"]
    assert isinstance(latest, dict)
    assert latest["path"].endswith("artifacts\\github-sync\\latest.json")


def test_generate_handoff_package_includes_managed_project_registry_summary(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    config = _config(tmp_path)
    assert init_managed_project_registry(config)['ok'] is True
    assert (
        register_managed_project(
            config,
            project_id='aresforge-main',
            name='AresForge',
            root_path=str(tmp_path),
        )['ok']
        is True
    )
    assert (
        register_managed_repo(
            config,
            project_id='aresforge-main',
            repo_id='docs',
            name='Docs Repo',
            path=str(tmp_path / 'docs'),
            role='docs',
            status='active',
        )['ok']
        is True
    )
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout='x\n', stderr=''),
    )
    payload = generate_handoff_package(config, output_format='json')
    assert payload['ok'] is True
    summary = payload['payload']['managed_project_registry_summary']
    assert isinstance(summary, dict)
    assert summary['project_count'] == 1
    assert summary['repo_count'] == 1


def test_generate_handoff_package_includes_project_queue_summary(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    config = _config(tmp_path)
    assert init_project_queue(config)['ok'] is True
    assert (
        add_queue_item(
            config,
            item_id='m33-1',
            project_id='p1',
            repo_id='r1',
            title='Track queue integration',
            status='ready',
        )['ok']
        is True
    )
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout='x\n', stderr=''),
    )
    payload = generate_handoff_package(config, output_format='json')
    assert payload['ok'] is True
    summary = payload['payload']['project_queue_summary']
    assert isinstance(summary, dict)
    assert summary['item_count'] == 1
    assert summary['status_counts']['ready'] == 1


def test_generate_handoff_package_includes_agent_profiles_summary(monkeypatch, tmp_path: Path) -> None:
    _write_source_docs(tmp_path)
    config = _config(tmp_path)
    assert init_agent_profiles(config)['ok'] is True
    assert (
        register_agent_profile(
            config,
            agent_id='architect-a',
            name='Architect A',
            role='architect',
            execution_mode='human',
            status='active',
        )['ok']
        is True
    )
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout='x\n', stderr=''),
    )
    payload = generate_handoff_package(config, output_format='json')
    assert payload['ok'] is True
    summary = payload['payload']['agent_profiles_summary']
    assert isinstance(summary, dict)
    assert summary['agent_count'] == 1
