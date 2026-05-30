from __future__ import annotations

import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.agent_route_recommendation import recommend_agent_route


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
        prompts_dir=artifact_root / "prompts",
        evidence_dir=artifact_root / "evidence",
        codex_handoffs_dir=artifact_root / "codex",
        github_owner="local",
        github_repo="aresforge",
    )


def _write_queue(tmp_path: Path, item: dict) -> Path:
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps({"work_items": [item]}, indent=2), encoding="utf-8")
    return queue_path


def test_recommend_agent_route_for_dashboard_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(
        tmp_path,
        {
            "item_id": "m117-agent-routing-decision-dashboard",
            "title": "M117 Agent Routing Decision Dashboard",
            "project_id": "aresforge",
            "status": "ready",
            "item_type": "dashboard",
            "tags": ["milestone:m117", "hub", "local-only"],
            "description": "Add Hub and CLI advisory routing dashboard.",
        },
    )

    result = recommend_agent_route(
        config,
        item_id="m117-agent-routing-decision-dashboard",
        output_format="json",
    )
    payload = json.loads(result["stdout"])

    assert result["ok"] is True
    assert payload["recommendation_type"] == "agent_route_recommendation"
    assert payload["recommended_lane"] == "codex_prompt_artifact"
    assert payload["codex_suitable"] is True
    assert payload["human_operator_required"] is True
    assert payload["dispatch_performed"] is False
    assert payload["execution_allowed"] is False
    assert payload["local_only"] is True


def test_recommend_agent_route_documentation_item(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(
        tmp_path,
        {
            "item_id": "docs-item",
            "title": "Docs update",
            "project_id": "aresforge",
            "status": "ready",
            "item_type": "documentation",
            "tags": ["milestone:m117"],
        },
    )

    payload = recommend_agent_route(config, item_id="docs-item", output_format="json")["payload"]

    assert payload["recommended_lane"] == "documentation_agent_patch_proposal"
    assert payload["documentation_agent_suitable"] is True
    assert "approval_gate_before_patch_intake" in payload["required_artifacts_before_dispatch"]


def test_recommend_agent_route_missing_item_blocks(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(tmp_path, {"item_id": "other", "title": "Other"})

    payload = recommend_agent_route(config, item_id="missing", output_format="json")["payload"]

    assert payload["ok"] is False
    assert payload["blocked"] is True
    assert payload["recommended_lane"] == "human_operator_manual_review"
    assert payload["dispatch_performed"] is False
    assert payload["execution_allowed"] is False


def test_recommend_agent_route_output_no_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(
        tmp_path,
        {
            "item_id": "m117",
            "title": "M117",
            "project_id": "aresforge",
            "item_type": "task",
            "tags": ["milestone:m117"],
        },
    )
    output = tmp_path / "artifacts" / "routes" / "m117.json"

    first = recommend_agent_route(config, item_id="m117", output=output, output_format="json")
    second = recommend_agent_route(config, item_id="m117", output=output, output_format="json")
    third = recommend_agent_route(config, item_id="m117", output=output, force=True, output_format="json")

    assert first["ok"] is True
    assert output.exists()
    assert second["ok"] is False
    assert "Output already exists" in second["payload"]["blocked_reasons"][0]
    assert third["ok"] is True
