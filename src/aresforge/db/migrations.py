from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from psycopg import Connection


@dataclass(frozen=True, slots=True)
class MigrationFile:
    version: str
    path: Path


def discover_migrations(migrations_dir: Path) -> list[MigrationFile]:
    files = sorted(migrations_dir.glob("*.sql"))
    return [MigrationFile(version=file.stem.split("_", 1)[0], path=file) for file in files]


def ensure_migration_table(conn: Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def applied_versions(conn: Connection) -> set[str]:
    ensure_migration_table(conn)
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        rows = cur.fetchall()
    return {row["version"] for row in rows}


def plan_migrations(conn: Connection, migrations_dir: Path) -> list[MigrationFile]:
    existing = applied_versions(conn)
    return [item for item in discover_migrations(migrations_dir) if item.version not in existing]


def apply_migrations(conn: Connection, migrations_dir: Path) -> list[str]:
    ensure_migration_table(conn)
    pending = plan_migrations(conn, migrations_dir)
    applied: list[str] = []
    for migration in pending:
        sql = migration.path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT DO NOTHING",
                (migration.version,),
            )
        applied.append(migration.path.name)
    return applied
