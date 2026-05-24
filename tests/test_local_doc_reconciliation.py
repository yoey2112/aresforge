import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_doc_reconciliation import generate_doc_reconciliation_plan


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


def _write_minimum_docs(repo_root: Path) -> None:
    (repo_root / "docs/context").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/roadmap").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/architecture").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs/operator").mkdir(parents=True, exist_ok=True)

    (repo_root / "docs/context/BUILD_STATE.md").write_text(
        "# Build State\n\n## Current Phase\n\nM27 local project state ledger implementation and documentation.\n",
        encoding="utf-8",
    )
    (repo_root / "docs/context/AGENT_CONTEXT.md").write_text("# Agent\n", encoding="utf-8")
    (repo_root / "docs/roadmap/ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (repo_root / "docs/architecture/RUNNABLE_SKELETON.md").write_text("# Runnable\n", encoding="utf-8")
    (repo_root / "docs/operator/LOCAL_OPERATOR_USAGE.md").write_text("# Local usage\n", encoding="utf-8")


def test_doc_reconciliation_detects_missing_docs(tmp_path: Path) -> None:
    _write_minimum_docs(tmp_path)
    (tmp_path / "docs/operator/LOCAL_OPERATOR_USAGE.md").unlink()
    payload = generate_doc_reconciliation_plan(_config(tmp_path), output_format="json")

    assert payload["ok"] is True
    plan = payload["payload"]
    assert "docs/operator/LOCAL_OPERATOR_USAGE.md" in plan["missing_docs"]
    assert any("missing" in item.lower() for item in plan["stale_or_missing_sections"])


def test_doc_reconciliation_generates_recommendations_from_state_and_docs(tmp_path: Path) -> None:
    _write_minimum_docs(tmp_path)
    (tmp_path / "src/aresforge").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/aresforge/cli.py").write_text(
        'subparsers.add_parser("generate-handoff-package")\nsubparsers.add_parser("plan-doc-reconciliation")\n',
        encoding="utf-8",
    )
    state_path = tmp_path / ".aresforge" / "state"
    state_path.mkdir(parents=True, exist_ok=True)
    (state_path / "project_state.json").write_text(
        json.dumps(
            {
                "current_milestone": "M28",
                "current_phase": "Implementation",
                "documentation_status": "in_progress",
            }
        ),
        encoding="utf-8",
    )

    payload = generate_doc_reconciliation_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert any("M28" in item for item in plan["recommended_doc_updates"])
    assert any("M28" in item for item in plan["stale_or_missing_sections"])


def test_doc_reconciliation_recommends_docs_review_when_sync_plan_exists(tmp_path: Path) -> None:
    _write_minimum_docs(tmp_path)
    sync_plan = tmp_path / "artifacts" / "github-sync" / "plan.md"
    sync_plan.parent.mkdir(parents=True, exist_ok=True)
    sync_plan.write_text("# sync plan", encoding="utf-8")

    payload = generate_doc_reconciliation_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert any("sync plan" in item.lower() for item in plan["recommended_doc_updates"])
