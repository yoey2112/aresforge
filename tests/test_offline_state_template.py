import json
import subprocess
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator.offline_state_template import generate_offline_closeout_state_template


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


def test_generator_writes_valid_json_with_parent_and_children(tmp_path: Path) -> None:
    output = tmp_path / "artifacts" / "offline-state" / "m25-421.template.json"
    payload = generate_offline_closeout_state_template(
        _config(tmp_path),
        parent_issue=421,
        children="422,423,424",
        output=output,
        final_main_head="abc123",
        final_validation_results="git diff --check: pass",
    )

    assert payload["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["template_only"] is True
    assert rendered["editable_local_artifact"] is True
    assert rendered["parent_issue"]["number"] == 421
    assert [item["number"] for item in rendered["child_issues"]] == [422, 423, 424]
    assert rendered["final_reconciliation"]["unaccounted_children"] == [422, 423, 424]
    assert rendered["final_main_head"] == "abc123"
    assert rendered["final_validation_results"] == "git diff --check: pass"


def test_generator_creates_missing_output_directories(tmp_path: Path) -> None:
    output = tmp_path / "missing" / "nested" / "path" / "template.json"
    payload = generate_offline_closeout_state_template(
        _config(tmp_path),
        parent_issue=500,
        children="501",
        output=output,
    )
    assert payload["ok"] is True
    assert output.exists()


def test_generator_refuses_overwrite_without_force(tmp_path: Path) -> None:
    output = tmp_path / "template.json"
    output.write_text("{}", encoding="utf-8")
    payload = generate_offline_closeout_state_template(
        _config(tmp_path),
        parent_issue=421,
        children="422",
        output=output,
    )
    assert payload["ok"] is False
    assert payload["error"] == "output_exists"
    assert output.read_text(encoding="utf-8") == "{}"


def test_generator_overwrites_with_force(tmp_path: Path) -> None:
    output = tmp_path / "template.json"
    output.write_text("{}", encoding="utf-8")
    payload = generate_offline_closeout_state_template(
        _config(tmp_path),
        parent_issue=421,
        children="422",
        output=output,
        force=True,
    )
    assert payload["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["parent_issue"]["number"] == 421


def test_generator_does_not_call_subprocess_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("subprocess.run must not be called"),
    )
    output = tmp_path / "template.json"
    payload = generate_offline_closeout_state_template(
        _config(tmp_path),
        parent_issue=421,
        children="422",
        output=output,
    )
    assert payload["ok"] is True
