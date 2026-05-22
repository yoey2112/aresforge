from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any
from uuid import uuid4

from psycopg import Connection

from aresforge.artifacts.store import write_markdown_json_bundle
from aresforge.config import AppConfig

COMMAND_NAME = "run-autonomous-cycle"
INSPECT_COMMAND_NAME = "inspect-autonomous-run"

MODE_DRY_RUN = "dry-run"
MODE_LOCAL_WRITE = "local-write"
MODE_BRANCH_WRITE = "branch-write"
MODE_PUSH_PR = "push-pr"
MODE_CLOSEOUT_ELIGIBLE = "closeout-eligible"

SUPPORTED_MODES = (
    MODE_DRY_RUN,
    MODE_LOCAL_WRITE,
    MODE_BRANCH_WRITE,
    MODE_PUSH_PR,
    MODE_CLOSEOUT_ELIGIBLE,
)


@dataclass(frozen=True)
class StepResult:
    step_type: str
    status: str
    started_at: str
    completed_at: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    failure_reason: str | None = None
    requires_human_approval: bool = False


def run_autonomous_cycle(
    config: AppConfig,
    *,
    conn: Connection,
    mode: str,
    parent_issue: int,
    target_issue: int,
    title: str | None = None,
    branch_name: str | None = None,
    commit_message: str | None = None,
    pr_title: str | None = None,
    pr_body: str | None = None,
    validation_commands: list[str] | None = None,
    allow_empty_commit: bool = False,
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "error": "unsupported_mode",
            "supported_modes": list(SUPPORTED_MODES),
        }

    run_id = f"run-m16-{target_issue}-{uuid4().hex[:10]}"
    now = _now_iso()
    run = {
        "run_id": run_id,
        "project_id": "project-aresforge",
        "parent_issue": parent_issue,
        "target_issue": target_issue,
        "current_step": "initialize",
        "status": "running",
        "selected_agent": "lifecycle-controller-agent",
        "model_tier": "human-gated",
        "branch_name": branch_name,
        "commit_hash": None,
        "pr_number": None,
        "pr_url": None,
        "validation_status": "pending",
        "qa_status": "pending",
        "closeout_status": "pending",
        "next_issue_candidate": None,
        "safety_mode": mode,
        "validation_expectations": validation_commands
        or ["python -m pytest", "python -m aresforge inspect-repo-governance"],
        "next_recommended_command": f"python -m aresforge {INSPECT_COMMAND_NAME} --run-id {run_id}",
        "metadata": {
            "title": title or f"M16 autonomous run for issue #{target_issue}",
            "constraints": _constraint_lines(),
            "created_at": now,
        },
    }
    _upsert_run(conn, run)

    step_results: list[StepResult] = []

    gates = _evaluate_gates(
        config,
        mode=mode,
        branch_name=branch_name,
        commit_message=commit_message,
        pr_title=pr_title,
        validation_commands=run["validation_expectations"],
    )
    step_results.append(
        _step(
            "evaluate_safety_gates",
            "passed" if gates["ok"] else "failed",
            {"mode": mode},
            gates,
            failure_reason=None if gates["ok"] else "safety_gates_failed",
        )
    )
    if not gates["ok"]:
        return _finalize_failed_run(conn, config, run, step_results, "safety_gates_failed")

    if mode in (MODE_DRY_RUN, MODE_LOCAL_WRITE, MODE_BRANCH_WRITE, MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
        validation_outputs = _run_validations(run["validation_expectations"], cwd=config.repo_root)
        validation_ok = all(item["ok"] for item in validation_outputs)
        run["validation_status"] = "passed" if validation_ok else "failed"
        step_results.append(
            _step(
                "run_validations",
                "passed" if validation_ok else "failed",
                {"commands": run["validation_expectations"]},
                {"results": validation_outputs},
                failure_reason=None if validation_ok else "validation_failed",
            )
        )
        if not validation_ok and mode in (MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
            return _finalize_failed_run(conn, config, run, step_results, "validation_failed")

    if mode in (MODE_BRANCH_WRITE, MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
        created_branch = _ensure_branch(branch_name or f"codex/m16-issue-{target_issue}", cwd=config.repo_root)
        run["branch_name"] = created_branch["branch"]
        step_results.append(
            _step(
                "git_branch_create",
                "passed" if created_branch["ok"] else "failed",
                {"requested_branch": branch_name},
                created_branch,
                failure_reason=None if created_branch["ok"] else "branch_create_failed",
            )
        )
        if not created_branch["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "branch_create_failed")

        committed = _create_commit(
            message=commit_message or f"M16 autonomous cycle issue #{target_issue}",
            cwd=config.repo_root,
            allow_empty_commit=allow_empty_commit,
        )
        run["commit_hash"] = committed.get("commit_hash")
        step_results.append(
            _step(
                "git_commit_create",
                "passed" if committed["ok"] else "failed",
                {"allow_empty_commit": allow_empty_commit},
                committed,
                failure_reason=None if committed["ok"] else "commit_create_failed",
            )
        )
        if not committed["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "commit_create_failed")

    if mode in (MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
        pushed = _push_branch(run["branch_name"], cwd=config.repo_root)
        step_results.append(
            _step(
                "git_push_branch",
                "passed" if pushed["ok"] else "failed",
                {"branch_name": run["branch_name"]},
                pushed,
                failure_reason=None if pushed["ok"] else "push_failed",
            )
        )
        if not pushed["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "push_failed")

        pr = _create_pr(
            repo_slug=f"{config.github_owner}/{config.github_repo}",
            title=pr_title or f"M16 autonomous cycle for issue #{target_issue}",
            body=pr_body
            or f"Implements work for #{target_issue}. Parent issue: #{parent_issue}.",
            base="main",
            head=run["branch_name"],
            cwd=config.repo_root,
        )
        run["pr_number"] = pr.get("pr_number")
        run["pr_url"] = pr.get("pr_url")
        run["qa_status"] = "pending_review"
        step_results.append(
            _step(
                "gh_pr_create",
                "passed" if pr["ok"] else "failed",
                {"head": run["branch_name"]},
                pr,
                failure_reason=None if pr["ok"] else "pr_create_failed",
            )
        )
        if not pr["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "pr_create_failed")

    if mode == MODE_CLOSEOUT_ELIGIBLE:
        closeout_gate = _evaluate_closeout_gate(run=run)
        step_results.append(
            _step(
                "evaluate_closeout_eligibility",
                "passed" if closeout_gate["ok"] else "failed",
                {"target_issue": target_issue},
                closeout_gate,
                failure_reason=None if closeout_gate["ok"] else "closeout_gate_failed",
                requires_human_approval=True,
            )
        )
        if not closeout_gate["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "closeout_gate_failed")

        closed = _close_issue(
            repo_slug=f"{config.github_owner}/{config.github_repo}",
            issue_number=target_issue,
            cwd=config.repo_root,
        )
        run["closeout_status"] = "closed" if closed["ok"] else "failed"
        step_results.append(
            _step(
                "gh_issue_close",
                "passed" if closed["ok"] else "failed",
                {"issue_number": target_issue},
                closed,
                failure_reason=None if closed["ok"] else "issue_close_failed",
            )
        )
        if not closed["ok"]:
            return _finalize_failed_run(conn, config, run, step_results, "issue_close_failed")

    run["status"] = "completed"
    run["current_step"] = "complete"
    _upsert_run(conn, run)
    _persist_step_results(conn, run_id=run_id, step_results=step_results)
    evidence = _write_evidence(config, run, step_results)
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "mode": mode,
        "run_id": run_id,
        "status": run["status"],
        "run": run,
        "run_steps": [_step_to_dict(item) for item in step_results],
        "evidence": evidence,
        "boundary_confirmations": _constraint_lines(),
    }


def inspect_autonomous_run(conn: Connection, *, run_id: str) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT run_id, parent_issue, target_issue, current_step, status,
                   selected_agent, model_tier, branch_name, commit_hash, pr_number, pr_url,
                   validation_status, qa_status, closeout_status, safety_mode,
                   validation_expectations, next_recommended_command, metadata,
                   created_at, updated_at
            FROM autonomous_runs
            WHERE run_id = %s
            """,
            (run_id,),
        )
        run = cur.fetchone()
        if run is None:
            return {
                "command": INSPECT_COMMAND_NAME,
                "ok": False,
                "error": "run_not_found",
                "run_id": run_id,
            }
        cur.execute(
            """
            SELECT step_order, step_type, status, inputs, outputs,
                   started_at, completed_at, failure_reason, retry_count, requires_human_approval
            FROM run_steps
            WHERE run_id = %s
            ORDER BY step_order ASC
            """,
            (run_id,),
        )
        steps = list(cur.fetchall())

    return {
        "command": INSPECT_COMMAND_NAME,
        "ok": True,
        "run": run,
        "steps": steps,
    }


def _finalize_failed_run(
    conn: Connection,
    config: AppConfig,
    run: dict[str, Any],
    step_results: list[StepResult],
    failure_reason: str,
) -> dict[str, Any]:
    run["status"] = "failed"
    run["current_step"] = "failed"
    _upsert_run(conn, run)
    _persist_step_results(conn, run_id=run["run_id"], step_results=step_results)
    evidence = _write_evidence(config, run, step_results)
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "mode": run["safety_mode"],
        "run_id": run["run_id"],
        "error": failure_reason,
        "run": run,
        "run_steps": [_step_to_dict(item) for item in step_results],
        "evidence": evidence,
    }


def _evaluate_gates(
    config: AppConfig,
    *,
    mode: str,
    branch_name: str | None,
    commit_message: str | None,
    pr_title: str | None,
    validation_commands: list[str],
) -> dict[str, Any]:
    failed: list[str] = []
    docs_required = [
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
    ]
    missing_docs = [item for item in docs_required if not (config.repo_root / item).exists()]
    if missing_docs:
        failed.append("required_docs_missing")
    if not validation_commands:
        failed.append("validation_commands_missing")

    if mode in (MODE_BRANCH_WRITE, MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
        if not branch_name:
            failed.append("branch_name_required")
        if not commit_message:
            failed.append("commit_message_required")

    if mode in (MODE_PUSH_PR, MODE_CLOSEOUT_ELIGIBLE):
        if not pr_title:
            failed.append("pr_title_required")

    return {
        "ok": not failed,
        "failed_gates": failed,
        "mode": mode,
        "missing_docs": missing_docs,
    }


def _evaluate_closeout_gate(*, run: dict[str, Any]) -> dict[str, Any]:
    failed: list[str] = []
    if run.get("validation_status") != "passed":
        failed.append("validation_not_passed")
    if not run.get("pr_number"):
        failed.append("pr_linkage_missing")
    if not run.get("pr_url"):
        failed.append("pr_url_missing")
    if not run.get("target_issue"):
        failed.append("target_issue_missing")
    return {"ok": not failed, "failed_gates": failed}


def _run_validations(commands: list[str], *, cwd: Path) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        )
        outputs.append(
            {
                "command": command,
                "ok": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )
    return outputs


def _ensure_branch(branch_name: str, *, cwd: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and "already exists" in (result.stderr or ""):
        switch = subprocess.run(
            ["git", "checkout", branch_name],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        result = switch
    return {
        "ok": result.returncode == 0,
        "branch": branch_name,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _create_commit(*, message: str, cwd: Path, allow_empty_commit: bool) -> dict[str, Any]:
    subprocess.run(["git", "add", "-A"], cwd=cwd, capture_output=True, text=True, check=False)
    cmd = ["git", "commit", "-m", message]
    if allow_empty_commit:
        cmd.append("--allow-empty")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ok": rev.returncode == 0,
        "commit_hash": rev.stdout.strip() if rev.returncode == 0 else None,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _push_branch(branch_name: str | None, *, cwd: Path) -> dict[str, Any]:
    if not branch_name:
        return {"ok": False, "error": "branch_missing"}
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch_name],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _create_pr(
    *, repo_slug: str, title: str, body: str, base: str, head: str | None, cwd: Path
) -> dict[str, Any]:
    if not head:
        return {"ok": False, "error": "head_branch_missing"}
    result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo_slug,
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
            "--head",
            head,
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    pr_number = None
    pr_url = _extract_pr_url(result.stdout) or _extract_pr_url(result.stderr)
    if pr_url is not None:
        pr_number = _extract_pr_number_from_url(pr_url)

    existing_pr_detected = (
        result.returncode != 0 and "already exists" in (result.stderr or "").lower() and pr_url is not None
    )

    if result.returncode == 0 or existing_pr_detected:
        view = subprocess.run(
            ["gh", "pr", "view", "--repo", repo_slug, "--json", "number,url", "--head", head],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if view.returncode == 0:
            try:
                payload = json.loads(view.stdout)
                if isinstance(payload, dict):
                    if isinstance(payload.get("number"), int):
                        pr_number = payload["number"]
                    if isinstance(payload.get("url"), str) and payload["url"].strip():
                        pr_url = payload["url"].strip()
                        if pr_number is None:
                            pr_number = _extract_pr_number_from_url(pr_url)
            except json.JSONDecodeError:
                pass
    return {
        "ok": result.returncode == 0 or existing_pr_detected,
        "existing_pr_detected": existing_pr_detected,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _extract_pr_url(stdout: str) -> str | None:
    if not stdout:
        return None
    match = re.search(r"https://github\.com/\S+/pull/\d+", stdout)
    if not match:
        return None
    return match.group(0).rstrip(").,")


def _extract_pr_number_from_url(pr_url: str) -> int | None:
    match = re.search(r"/pull/(\d+)$", pr_url)
    if not match:
        return None
    return int(match.group(1))


def _close_issue(*, repo_slug: str, issue_number: int, cwd: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "gh",
            "issue",
            "close",
            str(issue_number),
            "--repo",
            repo_slug,
            "--reason",
            "completed",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _step(
    step_type: str,
    status: str,
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    *,
    failure_reason: str | None,
    requires_human_approval: bool = False,
) -> StepResult:
    now = _now_iso()
    return StepResult(
        step_type=step_type,
        status=status,
        started_at=now,
        completed_at=now,
        inputs=inputs,
        outputs=outputs,
        failure_reason=failure_reason,
        requires_human_approval=requires_human_approval,
    )


def _persist_step_results(conn: Connection, *, run_id: str, step_results: list[StepResult]) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM run_steps WHERE run_id = %s", (run_id,))
        for index, item in enumerate(step_results, start=1):
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
                    index,
                    item.step_type,
                    item.status,
                    json.dumps(item.inputs),
                    json.dumps(item.outputs),
                    item.started_at,
                    item.completed_at,
                    item.failure_reason,
                    0,
                    item.requires_human_approval,
                ),
            )


def _upsert_run(conn: Connection, run: dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO autonomous_runs (
                run_id, project_id, parent_issue, target_issue, current_step, status,
                selected_agent, model_tier, branch_name, commit_hash, pr_number, pr_url,
                validation_status, qa_status, closeout_status, next_issue_candidate,
                safety_mode, validation_expectations, next_recommended_command, metadata
            ) VALUES (
                %(run_id)s, %(project_id)s, %(parent_issue)s, %(target_issue)s, %(current_step)s, %(status)s,
                %(selected_agent)s, %(model_tier)s, %(branch_name)s, %(commit_hash)s, %(pr_number)s, %(pr_url)s,
                %(validation_status)s, %(qa_status)s, %(closeout_status)s, %(next_issue_candidate)s,
                %(safety_mode)s, %(validation_expectations)s::jsonb, %(next_recommended_command)s, %(metadata)s::jsonb
            )
            ON CONFLICT (run_id) DO UPDATE
            SET current_step = EXCLUDED.current_step,
                status = EXCLUDED.status,
                branch_name = EXCLUDED.branch_name,
                commit_hash = EXCLUDED.commit_hash,
                pr_number = EXCLUDED.pr_number,
                pr_url = EXCLUDED.pr_url,
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
                **run,
                "validation_expectations": json.dumps(run["validation_expectations"]),
                "metadata": json.dumps(run["metadata"]),
            },
        )


def _step_to_dict(item: StepResult) -> dict[str, Any]:
    return {
        "step_type": item.step_type,
        "status": item.status,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
        "inputs": item.inputs,
        "outputs": item.outputs,
        "failure_reason": item.failure_reason,
        "requires_human_approval": item.requires_human_approval,
    }


def _write_evidence(config: AppConfig, run: dict[str, Any], step_results: list[StepResult]) -> dict[str, str]:
    payload = {
        "command": COMMAND_NAME,
        "run": run,
        "steps": [_step_to_dict(item) for item in step_results],
        "constraints": _constraint_lines(),
    }
    markdown_lines = [
        f"# Autonomous run {run['run_id']}",
        "",
        f"- mode: `{run['safety_mode']}`",
        f"- status: `{run['status']}`",
        f"- parent issue: `#{run['parent_issue']}`",
        f"- target issue: `#{run['target_issue']}`",
        "",
        "## Step Timeline",
    ]
    markdown_lines.extend(
        [f"- {item.step_type}: {item.status}" for item in step_results] or ["- none"]
    )
    markdown_lines.extend(["", "## Safety Constraints"])
    markdown_lines.extend([f"- {item}" for item in _constraint_lines()])

    bundle = write_markdown_json_bundle(
        config.evidence_dir,
        title=f"autonomous-run-{run['run_id']}",
        markdown="\n".join(markdown_lines),
        payload=payload,
    )
    return {
        "markdown_path": str(bundle.markdown_path),
        "json_path": str(bundle.json_path),
    }


def _constraint_lines() -> list[str]:
    return [
        "No mutation in dry-run mode.",
        "No GitHub mutation in local-write or branch-write mode.",
        "Push/PR creation requires explicit push-pr mode.",
        "Issue closeout requires explicit closeout-eligible mode.",
        "No automatic PR merge.",
        "No background scheduling or unattended execution.",
    ]


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
