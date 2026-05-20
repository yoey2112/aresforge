from aresforge.cli import build_parser, parse_metadata, parse_metadata_pairs


def test_cli_has_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for command in (
        "validate-config",
        "migrate",
        "inspect-project-state",
        "inspect-queue",
        "inspect-work-item",
        "list-projects",
        "list-agents",
        "list-queues",
        "create-work-item",
        "list-work-items",
        "generate-prompt-package",
        "record-evidence-package",
        "test-ollama",
        "prepare-codex-handoff",
    ):
        assert command in help_text


def test_parse_metadata_requires_object() -> None:
    assert parse_metadata('{"priority_hint": "high"}') == {"priority_hint": "high"}


def test_parse_metadata_pairs() -> None:
    assert parse_metadata_pairs(["issue=81", "protected_issue=39"]) == {
        "issue": "81",
        "protected_issue": "39",
    }


def test_cli_route_status_defaults_use_canonical_vocabulary() -> None:
    parser = build_parser()

    create_args = parser.parse_args(["create-work-item", "--title", "Test", "--queue-id", "queue-intake"])
    assert create_args.route_status == "queued"

    prompt_args = parser.parse_args(
        ["generate-prompt-package", "--title", "Prompt", "--objective", "Objective"]
    )
    assert prompt_args.route_status == "ready"

    handoff_args = parser.parse_args(
        [
            "prepare-codex-handoff",
            "--title",
            "Handoff",
            "--summary",
            "Summary",
            "--requested-output",
            "Output",
        ]
    )
    assert handoff_args.route_status == "ready"


def test_cli_inspection_commands_require_expected_ids() -> None:
    parser = build_parser()

    inspect_queue_args = parser.parse_args(["inspect-queue", "--queue-id", "queue-implementation"])
    assert inspect_queue_args.queue_id == "queue-implementation"

    inspect_work_item_args = parser.parse_args(
        ["inspect-work-item", "--work-item-id", "work-123"]
    )
    assert inspect_work_item_args.work_item_id == "work-123"
