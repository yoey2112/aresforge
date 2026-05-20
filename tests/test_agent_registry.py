from aresforge.db.repository import DEFAULT_AGENT_ID, DEFAULT_AGENT_RECORDS


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
