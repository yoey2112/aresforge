import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path


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


def test_cli_inspect_bootstrap_status_json(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))

    assert cli.main(["inspect-bootstrap-status"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "inspect-bootstrap-status"
    assert payload["local_only"] is True


def test_cli_plan_bootstrap_json_and_markdown(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))

    assert cli.main(["plan-bootstrap", "--format", "json"]) == 0
    json_payload = json.loads(capsys.readouterr().out)
    assert json_payload["plan_only"] is True
    assert json_payload["local_only"] is True

    assert cli.main(["plan-bootstrap", "--format", "markdown"]) == 0
    markdown_output = capsys.readouterr().out
    assert "# Local Bootstrap Plan" in markdown_output


def test_cli_apply_bootstrap_creates_files(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))

    assert cli.main(["apply-bootstrap", "--repo-path", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "apply-bootstrap"
    assert payload["bootstrap_ready"] is True


def test_cli_apply_bootstrap_seed_sample_work(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))

    assert (
        cli.main(["apply-bootstrap", "--seed-sample-work", "--repo-path", str(tmp_path), "--format", "json"])
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert "m43-hub-stabilization" in payload["seeded_queue_items"]

    queue_data = json.loads(resolve_project_queue_path(tmp_path, None).read_text(encoding="utf-8"))
    ids = [item.get("item_id") for item in queue_data.get("work_items", [])]
    assert "m43-hub-stabilization" in ids
