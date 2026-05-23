from aresforge.operator.validation_summary import (
    STATE_FAIL,
    STATE_PASS,
    STATE_UNKNOWN,
    STATE_WARNING,
    ValidationEntryInput,
    build_validation_summary,
    normalize_validation_entry,
)


def test_normalize_validation_entry_infers_pass() -> None:
    entry = normalize_validation_entry(
        ValidationEntryInput(command="python   -m   pytest", output="392 passed in 11.12s")
    )
    assert entry["command"] == "python -m pytest"
    assert entry["state"] == STATE_PASS
    assert entry["summary_line"] == "- python -m pytest: pass"


def test_normalize_validation_entry_infers_fail() -> None:
    entry = normalize_validation_entry(
        ValidationEntryInput(command="git diff --check", output="error: trailing whitespace")
    )
    assert entry["command"] == "git diff --check"
    assert entry["state"] == STATE_FAIL


def test_normalize_validation_entry_infers_warning() -> None:
    entry = normalize_validation_entry(
        ValidationEntryInput(command="custom check", output="warning: ambiguous input")
    )
    assert entry["command"] == "custom check"
    assert entry["state"] == STATE_WARNING


def test_normalize_validation_entry_unknown() -> None:
    entry = normalize_validation_entry(
        ValidationEntryInput(command="python -m aresforge inspect-milestone-state", output="")
    )
    assert entry["state"] == STATE_UNKNOWN


def test_build_validation_summary_state_rollup() -> None:
    payload = build_validation_summary(
        [
            ValidationEntryInput(command="git diff --check", state="pass"),
            ValidationEntryInput(command="python -m pytest", state="warning"),
            ValidationEntryInput(command="python -m aresforge inspect-repo-governance", state="unknown"),
        ]
    )
    assert payload["overall_state"] == STATE_WARNING
    assert payload["state_counts"][STATE_PASS] == 1
    assert payload["state_counts"][STATE_WARNING] == 1
    assert payload["state_counts"][STATE_UNKNOWN] == 1