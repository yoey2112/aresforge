import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_agent_orchestration import generate_agent_orchestration_plan


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


def _write_profiles(tmp_path: Path, agents: list[dict[str, object]]) -> Path:
    profiles_path = tmp_path / ".aresforge" / "agents" / "agents.json"
    profiles_path.parent.mkdir(parents=True, exist_ok=True)
    profiles_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-24T00:00:00+00:00",
                "agents": agents,
                "handoff_targets": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return profiles_path


def _write_registry(tmp_path: Path) -> Path:
    registry_path = tmp_path / ".aresforge" / "projects" / "projects.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "updated_at": "2026-05-24T00:00:00+00:00",
                "projects": [
                    {
                        "project_id": "p1",
                        "name": "P1",
                        "repos": [{"repo_id": "r1", "name": "R1"}],
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return registry_path


def _base_item(item_id: str, **overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "item_id": item_id,
        "project_id": "p1",
        "repo_id": "r1",
        "title": f"title-{item_id}",
        "description": f"description-{item_id}",
        "status": "ready",
        "priority": "normal",
        "item_type": "task",
        "dependencies": [],
        "blocked_by": [],
        "assigned_agent": "",
    }
    item.update(overrides)
    return item


def _agent(agent_id: str, role: str, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "agent_id": agent_id,
        "name": agent_id,
        "role": role,
        "status": "active",
        "execution_mode": "manual",
        "allowed_item_types": [],
        "constraints": ["local-only"],
        "handoff_target_id": "",
    }
    data.update(overrides)
    return data


def test_orchestration_with_missing_queue(tmp_path: Path) -> None:
    _write_profiles(tmp_path, [_agent("implementer-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert plan["selected_work_items"] == []
    assert any("queue file not found" in warning for warning in plan["risk_warnings"])


def test_orchestration_with_missing_profiles(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", item_type="feature")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    assert payload["ok"] is True
    plan = payload["payload"]
    assert plan["available_agents"] == []
    assert plan["unassigned_items"][0]["item_id"] == "i1"


def test_assignment_uses_existing_assigned_agent(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", assigned_agent="architect-a")])
    _write_profiles(tmp_path, [_agent("architect-a", "architect")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    assignment = payload["payload"]["recommended_assignments"][0]
    assert assignment["recommended_agent_id"] == "architect-a"
    assert assignment["assignment_source"] == "existing_assigned_agent"


def test_warning_when_assigned_agent_missing_from_profiles(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", assigned_agent="missing-agent")])
    _write_profiles(tmp_path, [_agent("architect-a", "architect")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    plan = payload["payload"]
    assert plan["unassigned_items"][0]["reason"] == "assigned_agent_missing_from_profiles"
    assert any("missing-agent" in warning for warning in plan["risk_warnings"])


def test_assignment_by_item_type(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", item_type="validation")])
    _write_profiles(
        tmp_path,
        [
            _agent("tester-a", "tester", allowed_item_types=["validation"]),
            _agent("impl-a", "implementer", allowed_item_types=["feature", "bug"]),
        ],
    )
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    assignment = payload["payload"]["recommended_assignments"][0]
    assert assignment["recommended_agent_id"] == "tester-a"
    assert assignment["recommended_agent_role"] == "tester"


def test_unassigned_when_no_suitable_agent_exists(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", item_type="sync")])
    _write_profiles(tmp_path, [_agent("tester-a", "tester", allowed_item_types=["validation"])])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    unassigned = payload["payload"]["unassigned_items"]
    assert unassigned and unassigned[0]["item_id"] == "i1"


def test_dependency_ordering(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _base_item("a", dependencies=[]),
            _base_item("b", dependencies=["a"]),
            _base_item("c", dependencies=["b"]),
        ],
    )
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    assert payload["payload"]["dependency_order"] == ["a", "b", "c"]


def test_active_item_dependency_on_done_item_is_not_missing_warning(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _base_item("done-upstream", status="done"),
            _base_item("active-downstream", dependencies=["done-upstream"]),
        ],
    )
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")

    assert payload["payload"]["dependency_order"] == ["active-downstream"]
    assert not any("depends on missing item 'done-upstream'" in warning for warning in payload["payload"]["risk_warnings"])


def test_blocked_items_detection(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _base_item("a", status="in_progress"),
            _base_item("b", blocked_by=["a"]),
        ],
    )
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    blocked = payload["payload"]["blocked_items"]
    assert blocked and blocked[0]["item_id"] == "b"


def test_circular_dependency_warning(tmp_path: Path) -> None:
    _write_queue(
        tmp_path,
        [
            _base_item("a", dependencies=["b"]),
            _base_item("b", dependencies=["a"]),
        ],
    )
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    warnings = payload["payload"]["risk_warnings"]
    assert any("Circular dependency detected" in warning for warning in warnings)


def test_handoff_prompt_generation(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1", item_type="documentation")])
    _write_profiles(tmp_path, [_agent("doc-a", "documentation", allowed_item_types=["documentation"])])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    prompt = payload["payload"]["handoff_prompts"][0]["prompt"]
    assert "agent role/name:" in prompt
    assert "Do not make any GitHub/API/LLM/network calls unless later explicitly allowed." in prompt


def test_json_output_structure(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1")])
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    _write_registry(tmp_path)
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="json")
    plan = payload["payload"]
    for key in (
        "generated_at",
        "local_only",
        "plan_only",
        "filters",
        "input_files",
        "selected_work_items",
        "available_agents",
        "recommended_assignments",
        "dependency_order",
        "blocked_items",
        "unassigned_items",
        "handoff_prompts",
        "risk_warnings",
        "next_actions",
        "boundary_confirmations",
    ):
        assert key in plan


def test_markdown_rendering(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1")])
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    payload = generate_agent_orchestration_plan(_config(tmp_path), output_format="markdown")
    assert payload["ok"] is True
    assert "# AresForge Local Agent Orchestration Plan" in payload["stdout"]


def test_overwrite_protection(tmp_path: Path) -> None:
    _write_queue(tmp_path, [_base_item("i1")])
    _write_profiles(tmp_path, [_agent("impl-a", "implementer")])
    output = tmp_path / "artifacts" / "orchestration" / "plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("{}", encoding="utf-8")

    first = generate_agent_orchestration_plan(_config(tmp_path), output=output, output_format="json")
    assert first["ok"] is False
    assert first["error"] == "output_exists"

    second = generate_agent_orchestration_plan(
        _config(tmp_path), output=output, output_format="json", force=True
    )
    assert second["ok"] is True
    rendered = json.loads(output.read_text(encoding="utf-8"))
    assert rendered["plan_only"] is True
