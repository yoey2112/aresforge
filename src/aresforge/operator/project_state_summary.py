from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig

_SOURCE_OF_TRUTH_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
)

_RELEVANT_DOCS: tuple[str, ...] = (
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
    "docs/operator/BATCH_READY_ISSUE_OPERATIONS.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/architecture/MODEL_ROUTING_STRATEGY.md",
    "docs/architecture/ISSUE_LIFECYCLE_AGENT_PIPELINE.md",
    "docs/planning/FUTURE_FEATURE_IDEAS.md",
)

_ARTIFACT_DIRS: tuple[tuple[str, str], ...] = (
    ("prompts", "artifacts/prompts/generated"),
    ("evidence", "artifacts/evidence/generated"),
    ("codex_handoffs", "artifacts/codex_handoffs/generated"),
    ("local_reviews", "artifacts/local_reviews/generated"),
    ("ready_issue_batches", "artifacts/ready_issue_batches/generated"),
)


def project_state_summary(config: AppConfig) -> dict[str, Any]:
    warnings: list[str] = []

    repository = _repository_summary(config, warnings)
    github = _github_summary(config, warnings)
    documentation = _documentation_summary(config, warnings)
    artifacts = _artifact_summary(config)
    milestone = _milestone_summary(config.repo_root, documentation, warnings)

    return {
        "command": "project-state-summary",
        "ok": True,
        "inspection_mode": "local_first_read_only",
        "repository": repository,
        "github": github,
        "documentation": documentation,
        "artifacts": artifacts,
        "milestone": milestone,
        "recommended_next_action": _recommended_next_action(
            repository=repository,
            github=github,
            warnings=warnings,
        ),
        "warnings": warnings,
        "boundary_confirmations": [
            "Read-only local-first summary only.",
            "No git, file, GitHub issue, PR, label, milestone, or artifact mutation was performed.",
            "No background jobs, polling, or schedulers were used.",
            "Issue #39 remains historical retired validation evidence and is not modified.",
        ],
    }


def _run_command(args: list[str], cwd: Path) -> tuple[bool, int | None, str, str]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, None, "", "command_not_found"
    except OSError as exc:
        return False, None, "", str(exc)

    return True, result.returncode, result.stdout, result.stderr


def _repository_summary(config: AppConfig, warnings: list[str]) -> dict[str, Any]:
    repo_root = config.repo_root
    branch: str | None = None
    working_tree_clean: bool | None = None
    local_commit: dict[str, str] | None = None
    origin_main_commit: dict[str, str] | None = None
    head_matches_origin_main: bool | None = None

    available, code, stdout, stderr = _run_command(["git", "branch", "--show-current"], repo_root)
    if not available:
        warnings.append("git command unavailable; repository summary is partial.")
    elif code == 0:
        branch = stdout.strip() or None
    else:
        warnings.append(f"git branch inspection failed: {stderr.strip() or 'unknown_error'}")

    if available:
        status_ok, status_code, status_stdout, status_stderr = _run_command(
            ["git", "status", "--porcelain"], repo_root
        )
        if status_ok and status_code == 0:
            working_tree_clean = status_stdout.strip() == ""
        elif status_ok:
            warnings.append(
                f"git working tree inspection failed: {status_stderr.strip() or 'unknown_error'}"
            )

        local_commit = _git_commit(repo_root, ["git", "log", "-1", "--pretty=format:%H%x09%s"])
        if local_commit is None:
            warnings.append("local HEAD commit summary unavailable.")

        origin_main_commit = _git_commit(
            repo_root, ["git", "log", "-1", "--pretty=format:%H%x09%s", "origin/main"]
        )
        if origin_main_commit is None:
            warnings.append("origin/main commit summary unavailable (no remote, no fetch, or offline).")

        if local_commit and origin_main_commit:
            head_matches_origin_main = local_commit["sha"] == origin_main_commit["sha"]

    return {
        "repo_root": str(repo_root),
        "current_branch": branch,
        "working_tree_clean": working_tree_clean,
        "latest_local_commit": local_commit,
        "latest_origin_main_commit": origin_main_commit,
        "head_matches_origin_main": head_matches_origin_main,
    }


def _git_commit(repo_root: Path, command: list[str]) -> dict[str, str] | None:
    available, code, stdout, _stderr = _run_command(command, repo_root)
    if not available or code != 0:
        return None
    line = stdout.strip()
    if not line:
        return None
    parts = line.split("\t", 1)
    sha = parts[0].strip()
    subject = parts[1].strip() if len(parts) > 1 else ""
    if not sha:
        return None
    return {"sha": sha, "subject": subject}


def _github_summary(config: AppConfig, warnings: list[str]) -> dict[str, Any]:
    repo_slug = f"{config.github_owner}/{config.github_repo}"
    issues, issue_warning = _gh_list(
        config.repo_root,
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "open",
            "--limit",
            "20",
            "--json",
            "number,title,url",
        ],
        "open issues",
    )
    if issue_warning:
        warnings.append(issue_warning)

    prs, pr_warning = _gh_list(
        config.repo_root,
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "open",
            "--limit",
            "20",
            "--json",
            "number,title,url",
        ],
        "open pull requests",
    )
    if pr_warning:
        warnings.append(pr_warning)

    return {
        "repo": repo_slug,
        "open_issues_count": len(issues) if issues is not None else None,
        "open_issues": issues or [],
        "open_prs_count": len(prs) if prs is not None else None,
        "open_prs": prs or [],
    }


def _gh_list(repo_root: Path, command: list[str], label: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    available, code, stdout, stderr = _run_command(command, repo_root)
    if not available:
        return None, f"gh command unavailable; {label} summary is unavailable."
    if code != 0:
        message = stderr.strip() or "unknown_error"
        return None, f"gh {label} query failed: {message}"
    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, f"gh {label} query returned invalid JSON: {exc}"
    if not isinstance(raw, list):
        return None, f"gh {label} query returned unexpected JSON shape."

    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        number = item.get("number")
        if not isinstance(number, int):
            continue
        rows.append(
            {
                "number": number,
                "title": item.get("title"),
                "url": item.get("url"),
            }
        )
    rows.sort(key=lambda row: row["number"])
    return rows, None


def _documentation_summary(config: AppConfig, warnings: list[str]) -> dict[str, Any]:
    source_of_truth = _doc_entries(config.repo_root, _SOURCE_OF_TRUTH_DOCS)
    relevant_docs = _doc_entries(config.repo_root, _RELEVANT_DOCS)

    missing_source_docs = [item["path"] for item in source_of_truth if not item["exists"]]
    if missing_source_docs:
        warnings.append(
            "Missing source-of-truth docs: " + ", ".join(missing_source_docs)
        )

    return {
        "source_of_truth_docs": source_of_truth,
        "relevant_docs": relevant_docs,
    }


def _doc_entries(repo_root: Path, relative_paths: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative_path in relative_paths:
        path = repo_root / relative_path
        rows.append(
            {
                "path": relative_path,
                "exists": path.exists(),
                "modified_at": _modified_at(path),
            }
        )
    return rows


def _artifact_summary(config: AppConfig) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for category, relative_root in _ARTIFACT_DIRS:
        latest = _latest_file(config.repo_root / relative_root)
        rows.append(
            {
                "category": category,
                "root": relative_root,
                "root_exists": (config.repo_root / relative_root).exists(),
                "latest": latest,
            }
        )
    return {
        "artifact_root": str(config.artifact_root),
        "artifact_root_exists": config.artifact_root.exists(),
        "latest_generated_artifacts": rows,
    }


def _latest_file(root: Path) -> dict[str, Any] | None:
    if not root.exists() or not root.is_dir():
        return None

    best: tuple[float, Path] | None = None
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, path)

    if best is None:
        return None

    _, path = best
    try:
        relative_path = path.relative_to(root).as_posix()
    except ValueError:
        relative_path = path.name
    return {
        "path": relative_path,
        "modified_at": _modified_at(path),
    }


def _milestone_summary(
    repo_root: Path,
    documentation: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    build_state_text = _read_doc_text(repo_root, documentation, "docs/context/BUILD_STATE.md")
    roadmap_text = _read_doc_text(repo_root, documentation, "docs/roadmap/ROADMAP.md")

    current_phase = _extract_heading_value(build_state_text, "Current Phase") if build_state_text else None
    active_milestone = _extract_active_milestone(roadmap_text) if roadmap_text else None
    planned_next_milestone = _extract_next_planned_milestone(roadmap_text) if roadmap_text else None

    if current_phase is None:
        warnings.append("Current phase could not be extracted from BUILD_STATE.")
    if active_milestone is None:
        warnings.append("Active milestone could not be extracted from ROADMAP.")

    direction = active_milestone or current_phase or "Undocumented"
    return {
        "current_phase": current_phase,
        "active_milestone": active_milestone,
        "next_planned_milestone": planned_next_milestone,
        "direction_summary": direction,
    }


def _read_doc_text(repo_root: Path, documentation: dict[str, Any], relative_path: str) -> str | None:
    for section in ("source_of_truth_docs", "relevant_docs"):
        entries = documentation.get(section)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("path") != relative_path:
                continue
            if not entry.get("exists"):
                return None
            try:
                return (repo_root / relative_path).read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def _extract_heading_value(text: str, heading: str) -> str | None:
    pattern = rf"^##\s+{re.escape(heading)}\s*$\n+([^\n]+)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _extract_active_milestone(text: str) -> str | None:
    pattern = r"^###\s+(.+?)\s*$\n+Status:\s+Active\."
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip() or None


def _extract_next_planned_milestone(text: str) -> str | None:
    marker = "## Planned Milestone Sequence"
    index = text.find(marker)
    if index < 0:
        return None
    tail = text[index:]
    match = re.search(r"^###\s+(.+?)\s*$", tail, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip() or None


def _recommended_next_action(
    *,
    repository: dict[str, Any],
    github: dict[str, Any],
    warnings: list[str],
) -> str:
    if repository.get("working_tree_clean") is False:
        return "Review local changes and run validation commands before next automation step."

    issues_count = github.get("open_issues_count")
    if isinstance(issues_count, int) and issues_count > 0:
        first_issue = github.get("open_issues", [{}])[0]
        number = first_issue.get("number") if isinstance(first_issue, dict) else None
        if isinstance(number, int):
            return f"Inspect the top open issue: python -m aresforge inspect-ready-issue --issue-number {number}"
        return "Inspect open issues with python -m aresforge list-ready-issues."

    prs_count = github.get("open_prs_count")
    if isinstance(prs_count, int) and prs_count > 0:
        first_pr = github.get("open_prs", [{}])[0]
        number = first_pr.get("number") if isinstance(first_pr, dict) else None
        if isinstance(number, int):
            return f"Run QA review on the earliest open PR: python -m aresforge qa-review-pr --pr-number {number}"
        return "Run python -m aresforge qa-review-pr --pr-number <number> for the active PR."

    if warnings:
        return "Resolve environment warnings (git/gh/docs availability) and rerun project-state-summary."

    return "No immediate blockers detected; continue with planned M3 issue execution and validation."


def _modified_at(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat_result.st_mtime, UTC).isoformat()