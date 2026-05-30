import json
import subprocess
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.safe_dispatch_handoff import generate_safe_dispatch_handoff


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


def _seed_queue(config: AppConfig, *, status: str = "ready", item_id: str = "m107-safe-dispatch") -> None:
    assert init_project_queue(config)["ok"] is True
    assert (
        add_queue_item(
            config,
            item_id=item_id,
            project_id="aresforge",
            repo_id="aresforge-main",
            title="M107 Safe Dispatch Handoff Package",
            description="Generate a local-only safe dispatch handoff package.",
            status=status,
            priority="high",
            item_type="handoff",
            tags=["milestone:m107", "dispatch-handoff", "local-only"],
        )["ok"]
        is True
    )


def _fake_git(monkeypatch) -> None:
    def fake_run(command, **_kwargs):
        outputs = {
            "git branch --show-current": "main\n",
            "git rev-parse HEAD": "abc123\n",
        }
        return subprocess.CompletedProcess(command, 0, stdout=outputs.get(" ".join(command), ""), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_safe_dispatch_handoff_includes_queue_summary(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)

    payload = _payload(generate_safe_dispatch_handoff(config, output_format="json"))

    assert payload["handoff_type"] == "safe_dispatch_handoff"
    assert payload["queue_summary"]["item_count"] == 1
    assert payload["queue_summary"]["status_counts"]["ready"] == 1
    assert payload["next_recommended_items"][0]["item_id"] == "m107-safe-dispatch"
    assert payload["execution_allowed"] is False


def test_safe_dispatch_handoff_includes_dispatch_boundaries(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)

    payload = _payload(generate_safe_dispatch_handoff(config, output_format="json"))

    assert payload["local_only"] is True
    assert payload["read_only_by_default"] is True
    assert payload["safety_boundary"]["executes_codex"] is False
    assert payload["safety_boundary"]["invokes_local_llm"] is False
    assert payload["safety_boundary"]["auto_handoff_allowed"] is False
    assert any("Manual operator approval" in item for item in payload["manual_approval_required_for"])


def test_safe_dispatch_handoff_includes_artifact_summary_when_artifacts_exist(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config, item_id="m98-codex-artifact")
    artifact = config.artifact_root / "codex_prompt_dispatch" / "generated" / "m98-codex-artifact.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Manual Codex prompt artifact.\n", encoding="utf-8")
    _fake_git(monkeypatch)

    payload = _payload(generate_safe_dispatch_handoff(config, output_format="json"))

    artifact_summary = payload["artifact_index_summary"]
    assert artifact_summary["artifact_count"] == 1
    assert artifact_summary["by_artifact_type"]["codex_prompt_dispatch"] == 1
    assert artifact_summary["artifacts"][0]["item_id"] == "m98-codex-artifact"
    assert artifact_summary["execution_allowed"] is False


def test_safe_dispatch_handoff_handles_missing_artifacts(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)

    payload = _payload(generate_safe_dispatch_handoff(config, output_format="json"))

    assert payload["artifact_index_summary"]["artifact_count"] == 0
    assert payload["artifact_index_summary"]["missing_locations"]
    assert any("known dispatch artifact locations are missing" in warning for warning in payload["warnings"])


def test_safe_dispatch_handoff_json_output_stable(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)

    result = generate_safe_dispatch_handoff(config, output_format="json")
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["safe_dispatch_handoff_version"] == "m107.1"
    assert parsed["repo_path"] == str(tmp_path)
    assert parsed["branch"] == "main"
    assert parsed["head"] == "abc123"
    assert parsed["execution_allowed"] is False
    assert parsed["approval_gate_summary"]["execution_allowed"] is False


def test_safe_dispatch_handoff_readable_output(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)

    result = generate_safe_dispatch_handoff(config)

    assert result["ok"] is True
    assert "# Safe Dispatch Handoff Package" in result["stdout"]
    assert "## Queue Summary" in result["stdout"]
    assert "execution_allowed: False" in result["stdout"]


def test_safe_dispatch_handoff_output_file_no_overwrite(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    _fake_git(monkeypatch)
    output = tmp_path / "artifacts" / "safe-dispatch" / "handoff.json"

    first = generate_safe_dispatch_handoff(config, output=output, output_format="json")
    second = generate_safe_dispatch_handoff(config, output=output, output_format="json")
    forced = generate_safe_dispatch_handoff(config, output=output, output_format="json", force=True)

    assert first["ok"] is True
    assert output.exists()
    assert second["ok"] is False
    assert second["error"] == "output_exists"
    assert forced["ok"] is True
