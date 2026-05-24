import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig


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


def test_cli_plan_github_sync_markdown_stdout(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "generate_github_sync_plan",
        lambda *_args, **_kwargs: {
            "ok": True,
            "wrote_output_file": False,
            "stdout": "# github sync plan",
        },
    )

    exit_code = cli.main(["plan-github-sync"])
    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "# github sync plan"


def test_cli_plan_github_sync_json_stdout(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "generate_github_sync_plan",
        lambda *_args, **_kwargs: {
            "ok": True,
            "wrote_output_file": False,
            "stdout": '{"hello":"world"}',
        },
    )

    exit_code = cli.main(["plan-github-sync", "--format", "json"])
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"hello": "world"}


def test_cli_plan_github_sync_overwrite_and_force(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    calls: list[dict[str, object]] = []

    def fake_generate(_config_obj, **kwargs):
        calls.append(kwargs)
        if kwargs.get("force"):
            return {"ok": True, "wrote_output_file": True, "output": str(tmp_path / "sync-plan.md")}
        return {"ok": False, "error": "output_exists", "wrote_output_file": False}

    monkeypatch.setattr(cli, "generate_github_sync_plan", fake_generate)

    output = str(tmp_path / "sync-plan.md")
    first = cli.main(["plan-github-sync", "--output", output])
    first_payload = json.loads(capsys.readouterr().out)
    assert first == 1
    assert first_payload["error"] == "output_exists"

    second = cli.main(["plan-github-sync", "--output", output, "--force"])
    second_payload = json.loads(capsys.readouterr().out)
    assert second == 0
    assert second_payload["ok"] is True
    assert calls[0]["force"] is False
    assert calls[1]["force"] is True
