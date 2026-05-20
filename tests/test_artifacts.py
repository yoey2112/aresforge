from pathlib import Path

from aresforge.artifacts.store import write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.service import (
    render_codex_handoff,
    render_evidence_package,
    render_prompt_package,
)
from aresforge.routing.routes import build_route_plan


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
        prompts_dir=tmp_path / "artifacts" / "prompts",
        evidence_dir=tmp_path / "artifacts" / "evidence",
        codex_handoffs_dir=tmp_path / "artifacts" / "handoffs",
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_generic_bundle_writer(tmp_path: Path) -> None:
    bundle = write_markdown_json_bundle(
        tmp_path, title="Example Prompt", markdown="# Test", payload={"ok": True}
    )
    assert bundle.markdown_path.exists()
    assert bundle.json_path.exists()


def test_prompt_evidence_and_handoff_renderers(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    route_plan = build_route_plan(
        work_item_id="work-123",
        queue_id="queue-implementation",
        agent_id="agent-local-operator",
        model_id="model-ollama-default",
        prompt_package=None,
        route_status="planned",
    )
    prompt = render_prompt_package(
        config=config,
        title="Prompt Title",
        objective="Build the local skeleton.",
        work_item_id="work-123",
        route_plan=route_plan,
        notes="Keep it practical.",
    )
    evidence = render_evidence_package(
        config=config,
        title="Evidence Title",
        work_item_id="work-123",
        files_changed=["src/aresforge/cli.py"],
        validations_run=["python -m pytest"],
        skipped_checks=["Ollama not running"],
        protected_issue_checks=["Issue #39 left unchanged."],
        automation_boundary_confirmation="No autonomous GitHub actions were used.",
    )
    handoff = render_codex_handoff(
        config=config,
        title="Codex Handoff",
        summary="Prepare a review prompt.",
        work_item_id="work-123",
        route_plan=route_plan,
        requested_output="Generate a human-reviewable implementation prompt.",
    )
    assert prompt.markdown_path.exists()
    assert evidence.json_path.exists()
    assert handoff.markdown_path.read_text(encoding="utf-8").startswith("# Codex Handoff")
