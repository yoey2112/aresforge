import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.artifact_discovery import (
    _TEXT_PREVIEW_CHAR_LIMIT,
    discover_local_artifacts,
    inspect_local_artifact,
)


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
            "extension": ".md",
            "text_readable": True,
            "text_preview": "# Handoff",
        },
        {
            "artifact_path": "evidence/generated/20260520T120001Z-issue-105-evidence.json",
            "filename": "20260520T120001Z-issue-105-evidence.json",
            "size_bytes": 2,
            "modified_at": payload["artifacts"][1]["modified_at"],
            "artifact_type": "evidence_package",
            "command_source_hint": "record-evidence-package",
            "extension": ".json",
            "text_readable": True,
            "text_preview": "{}",
        },
        {
            "artifact_path": "inspection_reports/generated/queue-inspection-report-queue-implementation-implementation.json",
            "filename": "queue-inspection-report-queue-implementation-implementation.json",
            "size_bytes": 2,
            "modified_at": payload["artifacts"][2]["modified_at"],
            "artifact_type": "inspection_report",
            "command_source_hint": "inspect-queue --write-artifact",
            "extension": ".json",
            "text_readable": True,
            "text_preview": "{}",
        },
        {
            "artifact_path": "prompts/generated/20260520T120000Z-issue-105-prompt.md",
            "filename": "20260520T120000Z-issue-105-prompt.md",
            "size_bytes": 8,
            "modified_at": payload["artifacts"][3]["modified_at"],
            "artifact_type": "prompt_package",
            "command_source_hint": "generate-prompt-package",
            "extension": ".md",
            "text_readable": True,
            "text_preview": "# Prompt",
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


def test_inspect_local_artifact_rejects_empty_path(tmp_path: Path) -> None:
    payload = inspect_local_artifact(make_config(tmp_path), "   ")

    assert payload["ok"] is False
    assert payload["error"] == "artifact_path_empty"


def test_inspect_local_artifact_rejects_unsafe_traversal_path(tmp_path: Path) -> None:
    payload = inspect_local_artifact(make_config(tmp_path), "../secrets.txt")

    assert payload["ok"] is False
    assert payload["error"] == "artifact_path_unsafe"


def test_inspect_local_artifact_rejects_absolute_path_outside_artifact_root(tmp_path: Path) -> None:
    payload = inspect_local_artifact(make_config(tmp_path), "C:\\temp\\artifact.json")

    assert payload["ok"] is False
    assert payload["error"] == "artifact_path_outside_root"


def test_inspect_local_artifact_returns_not_found_for_missing_artifact(tmp_path: Path) -> None:
    payload = inspect_local_artifact(make_config(tmp_path), "prompts/generated/missing.md")

    assert payload["ok"] is False
    assert payload["error"] == "artifact_not_found"
    assert payload["artifact_path"] == "prompts/generated/missing.md"


def test_inspect_local_artifact_returns_metadata_for_valid_artifact(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    artifact_path = config.artifact_root / "prompts" / "generated" / "artifact.md"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("# Preview\r\nHello world", encoding="utf-8")

    payload = inspect_local_artifact(config, "prompts/generated/artifact.md")

    assert payload["ok"] is True
    assert payload["artifact"] == {
        "artifact_path": "prompts/generated/artifact.md",
        "filename": "artifact.md",
        "size_bytes": artifact_path.stat().st_size,
        "modified_at": payload["artifact"]["modified_at"],
        "artifact_type": "prompt_package",
        "command_source_hint": "generate-prompt-package",
        "extension": ".md",
        "text_readable": True,
        "text_preview": "# Preview\nHello world",
    }


def test_inspect_local_artifact_binds_text_preview_to_deterministic_limit(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    artifact_path = config.artifact_root / "prompts" / "generated" / "long.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("a" * (_TEXT_PREVIEW_CHAR_LIMIT + 50), encoding="utf-8")

    payload = inspect_local_artifact(config, "prompts/generated/long.txt")

    assert payload["ok"] is True
    assert payload["artifact"]["text_readable"] is True
    assert payload["artifact"]["text_preview"] == "a" * _TEXT_PREVIEW_CHAR_LIMIT


def test_inspect_local_artifact_payload_is_json_serializable(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    artifact_path = config.artifact_root / "evidence" / "generated" / "artifact.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text('{"ok": true}', encoding="utf-8")

    payload = inspect_local_artifact(config, "evidence/generated/artifact.json")

    assert json.loads(json.dumps(payload)) == payload
