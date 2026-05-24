from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_project_factory_workflow_doc_contract() -> None:
    workflow_path = REPO_ROOT / "docs/architecture/PROJECT_FACTORY_WORKFLOW.md"
    assert workflow_path.exists()

    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert "Canonical AresForge Build Pipeline" in workflow_text
    assert "New Project Lifecycle" in workflow_text
    assert "Add Feature Lifecycle" in workflow_text
    assert "Multi-Project Orchestration" in workflow_text
    assert "Safety Model" in workflow_text
    assert "M47" in workflow_text
    assert "M55" in workflow_text


def test_roadmap_contains_m47_to_m55() -> None:
    roadmap_text = _read("docs/roadmap/ROADMAP.md")
    for milestone in range(47, 56):
        assert f"M{milestone}" in roadmap_text


def test_build_state_references_workflow_doc() -> None:
    build_state_text = _read("docs/context/BUILD_STATE.md")
    assert "PROJECT_FACTORY_WORKFLOW.md" in build_state_text


def test_agent_context_references_workflow_doc() -> None:
    agent_context_text = _read("docs/context/AGENT_CONTEXT.md")
    assert "PROJECT_FACTORY_WORKFLOW.md" in agent_context_text
