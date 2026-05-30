import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_result_evidence_parser import parse_dispatch_result_evidence
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue


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


def _seed_item(config: AppConfig, *, item_id: str = "m112-dispatch-result-evidence-parser") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M112 Dispatch Result Evidence Parser",
        description="Parse a human-pasted Codex result into structured evidence.",
        status="ready",
        priority="high",
        item_type="architecture",
        tags=["milestone:m112", "dispatch-evidence", "local-only"],
        notes="Evidence parser only; no execution or queue completion.",
    )["ok"] is True


def _fixture(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "dispatch_results" / name


def _copy_fixture(config: AppConfig, name: str) -> Path:
    target = config.repo_root / "artifacts" / "manual" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_fixture(name).read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_parses_codex_completion_sections(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    result_path = _copy_fixture(config, "sample-codex-result.md")

    payload = _payload(
        parse_dispatch_result_evidence(
            config,
            item_id="m112-dispatch-result-evidence-parser",
            result_path=result_path,
        )
    )

    assert payload["evidence_record_type"] == "dispatch_result_evidence"
    assert payload["parsed"] is True
    assert payload["blocked"] is False
    assert payload["result_exists"] is True
    assert "src/aresforge/cli.py" in payload["files_changed"]
    assert any("local-only parser" in entry for entry in payload["what_changed"])
    assert any("tests/test_cli.py" in entry for entry in payload["tests_reported"])
    assert any("parse-dispatch-result-evidence" in entry for entry in payload["smoke_checks_reported"])
    assert payload["commit_hash"] == "abc1234"
    assert payload["validation_confidence"] == "high"
    assert payload["completion_recommendation"] == "ready_for_human_completion_review"
    assert payload["human_review_required"] is True
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_missing_sections_warn_without_crashing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    result_path = _copy_fixture(config, "minimal-codex-result.md")

    payload = _payload(
        parse_dispatch_result_evidence(
            config,
            item_id="m112-dispatch-result-evidence-parser",
            result_path=result_path,
        )
    )

    assert payload["parsed"] is True
    assert payload["blocked"] is False
    assert payload["commit_hash"] == "def5678"
    assert payload["validation_confidence"] == "medium"
    assert any("Files changed section was not found" in entry for entry in payload["warnings_or_blockers"])
    assert any("What changed section was not found" in entry for entry in payload["warnings_or_blockers"])


def test_blocks_missing_queue_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    result_path = _copy_fixture(config, "sample-codex-result.md")

    payload = _payload(parse_dispatch_result_evidence(config, item_id="missing", result_path=result_path))

    assert payload["parsed"] is False
    assert payload["blocked"] is True
    assert "Queue item was not found." in payload["blocked_reasons"]


def test_blocks_missing_result_file(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(
        parse_dispatch_result_evidence(
            config,
            item_id="m112-dispatch-result-evidence-parser",
            result_path=tmp_path / "artifacts" / "manual" / "missing.md",
        )
    )

    assert payload["result_exists"] is False
    assert payload["blocked"] is True
    assert any("Result file is missing" in reason for reason in payload["blocked_reasons"])


def test_json_stdout_contains_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    result_path = _copy_fixture(config, "sample-codex-result.md")

    result = parse_dispatch_result_evidence(
        config,
        item_id="m112-dispatch-result-evidence-parser",
        result_path=result_path,
        output_format="json",
    )
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["evidence_record_type"] == "dispatch_result_evidence"
    assert parsed["parsed"] is True
    assert parsed["human_review_required"] is True
    assert parsed["execution_allowed"] is False


def test_output_file_no_overwrite_and_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    result_path = _copy_fixture(config, "sample-codex-result.md")
    output_path = tmp_path / "artifacts" / "dispatch_result_evidence" / "m112.json"

    first = parse_dispatch_result_evidence(
        config,
        item_id="m112-dispatch-result-evidence-parser",
        result_path=result_path,
        output=output_path,
        output_format="json",
    )
    duplicate = _payload(
        parse_dispatch_result_evidence(
            config,
            item_id="m112-dispatch-result-evidence-parser",
            result_path=result_path,
            output=output_path,
            output_format="json",
        )
    )
    forced = parse_dispatch_result_evidence(
        config,
        item_id="m112-dispatch-result-evidence-parser",
        result_path=result_path,
        output=output_path,
        output_format="json",
        force=True,
    )

    assert first["ok"] is True
    assert output_path.exists()
    assert duplicate["blocked"] is True
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["ok"] is True
