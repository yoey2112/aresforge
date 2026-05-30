import json

from aresforge.config import AppConfig
from aresforge.db.repository import DEFAULT_AGENT_ID, DEFAULT_AGENT_RECORDS
from aresforge.operator.agent_registry import (
    AGENT_REGISTRY_VERSION,
    build_agent_registry,
    inspect_agent_registry,
)


def _config(tmp_path):
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=tmp_path / "artifacts",
        prompts_dir=tmp_path / "artifacts" / "prompts",
        evidence_dir=tmp_path / "artifacts" / "evidence",
        codex_handoffs_dir=tmp_path / "artifacts" / "codex-handoffs",
        github_owner="",
        github_repo="",
    )


def test_default_agent_registry_roles_cover_issue_83_seed_set() -> None:
    role_ids = {record["id"] for record in DEFAULT_AGENT_RECORDS}
    assert role_ids == {
        "agent-planning-next-issue",
        "agent-triage-routing",
        "agent-worker",
        "agent-verification",
        "agent-testing",
        "agent-debug-routing",
        "agent-documentation",
        "agent-final-closeout",
        DEFAULT_AGENT_ID,
    }


def test_default_agent_registry_records_use_conservative_lifecycle_states() -> None:
    allowed_states = {"planned", "active", "paused", "blocked", "deprecated", "archived"}
    for record in DEFAULT_AGENT_RECORDS:
        assert record["status"] in allowed_states
        metadata = record["metadata"]
        assert metadata["registry_version"] == "m2-v1"
        assert metadata["queue_participation"]
        assert metadata["allowed_capabilities"]
        assert metadata["evidence_expectations"]
        assert metadata["approval_boundary"]


def test_agent_registry_loads_all_initial_agents(tmp_path):
    payload = build_agent_registry(_config(tmp_path))

    assert payload["registry_type"] == "agent_registry"
    assert payload["generated"] is True
    assert payload["agent_registry_version"] == AGENT_REGISTRY_VERSION
    assert payload["agent_count"] == 12
    assert payload["local_only"] is True
    assert payload["execution_performed"] is False
    assert sorted(payload["executable_agents"]) == [
        "artifact-registry-agent",
        "completion-recommendation-agent",
        "evidence-parser-agent",
        "queue-planner-agent",
        "sprint-summary-agent",
        "validation-agent",
    ]
    assert sorted(agent["agent_id"] for agent in payload["agents"]) == [
        "approval-ledger-agent",
        "artifact-registry-agent",
        "codex-dispatch-agent",
        "completion-recommendation-agent",
        "documentation-agent",
        "evidence-parser-agent",
        "github-sync-agent",
        "local-llm-advisory-agent",
        "queue-planner-agent",
        "sprint-summary-agent",
        "transaction-log-agent",
        "validation-agent",
    ]


def test_agent_registry_filters_by_agent_id(tmp_path):
    payload = build_agent_registry(_config(tmp_path), agent_id="documentation-agent")

    assert payload["agent_count"] == 1
    assert payload["agents"][0]["agent_id"] == "documentation-agent"
    assert payload["agents_by_type"] == {"documentation": ["documentation-agent"]}
    assert payload["dry_run_only_agents"] == ["documentation-agent"]


def test_agent_registry_marks_only_m130_low_risk_agents_real_runnable(tmp_path):
    payload = build_agent_registry(_config(tmp_path))

    real_agents = {agent["agent_id"] for agent in payload["agents"] if agent["can_run_real"]}
    assert real_agents == {
        "artifact-registry-agent",
        "completion-recommendation-agent",
        "evidence-parser-agent",
        "queue-planner-agent",
        "sprint-summary-agent",
        "validation-agent",
    }
    blocked_real_agents = {
        "codex-dispatch-agent",
        "local-llm-advisory-agent",
        "documentation-agent",
        "github-sync-agent",
    }
    assert not blocked_real_agents.intersection(real_agents)


def test_agent_registry_filters_by_safety_class(tmp_path):
    payload = build_agent_registry(_config(tmp_path), safety_class="local_file_write")

    assert payload["agent_count"] == 2
    assert payload["agents_by_safety_class"] == {
        "local_file_write": ["approval-ledger-agent", "transaction-log-agent"]
    }
    assert {agent["agent_id"] for agent in payload["agents"]} == {
        "approval-ledger-agent",
        "transaction-log-agent",
    }


def test_agent_registry_filters_by_autonomy_level(tmp_path):
    payload = build_agent_registry(_config(tmp_path), autonomy_level="manual_only")

    assert payload["agent_count"] == 4
    assert payload["agents_by_autonomy_level"] == {
        "manual_only": [
            "approval-ledger-agent",
            "codex-dispatch-agent",
            "github-sync-agent",
            "transaction-log-agent",
        ]
    }


def test_high_risk_agents_carry_forbidden_capabilities(tmp_path):
    payload = build_agent_registry(_config(tmp_path))
    high_risk = [
        agent
        for agent in payload["agents"]
        if agent["safety_class"] == "external_mutation_prohibited"
    ]

    assert {agent["agent_id"] for agent in high_risk} == {
        "codex-dispatch-agent",
        "documentation-agent",
        "github-sync-agent",
        "validation-agent",
    }
    for agent in high_risk:
        forbidden = set(agent["forbidden_capabilities"])
        assert "call_github_api" in forbidden
        assert "call_gh" in forbidden
        assert "call_external_network" in forbidden
        assert "apply_patch" in forbidden
        assert "automatic_next_item_execution" in forbidden


def test_agent_registry_json_output_and_file_write(tmp_path):
    output = tmp_path / "registry.json"
    result = inspect_agent_registry(
        _config(tmp_path),
        agent_id="queue-planner-agent",
        output=output,
        force=False,
        output_format="json",
    )

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["registry_type"] == "agent_registry"
    assert parsed["agents"][0]["agent_id"] == "queue-planner-agent"


def test_agent_registry_rejects_unknown_format(tmp_path):
    result = inspect_agent_registry(_config(tmp_path), output_format="markdown")

    assert result["ok"] is False
    assert result["error"] == "invalid_format"
