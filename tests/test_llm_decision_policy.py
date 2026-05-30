import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.llm_decision_policy import SUPPORTED_LANES, recommend_llm_decision
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


def _seed(config: AppConfig, *, item_id: str, item_type: str, title: str, notes: str = "", tags=None) -> None:
    if not (config.repo_root / ".aresforge" / "queue" / "work_items.json").exists():
        assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title=title,
        description=title,
        status="ready",
        priority="high",
        item_type=item_type,
        tags=tags or [f"milestone:{item_id.split('-', 1)[0]}", "local-only"],
        notes=notes,
    )["ok"] is True


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_docs_only_routes_to_documentation_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-docs", item_type="documentation", title="Update source-of-truth docs")

    payload = _payload(recommend_llm_decision(config, item_id="m127-docs"))

    assert payload["recommendation_type"] == "llm_decision_policy_v1"
    assert payload["recommended_lane"] == "documentation_agent"
    assert payload["recommended_provider"] == "agent_registry"
    assert payload["execution_performed"] is False
    assert payload["local_only"] is True


def test_high_risk_code_routes_to_codex_coding(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(
        config,
        item_id="m127-code",
        item_type="feature",
        title="Implement queue execution safety runner",
        notes="Touches src/ and tests/ with high-risk execution gates.",
    )

    payload = _payload(
        recommend_llm_decision(config, item_id="m127-code", risk_level="high", mutation_scope="source_code")
    )

    assert payload["recommended_lane"] == "codex_coding"
    assert payload["recommended_provider"] == "codex"
    assert payload["human_review_required"] is True
    assert payload["machine_gate_required"] is True
    assert payload["execution_performed"] is False


def test_validation_routes_to_validation_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-validation", item_type="validation", title="Run deterministic validation")

    payload = _payload(recommend_llm_decision(config, item_id="m127-validation"))

    assert payload["recommended_lane"] == "validation_agent"
    assert payload["recommended_model_profile"] == "deterministic_validation_plan"
    assert payload["autonomy_allowed"] is True


def test_github_sync_routes_to_github_sync_agent(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-sync", item_type="sync", title="Plan GitHub sync for evidence")

    payload = _payload(recommend_llm_decision(config, item_id="m127-sync", agent_id="github-sync-agent"))

    assert payload["recommended_lane"] == "github_sync_agent"
    assert payload["recommended_provider"] == "agent_registry"
    assert payload["local_only"] is False
    assert payload["execution_performed"] is False


def test_no_llm_required_for_read_only_chore(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-chore", item_type="architecture", title="Inspect deterministic local metadata")

    payload = _payload(
        recommend_llm_decision(
            config,
            item_id="m127-chore",
            task_type="chore",
            risk_level="low",
            mutation_scope="none",
        )
    )

    assert payload["recommended_lane"] == "no_llm_required"
    assert payload["recommended_provider"] == "none"
    assert payload["machine_gate_required"] is False
    assert payload["human_review_required"] is False


def test_low_risk_code_routes_to_local_coding_review(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-local-code", item_type="feature", title="Small UI copy change in src/")

    payload = _payload(
        recommend_llm_decision(config, item_id="m127-local-code", risk_level="low", mutation_scope="source_code")
    )

    assert payload["recommended_lane"] == "local_llm_coding_review"
    assert payload["recommended_provider"] == "local"
    assert payload["execution_performed"] is False


def test_output_json_and_no_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed(config, item_id="m127-output", item_type="architecture", title="Plan local decision policy")
    output = tmp_path / "artifacts" / "llm_decisions" / "m127.json"

    first = recommend_llm_decision(config, item_id="m127-output", output=output)
    duplicate = recommend_llm_decision(config, item_id="m127-output", output=output)
    forced = recommend_llm_decision(config, item_id="m127-output", output=output, force=True)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert first["ok"] is True
    assert duplicate["ok"] is False
    assert duplicate["error"] == "output_exists"
    assert forced["ok"] is True
    assert written["supported_lanes"] == list(SUPPORTED_LANES)
