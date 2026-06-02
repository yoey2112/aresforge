import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.github_link_registry import (
    LINK_RECORD_TYPE,
    RECORD_TYPE,
    inspect_github_link_registry,
    record_github_link,
)
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


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m170-github-link-registry-for-queue-items",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M170 GitHub Link Registry for Queue Items",
        status="ready",
        priority="high",
        item_type="sync",
    )["ok"] is True


def test_inspect_missing_registry_is_local_ready_with_warning(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(inspect_github_link_registry(config, project_id="aresforge"))

    assert payload["record_type"] == RECORD_TYPE
    assert payload["status"] == "registry_ready"
    assert payload["blocked"] is False
    assert payload["generated"] is True
    assert payload["project_id"] == "aresforge"
    assert payload["item_id"] == "m170-github-link-registry-for-queue-items"
    assert payload["record_count"] == 0
    assert payload["matched_record_count"] == 0
    assert payload["machine_gates_passed"] is True
    assert payload["dry_run"] is True
    assert payload["github_enabled"] is False
    assert payload["github_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["local_only"] is True
    assert any("not found yet" in warning for warning in payload["warnings"])


def test_record_link_persists_local_registry_and_lookup_by_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    recorded = _payload(
        record_github_link(
            config,
            queue_item_id="feature-one",
            repository="local/aresforge",
            issue_number=170,
            issue_url="https://github.com/local/aresforge/issues/170",
            pr_number=171,
            pr_url="https://github.com/local/aresforge/pull/171",
            sync_status="linked",
            last_sync_result="linked from local metadata",
            linked_by="unit-test",
            link_source="test",
        )
    )
    lookup = _payload(
        inspect_github_link_registry(
            config,
            project_id="aresforge",
            queue_item_id="feature-one",
        )
    )

    assert recorded["status"] == "link_recorded"
    assert recorded["mutation_performed"] is True
    assert recorded["github_execution_performed"] is False
    assert recorded["queue_mutation_performed"] is False
    assert recorded["link_record"]["record_type"] == LINK_RECORD_TYPE
    assert Path(str(recorded["registry_path"])).exists()
    assert lookup["matched_record_count"] == 1
    assert lookup["records"][0]["queue_item_id"] == "feature-one"
    assert lookup["records"][0]["issue_number"] == 170
    assert lookup["records"][0]["pr_number"] == 171


def test_lookup_by_issue_and_pr_filters_records(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    record_github_link(
        config,
        queue_item_id="feature-one",
        repository="local/aresforge",
        issue_number=170,
        pr_number=171,
    )
    record_github_link(
        config,
        queue_item_id="feature-two",
        repository="local/aresforge",
        issue_number=270,
        pr_number=271,
    )

    by_issue = _payload(inspect_github_link_registry(config, issue_number=270))
    by_pr = _payload(inspect_github_link_registry(config, pr_number=171))

    assert [record["queue_item_id"] for record in by_issue["records"]] == ["feature-two"]
    assert [record["queue_item_id"] for record in by_pr["records"]] == ["feature-one"]
    assert by_issue["issue_number"] == 270
    assert by_pr["pr_number"] == 171


def test_record_link_is_idempotent_for_same_material_values(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    first = _payload(
        record_github_link(
            config,
            queue_item_id="feature-one",
            repository="local/aresforge",
            issue_number=170,
            issue_url="https://github.com/local/aresforge/issues/170",
            pr_number=171,
            pr_url="https://github.com/local/aresforge/pull/171",
        )
    )
    second = _payload(
        record_github_link(
            config,
            queue_item_id="feature-one",
            repository="local/aresforge",
            issue_number=170,
            issue_url="https://github.com/local/aresforge/issues/170",
            pr_number=171,
            pr_url="https://github.com/local/aresforge/pull/171",
        )
    )
    registry = json.loads(Path(str(first["registry_path"])).read_text(encoding="utf-8"))

    assert first["record_created"] is True
    assert second["idempotent_noop"] is True
    assert second["mutation_performed"] is False
    assert len(registry["links"]) == 1


def test_record_link_blocks_invalid_status_without_file_write(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    payload = _payload(
        record_github_link(
            config,
            queue_item_id="feature-one",
            repository="local/aresforge",
            sync_status="surprise",
        )
    )

    assert payload["blocked"] is True
    assert payload["mutation_performed"] is False
    assert any("sync_status" in reason for reason in payload["blocked_reasons"])
    assert Path(str(payload["registry_path"])).exists() is False
