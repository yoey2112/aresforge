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


def test_cli_generate_local_milestone_template(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    exit_code = cli.main(
        [
            "generate-local-milestone-template",
            "--milestone-id",
            "M30",
            "--output",
            str(tmp_path / ".aresforge" / "milestones" / "m30.json"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["ok"] is True


def test_cli_inspect_and_readiness_stdout(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "inspect_local_milestone",
        lambda *_args, **_kwargs: {"ok": True, "wrote_output_file": False, "stdout": "# inspect"},
    )
    code_inspect = cli.main(["inspect-local-milestone", "--definition", "m30.json"])
    assert code_inspect == 0
    assert capsys.readouterr().out.strip() == "# inspect"

    monkeypatch.setattr(
        cli,
        "check_local_milestone_readiness",
        lambda *_args, **_kwargs: {"ok": True, "wrote_output_file": False, "stdout": "# readiness"},
    )
    code_ready = cli.main(["check-local-milestone-readiness", "--definition", "m30.json"])
    assert code_ready == 0
    assert capsys.readouterr().out.strip() == "# readiness"


def test_cli_generate_local_milestone_closeout_overwrite_path(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    calls: list[dict[str, object]] = []

    def fake_generate(_config_obj, **kwargs):
        calls.append(kwargs)
        if kwargs.get("force"):
            return {"ok": True, "output": str(tmp_path / "out.md")}
        return {"ok": False, "error": "output_exists"}

    monkeypatch.setattr(cli, "generate_local_milestone_closeout", fake_generate)
    first = cli.main(
        [
            "generate-local-milestone-closeout",
            "--definition",
            "m30.json",
            "--output",
            str(tmp_path / "out.md"),
        ]
    )
    first_payload = json.loads(capsys.readouterr().out)
    assert first == 1
    assert first_payload["error"] == "output_exists"

    second = cli.main(
        [
            "generate-local-milestone-closeout",
            "--definition",
            "m30.json",
            "--output",
            str(tmp_path / "out.md"),
            "--force",
        ]
    )
    second_payload = json.loads(capsys.readouterr().out)
    assert second == 0
    assert second_payload["ok"] is True
    assert calls[0]["force"] is False
    assert calls[1]["force"] is True
