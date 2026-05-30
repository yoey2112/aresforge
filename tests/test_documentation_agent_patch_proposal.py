import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.documentation_agent_patch_proposal import generate_documentation_agent_patch_proposal
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def _write_docs(tmp_path: Path) -> None:
    for path in (
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
        "docs/architecture/DOCUMENTATION_AGENT_CONTRACT.md",
        "docs/architecture/RUNNABLE_SKELETON.md",
    ):
        full = tmp_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("# Source Doc\n\nExisting text.\n", encoding="utf-8")


def _seed_item(config: AppConfig, *, item_id: str = "m116-doc-proposal") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M116 Documentation Agent Patch Proposal Generator",
        description="Generate documentation patch proposals without applying patches.",
        status="ready",
        priority="high",
        item_type="documentation",
        tags=["milestone:m116", "documentation-agent", "local-only"],
        notes="Acceptance criteria: proposal only; patch_application_allowed=false.",
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_generates_documentation_patch_proposal_and_patch_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_docs(tmp_path)
    _seed_item(config)

    payload = _payload(generate_documentation_agent_patch_proposal(config, item_id="m116-doc-proposal"))

    assert payload["artifact_type"] == "documentation_agent_patch_proposal"
    assert payload["generated"] is True
    assert payload["blocked"] is False
    assert payload["item_id"] == "m116-doc-proposal"
    assert payload["milestone"] == "m116"
    assert payload["source_documents_reviewed"]
    assert payload["detected_doc_gaps"]
    assert payload["proposed_doc_changes"]
    assert Path(payload["proposed_patch_path"]).exists()
    assert payload["approval_required"] is True
    assert payload["patch_application_allowed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_blocks_missing_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_docs(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = _payload(generate_documentation_agent_patch_proposal(config, item_id="missing", output_format="json"))

    assert payload["generated"] is False
    assert payload["blocked"] is True
    assert "Queue item was not found." in payload["blocked_reasons"]
    assert payload["patch_application_allowed"] is False


def test_json_stdout_contains_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_docs(tmp_path)
    _seed_item(config)

    result = generate_documentation_agent_patch_proposal(
        config,
        item_id="m116-doc-proposal",
        output_format="json",
        include_roadmap=True,
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["artifact_type"] == "documentation_agent_patch_proposal"
    assert parsed["generated"] is True
    assert parsed["source_documents_reviewed"]
    assert "docs/roadmap/ROADMAP.md" in parsed["source_documents_reviewed"]
    assert parsed["approval_required"] is True
    assert parsed["patch_application_allowed"] is False
    assert parsed["execution_allowed"] is False


def test_output_path_and_no_overwrite_behavior(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_docs(tmp_path)
    _seed_item(config)
    output = tmp_path / "artifacts" / "documentation_agent" / "patch_proposals" / "m116.json"

    first = _payload(generate_documentation_agent_patch_proposal(config, item_id="m116-doc-proposal", output=output))
    duplicate = _payload(generate_documentation_agent_patch_proposal(config, item_id="m116-doc-proposal", output=output))
    forced = _payload(
        generate_documentation_agent_patch_proposal(config, item_id="m116-doc-proposal", output=output, force=True)
    )

    assert first["generated"] is True
    assert first["output_path"] == str(output)
    assert Path(first["proposed_patch_path"]).exists()
    assert duplicate["generated"] is False
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["generated"] is True


def test_include_flags_limit_reviewed_source_documents(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_docs(tmp_path)
    _seed_item(config)

    payload = _payload(
        generate_documentation_agent_patch_proposal(
            config,
            item_id="m116-doc-proposal",
            include_operator_docs=True,
        )
    )

    assert "docs/operator/LOCAL_OPERATOR_USAGE.md" in payload["source_documents_reviewed"]
    assert "docs/roadmap/ROADMAP.md" not in payload["source_documents_reviewed"]
    assert "docs/context/BUILD_STATE.md" not in payload["source_documents_reviewed"]
