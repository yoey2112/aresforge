import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import qa_closeout_pr
from aresforge.operator.qa_closeout_pr import qa_closeout_pr as run_closeout


def make_config(tmp_path: Path) -> AppConfig:
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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def _review_payload(**overrides: object) -> dict[str, object]:
    base = {
        "ok": True,
        "pr_number": 119,
        "linked_issue_number": 119,
        "qa_decision": "pass",
        "merge_eligible": True,
        "closeout_eligible": True,
        "changed_files": ["src/aresforge/cli.py", "docs/context/BUILD_STATE.md"],
        "pr_labels": ["aresforge-ready", "aresforge-automerge"],
        "passed_gates": [
            "pr_exists",
            "pr_open",
            "pr_not_draft",
            "merge_state_clean",
            "linked_issue_present",
            "protected_issue_untouched",
            "validation_evidence_present",
            "required_tests_passed",
            "documentation_updated_when_required",
            "forbidden_changes_absent",
            "generated_conventions_respected",
        ],
        "failed_gates": [],
    }
    base.update(overrides)
    return base


def _stub_qa_review(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> None:
    monkeypatch.setattr(qa_closeout_pr, "qa_review_pr", lambda _config, _pr_number: payload)


def _stub_gh(monkeypatch: pytest.MonkeyPatch, calls: list[list[str]]) -> None:
    def fake_run(args: list[str]) -> tuple[int, str, str]:
        calls.append(args)
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "state": "OPEN",
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                        "labels": [
                            {"name": "aresforge-ready"},
                            {"name": "aresforge-automerge"},
                        ],
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)


def test_dry_run_is_default_and_performs_no_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []
    _stub_qa_review(monkeypatch, _review_payload())
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119)

    assert payload["mode"] == "dry_run"
    assert payload["mutation_attempted"] is False
    assert payload["merge_performed"] is False
    assert payload["issue_closed"] is False
    assert payload["closeout_comment_created"] is False
    assert all(not (call[:2] == ["pr", "merge"]) for call in calls)
    assert all(not (call[:2] == ["issue", "close"]) for call in calls)
    assert all(not (call[:2] == ["issue", "comment"]) for call in calls)


def test_execute_mode_requires_explicit_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []
    _stub_qa_review(monkeypatch, _review_payload())
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119, execute=False)

    assert payload["mode"] == "dry_run"
    assert payload["mutation_attempted"] is False
    assert all(call[:2] != ["pr", "merge"] for call in calls)


def test_missing_aresforge_ready_blocks_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(monkeypatch, _review_payload())

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "labels": [{"name": "aresforge-automerge"}],
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    payload = run_closeout(config, 119, execute=True)

    assert "required_labels_present" in payload["failed_gates"]
    assert payload["missing_required_labels"] == ["aresforge-ready"]
    assert payload["missing_linked_issue_labels"] == ["aresforge-ready"]
    assert payload["missing_pr_labels"] == []
    assert payload["required_label_target"] == "linked_issue"
    assert payload["linked_issue_labels"] == ["aresforge-automerge"]
    assert payload["pr_labels"] == ["aresforge-ready", "aresforge-automerge"]
    assert payload["human_required_label_commands"] == [
        'gh issue edit 119 --repo yoey2112/aresforge --add-label "aresforge-ready"'
    ]
    assert payload["recommended_next_command"] == (
        'gh issue edit 119 --repo yoey2112/aresforge --add-label "aresforge-ready"'
    )
    assert payload["mutation_attempted"] is False


def test_missing_aresforge_automerge_blocks_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(monkeypatch, _review_payload())

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "labels": [{"name": "aresforge-ready"}],
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    payload = run_closeout(config, 119, execute=True)

    assert "required_labels_present" in payload["failed_gates"]
    assert payload["missing_required_labels"] == ["aresforge-automerge"]
    assert payload["missing_linked_issue_labels"] == ["aresforge-automerge"]
    assert payload["missing_pr_labels"] == []
    assert payload["human_required_label_commands"] == [
        'gh issue edit 119 --repo yoey2112/aresforge --add-label "aresforge-automerge"'
    ]
    assert payload["mutation_attempted"] is False


def test_missing_linked_issue_and_pr_labels_are_distinguished(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(monkeypatch, _review_payload(pr_labels=[]))

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "labels": [],
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    payload = run_closeout(config, 119, execute=False)

    assert payload["missing_linked_issue_labels"] == ["aresforge-ready", "aresforge-automerge"]
    assert payload["missing_pr_labels"] == ["aresforge-ready", "aresforge-automerge"]
    assert payload["human_required_label_commands"] == [
        'gh issue edit 119 --repo yoey2112/aresforge --add-label "aresforge-ready" --add-label "aresforge-automerge"',
        'gh pr edit 119 --repo yoey2112/aresforge --add-label "aresforge-ready" --add-label "aresforge-automerge"',
    ]


def test_qa_fail_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(
        monkeypatch,
        _review_payload(
            qa_decision="fail",
            merge_eligible=False,
            closeout_eligible=False,
            passed_gates=[
                "pr_exists",
                "pr_open",
                "pr_not_draft",
                "merge_state_clean",
                "linked_issue_present",
                "protected_issue_untouched",
                "generated_conventions_respected",
            ],
            failed_gates=["validation_evidence_present", "required_tests_passed"],
        ),
    )
    calls: list[list[str]] = []
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119, execute=True)

    assert "qa_decision_pass" in payload["failed_gates"]
    assert payload["mutation_attempted"] is False
    assert all(call[:2] != ["pr", "merge"] for call in calls)


def test_qa_blocked_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(
        monkeypatch,
        _review_payload(
            qa_decision="blocked",
            merge_eligible=False,
            closeout_eligible=False,
            passed_gates=["pr_exists", "linked_issue_present", "protected_issue_untouched"],
            failed_gates=["pr_not_draft", "merge_state_clean"],
        ),
    )
    calls: list[list[str]] = []
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119, execute=True)

    assert "qa_decision_pass" in payload["failed_gates"]
    assert payload["mutation_attempted"] is False


def test_draft_pr_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(
        monkeypatch,
        _review_payload(
            qa_decision="blocked",
            merge_eligible=False,
            closeout_eligible=False,
            passed_gates=["pr_exists", "linked_issue_present", "protected_issue_untouched"],
            failed_gates=["pr_not_draft"],
        ),
    )
    calls: list[list[str]] = []
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119, execute=True)

    assert "pr_not_draft" in payload["failed_gates"]
    assert payload["mutation_attempted"] is False


def test_unclean_pr_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(
        monkeypatch,
        _review_payload(
            qa_decision="blocked",
            merge_eligible=False,
            closeout_eligible=False,
            passed_gates=[
                "pr_exists",
                "pr_open",
                "pr_not_draft",
                "linked_issue_present",
                "protected_issue_untouched",
            ],
            failed_gates=["merge_state_clean"],
        ),
    )
    calls: list[list[str]] = []
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119, execute=True)

    assert "merge_state_clean" in payload["failed_gates"]
    assert payload["mutation_attempted"] is False


def test_protected_issue_39_blocks_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    _stub_qa_review(
        monkeypatch,
        _review_payload(
            linked_issue_number=39,
            qa_decision="fail",
            merge_eligible=False,
            closeout_eligible=False,
            passed_gates=[
                "pr_exists",
                "pr_open",
                "pr_not_draft",
                "merge_state_clean",
                "linked_issue_present",
            ],
            failed_gates=["protected_issue_untouched"],
        ),
    )

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 39,
                        "labels": [
                            {"name": "aresforge-ready"},
                            {"name": "aresforge-automerge"},
                        ],
                        "url": "https://github.com/yoey2112/aresforge/issues/39",
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    payload = run_closeout(config, 119, execute=True)

    assert "protected_issue_untouched" in payload["failed_gates"]
    assert payload["mutation_attempted"] is False


def test_passing_execute_performs_expected_mutations_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []
    _stub_qa_review(monkeypatch, _review_payload())

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        calls.append(args)
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "state": "OPEN",
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                        "labels": [
                            {"name": "aresforge-ready"},
                            {"name": "aresforge-automerge"},
                        ],
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    payload = run_closeout(config, 119, execute=True)

    assert payload["failed_gates"] == []
    assert payload["mutation_attempted"] is True
    assert payload["merge_performed"] is True
    assert payload["closeout_comment_created"] is True
    assert payload["issue_closed"] is True
    assert payload["final_evidence_package_path"] is not None

    expected_steps = [
        ["issue", "view"],
        ["pr", "merge"],
        ["issue", "comment"],
        ["issue", "close"],
    ]
    assert [call[:2] for call in calls] == expected_steps


def test_payload_is_deterministic_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []
    _stub_qa_review(monkeypatch, _review_payload())
    _stub_gh(monkeypatch, calls)

    payload = run_closeout(config, 119)

    assert json.loads(json.dumps(payload)) == payload


def test_no_unrelated_github_mutation_targets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = make_config(tmp_path)
    calls: list[list[str]] = []
    _stub_qa_review(monkeypatch, _review_payload())

    def fake_run(args: list[str]) -> tuple[int, str, str]:
        calls.append(args)
        if args[:2] == ["issue", "view"]:
            return (
                0,
                json.dumps(
                    {
                        "number": 119,
                        "state": "OPEN",
                        "url": "https://github.com/yoey2112/aresforge/issues/119",
                        "labels": [
                            {"name": "aresforge-ready"},
                            {"name": "aresforge-automerge"},
                        ],
                    }
                ),
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(qa_closeout_pr, "_run_gh_command", fake_run)

    run_closeout(config, 119, execute=True)

    mutation_calls = [
        call
        for call in calls
        if call[:2] in (["pr", "merge"], ["issue", "comment"], ["issue", "close"])
    ]
    assert mutation_calls
    for call in mutation_calls:
        assert "119" in call
        assert "39" not in call

