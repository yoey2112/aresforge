from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_agent_profiles import agent_profiles_summary_for_handoff
from aresforge.operator.managed_project_registry_local import managed_project_registry_summary_for_handoff
from aresforge.operator.local_project_queue import project_queue_summary_for_handoff
from aresforge.operator.local_project_state import project_state_summary_for_handoff
from aresforge.operator.local_agent_orchestration import DEFAULT_OUTPUT_DIR

COMMAND_NAME = "generate-handoff-package"
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
WORKING_PREFERENCES: list[str] = [
    "Before deciding the next task, give options.",
    "Do not create GitHub issues unless explicitly requested.",
    "Do not run GitHub validation commands that could trigger GitHub GraphQL/API rate limits unless explicitly requested.",
    "Direct main work is allowed when explicitly requested.",
    "Prefer exact copy/paste-ready PowerShell when commands are needed.",
    "Avoid nested markdown fences inside PowerShell blocks or issue bodies.",
]


@dataclass(frozen=True)
class DocSnapshot:
    path: str
    exists: bool
    text: str


def generate_handoff_package(
    config: AppConfig,
    *,
    output: str | Path | None = None,
    output_format: str = "markdown",
    include_doc_excerpts: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    format_name = output_format.lower().strip()
    if format_name not in {"markdown", "json"}:
        return _error("invalid_format", {"format": output_format})

    docs = _load_docs(config.repo_root)
    warnings = _warnings_from_docs(docs)
    git_state = _collect_git_state(config.repo_root)
    payload = _build_payload(
        repo_root=config.repo_root,
        config=config,
        git_state=git_state,
        docs=docs,
        include_doc_excerpts=include_doc_excerpts,
        warnings=warnings,
    )
    rendered_markdown = _render_markdown(payload)
    rendered_json = json.dumps(payload, indent=2)

    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
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
        "format": format_name,
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "warnings": payload["warnings"],
        "boundary_confirmations": [
            "Local-only handoff generation.",
            "No gh command was executed.",
            "No GitHub API calls were executed.",
            "No network access was required.",
        ],
    }


def _collect_git_state(repo_root: Path) -> dict[str, Any]:
    results: dict[str, str] = {}
    failures: list[str] = []
    for command in ALLOWED_GIT_COMMANDS:
        try:
            completed = subprocess.run(
                list(command),
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            failures.append(f"{' '.join(command)}: {exc}")
            results[" ".join(command)] = ""
            continue
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            failures.append(f"{' '.join(command)}: {stderr or f'exit {completed.returncode}'}")
            results[" ".join(command)] = ""
            continue
        results[" ".join(command)] = (completed.stdout or "").strip()

    status_lines = [line for line in results.get("git status --short", "").splitlines() if line.strip()]
    return {
        "current_branch": results.get("git branch --show-current", "") or "unknown",
        "current_head": results.get("git rev-parse HEAD", "") or "unknown",
        "working_tree_summary": status_lines or ["clean working tree"],
        "recent_commits": [line for line in results.get("git log -n 10 --oneline", "").splitlines() if line.strip()],
        "warnings": failures,
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


def _warnings_from_docs(docs: list[DocSnapshot]) -> list[str]:
    warnings: list[str] = []
    for doc in docs:
        if not doc.exists:
            warnings.append(f"Missing source-of-truth doc: {doc.path}")
            continue
        for line in doc.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ") and ("warning" in stripped.lower() or "limitation" in stripped.lower()):
                warnings.append(stripped[2:].strip())
    return sorted(set(warnings))


def _extract_section_items(text: str, section_name: str) -> list[str]:
    lines = text.splitlines()
    section_header = section_name.strip().lower()
    in_section = False
    items: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        lowered = line.strip().lower()
        if lowered.startswith("## "):
            in_section = lowered[3:].strip() == section_header
            continue
        if not in_section:
            continue
        if line.strip().startswith("- "):
            items.append(line.strip()[2:].strip())
        elif line.strip() == "" and items:
            break
    return items


def _first_section_paragraph(text: str, section_name: str) -> str:
    lines = text.splitlines()
    section_header = section_name.strip().lower()
    in_section = False
    paragraphs: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        lowered = stripped.lower()
        if lowered.startswith("## "):
            in_section = lowered[3:].strip() == section_header
            continue
        if not in_section:
            continue
        if stripped.startswith("- "):
            continue
        if stripped == "":
            if paragraphs:
                break
            continue
        paragraphs.append(stripped)
    return " ".join(paragraphs).strip()


def _build_payload(
    *,
    repo_root: Path,
    config: AppConfig,
    git_state: dict[str, Any],
    docs: list[DocSnapshot],
    include_doc_excerpts: bool,
    warnings: list[str],
) -> dict[str, Any]:
    docs_by_path = {doc.path: doc for doc in docs}
    build_state = docs_by_path.get("docs/context/BUILD_STATE.md", DocSnapshot("", False, ""))
    agent_context = docs_by_path.get("docs/context/AGENT_CONTEXT.md", DocSnapshot("", False, ""))
    roadmap = docs_by_path.get("docs/roadmap/ROADMAP.md", DocSnapshot("", False, ""))

    completed_recent_capabilities = (
        _extract_items_after_label(roadmap.text, "Delivered M25 outcomes:")
        if roadmap.exists
        else []
    )
    known_blockers = _extract_section_items(build_state.text, "Known Limitations") if build_state.exists else []
    known_blockers.extend(_extract_section_items(agent_context.text, "Known Limitations") if agent_context.exists else [])
    known_blockers = sorted(set(known_blockers))

    current_phase = _first_section_paragraph(build_state.text, "Current Phase") if build_state.exists else ""
    current_goal = _first_section_paragraph(build_state.text, "Current Goal") if build_state.exists else ""
    project_status_summary = " ".join(item for item in [current_phase, current_goal] if item).strip()

    recommended_next_options = [
        "Run targeted local tests for the next scoped change.",
        "Choose one next milestone task and keep scope to a single focused change set.",
        "Regenerate a handoff package after completing the next task so the next session can resume immediately.",
    ]

    prompt_lines = [
        "Continue from this local handoff package.",
        f"Repo path: {repo_root}",
        f"Branch: {git_state['current_branch']}",
        f"HEAD: {git_state['current_head']}",
        "Respect local-only boundaries unless explicitly changed.",
        "Before deciding the next task, present options and wait for selection.",
    ]
    project_state_summary = project_state_summary_for_handoff(config)
    agent_profiles_summary = agent_profiles_summary_for_handoff(config)
    managed_project_registry_summary = managed_project_registry_summary_for_handoff(config)
    project_queue_summary = project_queue_summary_for_handoff(config)
    latest_doc_reconciliation_plan = _latest_doc_reconciliation_plan(repo_root)
    latest_github_sync_plan = _latest_github_sync_plan(repo_root)
    latest_orchestration_plan = _latest_orchestration_plan(repo_root)
    orchestration_capability_note = (
        "M35 local multi-agent orchestration planning is available via python -m aresforge plan-agent-orchestration."
    )
    project_state_warnings: list[str] = []
    if project_state_summary is None:
        project_state_warnings.append(
            "Local project state ledger not found at .aresforge/state/project_state.json."
        )
    elif "error" in project_state_summary:
        project_state_warnings.append(
            "Local project state ledger exists but could not be parsed."
        )
    if isinstance(managed_project_registry_summary, dict) and "error" in managed_project_registry_summary:
        project_state_warnings.append(
            "Managed project registry exists but could not be parsed."
        )
    if isinstance(agent_profiles_summary, dict) and "error" in agent_profiles_summary:
        project_state_warnings.append(
            "Local agent profiles exist but could not be parsed."
        )
    if isinstance(project_queue_summary, dict) and "error" in project_queue_summary:
        project_state_warnings.append(
            "Local project queue exists but could not be parsed."
        )

    payload: dict[str, Any] = {
        "title": "AresForge Local Handoff Package",
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_path": str(repo_root),
        "current_branch": git_state["current_branch"],
        "current_head": git_state["current_head"],
        "working_tree_summary": git_state["working_tree_summary"],
        "recent_commits": git_state["recent_commits"],
        "project_status_summary": project_status_summary or "No project status summary available.",
        "completed_recent_capabilities": completed_recent_capabilities,
        "known_blockers_or_warnings": known_blockers,
        "current_working_preferences": WORKING_PREFERENCES,
        "recommended_next_options": recommended_next_options,
        "codex_continuation_prompt": "\n".join(prompt_lines),
        "source_docs": [doc.path for doc in docs],
        "project_state_summary": project_state_summary,
        "agent_profiles_summary": agent_profiles_summary,
        "managed_project_registry_summary": managed_project_registry_summary,
        "project_queue_summary": project_queue_summary,
        "active_local_milestone": (
            project_state_summary.get("current_milestone")
            if isinstance(project_state_summary, dict)
            else None
        ),
        "latest_doc_reconciliation_plan": latest_doc_reconciliation_plan,
        "latest_github_sync_plan": latest_github_sync_plan,
        "latest_orchestration_plan": latest_orchestration_plan,
        "orchestration_capability_note": orchestration_capability_note,
        "warnings": sorted(
            set(warnings + list(git_state.get("warnings", [])) + project_state_warnings)
        ),
    }
    if include_doc_excerpts:
        payload["doc_excerpts"] = {
            doc.path: _excerpt(doc.text) if doc.exists else "<missing>"
            for doc in docs
        }
    return payload


def _excerpt(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[:8])


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        f"# {payload['title']}",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- repo path: {payload['repo_path']}",
        f"- current branch: {payload['current_branch']}",
        f"- current HEAD: {payload['current_head']}",
        "",
        "## Working Tree Summary",
    ]
    lines.extend(f"- {item}" for item in payload.get("working_tree_summary", []))
    lines.extend(["", "## Recent Commits"])
    commits = payload.get("recent_commits", [])
    if commits:
        lines.extend(f"- {item}" for item in commits)
    else:
        lines.append("- No recent commits available.")

    lines.extend(
        [
            "",
            "## Project Status Summary",
            payload.get("project_status_summary", ""),
            "",
            "## Completed Recent Capabilities",
        ]
    )
    for item in payload.get("completed_recent_capabilities", []):
        lines.append(f"- {item}")
    if not payload.get("completed_recent_capabilities"):
        lines.append("- None detected.")

    lines.extend(["", "## Known Blockers Or Warnings"])
    for item in payload.get("known_blockers_or_warnings", []):
        lines.append(f"- {item}")
    if not payload.get("known_blockers_or_warnings"):
        lines.append("- None reported in source docs.")

    lines.extend(["", "## Current Working Preferences"])
    lines.extend(f"- {item}" for item in payload.get("current_working_preferences", []))

    lines.extend(["", "## Local Project State Summary"])
    summary = payload.get("project_state_summary")
    if isinstance(summary, dict):
        lines.append(f"- path: {summary.get('path')}")
        lines.append(f"- current_phase: {summary.get('current_phase')}")
        lines.append(f"- current_milestone: {summary.get('current_milestone')}")
        lines.append(f"- current_mode: {summary.get('current_mode')}")
        lines.append(f"- validation_status: {summary.get('validation_status')}")
        lines.append(f"- documentation_status: {summary.get('documentation_status')}")
        lines.append(f"- pending_sync: {summary.get('pending_sync')}")
    else:
        lines.append("- No local project state ledger summary available.")
    active_local_milestone = payload.get("active_local_milestone")
    if isinstance(active_local_milestone, str) and active_local_milestone.strip():
        lines.append(f"- active_local_milestone: {active_local_milestone.strip()}")

    lines.extend(["", "## Recommended Next Options"])
    lines.extend(f"- {item}" for item in payload.get("recommended_next_options", []))

    lines.extend(["", "## Local Agent Profiles Summary"])
    agent_profiles = payload.get("agent_profiles_summary")
    if isinstance(agent_profiles, dict):
        lines.append(f"- path: {agent_profiles.get('path')}")
        lines.append(f"- schema_version: {agent_profiles.get('schema_version')}")
        lines.append(f"- updated_at: {agent_profiles.get('updated_at')}")
        lines.append(f"- agent_count: {agent_profiles.get('agent_count')}")
        lines.append(f"- handoff_target_count: {agent_profiles.get('handoff_target_count')}")
        status_counts = agent_profiles.get('status_counts')
        if isinstance(status_counts, dict):
            lines.append("- status_counts:")
            for key in sorted(status_counts.keys()):
                lines.append(f"  - {key}: {status_counts.get(key)}")
    else:
        lines.append("- No local agent profiles summary available.")

    lines.extend(["", "## Managed Project Registry Summary"])
    managed_summary = payload.get("managed_project_registry_summary")
    if isinstance(managed_summary, dict):
        lines.append(f"- path: {managed_summary.get('path')}")
        lines.append(f"- schema_version: {managed_summary.get('schema_version')}")
        lines.append(f"- updated_at: {managed_summary.get('updated_at')}")
        lines.append(f"- project_count: {managed_summary.get('project_count')}")
        lines.append(f"- repo_count: {managed_summary.get('repo_count')}")
    else:
        lines.append("- No managed project registry summary available.")

    lines.extend(["", "## Local Project Queue Summary"])
    queue_summary = payload.get("project_queue_summary")
    if isinstance(queue_summary, dict):
        lines.append(f"- path: {queue_summary.get('path')}")
        lines.append(f"- schema_version: {queue_summary.get('schema_version')}")
        lines.append(f"- updated_at: {queue_summary.get('updated_at')}")
        lines.append(f"- item_count: {queue_summary.get('item_count')}")
        status_counts = queue_summary.get('status_counts')
        if isinstance(status_counts, dict):
            lines.append("- status_counts:")
            for key in sorted(status_counts.keys()):
                lines.append(f"  - {key}: {status_counts.get(key)}")
    else:
        lines.append("- No local project queue summary available.")

    lines.extend(["", "## Latest Doc Reconciliation Plan"])
    latest_plan = payload.get("latest_doc_reconciliation_plan")
    if isinstance(latest_plan, dict):
        lines.append(f"- path: {latest_plan.get('path')}")
        lines.append(f"- modified_at: {latest_plan.get('modified_at')}")
    else:
        lines.append("- No local doc reconciliation plan detected under artifacts/doc-reconciliation/.")

    lines.extend(["", "## Latest GitHub Sync Plan"])
    latest_sync_plan = payload.get("latest_github_sync_plan")
    if isinstance(latest_sync_plan, dict):
        lines.append(f"- path: {latest_sync_plan.get('path')}")
        lines.append(f"- modified_at: {latest_sync_plan.get('modified_at')}")
    else:
        lines.append("- No local GitHub sync plan detected under artifacts/github-sync/.")

    lines.extend(["", "## Latest Orchestration Plan"])
    latest_orchestration_plan = payload.get("latest_orchestration_plan")
    if isinstance(latest_orchestration_plan, dict):
        lines.append(f"- path: {latest_orchestration_plan.get('path')}")
        lines.append(f"- modified_at: {latest_orchestration_plan.get('modified_at')}")
    else:
        lines.append("- No local orchestration plan detected under artifacts/orchestration/.")
        capability = str(payload.get("orchestration_capability_note", "")).strip()
        if capability:
            lines.append(f"- capability: {capability}")

    lines.extend(["", "## Codex Continuation Prompt", "```text", payload.get("codex_continuation_prompt", ""), "```"])

    warnings = payload.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {item}" for item in warnings)

    if "doc_excerpts" in payload:
        lines.extend(["", "## Doc Excerpts"])
        doc_excerpts = payload["doc_excerpts"]
        if isinstance(doc_excerpts, dict):
            for path, excerpt in doc_excerpts.items():
                lines.append(f"- {path}: {excerpt}")

    return "\n".join(lines)


def _extract_items_after_label(text: str, label: str) -> list[str]:
    lines = text.splitlines()
    start_idx: int | None = None
    normalized_label = label.strip().lower()
    for idx, line in enumerate(lines):
        if line.strip().lower() == normalized_label:
            start_idx = idx + 1
            break
    if start_idx is None:
        return []
    items: list[str] = []
    for line in lines[start_idx:]:
        stripped = line.strip()
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
            continue
        if stripped == "" and items:
            break
    return items


def _latest_doc_reconciliation_plan(repo_root: Path) -> dict[str, str] | None:
    reconciliation_root = repo_root / "artifacts" / "doc-reconciliation"
    if not reconciliation_root.exists():
        return None
    candidates = [
        candidate
        for candidate in reconciliation_root.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in {".json", ".md"}
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return {
        "path": str(latest),
        "modified_at": datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC).isoformat(),
    }


def _latest_github_sync_plan(repo_root: Path) -> dict[str, str] | None:
    sync_root = repo_root / "artifacts" / "github-sync"
    if not sync_root.exists():
        return None
    candidates = [
        candidate
        for candidate in sync_root.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in {".json", ".md"}
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return {
        "path": str(latest),
        "modified_at": datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC).isoformat(),
    }


def _latest_orchestration_plan(repo_root: Path) -> dict[str, str] | None:
    orchestration_root = repo_root / DEFAULT_OUTPUT_DIR
    if not orchestration_root.exists():
        return None
    candidates = [
        candidate
        for candidate in orchestration_root.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in {".json", ".md"}
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return {
        "path": str(latest),
        "modified_at": datetime.fromtimestamp(latest.stat().st_mtime, tz=UTC).isoformat(),
    }


def _error(error: str, details: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
    if payload is not None:
        result["payload"] = payload
    return result
