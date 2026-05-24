import re
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.hub.api import get_docs_status, get_health, get_summary


NAV_LABELS = [
    "Home",
    "Projects",
    "Repos",
    "Queue",
    "Agents",
    "Handoff",
    "Orchestration",
    "Escalation",
    "Reports",
    "Settings",
]


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


def _static_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "src" / "aresforge" / "hub" / "static"


def test_hub_static_files_exist() -> None:
    static_dir = _static_dir()
    assert (static_dir / "index.html").exists()
    assert (static_dir / "app.js").exists()
    assert (static_dir / "styles.css").exists()


def test_index_contains_required_navigation_labels() -> None:
    index_text = (_static_dir() / "index.html").read_text(encoding="utf-8")
    for label in NAV_LABELS:
        assert label in index_text


def test_static_assets_do_not_reference_external_resources() -> None:
    external_patterns = [
        r"https?://",
        r"cdn",
        r"fonts\.googleapis",
        r"fonts\.gstatic",
        r"unpkg",
        r"jsdelivr",
    ]
    pattern = re.compile("|".join(external_patterns), re.IGNORECASE)

    for name in ("index.html", "app.js", "styles.css"):
        content = (_static_dir() / name).read_text(encoding="utf-8")
        assert not pattern.search(content)


def test_api_health_response_contains_boundaries() -> None:
    payload = get_health()

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["service"] == "aresforge-hub"
    assert any("No GitHub calls" in item for item in payload["boundary_confirmations"])


def test_api_summary_with_missing_files_returns_empty_state(tmp_path: Path) -> None:
    payload = get_summary(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert payload["project_count"] == 0
    assert payload["repo_count"] == 0
    assert payload["queue_status_counts"] == {}
    assert payload["agent_count"] == 0
    assert payload["warnings"]
    assert payload["next_recommended_actions"]
    assert any("No network service calls" in item for item in payload["boundary_confirmations"])


def test_api_docs_status_response(tmp_path: Path) -> None:
    payload = get_docs_status(_config(tmp_path))

    assert payload["ok"] is True
    assert payload["local_only"] is True
    assert payload["report_only"] is True
    assert isinstance(payload["docs"], list)
    assert payload["missing_count"] >= 0
    assert "boundary_confirmations" in payload
