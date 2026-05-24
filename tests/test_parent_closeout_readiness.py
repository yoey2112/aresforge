from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator import parent_closeout_readiness


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
        github_owner="yoey2112",
        github_repo="aresforge",
    )


def test_parent_closeout_readiness_reports_blockers(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "parent"},
            "child_issues": [
                {
                    "issue_number": 298,
                    "state": "OPEN",
                    "title": "child",
                    "lineage_detected": True,
                    "lineage_sources": ["reference_classification"],
                }
            ],
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": False},
            "issues": [
                {
                    "issue": {"number": 298},
                    "classification": "not_ready",
                    "evidence_signals": {"explicit_issue_evidence_mapping": False},
                }
            ],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {
            "ok": True,
            "ready_for_final_reconciliation": False,
            "parent_should_remain_open": True,
            "required_operator_actions": ["Close or evidence-account all implementation children before final reconciliation."],
            "boundary_confirmations": ["close_issues: false"],
        },
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(config, parent_issue=294)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["closeout_readiness"]["parent_closeout_ready"] is False
    assert "one_or_more_children_not_individually_closed" in payload["blocked_reasons"]
    assert "missing_issue_specific_evidence_mapping_for_one_or_more_children" in payload["blocked_reasons"]
    assert payload["safety_gates"]["mutation_allowed"] is False


def test_parent_closeout_readiness_reports_ready(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "parent"},
            "child_issues": [
                {
                    "issue_number": 298,
                    "state": "CLOSED",
                    "title": "child",
                    "lineage_detected": True,
                    "lineage_sources": ["reference_classification"],
                }
            ],
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": True},
            "issues": [
                {
                    "issue": {"number": 298},
                    "classification": "already_closed",
                    "evidence_signals": {"explicit_issue_evidence_mapping": True},
                }
            ],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {
            "ok": True,
            "ready_for_final_reconciliation": True,
            "parent_should_remain_open": False,
            "required_operator_actions": [],
            "boundary_confirmations": ["close_issues: false"],
        },
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(config, parent_issue=294)
    assert payload["ok"] is True
    assert payload["closeout_readiness"]["parent_closeout_ready"] is True
    assert payload["blocked_reasons"] == []
    assert payload["lineage_signals"]["ambiguous_child_lineage"] is False


def test_parent_closeout_readiness_dependency_failure(monkeypatch, tmp_path: Path) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": False,
            "error": "gh_cli_failed",
            "parent_issue": parent_issue,
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {"ok": True},
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {"ok": True},
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(config, parent_issue=294)
    assert payload["ok"] is False
    assert payload["error"] == "parent_closeout_readiness_dependency_failed"
    assert payload["failures"][0]["command"] == "inspect-milestone-state"


def test_parent_closeout_readiness_m20_children_closed_and_reconciliation_complete(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)

    child_issues = []
    for issue_number in range(327, 335):
        child_issues.append(
            {
                "issue_number": issue_number,
                "state": "CLOSED",
                "title": "source-of-truth reconciliation" if issue_number == 334 else f"child-{issue_number}",
                "lineage_detected": True,
                "lineage_sources": ["explicit_parent_issue_line"],
            }
        )

    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "M20 parent"},
            "child_issues": child_issues,
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": True},
            "issues": [
                {
                    "issue": {"number": issue_number},
                    "classification": "already_closed",
                    "evidence_signals": {"explicit_issue_evidence_mapping": True},
                }
                for issue_number in range(327, 335)
            ],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda _config, parent_issue: {
            "ok": True,
            "ready_for_final_reconciliation": True,
            "parent_should_remain_open": False,
            "final_reconciliation_issue": {"issue_number": 334, "state": "CLOSED"},
            "required_operator_actions": [],
            "boundary_confirmations": ["close_issues: false"],
        },
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(config, parent_issue=326)
    assert payload["ok"] is True
    assert payload["closeout_readiness"]["parent_closeout_ready"] is True
    assert payload["lineage_signals"]["discovered_child_issue_numbers"] == [327, 328, 329, 330, 331, 332, 333, 334]
    assert payload["lineage_signals"]["child_issue_count"] == 8
    assert payload["blocked_reasons"] == []


def test_parent_closeout_readiness_offline_mode_ready_with_final_reconciliation(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state.json"
    state_file.write_text(
        """{
  "parent_issue": {"number": 421, "state": "OPEN", "title": "parent"},
  "child_issues": [],
  "final_reconciliation": {
    "ready_for_final_reconciliation": true,
    "final_reconciliation_issue": 430,
    "parent_should_remain_open": false,
    "unaccounted_children": []
  }
}""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "parent"},
            "child_issues": [
                {
                    "issue_number": 422,
                    "state": "CLOSED",
                    "title": "child",
                    "lineage_detected": True,
                    "lineage_sources": ["reference_classification"],
                }
            ],
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": True},
            "issues": [
                {
                    "issue": {"number": 422},
                    "classification": "already_closed",
                    "evidence_signals": {"explicit_issue_evidence_mapping": True},
                }
            ],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("online reconciliation should not be called")),
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "subprocess",
        type(
            "SubprocessStub",
            (),
            {"run": staticmethod(lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("subprocess.run should not be called")))},
        )(),
        raising=False,
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(
        config,
        parent_issue=421,
        state_file=state_file,
    )
    assert payload["ok"] is True
    assert payload["inspection_mode"] == "local_state_file"
    assert payload["state_file"] == str(state_file)
    assert payload["closeout_readiness"]["parent_closeout_ready"] is True


def test_parent_closeout_readiness_offline_mode_blocked_when_final_reconciliation_missing(
    monkeypatch, tmp_path: Path
) -> None:
    config = _config(tmp_path)
    state_file = tmp_path / "offline-state.json"
    state_file.write_text(
        """{
  "parent_issue": {"number": 421, "state": "OPEN", "title": "parent"},
  "child_issues": []
}""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "inspect_milestone_state",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "parent_issue": {"issue_number": parent_issue, "state": "OPEN", "title": "parent"},
            "child_issues": [],
            "boundary_confirmations": ["read_only: true"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "check_milestone_evidence_readiness",
        lambda _config, parent_issue, state_file=None: {
            "ok": True,
            "milestone_closeout_readiness": {"closeout_ready": True},
            "issues": [],
            "boundary_confirmations": ["mutation_allowed: false"],
        },
    )
    monkeypatch.setattr(
        parent_closeout_readiness,
        "plan_milestone_final_reconciliation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("online reconciliation should not be called")),
    )

    payload = parent_closeout_readiness.inspect_parent_closeout_readiness(
        config,
        parent_issue=421,
        state_file=state_file,
    )
    assert payload["ok"] is True
    assert payload["inspection_mode"] == "local_state_file"
    assert payload["closeout_readiness"]["parent_closeout_ready"] is False
    assert "final_source_of_truth_reconciliation_incomplete" in payload["blocked_reasons"]
