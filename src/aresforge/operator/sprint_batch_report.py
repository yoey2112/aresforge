from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

COMMAND_NAME = "inspect-sprint-batch-report"
REPORT_VERSION = "m94.1"
QUEUE_PATH = Path(".aresforge") / "queue" / "work_items.json"
RUNS_PATH = Path(".aresforge") / "codex_dispatch" / "runs"

_BOUNDARY_CONFIRMATIONS = (
    "M94 sprint batch reporting is local-only.",
    "Report generation is read-only by default.",
    "Only an explicit --output path writes a local report artifact.",
    "Local git history is read with git log only.",
    "Local queue and dispatch run states are read from repo files only.",
    "No GitHub API calls.",
    "No gh calls.",
    "No external workflow execution.",
    "No Codex execution.",
    "No local LLM invocation.",
    "No queue mutation.",
    "No automatic next-item execution.",
)


def inspect_sprint_batch_report(
    config: AppConfig,
    *,
    since_commit: str | None = None,
    commit_count: int = 20,
    output: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    payload = build_sprint_batch_report(
        config,
        since_commit=since_commit,
        commit_count=commit_count,
    )
    markdown = _render_markdown(payload)
    fmt = str(output_format or "json").lower().strip()
    if fmt not in {"json", "markdown"}:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "error": "invalid_format",
            "details": {"format": output_format, "supported_formats": ["json", "markdown"]},
        }

    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (config.repo_root / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(payload, indent=2) if fmt == "json" else markdown
        output_path.write_text(content + "\n", encoding="utf-8")
        return {
            "command": COMMAND_NAME,
            "ok": bool(payload.get("ok", False)),
            "local_only": True,
            "format": fmt,
            "wrote_output_file": True,
            "output_path": str(output_path),
            "safety_boundary": payload["safety_boundary"],
            "boundary_confirmations": payload["boundary_confirmations"],
            "payload": payload,
        }

    return {
        "command": COMMAND_NAME,
        "ok": bool(payload.get("ok", False)),
        "local_only": True,
        "format": fmt,
        "wrote_output_file": False,
        "stdout": json.dumps(payload, indent=2) if fmt == "json" else markdown,
        "payload": payload,
    }


def build_sprint_batch_report(
    config: AppConfig,
    *,
    since_commit: str | None = None,
    commit_count: int = 20,
) -> dict[str, Any]:
    normalized_count = max(1, min(int(commit_count or 20), 200))
    commit_window = _collect_commit_window(config.repo_root, since_commit=since_commit, commit_count=normalized_count)
    queue = _load_queue(config.repo_root)
    queue_items = queue.get("items", []) if isinstance(queue.get("items"), list) else []
    commit_hashes = {str(item.get("hash", "")).strip() for item in commit_window.get("commits", [])}
    completed_items = _completed_items(queue_items, commit_hashes=commit_hashes)
    dispatch_summary = _dispatch_summary(config.repo_root, item_ids={str(item.get("item_id", "")) for item in completed_items})
    tests_summary = _tests_summary(completed_items)
    queue_posture = _queue_posture(queue_items)
    warnings = _unique(
        [
            *queue.get("warnings", []),
            *commit_window.get("warnings", []),
            *dispatch_summary.get("warnings", []),
            *queue_posture.get("warnings", []),
        ]
    )

    return {
        "ok": True,
        "local_only": True,
        "read_only_by_default": True,
        "report_name": "overnight_sprint_batch_report",
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_window": commit_window,
        "items_completed": {
            "count": len(completed_items),
            "items": completed_items,
        },
        "validation_evidence": tests_summary,
        "dispatch_runs": dispatch_summary,
        "queue_posture": queue_posture,
        "unresolved_warnings": warnings,
        "next_recommended_milestone": _next_recommended_milestone(queue_items),
        "safe_next_actions": [
            "Review unresolved_warnings before choosing more work.",
            "Inspect readiness for a selected proposed or ready item before starting it.",
            "Regenerate this report after the next sprint batch or after queue evidence is recorded.",
        ],
        "safety_boundary": {
            "local_only": True,
            "read_only_by_default": True,
            "writes_files_by_default": False,
            "explicit_output_write_only": True,
            "github_api_allowed": False,
            "gh_allowed": False,
            "external_workflow_allowed": False,
            "codex_execution_allowed": False,
            "local_llm_invocation_allowed": False,
            "queue_mutation_allowed": False,
            "automatic_next_item_execution_allowed": False,
        },
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }


def _collect_commit_window(repo_root: Path, *, since_commit: str | None, commit_count: int) -> dict[str, Any]:
    normalized_since = str(since_commit or "").strip()
    command = ("git", "log", "--oneline", f"{normalized_since}..HEAD") if normalized_since else (
        "git",
        "log",
        "-n",
        str(commit_count),
        "--oneline",
    )
    code, stdout, stderr = _run_git(repo_root, command)
    warnings: list[str] = []
    if code != 0:
        warnings.append(stderr.strip() or f"git log exited {code}")
    commits = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        short_hash, _, subject = stripped.partition(" ")
        commits.append({"hash": short_hash.strip(), "subject": subject.strip(), "raw": stripped})
    return {
        "mode": "since_commit" if normalized_since else "last_n_commits",
        "since_commit": normalized_since,
        "commit_count_requested": commit_count,
        "command": " ".join(command),
        "count": len(commits),
        "commits": commits,
        "warnings": warnings,
    }


def _run_git(repo_root: Path, command: tuple[str, ...]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            list(command),
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def _load_queue(repo_root: Path) -> dict[str, Any]:
    path = repo_root / QUEUE_PATH
    if not path.exists():
        return {"path": str(path), "items": [], "warnings": [f"Local queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"path": str(path), "items": [], "warnings": [f"Local queue could not be read: {exc}"]}
    items = raw.get("work_items", []) if isinstance(raw, dict) else []
    return {
        "path": str(path),
        "updated_at": raw.get("updated_at") if isinstance(raw, dict) else "",
        "items": [item for item in items if isinstance(item, dict)],
        "warnings": [],
    }


def _completed_items(items: list[dict[str, Any]], *, commit_hashes: set[str]) -> list[dict[str, Any]]:
    completed = []
    for item in items:
        if str(item.get("status", "")).strip() != "done":
            continue
        completion_commit = str(item.get("completion_commit", "")).strip()
        short_commit = completion_commit[:7]
        if commit_hashes and completion_commit not in commit_hashes and short_commit not in commit_hashes:
            continue
        completed.append(
            {
                "item_id": item.get("item_id"),
                "title": item.get("title"),
                "project_id": item.get("project_id"),
                "repo_id": item.get("repo_id"),
                "completed_at": item.get("completed_at"),
                "completed_by": item.get("completed_by"),
                "completion_commit": completion_commit,
                "validation_summary": item.get("validation_summary"),
                "evidence_note": item.get("evidence_note"),
                "tests_run": item.get("tests_run") if isinstance(item.get("tests_run"), list) else [],
                "changed_files": item.get("changed_files") if isinstance(item.get("changed_files"), list) else [],
            }
        )
    return sorted(completed, key=lambda item: str(item.get("completed_at") or ""), reverse=True)


def _tests_summary(completed_items: list[dict[str, Any]]) -> dict[str, Any]:
    tests: list[dict[str, str]] = []
    for item in completed_items:
        for test in item.get("tests_run", []):
            text = str(test).strip()
            if text:
                tests.append({"item_id": str(item.get("item_id", "")), "test": text})
    return {
        "tests_recorded_count": len(tests),
        "items_with_tests_count": len({entry["item_id"] for entry in tests}),
        "tests": tests,
    }


def _dispatch_summary(repo_root: Path, *, item_ids: set[str]) -> dict[str, Any]:
    runs_root = repo_root / RUNS_PATH
    states: list[dict[str, Any]] = []
    warnings: list[str] = []
    if runs_root.exists():
        for path in sorted(runs_root.rglob("run_state.json")):
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"Dispatch run state unreadable: {path}: {exc}")
                continue
            if not isinstance(state, dict):
                continue
            item_id = str(state.get("item_id", "")).strip()
            if item_ids and item_id not in item_ids:
                continue
            states.append(
                {
                    "run_id": str(state.get("run_id", path.parent.name)).strip(),
                    "item_id": item_id,
                    "dispatch_state": str(state.get("dispatch_state", "")).strip(),
                    "recovered": isinstance(state.get("recovery"), dict),
                    "review_required": bool(state.get("review_required", False)),
                    "validation_evidence_required": bool(state.get("validation_evidence_required", False)),
                    "error_summary": str(state.get("error_summary", "")).strip(),
                    "next_safe_action": str(state.get("next_safe_action", "")).strip(),
                }
            )
    state_counts = Counter(str(item.get("dispatch_state") or "unknown") for item in states)
    return {
        "runs_root": str(runs_root),
        "run_count": len(states),
        "state_counts": dict(sorted(state_counts.items())),
        "recovered_count": sum(1 for item in states if item.get("recovered")),
        "review_required_count": sum(1 for item in states if item.get("review_required")),
        "runs": sorted(states, key=lambda item: str(item.get("run_id") or ""), reverse=True),
        "warnings": warnings,
    }


def _queue_posture(items: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(str(item.get("status") or "unknown").strip() for item in items)
    active = [
        _queue_item_row(item)
        for item in items
        if str(item.get("status", "")).strip() in {"proposed", "ready", "in_progress", "blocked"}
    ]
    warnings = []
    blocked = [item for item in active if str(item.get("status")) == "blocked"]
    if blocked:
        warnings.append(f"{len(blocked)} queue item(s) are blocked.")
    return {
        "item_count": len(items),
        "status_counts": dict(sorted(status_counts.items())),
        "active_items": sorted(active, key=lambda item: str(item.get("updated_at") or ""), reverse=True),
        "warnings": warnings,
    }


def _queue_item_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": item.get("item_id"),
        "title": item.get("title"),
        "status": item.get("status"),
        "priority": item.get("priority"),
        "item_type": item.get("item_type"),
        "updated_at": item.get("updated_at"),
        "dependencies": item.get("dependencies") if isinstance(item.get("dependencies"), list) else [],
    }


def _next_recommended_milestone(items: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        _queue_item_row(item)
        for item in items
        if str(item.get("status", "")).strip() in {"ready", "proposed"}
    ]
    candidates.sort(key=lambda item: (str(item.get("status") != "ready"), str(item.get("updated_at") or "")))
    if candidates:
        selected = candidates[0]
        return {
            "available": True,
            "item_id": selected.get("item_id"),
            "title": selected.get("title"),
            "status": selected.get("status"),
            "next_safe_action": f"Inspect readiness for {selected.get('item_id')} before starting it manually.",
        }
    return {
        "available": False,
        "item_id": "",
        "title": "",
        "status": "",
        "next_safe_action": "No proposed or ready queue item is available; review roadmap before seeding more work.",
    }


def _unique(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _render_markdown(payload: dict[str, Any]) -> str:
    commit_window = payload.get("commit_window", {}) if isinstance(payload.get("commit_window"), dict) else {}
    items_completed = payload.get("items_completed", {}) if isinstance(payload.get("items_completed"), dict) else {}
    queue_posture = payload.get("queue_posture", {}) if isinstance(payload.get("queue_posture"), dict) else {}
    dispatch = payload.get("dispatch_runs", {}) if isinstance(payload.get("dispatch_runs"), dict) else {}
    tests = payload.get("validation_evidence", {}) if isinstance(payload.get("validation_evidence"), dict) else {}
    next_milestone = payload.get("next_recommended_milestone", {}) if isinstance(payload.get("next_recommended_milestone"), dict) else {}
    lines = [
        "# Overnight Sprint Batch Report",
        "",
        f"- report_version: {payload.get('report_version')}",
        f"- local_only: {payload.get('local_only')}",
        f"- read_only_by_default: {payload.get('read_only_by_default')}",
        f"- commits: {commit_window.get('count', 0)}",
        f"- completed_items: {items_completed.get('count', 0)}",
        f"- tests_recorded: {tests.get('tests_recorded_count', 0)}",
        f"- dispatch_runs: {dispatch.get('run_count', 0)}",
        f"- recovered_dispatch_runs: {dispatch.get('recovered_count', 0)}",
        f"- queue_status_counts: {queue_posture.get('status_counts', {})}",
        f"- next_recommended_item: {next_milestone.get('item_id') or '-'}",
        "",
        "## Safe Next Actions",
    ]
    lines.extend(f"- {item}" for item in payload.get("safe_next_actions", []))
    warnings = payload.get("unresolved_warnings", [])
    lines.extend(["", "## Unresolved Warnings"])
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- None")
    return "\n".join(lines)
