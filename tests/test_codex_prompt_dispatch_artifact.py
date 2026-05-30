import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.codex_prompt_dispatch_artifact import generate_codex_prompt_dispatch_artifact
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


def _seed_item(config: AppConfig, *, item_id: str = "m98-codex-artifact", item_type: str = "feature") -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id=item_id,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M98 Codex Prompt Dispatch Artifact Generator v1",
        description="Generate a local-only Codex prompt dispatch artifact from the M97 plan.",
        status="ready",
        priority="high",
        item_type=item_type,
        tags=["milestone:m98", "local-only"],
        notes="Acceptance criteria:\n- Generate prompt artifacts only\n- Preserve execution_allowed=false",
    )["ok"] is True


def _plan(*, lane: str = "codex_prompt_artifact") -> dict[str, object]:
    return {
        "ok": True,
        "local_only": True,
        "dispatch_plan_version": "m97.1",
        "item_id": "m98-codex-artifact",
        "title": "M98 Codex Prompt Dispatch Artifact Generator v1",
        "status": "ready",
        "project_id": "aresforge",
        "repo_id": "aresforge-main",
        "milestone": "m98",
        "selected_lane": lane,
        "routing_confidence": {"score": 82, "level": "high", "reason": "coding-oriented item"},
        "lane_selection_reason": "Queue item requires implementation artifact preparation.",
        "planned_artifact_intent": {
            "artifact_type": "codex_prompt_dispatch_plan",
            "generator_milestone": "M98",
            "intent": "Prepare a Codex prompt artifact without execution.",
            "full_prompt_generated": False,
        },
        "blocked": False,
        "blocked_reasons": [],
        "execution_allowed": False,
    }


def _payload(result: dict[str, object]) -> dict[str, object]:
    return result["payload"]  # type: ignore[index]


def test_generates_codex_prompt_artifact_for_codex_prompt_lane(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    payload = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact"))

    assert payload["generated"] is True
    assert payload["blocked"] is False
    assert payload["selected_lane"] == "codex_prompt_artifact"
    assert payload["local_only"] is True
    assert payload["execution_allowed"] is False
    assert "M98 Codex Prompt Dispatch Artifact Generator v1" in payload["prompt_text"]


def test_blocks_generation_for_non_codex_lanes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    for lane in (
        "local_llm_advisory",
        "local_llm_coding_draft",
        "documentation_agent_dry_run",
        "human_only_manual",
    ):
        plan = _plan(lane=lane)
        payload = _payload(
            generate_codex_prompt_dispatch_artifact(
                config,
                item_id="m98-codex-artifact",
                dispatch_plan=plan,
            )
        )
        assert payload["generated"] is False
        assert payload["blocked"] is True
        assert payload["prompt_text"] == ""
        assert any("M98 only generates artifacts" in reason for reason in payload["blocked_reasons"])


def test_blocks_when_dispatch_plan_has_blocked_reasons(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    plan = _plan()
    plan["blocked"] = True
    plan["blocked_reasons"] = ["Queue item has unresolved blockers."]

    payload = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", dispatch_plan=plan))

    assert payload["generated"] is False
    assert "Queue item has unresolved blockers." in payload["blocked_reasons"]
    assert "Dispatch plan is blocked." in payload["blocked_reasons"]


def test_blocks_if_local_only_is_false(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    plan = _plan()
    plan["local_only"] = False

    payload = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", dispatch_plan=plan))

    assert payload["generated"] is False
    assert "Dispatch plan local_only must be true." in payload["blocked_reasons"]


def test_blocks_if_execution_allowed_is_true(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    plan = _plan()
    plan["execution_allowed"] = True

    payload = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", dispatch_plan=plan))

    assert payload["generated"] is False
    assert "Dispatch plan execution_allowed must be false." in payload["blocked_reasons"]


def test_generated_prompt_includes_required_sections_and_avoids_markdown_fences(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    prompt = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact"))["prompt_text"]

    assert "item_id: m98-codex-artifact" in prompt
    assert "task title: M98 Codex Prompt Dispatch Artifact Generator v1" in prompt
    assert "dispatch lane: codex_prompt_artifact" in prompt
    assert "Safety boundaries:" in prompt
    assert "Validation commands:" in prompt
    assert "Final response format:" in prompt
    assert "execution_allowed=false" in prompt
    assert "```" not in prompt


def test_optional_output_file_writes_safely_and_force_overwrites(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)
    output_path = tmp_path / "artifacts" / "codex_prompt_dispatch" / "generated" / "prompt.txt"

    first = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", output=output_path))
    duplicate = _payload(generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", output=output_path))
    forced = _payload(
        generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", output=output_path, force=True)
    )

    assert first["generated"] is True
    assert Path(first["output_path"]).exists()
    assert first["prompt_text"] == ""
    assert duplicate["generated"] is False
    assert any("already exists" in reason for reason in duplicate["blocked_reasons"])
    assert forced["generated"] is True
    assert "Manual/operator-gated" in output_path.read_text(encoding="utf-8")


def test_json_stdout_contains_stable_fields(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_item(config)

    result = generate_codex_prompt_dispatch_artifact(config, item_id="m98-codex-artifact", output_format="json")
    parsed = json.loads(result["stdout"])  # type: ignore[arg-type]

    assert parsed["generated"] is True
    assert parsed["blocked"] is False
    assert parsed["item_id"] == "m98-codex-artifact"
    assert parsed["selected_lane"] == "codex_prompt_artifact"
    assert parsed["local_only"] is True
    assert parsed["execution_allowed"] is False
