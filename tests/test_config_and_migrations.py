from pathlib import Path

from aresforge.config import AppConfig
from aresforge.db.migrations import discover_migrations


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
