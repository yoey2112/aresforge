import json
from pathlib import Path

import pytest

from aresforge.config import AppConfig
from aresforge.operator import ready_issue_pipeline
from aresforge.operator.ready_issue_pipeline import run_ready_issue_pipeline


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


def _inspect_ready_ok() -> dict[str, object]:
    return {
        "ok": True,
        "issue": {
            "number": 120,
            "title": "M2 sprint: Ready issue automation pipeline",
            "labels": ["aresforge-ready", "aresforge-automerge"],
        },
    }


def _plan_ready_ok() -> dict[str, object]:
    return {
        "issue_number": 120,
        "issue_title": "M2 sprint: Ready issue automation pipeline",
        "automation_eligible": True,
        "selected_primary_agent": "implementation-agent",
        "selected_model_tier": "local",
        "model_routing_reason": "Local-first routing for bounded implementation scope.",
        "lower_tiers_sufficient": True,
        "codex_justified": False,
        "paid_use_blocked": True,
        "blocked_reason": None,
    }


def _qa_review_pass() -> dict[str, object]:
    return {
        "ok": True,
        "qa_decision": "pass",
        "failed_gates": [],
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
        "merge_eligible": True,
        "closeout_eligible": True,
    }


def test_plan_only_mode_is_non_mutating(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(
        ready_issue_pipeline,
        "qa_review_pr",
        lambda *_args, **_kwargs: pytest.fail("plan-only mode must not run qa-review-pr"),
    )
    monkeypatch.setattr(
        ready_issue_pipeline,
        "qa_closeout_pr",
        lambda *_args, **_kwargs: pytest.fail("plan-only mode must not run qa-closeout-pr"),
    )

    payload = run_ready_issue_pipeline(config, issue_number=120, mode="plan-only")

    assert payload["mode"] == "plan-only"
    assert payload["failed_gates"] == []
    assert payload["closeout_attempted"] is False
    assert payload["closeout_completed"] is False
    assert payload["review_package_path"] is None
    assert payload["evidence_package_path"] is None


def test_review_pr_mode_is_non_mutating(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "qa_review_pr", lambda _config, _pr: _qa_review_pass())
    monkeypatch.setattr(
        ready_issue_pipeline,
        "qa_closeout_pr",
        lambda *_args, **_kwargs: pytest.fail("review-pr mode must not run qa-closeout-pr"),
    )

    payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="review-pr",
    )

    assert payload["mode"] == "review-pr"
    assert payload["qa_decision"] == "pass"
    assert payload["closeout_attempted"] is False
    assert payload["closeout_completed"] is False


def test_closeout_mode_delegates_when_eligible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    delegated: list[bool] = []

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "qa_review_pr", lambda _config, _pr: _qa_review_pass())

    def fake_closeout(_config: AppConfig, _pr: int, execute: bool = False) -> dict[str, object]:
        delegated.append(execute)
        return {
            "qa_decision": "pass",
            "failed_gates": [],
            "merge_performed": execute,
            "issue_closed": execute,
        }

    monkeypatch.setattr(ready_issue_pipeline, "qa_closeout_pr", fake_closeout)

    payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
        execute_closeout=False,
    )

    assert payload["closeout_attempted"] is True
    assert payload["closeout_completed"] is False
    assert delegated == [False]


def test_missing_ready_label_blocks_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        ready_issue_pipeline,
        "inspect_ready_issue",
        lambda _config, _issue: {"ok": False, "error": "issue_not_ready"},
    )
    monkeypatch.setattr(
        ready_issue_pipeline,
        "plan_ready_issue",
        lambda _config, _issue: {**_plan_ready_ok(), "automation_eligible": False, "blocked_reason": "missing_ready_label:aresforge-ready"},
    )

    payload = run_ready_issue_pipeline(config, issue_number=120, mode="plan-only")

    assert payload["automation_eligible"] is False
    assert "missing_ready_label" in payload["failed_gates"]


def test_missing_automerge_label_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    inspect_payload = _inspect_ready_ok()
    inspect_payload["issue"] = {
        "number": 120,
        "title": "M2 sprint: Ready issue automation pipeline",
        "labels": ["aresforge-ready"],
    }

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: inspect_payload)
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())

    payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
    )

    assert "missing_automerge_label" in payload["failed_gates"]
    assert payload["closeout_attempted"] is False


def test_protected_issue_39_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(
        ready_issue_pipeline,
        "inspect_ready_issue",
        lambda _config, _issue: {"ok": False, "error": "protected_issue"},
    )
    monkeypatch.setattr(
        ready_issue_pipeline,
        "plan_ready_issue",
        lambda _config, _issue: {**_plan_ready_ok(), "automation_eligible": False, "blocked_reason": "protected_issue"},
    )

    payload = run_ready_issue_pipeline(config, issue_number=39, mode="plan-only")

    assert payload["automation_eligible"] is False
    assert "protected_issue_blocked" in payload["failed_gates"]


def test_missing_pr_in_review_mode_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())

    payload = run_ready_issue_pipeline(config, issue_number=120, mode="review-pr")

    assert "missing_pr_number" in payload["failed_gates"]


def test_failed_qa_blocks_closeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(
        ready_issue_pipeline,
        "qa_review_pr",
        lambda _config, _pr: {
            "qa_decision": "fail",
            "failed_gates": ["required_tests_passed"],
            "passed_gates": ["pr_exists"],
            "merge_eligible": False,
            "closeout_eligible": False,
        },
    )
    monkeypatch.setattr(
        ready_issue_pipeline,
        "qa_closeout_pr",
        lambda *_args, **_kwargs: pytest.fail("failed QA must block qa-closeout-pr delegation"),
    )

    payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
    )

    assert payload["qa_decision"] == "fail"
    assert "required_tests_passed" in payload["failed_gates"]
    assert payload["closeout_attempted"] is False


def test_qa_pass_allows_closeout_delegation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)
    delegated: list[bool] = []

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "qa_review_pr", lambda _config, _pr: _qa_review_pass())

    def fake_closeout(_config: AppConfig, _pr: int, execute: bool = False) -> dict[str, object]:
        delegated.append(execute)
        return {
            "qa_decision": "pass",
            "failed_gates": [],
            "merge_performed": False,
            "issue_closed": False,
        }

    monkeypatch.setattr(ready_issue_pipeline, "qa_closeout_pr", fake_closeout)

    payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
    )

    assert payload["closeout_attempted"] is True
    assert delegated == [False]


def test_payload_is_deterministic_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())

    payload = run_ready_issue_pipeline(config, issue_number=120, mode="plan-only")

    assert json.loads(json.dumps(payload)) == payload


def test_no_background_polling_behavior(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = make_config(tmp_path)

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())

    payload = run_ready_issue_pipeline(config, issue_number=120, mode="plan-only")

    assert any("No background jobs" in note for note in payload["boundary_confirmations"])


def test_closeout_mutation_only_through_qa_closeout_pr_with_explicit_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = make_config(tmp_path)
    delegated: list[bool] = []

    monkeypatch.setattr(ready_issue_pipeline, "inspect_ready_issue", lambda _config, _issue: _inspect_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "plan_ready_issue", lambda _config, _issue: _plan_ready_ok())
    monkeypatch.setattr(ready_issue_pipeline, "qa_review_pr", lambda _config, _pr: _qa_review_pass())

    def fake_closeout(_config: AppConfig, _pr: int, execute: bool = False) -> dict[str, object]:
        delegated.append(execute)
        return {
            "qa_decision": "pass",
            "failed_gates": [],
            "merge_performed": execute,
            "issue_closed": execute,
        }

    monkeypatch.setattr(ready_issue_pipeline, "qa_closeout_pr", fake_closeout)

    dry_payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
        execute_closeout=False,
    )
    execute_payload = run_ready_issue_pipeline(
        config,
        issue_number=120,
        pr_number=128,
        mode="closeout-when-eligible",
        execute_closeout=True,
    )

    assert delegated == [False, True]
    assert dry_payload["closeout_completed"] is False
    assert execute_payload["closeout_completed"] is True
