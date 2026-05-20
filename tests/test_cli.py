from aresforge.cli import build_parser, parse_metadata, parse_metadata_pairs


def test_cli_has_expected_commands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for command in (
        "validate-config",
        "migrate",
        "inspect-project-state",
        "list-projects",
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
