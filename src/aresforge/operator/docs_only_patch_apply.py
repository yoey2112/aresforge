from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.queue_transaction_log import append_queue_transaction, queue_transaction_warning

COMMAND_NAME = "apply-docs-only-patch"
ACTION_TYPE = "docs_only_patch_apply"
DOCS_ONLY_PATCH_APPLY_VERSION = "m133.1"

_ALLOWED_EXACT_DOCS = frozenset(
    {
        "docs/context/BUILD_STATE.md",
        "docs/context/AGENT_CONTEXT.md",
        "docs/roadmap/ROADMAP.md",
        "docs/operator/LOCAL_OPERATOR_USAGE.md",
    }
)
_BLOCKED_PREFIXES = (
    "src/",
    "tests/",
    "scripts/",
    ".github/",
    ".aresforge/",
)
_BLOCKED_EXACT = frozenset(
    {
        "pyproject.toml",
        "poetry.lock",
        "requirements.txt",
        "requirements-dev.txt",
        "setup.py",
        "setup.cfg",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "tsconfig.json",
        "vite.config.js",
        "vite.config.ts",
    }
)
_BOUNDARY_CONFIRMATIONS = (
    "M133 docs-only patch application is local-only and patch-target restricted.",
    "M133 requires docs_only_patch_apply machine gates before any patch application.",
    "M133 allows Markdown documentation paths only and blocks source, tests, config, scripts, workflows, binary files, and queue-file patch targets.",
    "M133 performs no Codex, local LLM, remote LLM, GitHub, gh, network, validation command, or next-item execution.",
    "M133 writes a local transaction-log entry only after a non-dry-run patch is applied and post-apply checks pass.",
)


def apply_docs_only_patch(
    config: AppConfig,
    *,
    item_id: str,
    patch_path: str | Path,
    dry_run: bool = False,
    force: bool = False,
    queue_path: str | Path | None = None,
    output: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    resolved_patch_path = _resolve(config.repo_root, patch_path)
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    queue, queue_errors = _load_queue(resolved_queue_path)
    item = _find_item(queue, normalized_item_id)
    patch_text, patch_read_errors = _read_patch(resolved_patch_path)
    analysis = _analyze_patch(patch_text)

    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="docs_only_patch_apply",
        patch_path=resolved_patch_path,
        queue_path=queue_path,
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    pre_status = _git_status(config.repo_root)
    clean_apply = _git_apply_check(config.repo_root, resolved_patch_path)

    blocked_reasons = _blocked_reasons(
        queue_errors=queue_errors,
        item=item,
        patch_read_errors=patch_read_errors,
        analysis=analysis,
        machine_gate=machine_gate,
        pre_status=pre_status,
        clean_apply=clean_apply,
    )
    blocked = bool(blocked_reasons)
    applied = False
    patch_application_performed = False
    transaction_log_entry: dict[str, Any] = {}
    transaction_warnings: list[str] = []
    post_apply_diff_check: dict[str, Any] = {
        "checked": False,
        "passed": False,
        "changed_files": [],
        "blocked_reasons": [],
    }

    if not blocked and not dry_run:
        apply_result = _git_apply(config.repo_root, resolved_patch_path)
        if not apply_result["ok"]:
            blocked = True
            blocked_reasons.extend(apply_result["blocked_reasons"])
        else:
            applied = True
            patch_application_performed = True
            post_apply_diff_check = _post_apply_diff_check(config.repo_root, analysis["targets"])
            if not post_apply_diff_check["passed"]:
                blocked = True
                blocked_reasons.extend(post_apply_diff_check["blocked_reasons"])
            else:
                transaction_result = append_queue_transaction(
                    config,
                    project_id=str(item.get("project_id", "")).strip(),
                    item_id=normalized_item_id,
                    title=str(item.get("title", "")).strip(),
                    previous_status=str(item.get("status", "")).strip(),
                    new_status=str(item.get("status", "")).strip(),
                    mutation_type=ACTION_TYPE,
                    actor=ACTION_TYPE,
                    source=COMMAND_NAME,
                    evidence_summary="Applied a machine-gated docs-only Markdown patch.",
                    reason="Machine-gated documentation-agent docs-only patch application.",
                    queue_path=resolved_queue_path,
                    metadata={
                        "patch_path": str(resolved_patch_path),
                        "changed_files": analysis["targets"],
                        "dry_run": False,
                        "source_code_changed": False,
                        "tests_changed": False,
                    },
                )
                transaction_log_entry = transaction_result.get("transaction", {})
                transaction_warnings = queue_transaction_warning(transaction_result)
                if not transaction_result.get("ok"):
                    blocked = True
                    blocked_reasons.append("Transaction log could not record the docs-only patch application.")

    changed_files = analysis["targets"]
    payload = {
        "action_type": ACTION_TYPE,
        "docs_only_patch_apply_version": DOCS_ONLY_PATCH_APPLY_VERSION,
        "item_id": normalized_item_id,
        "patch_path": str(resolved_patch_path),
        "dry_run": bool(dry_run),
        "applied": applied and not blocked,
        "blocked": blocked,
        "blocked_reasons": _dedupe(blocked_reasons),
        "changed_files": changed_files,
        "machine_gates_checked": bool(machine_gate),
        "machine_gates_passed": bool(machine_gate.get("passed")) and not bool(machine_gate.get("blocked")),
        "transaction_log_entry": transaction_log_entry,
        "patch_application_performed": patch_application_performed and not blocked,
        "source_code_changed": False,
        "tests_changed": False,
        "local_only": True,
        "external_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "next_safe_action": _next_safe_action(blocked=blocked, dry_run=bool(dry_run), applied=applied),
        "machine_gate_result": machine_gate,
        "machine_gates_profile": "docs_only_patch_apply",
        "path_allowlist_passed": not analysis["path_blockers"],
        "clean_apply_check": clean_apply,
        "post_apply_diff_check": post_apply_diff_check,
        "markdown_source_of_truth_consistency_check": _markdown_consistency_check(
            targets=changed_files,
            patch_text=patch_text,
            patch_read_errors=patch_read_errors,
        ),
        "hidden_executable_changes_detected": analysis["hidden_executable_changes_detected"],
        "binary_patch_detected": analysis["binary_patch_detected"],
        "transaction_warnings": transaction_warnings,
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
        "recorded_at": _now_iso(),
    }
    ok = (not blocked and dry_run) or (applied and not blocked)
    return _emit_or_write(config=config, payload=payload, ok=ok, output=output, force=force)


def _blocked_reasons(
    *,
    queue_errors: list[str],
    item: dict[str, Any],
    patch_read_errors: list[str],
    analysis: dict[str, Any],
    machine_gate: dict[str, Any],
    pre_status: dict[str, Any],
    clean_apply: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    reasons.extend(queue_errors)
    if not item:
        reasons.append("Queue item was not found.")
    reasons.extend(patch_read_errors)
    if not analysis["targets"]:
        reasons.append("Patch does not declare any target files.")
    reasons.extend(analysis["path_blockers"])
    if analysis["binary_patch_detected"]:
        reasons.append("Binary patch content is not allowed for docs-only patch application.")
    if analysis["hidden_executable_changes_detected"]:
        reasons.append("Patch contains hidden executable or file-mode changes.")
    if machine_gate.get("passed") is not True or machine_gate.get("blocked") is True:
        reasons.append("Machine safety gate profile docs_only_patch_apply did not pass.")
        reasons.extend(_list(machine_gate.get("blocked_reasons")))
    dirty_targets = _dirty_targets(pre_status, analysis["targets"])
    if dirty_targets:
        reasons.append("Patch target already has local changes: " + ", ".join(dirty_targets))
    if not clean_apply["passed"]:
        reasons.append("Patch did not pass clean apply check.")
        reasons.extend(_list(clean_apply.get("blocked_reasons")))
    return _dedupe(reasons)


def _analyze_patch(patch_text: str) -> dict[str, Any]:
    targets = _patch_targets(patch_text)
    path_blockers: list[str] = []
    for target in targets:
        if _is_source_path(target):
            path_blockers.append(f"Source code path is blocked: {target}")
        elif _is_test_path(target):
            path_blockers.append(f"Test path is blocked: {target}")
        elif _is_blocked_non_doc_path(target):
            path_blockers.append(f"Non-doc or protected path is blocked: {target}")
        elif not _is_allowed_doc_path(target):
            path_blockers.append(f"Path is outside the docs-only Markdown allowlist: {target}")
    binary_patch_detected = any(
        marker in patch_text
        for marker in ("GIT binary patch", "Binary files ", "\nliteral ", "\ndelta ")
    )
    mode_lines = [
        line.strip()
        for line in patch_text.splitlines()
        if line.startswith(("new file mode ", "old mode ", "new mode ", "deleted file mode "))
    ]
    hidden_executable_changes_detected = any(line.endswith("755") for line in mode_lines) or any(
        line.startswith(("old mode ", "new mode ")) for line in mode_lines
    )
    return {
        "targets": targets,
        "path_blockers": _dedupe(path_blockers),
        "binary_patch_detected": binary_patch_detected,
        "hidden_executable_changes_detected": hidden_executable_changes_detected,
        "mode_lines": mode_lines,
    }


def _patch_targets(patch_text: str) -> list[str]:
    targets: list[str] = []
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                targets.append(_strip_patch_prefix(parts[3]))
        elif line.startswith("+++ "):
            target = line[4:].strip()
            if target != "/dev/null":
                targets.append(_strip_patch_prefix(target))
        elif line.startswith("--- "):
            target = line[4:].strip()
            if target != "/dev/null":
                targets.append(_strip_patch_prefix(target))
    return sorted(set(target for target in (_normalize_patch_target(target) for target in targets) if target))


def _strip_patch_prefix(value: str) -> str:
    text = value.strip().replace("\\", "/")
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return re.sub(r"^[ab]/", "", text)


def _normalize_patch_target(value: str) -> str:
    normalized = value.replace("\\", "/").lstrip("/")
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return "__outside_repo__"
    return "/".join(parts)


def _is_allowed_doc_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized in _ALLOWED_EXACT_DOCS:
        return True
    if normalized.startswith("docs/architecture/") and normalized.endswith(".md"):
        return True
    return normalized.startswith("docs/") and normalized.endswith(".md")


def _is_source_path(path: str) -> bool:
    return path.replace("\\", "/").lstrip("/").startswith("src/")


def _is_test_path(path: str) -> bool:
    return path.replace("\\", "/").lstrip("/").startswith("tests/")


def _is_blocked_non_doc_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("/")
    if normalized in _BLOCKED_EXACT:
        return True
    return any(normalized.startswith(prefix) for prefix in _BLOCKED_PREFIXES)


def _git_apply_check(repo_root: Path, patch_path: Path) -> dict[str, Any]:
    return _run_git_apply(repo_root, patch_path, check_only=True)


def _git_apply(repo_root: Path, patch_path: Path) -> dict[str, Any]:
    return _run_git_apply(repo_root, patch_path, check_only=False)


def _run_git_apply(repo_root: Path, patch_path: Path, *, check_only: bool) -> dict[str, Any]:
    args = ["git", "apply", "--check" if check_only else "--whitespace=nowarn", str(patch_path)]
    if not check_only:
        args = ["git", "apply", "--whitespace=nowarn", str(patch_path)]
    try:
        result = subprocess.run(
            args,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"checked": check_only, "passed": False, "blocked_reasons": [f"git apply failed to run: {exc}"]}
    stderr = result.stderr.strip()
    stdout = result.stdout.strip()
    return {
        "ok": result.returncode == 0,
        "checked": check_only,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "blocked_reasons": [text for text in (stderr, stdout) if text] if result.returncode != 0 else [],
    }


def _post_apply_diff_check(repo_root: Path, targets: list[str]) -> dict[str, Any]:
    status = _git_status(repo_root)
    changed = sorted(set(path for path in targets if path))
    blockers: list[str] = []
    for path in changed:
        if not _is_allowed_doc_path(path):
            blockers.append(f"Post-apply changed file is outside docs-only Markdown allowlist: {path}")
        if _is_source_path(path):
            blockers.append(f"Post-apply source path changed: {path}")
        if _is_test_path(path):
            blockers.append(f"Post-apply test path changed: {path}")
    if not status.get("available", False):
        blockers.append("Post-apply git status could not be inspected.")
    return {
        "checked": True,
        "passed": not blockers,
        "changed_files": changed,
        "blocked_reasons": _dedupe(blockers),
    }


def _markdown_consistency_check(*, targets: list[str], patch_text: str, patch_read_errors: list[str]) -> dict[str, Any]:
    blockers: list[str] = []
    if patch_read_errors:
        blockers.extend(patch_read_errors)
    for target in targets:
        if not target.endswith(".md"):
            blockers.append(f"Target is not Markdown: {target}")
    if "\x00" in patch_text:
        blockers.append("Patch contains NUL bytes and is not safe Markdown text.")
    return {
        "checked": True,
        "passed": not blockers,
        "blocked_reasons": _dedupe(blockers),
        "source_of_truth_targets": [target for target in targets if target in _ALLOWED_EXACT_DOCS or target.startswith("docs/architecture/")],
    }


def _dirty_targets(status: dict[str, Any], targets: list[str]) -> list[str]:
    if not status.get("available", False):
        return []
    dirty_paths = set()
    for line in status.get("status_lines", []):
        text = str(line)
        if len(text) < 4:
            continue
        path_text = text[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        dirty_paths.add(path_text.replace("\\", "/"))
    return sorted(target for target in targets if target in dirty_paths)


def _git_status(repo_root: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "dirty": False, "status_lines": [], "warnings": [str(exc)]}
    return {
        "available": result.returncode == 0,
        "dirty": bool(result.stdout.strip()),
        "status_lines": [line for line in result.stdout.splitlines() if line.strip()],
        "warnings": [result.stderr.strip()] if result.stderr.strip() else [],
    }


def _load_queue(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Queue file is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Queue file is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Queue file could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Queue file JSON root must be an object."]
    return raw, []


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and str(item.get("item_id", "")).strip() == item_id:
            return item
    return {}


def _read_patch(path: Path) -> tuple[str, list[str]]:
    if not path.exists():
        return "", [f"Patch file is missing: {path}"]
    try:
        return path.read_text(encoding="utf-8"), []
    except UnicodeDecodeError:
        return "", [f"Patch file is not UTF-8 text: {path}"]
    except OSError as exc:
        return "", [f"Patch file could not be read: {exc}"]


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    ok: bool,
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": bool(ok),
            "local_only": True,
            "format": "json",
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = _resolve(config.repo_root, output)
    if output_path.exists() and not force:
        blocked = dict(payload)
        blocked["blocked"] = True
        blocked["blocked_reasons"] = _dedupe(
            [*_list(blocked.get("blocked_reasons")), "Output file already exists. Re-run with --force to overwrite."]
        )
        rendered = json.dumps(blocked, indent=2)
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "local_only": True,
            "format": "json",
            "output": str(output_path),
            "force": force,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": blocked,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _next_safe_action(*, blocked: bool, dry_run: bool, applied: bool) -> str:
    if blocked:
        return "Resolve blocked reasons and re-run docs-only patch application in dry-run before applying."
    if dry_run:
        return "Dry-run passed; re-run without --dry-run to apply this docs-only patch."
    if applied:
        return "Inspect the applied docs diff and transaction log before any further operator-gated action."
    return "No patch application was performed."


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry).strip()]
    if value in (None, ""):
        return []
    return [str(value).strip()]


def _dedupe(values: list[Any] | tuple[Any, ...] | Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
