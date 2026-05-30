import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.dispatch_artifact_registry import inspect_artifact_registry


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


def _write_queue(config: AppConfig, *item_ids: str) -> None:
    queue_path = config.repo_root / ".aresforge" / "queue" / "work_items.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-30T00:00:00+00:00",
                "work_items": [
                    {
                        "item_id": item_id,
                        "project_id": "aresforge",
                        "title": item_id,
                        "status": "done",
                    }
                    for item_id in item_ids
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_indexes_new_dispatch_artifact_types(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(config, "m109-item", "m110-item", "m111-item", "m112-item", "m113-item", "m116-item", "m117-item")
    records = {
        "manual_codex_dispatch/prepared/m109.json": {
            "preparation_record_type": "manual_codex_dispatch_preparation",
            "item_id": "m109-item",
            "prepared": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "local_llm_advisory/requests/m110.json": {
            "artifact_type": "local_llm_advisory_request",
            "item_id": "m110-item",
            "generated": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "patch_intake/m111.json": {
            "intake_record_type": "patch_proposal_intake",
            "item_id": "m111-item",
            "accepted_for_review": True,
            "operator_review_required": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "dispatch_result_evidence/m112.json": {
            "evidence_record_type": "dispatch_result_evidence",
            "item_id": "m112-item",
            "parsed": True,
            "human_review_required": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "queue_completion_recommendations/m113.json": {
            "recommendation_record_type": "queue_completion_recommendation",
            "item_id": "m113-item",
            "recommended_complete": True,
            "operator_decision_required": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "documentation_agent/patch_proposals/m116.json": {
            "artifact_type": "documentation_agent_patch_proposal",
            "item_id": "m116-item",
            "generated": True,
            "approval_required": True,
            "local_only": True,
            "execution_allowed": False,
        },
        "agent_route_recommendations/m117.json": {
            "recommendation_type": "agent_route_recommendation",
            "item_id": "m117-item",
            "local_only": True,
            "execution_allowed": False,
        },
    }
    for relative, payload in records.items():
        path = config.artifact_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    payload = _payload(inspect_artifact_registry(config))

    assert payload["registry_type"] == "dispatch_artifact_registry_v2"
    assert payload["artifact_count"] == 7
    by_type = payload["artifacts_by_type"]
    assert by_type["manual_codex_dispatch_preparation"] == 1
    assert by_type["local_llm_advisory_request"] == 1
    assert by_type["patch_proposal_intake"] == 1
    assert by_type["dispatch_result_evidence"] == 1
    assert by_type["queue_completion_recommendation"] == 1
    assert by_type["documentation_agent_patch_proposal"] == 1
    assert by_type["agent_route_recommendation"] == 1
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_filters_by_item_and_artifact_type(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(config, "m117-a", "m117-b")
    for name in ("m117-a", "m117-b"):
        path = config.artifact_root / "agent_route_recommendations" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"recommendation_type": "agent_route_recommendation", "item_id": name}), encoding="utf-8")

    payload = _payload(
        inspect_artifact_registry(
            config,
            item_id="m117-a",
            artifact_type="agent_route_recommendation",
        )
    )

    assert payload["artifact_count"] == 1
    assert payload["item_id"] == "m117-a"
    assert payload["artifact_type_filter"] == "agent_route_recommendation"
    assert payload["artifacts"][0]["item_id"] == "m117-a"  # type: ignore[index]


def test_missing_folders_are_reported_without_crashing(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(config, "m119")

    payload = _payload(inspect_artifact_registry(config))

    assert payload["artifact_count"] == 0
    assert payload["missing_expected_artifacts"]
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False


def test_stale_duplicate_and_blocked_artifacts_are_reported(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(config, "m111-known")
    for name in ("one", "two"):
        path = config.artifact_root / "patch_intake" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "intake_record_type": "patch_proposal_intake",
                    "item_id": "m111-known",
                    "blocked": name == "two",
                    "blocked_reasons": ["needs approval"] if name == "two" else [],
                    "operator_review_required": True,
                }
            ),
            encoding="utf-8",
        )
    stale = config.artifact_root / "dispatch_result_evidence" / "missing-item.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(json.dumps({"evidence_record_type": "dispatch_result_evidence", "item_id": "missing-item"}), encoding="utf-8")

    payload = _payload(inspect_artifact_registry(config))

    assert payload["duplicate_artifacts"]
    assert payload["blocked_artifacts"]
    assert payload["stale_artifacts"]
    assert payload["review_required_artifacts"]


def test_json_output_and_output_path_no_overwrite(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _write_queue(config, "m119")
    output = tmp_path / "artifacts" / "registry" / "index.json"

    result = inspect_artifact_registry(config, output=output, output_format="json")
    parsed = json.loads(output.read_text(encoding="utf-8"))
    blocked = inspect_artifact_registry(config, output=output, output_format="json")
    forced = inspect_artifact_registry(config, output=output, output_format="json", force=True)

    assert result["ok"] is True
    assert parsed["registry_type"] == "dispatch_artifact_registry_v2"
    assert blocked["ok"] is False
    assert "Output file already exists" in blocked["stdout"]  # type: ignore[operator]
    assert forced["ok"] is True
