from aresforge.db.repository import DEFAULT_AGENT_RECORDS, DEFAULT_QUEUES
from aresforge.validation.registry import (
    CANONICAL_ROUTE_STATUSES,
    validate_registry_seed_data,
)


def test_default_registry_seed_data_passes_validation() -> None:
    report = validate_registry_seed_data()

    assert report.ok is True
    assert report.findings == ()


def test_registry_validation_detects_invalid_queue_references() -> None:
    invalid_queues = list(DEFAULT_QUEUES)
    invalid_queues[0] = {
        **invalid_queues[0],
        "metadata": {
            **invalid_queues[0]["metadata"],
            "allowed_next_queues": ["queue-planning", "queue-not-real"],
        },
    }

    report = validate_registry_seed_data(queues=tuple(invalid_queues))

    assert report.ok is False
    assert any(
        finding.code == "queue.invalid_allowed_next_queue"
        and finding.location.endswith("allowed_next_queues")
        for finding in report.findings
    )


def test_registry_validation_detects_missing_required_queue_metadata() -> None:
    invalid_queues = list(DEFAULT_QUEUES)
    invalid_queues[0] = {
        **invalid_queues[0],
        "metadata": {
            **invalid_queues[0]["metadata"],
            "local_operator_visibility_expectations": [],
        },
    }

    report = validate_registry_seed_data(queues=tuple(invalid_queues))

    assert report.ok is False
    assert any(
        finding.code == "queue.missing_required_metadata"
        and finding.location.endswith("local_operator_visibility_expectations")
        for finding in report.findings
    )


def test_registry_validation_detects_invalid_agent_queue_participation() -> None:
    invalid_agents = list(DEFAULT_AGENT_RECORDS)
    invalid_agents[0] = {
        **invalid_agents[0],
        "metadata": {
            **invalid_agents[0]["metadata"],
            "queue_participation": ["queue-intake", "queue-not-real"],
        },
    }

    report = validate_registry_seed_data(agents=tuple(invalid_agents))

    assert report.ok is False
    assert any(
        finding.code == "agent.invalid_queue_participation"
        and finding.location.endswith("queue_participation")
        for finding in report.findings
    )


def test_canonical_route_status_vocabulary_includes_required_values() -> None:
    assert set(CANONICAL_ROUTE_STATUSES) >= {
        "queued",
        "ready",
        "in_progress",
        "waiting_for_human",
        "waiting_for_external_input",
        "blocked",
        "failed",
        "handed_off",
    }
