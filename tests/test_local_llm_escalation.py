import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_llm_escalation import generate_llm_escalation_plan


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


def _item(item_id: str, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "item_id": item_id,
        "project_id": "p1",
        "repo_id": "r1",
        "title": f"title-{item_id}",
        "description": f"description-{item_id}",
        "status": "ready",
        "priority": "normal",
        "item_type": "task",
        "assigned_agent": "",
        "dependencies": [],
        "blocked_by": [],
        "tags": [],
        "notes": "",
    }
    data.update(overrides)
    return data


def _write_queue(tmp_path: Path, items: list[dict[str, object]]) -> Path:
    queue_path = tmp_path / ".aresforge" / "queue" / "work_items.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-24T00:00:00+00:00",
                "work_items": items,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return queue_path


def _write_profiles(
    tmp_path: Path,
    agents: list[dict[str, object]],
    targets: list[dict[str, object]] | None = None,
) -> Path:
    profiles_path = tmp_path / ".aresforge" / "agents" / "agents.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-24T00:00:00+00:00",
                "agents": agents,
                "handoff_targets": targets or [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return profiles_path


def _agent(agent_id: str, execution_mode: str, role: str, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "agent_id": agent_id,
        "name": agent_id,
        "role": role,
        "status": "active",
        "execution_mode": execution_mode,
        "allowed_item_types": [],
        "handoff_target_id": "",
        "escalation_allowed": True,
    }
    data.update(overrides)
    return data


def test_missing_queue_warning(tmp_path: Path) -> None:
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    warnings = payload["payload"]["risk_warnings"]
    assert any("queue file not found" in warning for warning in warnings)


def test_classification_local_llm_suitable(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "doc-1",
                item_type="documentation",
                title="Documentation cleanup",
                description="Summarize and format the handoff notes.",
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    classification = payload["payload"]["classifications"][0]["classification"]
    assert classification == "local_llm_suitable"


def test_classification_codex_suitable(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "code-1",
                item_type="feature",
                title="Implement CLI command",
                description="Deterministic implementation with tests.",
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    classification = payload["payload"]["classifications"][0]["classification"]
    assert classification == "codex_suitable"


def test_classification_cloud_llm_recommended(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "arch-1",
                item_type="task",
                title="Architecture tradeoff",
                description="Cross-project security-sensitive data model design and long-context planning.",
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    classification = payload["payload"]["classifications"][0]["classification"]
    assert classification == "cloud_llm_recommended"


def test_classification_human_required(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "human-1",
                item_type="task",
                title="Business priority approval",
                description="Need policy and legal approval before continuing.",
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    classification = payload["payload"]["classifications"][0]["classification"]
    assert classification == "human_required"


def test_classification_blocked_or_needs_clarification(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "block-1",
                status="blocked",
                title="todo",
                description="",
                dependencies=["missing-dep"],
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    classification = payload["payload"]["classifications"][0]["classification"]
    assert classification == "blocked_or_needs_clarification"


def test_filtering_by_item_project_repo_status(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item("a", project_id="p1", repo_id="r1", status="ready"),
            _item("b", project_id="p2", repo_id="r2", status="blocked"),
        ],
    )
    payload = generate_llm_escalation_plan(
        _config(tmp_path),
        item_id="a",
        project_id="p1",
        repo_id="r1",
        status="ready",
        output_format="json",
    )
    selected = payload["payload"]["selected_work_items"]
    assert len(selected) == 1
    assert selected[0]["item_id"] == "a"


def test_recommended_handoff_target_from_profiles(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "code-1",
                item_type="feature",
                title="Implement local planner",
                description="deterministic repo-local change",
            )
        ],
    )
    _write_profiles(
        tmp_path,
        [
            _agent(
                "impl-a",
                "codex",
                "implementer",
                handoff_target_id="codex-target",
                allowed_item_types=["feature"],
            )
        ],
        targets=[
            {
                "target_id": "codex-target",
                "name": "Codex Target",
                "target_type": "codex_prompt",
                "status": "active",
            }
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    target = payload["payload"]["recommended_handoff_targets"][0]
    assert target["recommended_agent_id"] == "impl-a"
    assert target["recommended_target_id"] == "codex-target"


def test_warning_when_recommended_target_missing(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "code-1",
                item_type="feature",
                title="Implement local planner",
                description="deterministic repo-local change",
            )
        ],
    )
    _write_profiles(
        tmp_path,
        [
            _agent(
                "impl-a",
                "codex",
                "implementer",
                handoff_target_id="missing-target",
                allowed_item_types=["feature"],
            )
        ],
        targets=[],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    warnings = payload["payload"]["risk_warnings"]
    assert any("missing handoff target" in warning for warning in warnings)


def test_prompt_guidance_generation(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _item(
                "doc-1",
                item_type="documentation",
                title="Documentation cleanup",
                description="Summarize and format references.",
            )
        ],
    )
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    guidance = payload["payload"]["prompt_guidance"][0]
    assert guidance["classification"] == "local_llm_suitable"
    assert "No external calls should be made" in guidance["external_call_policy"]


def test_json_output_structure(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_item("x")])
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="json")
    plan = payload["payload"]
    for key in (
        "generated_at",
        "local_only",
        "plan_only",
        "filters",
        "input_files",
        "selected_work_items",
        "available_agents",
        "classifications",
        "local_llm_suitable",
        "codex_suitable",
        "cloud_llm_recommended",
        "human_required",
        "blocked_or_needs_clarification",
        "escalation_reasons",
        "recommended_handoff_targets",
        "prompt_guidance",
        "risk_warnings",
        "next_actions",
        "boundary_confirmations",
    ):
        assert key in plan


def test_markdown_rendering(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_item("x")])
    payload = generate_llm_escalation_plan(_config(tmp_path), output_format="markdown")
    assert payload["ok"] is True
    assert "# AresForge Local LLM Escalation Plan" in payload["stdout"]


def test_overwrite_protection(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_item("x")])
    output = tmp_path / "artifacts" / "escalation" / "plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("{}", encoding="utf-8")

    first = generate_llm_escalation_plan(_config(tmp_path), output=output, output_format="json")
    assert first["ok"] is False
    assert first["error"] == "output_exists"

    second = generate_llm_escalation_plan(
        _config(tmp_path),
        output=output,
        output_format="json",
        force=True,
    )
    assert second["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["plan_only"] is True