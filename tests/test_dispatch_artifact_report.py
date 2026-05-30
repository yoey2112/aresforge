import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_artifact_report import inspect_dispatch_artifacts


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


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_empty_artifact_directory_is_handled_safely(tmp_path: Path) -> None:
    config = _config(tmp_path)

    payload = _payload(inspect_dispatch_artifacts(config))

    assert payload["ok"] is True
    assert payload["artifact_count"] == 0
    assert payload["artifacts"] == []
    assert payload["local_only"] is True
    assert payload["read_only"] is True
    assert payload["execution_allowed"] is False
    assert payload["missing_locations"]


def test_existing_artifact_is_discovered_and_linked_to_item_id(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = config.artifact_root / "codex_prompt_dispatch" / "generated" / "m98-codex-artifact.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("Manual/operator-gated prompt only.\n", encoding="utf-8")

    payload = _payload(inspect_dispatch_artifacts(config))

    assert payload["artifact_count"] == 1
    artifact = payload["artifacts"][0]  # type: ignore[index]
    assert artifact["artifact_type"] == "codex_prompt_dispatch"
    assert artifact["item_id"] == "m98-codex-artifact"
    assert artifact["dispatch_lane"] == "codex_prompt_artifact"
    assert artifact["file_path"] == str(artifact_path.resolve())
    assert artifact["approval_gate_status"] == "missing"
    assert artifact["execution_allowed"] is False


def test_approval_gate_status_is_joined_where_available(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = config.artifact_root / "documentation_agent" / "dry_runs" / "m100-docs.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("Dry-run review only.\n", encoding="utf-8")
    approval_path = tmp_path / ".aresforge" / "dispatch_approval_gates.json"
    approval_path.parent.mkdir(parents=True)
    approval_path.write_text(
        json.dumps(
            {
                "schema_version": "m101.1",
                "approval_gates": [
                    {
                        "approval_id": "approval-docs",
                        "item_id": "m100-docs",
                        "artifact_type": "documentation_agent_dry_run",
                        "artifact_path": str(artifact_path.resolve()),
                        "dispatch_lane": "documentation_agent_dry_run",
                        "status": "approved_for_manual_handoff",
                        "updated_at": "2026-05-30T00:00:00+00:00",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = _payload(inspect_dispatch_artifacts(config))
    artifact = payload["artifacts"][0]  # type: ignore[index]

    assert artifact["approval_gate_status"] == "approved_for_manual_handoff"
    assert artifact["approval_id"] == "approval-docs"
    assert "manual handoff" in artifact["next_safe_action"]


def test_json_output_contains_stable_report_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = config.artifact_root / "local_llm_advisory" / "dry_runs" / "m99.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text('{"dry_run": true}\n', encoding="utf-8")

    result = inspect_dispatch_artifacts(config, project_id="aresforge", output_format="json")
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["report_type"] == "dispatch_artifact_index"
    assert parsed["project_id"] == "aresforge"
    assert parsed["artifact_count"] == 1
    assert parsed["local_only"] is True
    assert parsed["read_only"] is True
    assert parsed["execution_allowed"] is False
    assert parsed["artifacts"][0]["item_id"] == "m99"
    assert parsed["artifacts"][0]["artifact_id"].startswith("dispatch-artifact-")


def test_readable_output_lists_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    artifact_path = config.artifact_root / "codex_prompt_dispatch" / "generated" / "m98.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("Prompt artifact.\n", encoding="utf-8")

    result = inspect_dispatch_artifacts(config)

    assert result["ok"] is True
    assert "# Dispatch Artifact Index" in result["stdout"]
    assert "codex_prompt_dispatch" in result["stdout"]
    assert "execution_allowed: False" in result["stdout"]
