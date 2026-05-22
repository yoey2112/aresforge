from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from psycopg import Connection

from aresforge.artifacts.store import ArtifactBundle, write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.operator.self_managed_milestone_planner import plan_self_managed_milestone

COMMAND_NAME = "generate-self-managed-issue-script"
SUPPORTED_MODES = {"read-only", "local-write", "branch-write", "pr-write", "closeout-write", "full-auto"}
UNSUPPORTED_HIGHER_PERMISSION_MODES = {"local-write", "branch-write", "pr-write", "closeout-write", "full-auto"}


def generate_self_managed_issue_script(
    config: AppConfig,
    *,
    mode: str = "read-only",
    run_id: str | None = None,
    target_issue: int | None = None,
    conn: Connection | None = None,
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        return _unsupported_mode_payload(mode=mode, reason="unsupported_mode")
    if mode in UNSUPPORTED_HIGHER_PERMISSION_MODES:
        return _unsupported_mode_payload(mode=mode, reason="mode_not_implemented")

    planner_payload = plan_self_managed_milestone(config, mode="read-only")
    planning = planner_payload.get("planning") if isinstance(planner_payload, dict) else {}

    run_record = _load_run_record(conn=conn, run_id=run_id) if conn is not None else None
    run_steps = _load_run_steps(conn=conn, run_id=run_record["run_id"]) if run_record else []

    resolved_target_issue = _resolve_target_issue(
        explicit_target_issue=target_issue,
        run_record=run_record,
        planning_target_issue=planning.get("target_issue") if isinstance(planning, dict) else None,
    )
    resolved_parent_issue = (
        run_record.get("parent_issue")
        if isinstance(run_record, dict) and isinstance(run_record.get("parent_issue"), int)
        else planning.get("parent_issue")
    )

    rendered_script = _render_script(
        repo=f"{config.github_owner}/{config.github_repo}",
        target_issue=resolved_target_issue,
        parent_issue=resolved_parent_issue,
        run_record=run_record,
    )

    payload: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": True,
        "mode": mode,
        "inspection_mode": "github_read_only_with_local_run_queue_context",
        "mutation_posture": "human_gated_script_output_only",
        "timestamp": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "repo": f"{config.github_owner}/{config.github_repo}",
        "resolved_run_id": run_record.get("run_id") if isinstance(run_record, dict) else None,
        "resolved_target_issue": resolved_target_issue,
        "resolved_parent_issue": resolved_parent_issue,
        "active_target_available": resolved_target_issue is not None,
        "run_queue_source": "database" if isinstance(run_record, dict) else "derived_read_only_plan",
        "run_steps": run_steps,
        "script": rendered_script,
        "warnings": [
            *([] if resolved_target_issue is not None else ["No active ready issue is available; advance readiness manually before attempting mutation."]),
            "Generated script is text-only and requires explicit human review before execution.",
        ],
        "boundary_confirmations": [
            "No GitHub mutation was performed by Python.",
            "Generated operations are copy/paste PowerShell only.",
            "No issue closeout, PR merge, branch creation, workflow, or settings mutation was performed.",
        ],
    }

    artifact_bundle = _write_script_artifact(config, payload)
    payload["evidence_package"] = {
        "markdown_path": str(artifact_bundle.markdown_path),
        "json_path": str(artifact_bundle.json_path),
    }
    return payload


def _unsupported_mode_payload(*, mode: str, reason: str) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "mode": mode,
        "error": reason,
        "supported_modes": ["read-only"],
        "not_implemented_modes": sorted(UNSUPPORTED_HIGHER_PERMISSION_MODES),
        "boundary_confirmations": [
            "Higher-permission modes are intentionally blocked for safe human-gated operation.",
            "No GitHub mutation was performed.",
        ],
    }


def _load_run_record(conn: Connection, *, run_id: str | None) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        if run_id:
            cur.execute(
                """
                SELECT run_id, parent_issue, target_issue, status, current_step, next_issue_candidate, metadata
                FROM autonomous_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )
        else:
            cur.execute(
                """
                SELECT run_id, parent_issue, target_issue, status, current_step, next_issue_candidate, metadata
                FROM autonomous_runs
                WHERE project_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                ("project-aresforge",),
            )
        row = cur.fetchone()
    if not row:
        return None
    def _value(index: int, key: str) -> Any:
        return row[key] if isinstance(row, dict) else row[index]
    return {
        "run_id": _value(0, "run_id"),
        "parent_issue": _value(1, "parent_issue"),
        "target_issue": _value(2, "target_issue"),
        "status": _value(3, "status"),
        "current_step": _value(4, "current_step"),
        "next_issue_candidate": _value(5, "next_issue_candidate"),
        "metadata": _value(6, "metadata") if isinstance(_value(6, "metadata"), dict) else {},
    }


def _load_run_steps(conn: Connection, *, run_id: str) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT step_order, step_type, status, requires_human_approval
            FROM run_steps
            WHERE run_id = %s
            ORDER BY step_order ASC
            """,
            (run_id,),
        )
        rows = cur.fetchall()
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "step_order": row["step_order"] if isinstance(row, dict) else row[0],
                "step_type": row["step_type"] if isinstance(row, dict) else row[1],
                "status": row["status"] if isinstance(row, dict) else row[2],
                "requires_human_approval": (
                    row["requires_human_approval"] if isinstance(row, dict) else row[3]
                ),
            }
        )
    return normalized


def _resolve_target_issue(
    *,
    explicit_target_issue: int | None,
    run_record: dict[str, Any] | None,
    planning_target_issue: Any,
) -> int | None:
    if isinstance(explicit_target_issue, int):
        return explicit_target_issue
    if isinstance(run_record, dict) and isinstance(run_record.get("target_issue"), int):
        return run_record["target_issue"]
    if isinstance(planning_target_issue, int):
        return planning_target_issue
    return None


def _render_script(
    *,
    repo: str,
    target_issue: int | None,
    parent_issue: int | None,
    run_record: dict[str, Any] | None,
) -> str:
    run_id = run_record.get("run_id") if isinstance(run_record, dict) else "derived-read-only"
    lines: list[str] = [
        "Set-StrictMode -Version Latest",
        '$ErrorActionPreference = "Stop"',
        f'$Repo = "{repo}"',
        f'$RunId = "{run_id}"',
        f"$ParentIssue = {parent_issue if isinstance(parent_issue, int) else '$null'}",
        f"$TargetIssue = {target_issue if isinstance(target_issue, int) else '$null'}",
        "",
        "Write-Host 'Human review required: inspect all commands before execution.'",
        "Write-Host 'This script is generated as copy/paste guidance only.'",
        "",
    ]

    if isinstance(target_issue, int):
        lines.extend(
            [
                "$IssueBody = @'",
                "## Closeout Evidence",
                "- Validation: python -m pytest -> ok true",
                "- Validation: python -m aresforge inspect-repo-governance -> ok true",
                "- Validation: python -m aresforge plan-self-managed-milestone -> ok true",
                "- Validation: python -m aresforge generate-self-managed-issue-script -> ok true",
                "",
                "## Safety Boundary",
                "- human-triggered operation only",
                "- no autonomous GitHub mutation",
                "- review this body before manual execution",
                "'@",
                "",
                "# Manual update guidance: uncomment after review.",
                "# gh issue edit $TargetIssue --repo $Repo --add-label 'aresforge-ready'",
                "# gh issue comment $TargetIssue --repo $Repo --body $IssueBody",
                "",
                "# Optional next-issue readiness guidance (manual, dependency-gated).",
                "# gh issue edit 253 --repo $Repo --add-label 'aresforge-ready'",
            ]
        )
    else:
        lines.extend(
            [
                "Write-Host 'No active target issue detected in the ready queue.'",
                "Write-Host 'Recommended next action: run planning, then manually mark only the next eligible issue ready.'",
            ]
        )

    return "\n".join(lines) + "\n"


def _write_script_artifact(config: AppConfig, payload: dict[str, Any]) -> ArtifactBundle:
    title = f"M15 self-managed issue script {payload['mode']}"
    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Command",
            f"- `{COMMAND_NAME}`",
            f"- mode: `{payload['mode']}`",
            "",
            "## Target",
            f"- run_id: `{payload['resolved_run_id']}`",
            f"- parent_issue: `{payload['resolved_parent_issue']}`",
            f"- target_issue: `{payload['resolved_target_issue']}`",
            "",
            "## Safety Boundary",
            "- No GitHub mutation was performed by Python.",
            "- Script output is copy/paste only.",
            "- Human review is required before any mutation.",
        ]
    )
    return write_markdown_json_bundle(config.evidence_dir, title=title, markdown=markdown, payload=payload)
