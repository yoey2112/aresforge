from pathlib import Path

from aresforge.config import AppConfig
from aresforge.db.migrations import discover_migrations
from aresforge.db.repository import (
    CANONICAL_QUEUE_IDS,
    DEFAULT_QUEUES,
    MODEL_SCHEMA_SOURCE_DOCUMENT,
    QUEUE_SCHEMA_SOURCE_DOCUMENT,
    build_default_model_seed,
    enrich_model_record,
    enrich_queue_record,
    enrich_work_item_record,
)


def test_config_validation_and_directory_creation(tmp_path: Path) -> None:
    config = AppConfig(
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
    assert config.validate() == []
    config.ensure_directories()
    assert config.prompts_dir.exists()
    assert config.evidence_dir.exists()
    assert config.codex_handoffs_dir.exists()


def test_discover_migrations_reads_repo_sql_files() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    migrations = discover_migrations(repo_root / "migrations")
    assert [migration.path.name for migration in migrations] == [
        "0001_initial_schema.sql",
        "0002_m15_autonomous_run_queue.sql",
        "0003_m16_autonomous_run_pr_linkage.sql",
        "0004_roadmap_control_schema.sql",
    ]


def test_default_queue_seed_set_matches_canonical_m2_queue_ids() -> None:
    assert {record["id"] for record in DEFAULT_QUEUES} == set(CANONICAL_QUEUE_IDS)


def test_default_queue_seed_records_include_canonical_source_document_metadata() -> None:
    for record in DEFAULT_QUEUES:
        metadata = record["metadata"]
        assert metadata["source_document"] == QUEUE_SCHEMA_SOURCE_DOCUMENT
        assert metadata["human_approval_requirement"] == "human_review_required"


def test_default_queue_allowed_next_queues_reference_only_canonical_queue_ids() -> None:
    canonical_ids = set(CANONICAL_QUEUE_IDS)
    for record in DEFAULT_QUEUES:
        allowed_next_queues = record["metadata"]["allowed_next_queues"]
        assert set(allowed_next_queues).issubset(canonical_ids)


def test_enrich_queue_record_exposes_registry_aware_metadata_fields() -> None:
    queue_record = enrich_queue_record(
        {
            "id": "queue-implementation",
            "name": "implementation",
            "status": "active",
            "purpose": "Active implementation work.",
            "metadata": {
                "lifecycle_stage_mapping": "implementation",
                "accepted_work_item_types": ["github_issue", "correction_pass"],
                "allowed_next_queues": ["queue-verification", "queue-blocked"],
                "human_approval_requirement": "human_review_required",
                "local_operator_visibility_expectations": ["changed files", "current route status"],
                "source_document": QUEUE_SCHEMA_SOURCE_DOCUMENT,
            },
        }
    )

    assert queue_record["lifecycle_stage_mapping"] == "implementation"
    assert queue_record["accepted_work_item_types"] == ["github_issue", "correction_pass"]
    assert queue_record["allowed_next_queues"] == ["queue-verification", "queue-blocked"]
    assert queue_record["human_approval_requirement"] == "human_review_required"
    assert queue_record["source_document"] == QUEUE_SCHEMA_SOURCE_DOCUMENT


def test_enrich_model_record_exposes_existing_row_fields_and_metadata() -> None:
    model_record = enrich_model_record(
        {
            "id": "model-ollama-default",
            "name": "qwen2.5:32b",
            "provider": "ollama",
            "status": "configured",
            "endpoint": "http://127.0.0.1:11434",
            "metadata": {
                "default": True,
                "display_name": "Qwen 2.5 32B",
                "runtime": "ollama_local",
                "model_key": "ollama/qwen2.5:32b",
                "execution_location": "local_machine",
                "hosting_posture": "local_only",
                "allowed_task_classes": ["documentation_support"],
                "approval_posture": "local_human_review_required",
                "restricted_task_classes": ["governance_decision"],
                "governance_sensitive_task_posture": "advisory_only_human_approval_required",
                "source_document": MODEL_SCHEMA_SOURCE_DOCUMENT,
            },
            "updated_at": "2026-05-20T00:00:00Z",
        }
    )

    assert model_record["id"] == "model-ollama-default"
    assert model_record["name"] == "qwen2.5:32b"
    assert model_record["display_name"] == "Qwen 2.5 32B"
    assert model_record["provider"] == "ollama"
    assert model_record["runtime"] == "ollama_local"
    assert model_record["status"] == "configured"
    assert model_record["local_endpoint"] == "http://127.0.0.1:11434"
    assert model_record["model_key"] == "ollama/qwen2.5:32b"
    assert model_record["execution_location"] == "local_machine"
    assert model_record["hosting_posture"] == "local_only"
    assert model_record["allowed_task_classes"] == ["documentation_support"]
    assert model_record["approval_posture"] == "local_human_review_required"
    assert model_record["restricted_task_classes"] == ["governance_decision"]
    assert (
        model_record["governance_sensitive_task_posture"]
        == "advisory_only_human_approval_required"
    )
    assert model_record["source_document"] == MODEL_SCHEMA_SOURCE_DOCUMENT
    assert model_record["metadata"]["default"] is True


def test_default_model_seed_includes_registry_visibility_fields() -> None:
    config = AppConfig(
        repo_root=Path("C:/Projects/aresforge"),
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=Path("C:/Projects/aresforge/artifacts"),
        prompts_dir=Path("C:/Projects/aresforge/artifacts/prompts"),
        evidence_dir=Path("C:/Projects/aresforge/artifacts/evidence"),
        codex_handoffs_dir=Path("C:/Projects/aresforge/artifacts/handoffs"),
        github_owner="yoey2112",
        github_repo="aresforge",
    )

    model_seed = build_default_model_seed(config)

    assert model_seed["id"] == "model-ollama-default"
    assert model_seed["provider"] == "ollama"
    assert model_seed["metadata"]["model_key"] == "ollama/qwen2.5:32b"
    assert model_seed["metadata"]["approval_posture"] == "local_human_review_required"
    assert model_seed["metadata"]["allowed_task_classes"]
    assert model_seed["metadata"]["restricted_task_classes"]
    assert model_seed["metadata"]["source_document"] == MODEL_SCHEMA_SOURCE_DOCUMENT


def test_enrich_work_item_record_exposes_registry_aware_queue_and_runtime_fields() -> None:
    work_item_record = enrich_work_item_record(
        {
            "id": "work-123",
            "title": "Implement inspection",
            "description": "Add read-only inspection commands.",
            "status": "queued",
            "priority": "normal",
            "route_status": "ready",
            "queue_id": "queue-implementation",
            "queue_name": "implementation",
            "queue_purpose": "Active implementation work.",
            "queue_metadata": {
                "lifecycle_stage_mapping": "implementation",
                "accepted_work_item_types": ["github_issue", "correction_pass"],
                "allowed_next_queues": ["queue-verification", "queue-blocked"],
                "human_approval_requirement": "human_review_required",
                "local_operator_visibility_expectations": ["changed files", "current route status"],
            },
            "agent_id": "agent-worker",
            "agent_name": "worker-agent",
            "model_id": "model-ollama-default",
            "model_name": "qwen2.5:32b",
            "model_provider": "ollama",
            "prompt_id": "prompt-123",
            "metadata": {
                "lifecycle_state": "implementation_ready",
                "approval_state": "not_requested",
                "blocked_reason": None,
                "failure_reason": None,
                "retry_or_correction_context": None,
            },
            "created_at": "2026-05-19T20:00:00Z",
            "updated_at": "2026-05-19T20:05:00Z",
        }
    )

    assert work_item_record["queue_lifecycle_stage_mapping"] == "implementation"
    assert work_item_record["queue_accepted_work_item_types"] == [
        "github_issue",
        "correction_pass",
    ]
    assert work_item_record["queue_allowed_next_queues"] == [
        "queue-verification",
        "queue-blocked",
    ]
    assert work_item_record["agent_id"] == "agent-worker"
    assert work_item_record["model_provider"] == "ollama"
    assert work_item_record["lifecycle_state"] == "implementation_ready"
    assert work_item_record["approval_state"] == "not_requested"
