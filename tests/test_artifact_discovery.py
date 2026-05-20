import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.artifact_discovery import discover_local_artifacts


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


def test_discover_local_artifacts_handles_missing_artifact_root(tmp_path: Path) -> None:
    payload = discover_local_artifacts(make_config(tmp_path))

    assert payload["ok"] is True
    assert payload["artifact_root_exists"] is False
    assert payload["artifact_count"] == 0
    assert payload["artifacts"] == []


def test_discover_local_artifacts_handles_empty_artifact_root(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.artifact_root.mkdir(parents=True)

    payload = discover_local_artifacts(config)

    assert payload["artifact_root_exists"] is True
    assert payload["artifact_count"] == 0
    assert payload["artifacts"] == []


def test_discover_local_artifacts_summarizes_known_generated_artifacts(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    queue_report = config.artifact_root / "inspection_reports" / "generated" / "queue-inspection-report-queue-implementation-implementation.json"
    prompt_package = config.artifact_root / "prompts" / "generated" / "20260520T120000Z-issue-105-prompt.md"
    evidence_package = config.artifact_root / "evidence" / "generated" / "20260520T120001Z-issue-105-evidence.json"
    codex_handoff = config.artifact_root / "codex_handoffs" / "generated" / "20260520T120002Z-issue-105-handoff.md"

    queue_report.parent.mkdir(parents=True)
    prompt_package.parent.mkdir(parents=True)
    evidence_package.parent.mkdir(parents=True)
    codex_handoff.parent.mkdir(parents=True)

    queue_report.write_text("{}", encoding="utf-8")
    prompt_package.write_text("# Prompt", encoding="utf-8")
    evidence_package.write_text("{}", encoding="utf-8")
    codex_handoff.write_text("# Handoff", encoding="utf-8")

    payload = discover_local_artifacts(config)

    assert payload["artifact_count"] == 4
    assert payload["artifacts"] == [
        {
            "artifact_path": "codex_handoffs/generated/20260520T120002Z-issue-105-handoff.md",
            "filename": "20260520T120002Z-issue-105-handoff.md",
            "size_bytes": 9,
            "modified_at": payload["artifacts"][0]["modified_at"],
            "artifact_type": "codex_handoff",
            "command_source_hint": "prepare-codex-handoff",
        },
        {
            "artifact_path": "evidence/generated/20260520T120001Z-issue-105-evidence.json",
            "filename": "20260520T120001Z-issue-105-evidence.json",
            "size_bytes": 2,
            "modified_at": payload["artifacts"][1]["modified_at"],
            "artifact_type": "evidence_package",
            "command_source_hint": "record-evidence-package",
        },
        {
            "artifact_path": "inspection_reports/generated/queue-inspection-report-queue-implementation-implementation.json",
            "filename": "queue-inspection-report-queue-implementation-implementation.json",
            "size_bytes": 2,
            "modified_at": payload["artifacts"][2]["modified_at"],
            "artifact_type": "inspection_report",
            "command_source_hint": "inspect-queue --write-artifact",
        },
        {
            "artifact_path": "prompts/generated/20260520T120000Z-issue-105-prompt.md",
            "filename": "20260520T120000Z-issue-105-prompt.md",
            "size_bytes": 8,
            "modified_at": payload["artifacts"][3]["modified_at"],
            "artifact_type": "prompt_package",
            "command_source_hint": "generate-prompt-package",
        },
    ]


def test_discover_local_artifacts_orders_results_deterministically_by_relative_path(
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    later_path = config.artifact_root / "prompts" / "generated" / "z-last.md"
    earlier_path = config.artifact_root / "prompts" / "generated" / "a-first.md"

    later_path.parent.mkdir(parents=True)
    later_path.write_text("later", encoding="utf-8")
    earlier_path.write_text("first", encoding="utf-8")

    payload = discover_local_artifacts(config)

    assert [artifact["artifact_path"] for artifact in payload["artifacts"]] == [
        "prompts/generated/a-first.md",
        "prompts/generated/z-last.md",
    ]


def test_discover_local_artifacts_payload_is_json_serializable(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    artifact_path = config.artifact_root / "prompts" / "generated" / "artifact.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("content", encoding="utf-8")

    payload = discover_local_artifacts(config)

    assert json.loads(json.dumps(payload)) == payload
