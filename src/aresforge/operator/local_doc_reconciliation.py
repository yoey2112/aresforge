from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

COMMAND_NAME = "plan-doc-reconciliation"
ALLOWED_GIT_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("git", "branch", "--show-current"),
    ("git", "rev-parse", "HEAD"),
    ("git", "status", "--short"),
    ("git", "log", "-n", "10", "--oneline"),
)
SOURCE_DOCS: tuple[str, ...] = (
    "docs/context/BUILD_STATE.md",
    "docs/context/AGENT_CONTEXT.md",
    "docs/roadmap/ROADMAP.md",
    "docs/architecture/RUNNABLE_SKELETON.md",
    "docs/operator/LOCAL_OPERATOR_USAGE.md",
)
PROJECT_STATE_PATH = Path(".aresforge") / "state" / "project_state.json"


@dataclass(frozen=True)
class DocSnapshot:
    path: str
    exists: bool
    text: str


def generate_doc_reconciliation_plan(
    config: AppConfig,
    *,
    output: str | Path | None = None,
    output_format: str = "markdown",
    include_git_state: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    format_name = output_format.lower().strip()
    if format_name not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format})

    docs = _load_docs(config.repo_root)
    project_state = _load_project_state(config.repo_root)
    git_state = _collect_git_state(config.repo_root) if include_git_state else None
    cli_command_names = _detect_cli_command_names(config.repo_root)
    payload = _build_payload(
        repo_root=config.repo_root,
        docs=docs,
        project_state=project_state,
        cli_command_names=cli_command_names,
        git_state=git_state,
    )
    rendered_markdown = _render_markdown(payload)
    rendered_json = json.dumps(payload, indent=2)

    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "plan_only": True,
            "format": format_name,
            "wrote_output_file": False,
            "stdout": rendered_json if format_name == "json" else rendered_markdown,
            "payload": payload,
        }

    output_path = Path(output)
    if output_path.exists() and not force:
        return _error(
            "output_exists",
            {"path": str(output_path), "hint": "Re-run with --force to overwrite."},
            payload=payload,
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error("output_directory_create_failed", {"path": str(output_path.parent), "message": str(exc)})

    content = rendered_json if format_name == "json" else rendered_markdown
    try:
        output_path.write_text(content + "\n", encoding="utf-8")
    except OSError as exc:
        return _error("output_write_failed", {"path": str(output_path), "message": str(exc)}, payload=payload)

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "plan_only": True,
        "format": format_name,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "warnings": payload["risks"],
        "boundary_confirmations": [
            "Plan-only documentation reconciliation.",
            "Local-only inspection.",
            "No gh command was executed.",
            "No GitHub API calls were executed.",
            "No LLM calls were executed.",
            "No external network access was required.",
        ],
    }


def _load_docs(repo_root: Path) -> list[DocSnapshot]:
    docs: list[DocSnapshot] = []
    for relative_path in SOURCE_DOCS:
        path = repo_root / relative_path
        if not path.exists():
            docs.append(DocSnapshot(path=relative_path, exists=False, text=""))
            continue
        try:
            docs.append(DocSnapshot(path=relative_path, exists=True, text=path.read_text(encoding="utf-8")))
        except OSError:
            docs.append(DocSnapshot(path=relative_path, exists=False, text=""))
    return docs


def _load_project_state(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root / PROJECT_STATE_PATH
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"path": str(path), "error": "project_state_invalid_json"}
    if not isinstance(raw, dict):
        return {"path": str(path), "error": "project_state_not_object"}
    raw["path"] = str(path)
    return raw


def _collect_git_state(repo_root: Path) -> dict[str, Any]:
    results: dict[str, str] = {}
    failures: list[str] = []
    for command in ALLOWED_GIT_COMMANDS:
        command_text = " ".join(command)
        try:
            completed = subprocess.run(
                list(command),
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            results[command_text] = ""
            failures.append(f"{command_text}: {exc}")
            continue
        if completed.returncode != 0:
            results[command_text] = ""
            stderr = (completed.stderr or "").strip()
            failures.append(f"{command_text}: {stderr or f'exit {completed.returncode}'}")
            continue
        results[command_text] = (completed.stdout or "").strip()

    return {
        "current_branch": results.get("git branch --show-current", "") or "unknown",
        "current_head": results.get("git rev-parse HEAD", "") or "unknown",
        "working_tree_summary": [
            line for line in results.get("git status --short", "").splitlines() if line.strip()
        ]
        or ["clean working tree"],
        "recent_commits": [line for line in results.get("git log -n 10 --oneline", "").splitlines() if line.strip()],
        "warnings": failures,
    }


def _detect_cli_command_names(repo_root: Path) -> list[str]:
    cli_path = repo_root / "src" / "aresforge" / "cli.py"
    if not cli_path.exists():
        return []
    try:
        text = cli_path.read_text(encoding="utf-8")
    except OSError:
        return []
    matches = re.findall(r'subparsers\.add_parser\("([a-z0-9-]+)"\)', text)
    return sorted(set(matches))


def _extract_milestones(text: str) -> list[str]:
    return sorted(set(re.findall(r"\\bM\\d+\\b", text)))


def _extract_commands(text: str) -> list[str]:
    return sorted(
        set(
            match.strip()
            for match in re.findall(r"python -m aresforge [^`\\n]+", text)
            if match.strip()
        )
    )


def _build_payload(
    *,
    repo_root: Path,
    docs: list[DocSnapshot],
    project_state: dict[str, Any] | None,
    cli_command_names: list[str],
    git_state: dict[str, Any] | None,
) -> dict[str, Any]:
    docs_by_path = {doc.path: doc for doc in docs}
    missing_docs = [doc.path for doc in docs if not doc.exists]

    milestone_set: set[str] = set()
    command_set: set[str] = set()
    for doc in docs:
        if not doc.exists:
            continue
        milestone_set.update(_extract_milestones(doc.text))
        command_set.update(_extract_commands(doc.text))

    stale_or_missing_sections: list[str] = []
    recommended_doc_updates: list[str] = []
    alignment_notes: list[str] = []
    risks: list[str] = []
    next_actions: list[str] = []

    build_state = docs_by_path.get("docs/context/BUILD_STATE.md", DocSnapshot("", False, ""))
    agent_context = docs_by_path.get("docs/context/AGENT_CONTEXT.md", DocSnapshot("", False, ""))
    roadmap = docs_by_path.get("docs/roadmap/ROADMAP.md", DocSnapshot("", False, ""))
    runnable = docs_by_path.get("docs/architecture/RUNNABLE_SKELETON.md", DocSnapshot("", False, ""))
    local_operator = docs_by_path.get("docs/operator/LOCAL_OPERATOR_USAGE.md", DocSnapshot("", False, ""))

    if missing_docs:
        stale_or_missing_sections.append("One or more source-of-truth docs are missing.")
        recommended_doc_updates.append("Restore all missing source-of-truth docs before reconciliation-dependent work.")

    latest_state_milestone = ""
    if isinstance(project_state, dict) and "error" not in project_state:
        raw_milestone = project_state.get("current_milestone")
        if isinstance(raw_milestone, str):
            latest_state_milestone = raw_milestone.strip()
    if latest_state_milestone and build_state.exists and latest_state_milestone not in build_state.text:
        stale_or_missing_sections.append(
            "BUILD_STATE.md does not mention current_milestone from local project state ledger."
        )
        recommended_doc_updates.append(
            f"Update BUILD_STATE.md Current Phase/Goal to include local ledger milestone '{latest_state_milestone}'."
        )

    if local_operator.exists and cli_command_names:
        operator_text = local_operator.text
        documented_names = {
            match.group(1)
            for match in re.finditer(r"python -m aresforge ([a-z0-9-]+)", operator_text)
        }
        missing_cli_docs = sorted(name for name in cli_command_names if name not in documented_names)
        if missing_cli_docs:
            stale_or_missing_sections.append(
                "LOCAL_OPERATOR_USAGE.md does not mention some CLI parser commands."
            )
            recommended_doc_updates.append(
                "Document key missing commands in LOCAL_OPERATOR_USAGE.md: " + ", ".join(missing_cli_docs[:12])
            )

    required_runnable_terms = ["M26", "M27", "M28", "generate-handoff-package", "plan-doc-reconciliation"]
    if runnable.exists:
        missing_terms = [term for term in required_runnable_terms if term not in runnable.text]
        if missing_terms:
            stale_or_missing_sections.append(
                "RUNNABLE_SKELETON.md is missing architecture/command references expected for current milestone layers."
            )
            recommended_doc_updates.append(
                "Add runnable surface references: " + ", ".join(missing_terms)
            )

    if agent_context.exists:
        required_constraints = ["plan-only", "local-only", "No LLM", "No gh", "No GitHub API", "No network"]
        normalized = agent_context.text.lower()
        missing_constraints = []
        for constraint in required_constraints:
            if constraint.lower() not in normalized:
                missing_constraints.append(constraint)
        if missing_constraints:
            stale_or_missing_sections.append(
                "AGENT_CONTEXT.md does not capture recent local documentation-agent operating constraints."
            )
            recommended_doc_updates.append(
                "Add explicit M28 constraints in AGENT_CONTEXT.md: " + ", ".join(missing_constraints)
            )

    if roadmap.exists and "M28" not in roadmap.text:
        stale_or_missing_sections.append("ROADMAP.md does not mention M28 milestone direction.")
        recommended_doc_updates.append("Add M28 section with status, outcomes, and local-only boundaries.")

    if not stale_or_missing_sections:
        alignment_notes.append("Source-of-truth docs appear aligned with detected local project/documentation state.")
    else:
        alignment_notes.append("Source-of-truth docs require targeted updates before relying on them as current truth.")

    if isinstance(project_state, dict) and "error" in project_state:
        risks.append("Local project state file exists but could not be parsed; milestone alignment checks may be incomplete.")
    if project_state is None:
        risks.append("Local project state file is missing; reconciliation cannot compare against tracked documentation status.")
    if missing_docs:
        risks.append("Missing source-of-truth docs reduce confidence in reconciliation findings.")
    if git_state is not None and git_state.get("warnings"):
        risks.append("Some local git-state signals could not be collected from the approved command set.")

    next_actions.extend(
        [
            "Update stale or missing sections listed in recommended_doc_updates.",
            "Regenerate plan-doc-reconciliation after documentation updates.",
            "Record documentation progress in .aresforge/state/project_state.json documentation_status.",
        ]
    )

    return {
        "title": "AresForge Documentation Reconciliation Plan",
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_path": str(repo_root),
        "plan_only": True,
        "local_only": True,
        "docs_inspected": [doc.path for doc in docs],
        "missing_docs": missing_docs,
        "detected_milestone_references": sorted(milestone_set),
        "detected_command_references": sorted(command_set),
        "stale_or_missing_sections": stale_or_missing_sections,
        "recommended_doc_updates": recommended_doc_updates,
        "source_of_truth_alignment_notes": alignment_notes,
        "risks": risks,
        "next_actions": next_actions,
        "project_state_path": str(repo_root / PROJECT_STATE_PATH),
        "project_state_detected": project_state is not None,
        "project_state_summary": _project_state_summary(project_state),
        "include_git_state": git_state is not None,
        "git_state": git_state,
        "boundary_confirmations": [
            "Plan-only documentation reconciliation.",
            "Local-only inspection.",
            "No gh commands executed.",
            "No GitHub API calls executed.",
            "No LLM calls executed.",
            "No external network access used.",
        ],
    }


def _project_state_summary(project_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if project_state is None:
        return None
    if "error" in project_state:
        return {"error": project_state["error"], "path": project_state.get("path")}
    return {
        "current_milestone": project_state.get("current_milestone"),
        "current_phase": project_state.get("current_phase"),
        "current_mode": project_state.get("current_mode"),
        "validation_status": project_state.get("validation_status"),
        "documentation_status": project_state.get("documentation_status"),
        "updated_at": project_state.get("updated_at"),
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# {payload['title']}",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- repo_path: {payload['repo_path']}",
        f"- plan_only: {payload['plan_only']}",
        f"- local_only: {payload['local_only']}",
        "",
        "## Docs Inspected",
    ]
    lines.extend(f"- {item}" for item in payload.get("docs_inspected", []))

    lines.extend(["", "## Missing Docs"])
    missing_docs = payload.get("missing_docs", [])
    lines.extend(f"- {item}" for item in missing_docs)
    if not missing_docs:
        lines.append("- None")

    lines.extend(["", "## Detected Milestone References"])
    milestones = payload.get("detected_milestone_references", [])
    lines.extend(f"- {item}" for item in milestones)
    if not milestones:
        lines.append("- None")

    lines.extend(["", "## Detected Command References"])
    commands = payload.get("detected_command_references", [])
    lines.extend(f"- {item}" for item in commands)
    if not commands:
        lines.append("- None")

    lines.extend(["", "## Stale Or Missing Sections"])
    stale_sections = payload.get("stale_or_missing_sections", [])
    lines.extend(f"- {item}" for item in stale_sections)
    if not stale_sections:
        lines.append("- None detected")

    lines.extend(["", "## Recommended Doc Updates"])
    updates = payload.get("recommended_doc_updates", [])
    lines.extend(f"- {item}" for item in updates)
    if not updates:
        lines.append("- No updates recommended")

    lines.extend(["", "## Source Of Truth Alignment Notes"])
    lines.extend(f"- {item}" for item in payload.get("source_of_truth_alignment_notes", []))

    lines.extend(["", "## Risks"])
    risks = payload.get("risks", [])
    lines.extend(f"- {item}" for item in risks)
    if not risks:
        lines.append("- None detected")

    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in payload.get("next_actions", []))

    if payload.get("include_git_state") and isinstance(payload.get("git_state"), dict):
        git_state = payload["git_state"]
        lines.extend(["", "## Local Git State"])
        lines.append(f"- branch: {git_state.get('current_branch')}")
        lines.append(f"- head: {git_state.get('current_head')}")
        lines.append("- working_tree_summary:")
        lines.extend(f"  - {item}" for item in git_state.get("working_tree_summary", []))
        lines.append("- recent_commits:")
        lines.extend(f"  - {item}" for item in git_state.get("recent_commits", []))
        warnings = git_state.get("warnings", [])
        if warnings:
            lines.append("- warnings:")
            lines.extend(f"  - {item}" for item in warnings)

    return "\n".join(lines)


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "plan_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
