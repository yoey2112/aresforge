from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(slots=True)
class AppConfig:
    repo_root: Path
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    ollama_base_url: str
    ollama_model: str
    artifact_root: Path
    prompts_dir: Path
    evidence_dir: Path
    codex_handoffs_dir: Path
    github_owner: str
    github_repo: str

    @classmethod
    def from_env(cls) -> "AppConfig":
        repo_root = Path(os.getenv("ARESFORGE_REPO_ROOT", os.getcwd())).resolve()
        load_dotenv(repo_root)
        repo_root = Path(os.getenv("ARESFORGE_REPO_ROOT", os.getcwd())).resolve()
        artifact_root = cls._resolve_path(
            repo_root, os.getenv("ARESFORGE_ARTIFACT_ROOT", "artifacts")
        )
        return cls(
            repo_root=repo_root,
            db_host=os.getenv("ARESFORGE_DB_HOST", "127.0.0.1"),
            db_port=int(os.getenv("ARESFORGE_DB_PORT", "5433")),
            db_name=os.getenv("ARESFORGE_DB_NAME", "aresforge"),
            db_user=os.getenv("ARESFORGE_DB_USER", "aresforge"),
            db_password=os.getenv("ARESFORGE_DB_PASSWORD", "aresforge"),
            ollama_base_url=os.getenv(
                "ARESFORGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"
            ).rstrip("/"),
            ollama_model=os.getenv("ARESFORGE_OLLAMA_MODEL", "qwen2.5:32b"),
            artifact_root=artifact_root,
            prompts_dir=cls._resolve_path(
                repo_root,
                os.getenv("ARESFORGE_PROMPTS_DIR", "artifacts/prompts/generated"),
            ),
            evidence_dir=cls._resolve_path(
                repo_root,
                os.getenv("ARESFORGE_EVIDENCE_DIR", "artifacts/evidence/generated"),
            ),
            codex_handoffs_dir=cls._resolve_path(
                repo_root,
                os.getenv(
                    "ARESFORGE_CODEX_HANDOFFS_DIR",
                    "artifacts/codex_handoffs/generated",
                ),
            ),
            github_owner=os.getenv("ARESFORGE_GITHUB_OWNER", "yoey2112"),
            github_repo=os.getenv("ARESFORGE_GITHUB_REPO", "aresforge"),
        )

    @staticmethod
    def _resolve_path(repo_root: Path, raw_value: str) -> Path:
        candidate = Path(raw_value)
        if candidate.is_absolute():
            return candidate
        return (repo_root / candidate).resolve()

    def database_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )

    def ensure_directories(self) -> None:
        for path in (
            self.artifact_root,
            self.prompts_dir,
            self.evidence_dir,
            self.codex_handoffs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.repo_root.exists():
            errors.append(f"Repo root does not exist: {self.repo_root}")
        if not self.github_owner.strip():
            errors.append("GitHub owner must not be empty.")
        if not self.github_repo.strip():
            errors.append("GitHub repo must not be empty.")
        if not self.ollama_base_url.startswith(("http://", "https://")):
            errors.append("Ollama base URL must start with http:// or https://.")
        if self.db_port <= 0:
            errors.append("Database port must be a positive integer.")
        return errors

    def summary(self) -> dict[str, str | int]:
        return {
            "repo_root": str(self.repo_root),
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "ollama_base_url": self.ollama_base_url,
            "ollama_model": self.ollama_model,
            "artifact_root": str(self.artifact_root),
            "prompts_dir": str(self.prompts_dir),
            "evidence_dir": str(self.evidence_dir),
            "codex_handoffs_dir": str(self.codex_handoffs_dir),
            "github_owner": self.github_owner,
            "github_repo": self.github_repo,
        }
