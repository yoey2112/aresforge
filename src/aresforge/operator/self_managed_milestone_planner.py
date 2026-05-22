from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from psycopg import Connection

from aresforge.artifacts.store import ArtifactBundle, write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.project_state_summary import project_state_summary
from aresforge.operator.ready_issue_intake import list_ready_issues
from aresforge.operator.repo_governance import inspect_repo_governance

COMMAND_NAME = "plan-self-managed-milestone"
SUPPORTED_MODES = {
    "read-only",
    "local-write",
    "branch-write",
    "pr-write",
    "closeout-write",
    "full-auto",
}
UNSUPPORTED_HIGHER_PERMISSION_MODES = {
    "branch-write",
    "pr-write",
    "closeout-write",
    "full-auto",
}


@dataclass(frozen=True)
class SequencedIssue:
    issue_number: int
    title: str
    role: str
    status: str
    depends_on: tuple[int, ...]


def plan_self_managed_milestone(
    config: AppConfig,
    *,
    mode: str = "read-only",
    conn: Connection | None = None,
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        return _unsupported_mode_payload(mode=mode, reason="unsupported_mode")

    if mode in UNSUPPORTED_HIGHER_PERMISSION_MODES:
        return _unsupported_mode_payload(mode=mode, reason="mode_not_implemented")

    if mode == "local-write" and conn is None:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "mode": mode,
            "error": "local_write_requires_database_connection",
        }

    docs = _read_source_of_truth_docs(config.repo_root)
    governance = inspect_repo_governance(config)
    ready_issues = list_ready_issues(config)
    readiness = project_state_summary(config)

    sequence = _deterministic_sequence()
    parent_issue = 249
    target_issue = 251
    selected_agent = "model-routing-agent"
    model_tier = "copilot"
    validation_expectations = [
        "python -m pytest",
        "python -m aresforge inspect-repo-governance",
        "python -m aresforge plan-self-managed-milestone",
        "python -m aresforge plan-self-managed-milestone --mode local-write",
    ]
    next_recommended_command = "python -m aresforge plan-self-managed-milestone --mode local-write"
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    run_id = f"run-m15-{target_issue}-{uuid4().hex[:10]}"
    steps = _build_run_steps(
        docs=docs,
        governance=governance,
        readiness=readiness,
        sequence=sequence,
        target_issue=target_issue,
        parent_issue=parent_issue,
    )

    payload: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": True,
        "mode": mode,
        "inspection_mode": "github_read_only_with_local_source_of_truth",
        "mutation_posture": "read_only" if mode == "read-only" else "local_db_and_artifact_write_only",
        "timestamp": now,
        "repo": f"{config.github_owner}/{config.github_repo}",
        "source_of_truth": docs,
        "governance_summary": {
            "ok": governance.get("ok") is True,
            "milestone_naming_ok": ((governance.get("milestone_naming_status") or {}).get("naming_ok")),
            "warnings": governance.get("warnings", []),
        },
        "repo_readiness": {
            "working_tree_clean": ((readiness.get("repository") or {}).get("working_tree_clean")),
            "open_issues_count": ((readiness.get("github") or {}).get("open_issues_count")),
            "open_prs_count": ((readiness.get("github") or {}).get("open_prs_count")),
            "ready_issue_count": ready_issues.get("issue_count"),
        },
        "planning": {
            "parent_issue": parent_issue,
            "target_issue": target_issue,
            "selected_agent": selected_agent,
            "model_tier": model_tier,
            "safety_mode": mode,
            "next_recommended_command": next_recommended_command,
            "validation_expectations": validation_expectations,
            "dependency_order": [item.issue_number for item in sequence],
            "issue_sequence": [
                {
                    "issue_number": item.issue_number,
                    "title": item.title,
                    "role": item.role,
                    "status": item.status,
                    "depends_on": list(item.depends_on),
                }
                for item in sequence
            ],
        },
        "autonomous_run": {
            "run_id": run_id,
            "parent_issue": parent_issue,
            "target_issue": target_issue,
            "current_step": "planned",
            "status": "planned" if mode == "read-only" else "initialized",
            "selected_agent": selected_agent,
            "model_tier": model_tier,
            "branch_name": None,
            "commit_hash": None,
            "pr_number": None,
            "validation_status": "pending",
            "qa_status": "pending",
            "closeout_status": "pending",
            "next_issue_candidate": 252,
        },
        "run_steps": steps,
        "warnings": [
            "No GitHub mutation was performed.",
            "Unsupported higher-permission modes remain fail-safe and unimplemented.",
            "Issue script generation scope (#252) and source-of-truth reconciliation scope (#253) are not implemented here.",
        ],
        "boundary_confirmations": [
            "Read-only GitHub inspection only (where available).",
            "No labels, milestones, issues, pull requests, branches, workflows, or settings were mutated.",
            "Local database writes are only allowed in local-write mode.",
        ],
    }

    artifact_bundle = _write_planner_artifact(config, payload)
    payload["evidence_package"] = {
        "markdown_path": str(artifact_bundle.markdown_path),
        "json_path": str(artifact_bundle.json_path),
    }

    if mode == "local-write":
        assert conn is not None
        _persist_autonomous_run(
            conn,
            run=payload["autonomous_run"],
            safety_mode=mode,
            validation_expectations=validation_expectations,
            next_recommended_command=next_recommended_command,
            metadata={
                "command": COMMAND_NAME,
                "target_issue_title": sequence[1].title,
                "dependency_order": [item.issue_number for item in sequence],
                "parent_issue": parent_issue,
                "target_issue": target_issue,
            },
        )
        _persist_run_steps(conn, run_id=run_id, steps=steps)
        payload["db_write"] = {
            "ok": True,
            "tables": ["autonomous_runs", "run_steps"],
            "run_id": run_id,
            "run_step_count": len(steps),
        }

    return payload


def _unsupported_mode_payload(*, mode: str, reason: str) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "mode": mode,
        "error": reason,
        "supported_modes": ["read-only", "local-write"],
        "not_implemented_modes": sorted(UNSUPPORTED_HIGHER_PERMISSION_MODES),
        "boundary_confirmations": [
            "Higher-permission modes are intentionally blocked for safe human-gated operation.",
            "No GitHub mutation was performed.",
        ],
    }


def _deterministic_sequence() -> tuple[SequencedIssue, ...]:
    return (
        SequencedIssue(
            issue_number=250,
            title="M15: define self-managed milestone planning contract",
            role="contract",
            status="completed_dependency",
            depends_on=(),
        ),
        SequencedIssue(
            issue_number=251,
            title="M15: add database-backed self-managed milestone planner and run queue initializer",
            role="implementation",
            status="ready",
            depends_on=(250,),
        ),
        SequencedIssue(
            issue_number=252,
            title="M15: add issue script generator for self-managed milestone plan",
            role="follow_on",
            status="blocked",
            depends_on=(251,),
        ),
        SequencedIssue(
            issue_number=253,
            title="M15: reconcile source-of-truth docs for self-managed milestone planning",
            role="reconciliation",
            status="blocked",
            depends_on=(251, 252),
        ),
    )


def _read_source_of_truth_docs(repo_root: Path) -> dict[str, Any]:
    paths = [
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
        "docs/architecture/SELF_MANAGED_MILESTONE_PLANNING_CONTRACT.md",
    ]
    docs: list[dict[str, Any]] = []
    for relative in paths:
        path = repo_root / relative
        exists = path.exists()
        docs.append(
            {
                "path": relative,
                "exists": exists,
                "line_count": len(path.read_text(encoding="utf-8").splitlines()) if exists else 0,
            }
        )
    return {"documents": docs, "all_present": all(item["exists"] for item in docs)}


def _build_run_steps(
    *,
    docs: dict[str, Any],
    governance: dict[str, Any],
    readiness: dict[str, Any],
    sequence: tuple[SequencedIssue, ...],
    target_issue: int,
    parent_issue: int,
) -> list[dict[str, Any]]:
    return [
        {
            "step_order": 1,
            "step_type": "read_source_of_truth",
            "status": "pending",
            "inputs": {"documents": docs.get("documents")},
            "outputs": {"all_present": docs.get("all_present")},
            "started_at": None,
            "completed_at": None,
            "failure_reason": None,
            "retry_count": 0,
            "requires_human_approval": False,
        },
        {
            "step_order": 2,
            "step_type": "inspect_repo_readiness",
            "status": "pending",
            "inputs": {"parent_issue": parent_issue, "target_issue": target_issue},
            "outputs": {
                "governance_ok": governance.get("ok") is True,
                "open_issues_count": ((readiness.get("github") or {}).get("open_issues_count")),
            },
            "started_at": None,
            "completed_at": None,
            "failure_reason": None,
            "retry_count": 0,
            "requires_human_approval": False,
        },
        {
            "step_order": 3,
            "step_type": "persist_local_run_queue",
            "status": "pending",
            "inputs": {
                "dependency_order": [item.issue_number for item in sequence],
                "target_issue": target_issue,
            },
            "outputs": {
                "queued_step_count": 3,
                "next_issue_candidate": 252,
            },
            "started_at": None,
            "completed_at": None,
            "failure_reason": None,
            "retry_count": 0,
            "requires_human_approval": True,
        },
    ]


def _write_planner_artifact(config: AppConfig, payload: dict[str, Any]) -> ArtifactBundle:
    title = f"M15 self-managed milestone plan {payload['mode']}"
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Command",
            f"- `{COMMAND_NAME}`",
            f"- mode: `{payload['mode']}`",
            "",
            "## Deterministic Issue Sequence",
            *[
                (
                    f"- #{item['issue_number']} {item['title']} "
                    f"({item['status']}; depends_on={item['depends_on']})"
                )
                for item in payload["planning"]["issue_sequence"]
            ],
            "",
            "## Safety Boundary",
            "- No GitHub mutation was performed.",
            "- Local DB writes occur only in local-write mode.",
            "- Higher-permission modes are unimplemented and fail safely.",
        ]
    )
    return write_markdown_json_bundle(config.evidence_dir, title=title, markdown=markdown, payload=payload)


def _persist_autonomous_run(
    conn: Connection,
    *,
    run: dict[str, Any],
    safety_mode: str,
    validation_expectations: list[str],
    next_recommended_command: str,
    metadata: dict[str, Any],
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO autonomous_runs (
                run_id, project_id, parent_issue, target_issue, current_step, status,
                selected_agent, model_tier, branch_name, commit_hash, pr_number,
                validation_status, qa_status, closeout_status, next_issue_candidate,
                safety_mode, validation_expectations, next_recommended_command, metadata
            ) VALUES (
                %(run_id)s, %(project_id)s, %(parent_issue)s, %(target_issue)s, %(current_step)s, %(status)s,
                %(selected_agent)s, %(model_tier)s, %(branch_name)s, %(commit_hash)s, %(pr_number)s,
                %(validation_status)s, %(qa_status)s, %(closeout_status)s, %(next_issue_candidate)s,
                %(safety_mode)s, %(validation_expectations)s::jsonb, %(next_recommended_command)s, %(metadata)s::jsonb
            )
            ON CONFLICT (run_id) DO UPDATE
            SET current_step = EXCLUDED.current_step,
                status = EXCLUDED.status,
                validation_status = EXCLUDED.validation_status,
                qa_status = EXCLUDED.qa_status,
                closeout_status = EXCLUDED.closeout_status,
                next_issue_candidate = EXCLUDED.next_issue_candidate,
                safety_mode = EXCLUDED.safety_mode,
                validation_expectations = EXCLUDED.validation_expectations,
                next_recommended_command = EXCLUDED.next_recommended_command,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            """,
            {
                "run_id": run["run_id"],
                "project_id": "project-aresforge",
                "parent_issue": run["parent_issue"],
                "target_issue": run["target_issue"],
                "current_step": run["current_step"],
                "status": run["status"],
                "selected_agent": run["selected_agent"],
                "model_tier": run["model_tier"],
                "branch_name": run["branch_name"],
                "commit_hash": run["commit_hash"],
                "pr_number": run["pr_number"],
                "validation_status": run["validation_status"],
                "qa_status": run["qa_status"],
                "closeout_status": run["closeout_status"],
                "next_issue_candidate": run["next_issue_candidate"],
                "safety_mode": safety_mode,
                "validation_expectations": json.dumps(validation_expectations),
                "next_recommended_command": next_recommended_command,
                "metadata": json.dumps(metadata),
            },
        )


def _persist_run_steps(conn: Connection, *, run_id: str, steps: list[dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM run_steps WHERE run_id = %s", (run_id,))
        for step in steps:
            cur.execute(
                """
                INSERT INTO run_steps (
                    id, run_id, step_order, step_type, status,
                    inputs, outputs, started_at, completed_at,
                    failure_reason, retry_count, requires_human_approval
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    f"step-{uuid4().hex[:12]}",
                    run_id,
                    step["step_order"],
                    step["step_type"],
                    step["status"],
                    json.dumps(step["inputs"]),
                    json.dumps(step["outputs"]),
                    step["started_at"],
                    step["completed_at"],
                    step["failure_reason"],
                    step["retry_count"],
                    step["requires_human_approval"],
                ),
            )
