import json
from pathlib import Path

from aresforge import cli
from aresforge.config import AppConfig
from aresforge.operator.self_managed_issue_script_generator import generate_self_managed_issue_script


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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_generate_self_managed_issue_script_is_text_only_and_human_gated(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.ensure_directories()

    monkeypatch.setattr(
        "aresforge.operator.self_managed_issue_script_generator.plan_self_managed_milestone",
        lambda _config, mode: {
            "planning": {"parent_issue": 249, "target_issue": 252},
            "ok": True,
        },
    )

    payload = generate_self_managed_issue_script(config, mode="read-only")

    assert payload["ok"] is True
    assert payload["resolved_target_issue"] == 252
    assert payload["mutation_posture"] == "human_gated_script_output_only"
    assert "gh issue" in payload["script"]
    assert "```" not in payload["script"]


def test_generate_self_managed_issue_script_unsupported_mode_fails_safe(tmp_path: Path) -> None:
    config = _config(tmp_path)
    payload = generate_self_managed_issue_script(config, mode="full-auto")
    assert payload["ok"] is False
    assert payload["error"] == "mode_not_implemented"


def test_cli_dispatch_generate_self_managed_issue_script(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(cli.AppConfig, "from_env", lambda: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "generate_self_managed_issue_script",
        lambda *_args, **_kwargs: {
            "command": "generate-self-managed-issue-script",
            "ok": True,
            "mode": "read-only",
            "script": "Write-Host 'hello'\n",
        },
    )

    exit_code = cli.main(["generate-self-managed-issue-script", "--mode", "read-only"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["command"] == "generate-self-managed-issue-script"
