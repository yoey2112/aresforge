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


def test_serve_hub_parser_defaults() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["serve-hub"])

    assert args.command == "serve-hub"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.open_browser is False


def test_cli_dispatches_serve_hub(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    calls: list[dict[str, object]] = []

    def fake_serve(_config_obj, **kwargs):
        calls.append(kwargs)
        return {
            "command": "serve-hub",
            "ok": True,
            "local_only": True,
            "host": kwargs["host"],
            "port": kwargs["port"],
            "open_browser": kwargs["open_browser"],
        }

    monkeypatch.setattr(cli, "serve_hub", fake_serve)

    exit_code = cli.main(["serve-hub", "--host", "127.0.0.1", "--port", "8765", "--open-browser"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert calls == [{"host": "127.0.0.1", "port": 8765, "open_browser": True}]
