from pathlib import Path

from aresforge.config import AppConfig
from aresforge.db.migrations import discover_migrations
from aresforge.db.repository import CANONICAL_QUEUE_IDS, DEFAULT_QUEUES, QUEUE_SCHEMA_SOURCE_DOCUMENT


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
    assert [migration.path.name for migration in migrations] == ["0001_initial_schema.sql"]


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
