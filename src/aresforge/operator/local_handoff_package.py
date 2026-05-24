from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

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
        "warnings": sorted(set(warnings + list(git_state.get("warnings", [])))),
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

    lines.extend(["", "## Recommended Next Options"])
    lines.extend(f"- {item}" for item in payload.get("recommended_next_options", []))

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
