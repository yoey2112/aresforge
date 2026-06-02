from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.github_issue_sync_plan import plan_github_issue_sync
from aresforge.operator.local_project_queue import resolve_project_queue_path
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.operator_autonomy_configuration_profile import inspect_autonomy_profile

COMMAND_NAME = "generate-pr-draft-summary"
RECORD_TYPE = "pull_request_draft_summary_generator_v1"
DEFAULT_PROJECT_ID = "aresforge"
DEFAULT_AUTONOMY_PROFILE = "github_sync_dry_run"

_BOUNDARY_CONFIRMATIONS: tuple[str, ...] = (
    "This command generates local draft PR summary artifacts only.",
    "Draft summaries are assembled from local queue context, validation evidence, changed files, artifact paths, and optional Codex evidence bundles.",
    "No pull request is created, updated, merged, marked auto-merge, or pushed by this command.",
    "GitHub mutation remains blocked until a separate future explicitly enabled machine-gated path exists.",
    "No queue mutation, Codex execution, model execution, source patch application, validation command execution, release, workflow mutation, retry, resume, or next-item execution is performed.",
)

_GITHUB_OPERATIONS_BLOCKED: tuple[str, ...] = (
    "create_pull_request",
    "update_pull_request",
    "merge_pull_request",
    "force_push",
    "update_protected_branch",
    "enable_auto_merge",
    "create_release",
    "modify_github_workflow",
)


def generate_pr_draft_summary(
    config: AppConfig,
    *,
    item_id: str,
    project_id: str = DEFAULT_PROJECT_ID,
    queue_path: str | Path | None = None,
    run_id: str | None = None,
    autonomy_profile: str = DEFAULT_AUTONOMY_PROFILE,
    evidence_bundle: str | Path | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
) -> dict[str, Any]:
    fmt = _text(output_format).lower() or "json"
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = _text(item_id)
    normalized_project_id = _text(project_id) or DEFAULT_PROJECT_ID
    selected_autonomy_profile = _text(autonomy_profile) or DEFAULT_AUTONOMY_PROFILE
    normalized_run_id = _text(run_id)
    generated_at = _now_iso()
    resolved_queue_path = resolve_project_queue_path(config.repo_root, queue_path)
    output_path = _resolve(config.repo_root, output) if output else _default_output_path(config, normalized_item_id)
    markdown_path = output_path.with_suffix(".md")

    if output_path.exists() and not force:
        payload = _base_payload(
            project_id=normalized_project_id,
            item_id=normalized_item_id,
            run_id=normalized_run_id,
            generated_at=generated_at,
            autonomy_profile=selected_autonomy_profile,
        )
        payload.update(
            {
                "status": "blocked",
                "blocked": True,
                "blocked_reasons": ["Output file already exists. Re-run with --force to overwrite."],
                "next_safe_action": "Re-run with --force or choose a different output path.",
            }
        )
        return _emit(config=config, payload=payload, output_path=output_path, markdown_path=markdown_path, ok=False)

    queue_result = _load_queue(resolved_queue_path)
    queue = queue_result.get("queue") if queue_result.get("ok") else {}
    item = _find_item(queue, normalized_item_id)
    item_project_id = _text(item.get("project_id")) or normalized_project_id

    evidence = _load_evidence_bundle(
        config,
        item_id=normalized_item_id,
        explicit_path=evidence_bundle,
    )
    plan_payload = _payload(
        plan_github_issue_sync(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            queue_path=queue_path,
            output_format="json",
        )
    )
    item_plan = _item_plan(plan_payload, normalized_item_id)
    linked_issue = item_plan.get("linked_issue") if isinstance(item_plan.get("linked_issue"), dict) else {}
    autonomy_payload = _payload(
        inspect_autonomy_profile(
            config,
            project_id=item_project_id,
            item_id=normalized_item_id,
            autonomy_profile=selected_autonomy_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )

    read_only_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="read_only_agent", queue_path=queue_path)
    )
    artifact_gate = _gate_summary(
        _gate_payload(config, item_id=normalized_item_id, gate_profile="local_artifact_write", queue_path=queue_path)
    )
    machine_gates = [read_only_gate, artifact_gate]

    changed_files = _changed_files(config=config, item=item, evidence=evidence)
    validation = _validation_evidence(item=item, evidence=evidence)
    artifacts = _artifact_paths(item=item, evidence=evidence)
    tests = _tests(validation)
    smoke_checks = _smoke_checks(item)
    risks = _risks(item=item, evidence=evidence, plan_payload=plan_payload, gates=machine_gates)
    rollback_notes = _rollback_notes(item=item, changed_files=changed_files)
    remaining_blockers = _remaining_blockers(
        queue_result=queue_result,
        item=item,
        validation=validation,
        artifacts=artifacts,
        gates=machine_gates,
        plan_payload=plan_payload,
        item_plan=item_plan,
        evidence=evidence,
    )
    warnings = _warnings(
        queue_result=queue_result,
        item=item,
        evidence=evidence,
        plan_payload=plan_payload,
        item_plan=item_plan,
        autonomy_payload=autonomy_payload,
        changed_files=changed_files,
    )
    blocked = bool(remaining_blockers)
    draft = _draft_summary(
        item=item,
        item_id=normalized_item_id,
        project_id=item_project_id,
        changed_files=changed_files,
        validation=validation,
        tests=tests,
        smoke_checks=smoke_checks,
        risks=risks,
        rollback_notes=rollback_notes,
        linked_issue=linked_issue,
        artifacts=artifacts,
        remaining_blockers=remaining_blockers,
    )
    markdown = _render_markdown(draft)

    payload = _base_payload(
        project_id=item_project_id,
        item_id=normalized_item_id,
        run_id=normalized_run_id or _text(evidence.get("run_id")),
        generated_at=generated_at,
        autonomy_profile=selected_autonomy_profile,
    )
    payload.update(
        {
            "status": "blocked" if blocked else "draft_summary_created",
            "blocked": blocked,
            "blocked_reasons": remaining_blockers,
            "warnings": warnings,
            "machine_gates_checked": machine_gates,
            "machine_gates_passed": bool(machine_gates) and all(bool(gate.get("passed")) for gate in machine_gates),
            "artifacts_created": [str(output_path), str(markdown_path)],
            "next_safe_action": _next_safe_action(blocked=blocked),
            "queue_path": str(resolved_queue_path),
            "queue_item_found": bool(item),
            "queue_summary": _queue_summary(item),
            "codex_evidence_bundle": _evidence_summary(evidence),
            "source_plan_summary": _source_plan_summary(plan_payload, item_plan),
            "autonomy_profile_summary": _autonomy_summary(autonomy_payload),
            "draft_pr_summary": draft,
            "draft_pr_body_markdown": markdown,
            "summary": draft["summary"],
            "changed_files": changed_files,
            "tests": tests,
            "smoke_checks": smoke_checks,
            "risks": risks,
            "rollback_notes": rollback_notes,
            "linked_issue_references": draft["linked_issue_references"],
            "artifact_paths": artifacts,
            "remaining_blockers": remaining_blockers,
            "pr_creation_allowed": False,
            "pull_request_created": False,
            "github_mutation_scope": "none_summary_artifact_only",
            "github_operations_blocked": list(_GITHUB_OPERATIONS_BLOCKED),
            "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
            "completed_at": _now_iso(),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown + "\n", encoding="utf-8")
    return _emit(config=config, payload=payload, output_path=output_path, markdown_path=markdown_path, ok=not blocked)


def _base_payload(
    *,
    project_id: str,
    item_id: str,
    run_id: str,
    generated_at: str,
    autonomy_profile: str,
) -> dict[str, Any]:
    return {
        "record_type": RECORD_TYPE,
        "artifact_type": RECORD_TYPE,
        "generated": True,
        "generated_at": generated_at,
        "project_id": project_id,
        "item_id": item_id,
        "run_id": run_id,
        "status": "unknown",
        "blocked": False,
        "blocked_reasons": [],
        "warnings": [],
        "machine_gates_checked": [],
        "machine_gates_passed": False,
        "autonomy_profile": autonomy_profile,
        "artifacts_created": [],
        "mutation_performed": False,
        "queue_mutation_performed": False,
        "codex_execution_performed": False,
        "model_execution_performed": False,
        "github_execution_performed": False,
        "patch_application_performed": False,
        "validation_command_execution_performed": False,
        "local_only": True,
        "next_safe_action": "",
    }


def _draft_summary(
    *,
    item: dict[str, Any],
    item_id: str,
    project_id: str,
    changed_files: list[str],
    validation: dict[str, Any],
    tests: list[str],
    smoke_checks: list[str],
    risks: list[str],
    rollback_notes: list[str],
    linked_issue: dict[str, Any],
    artifacts: list[str],
    remaining_blockers: list[str],
) -> dict[str, Any]:
    title = _text(item.get("title")) or item_id
    summary = _text(item.get("validation_summary")) or _text(item.get("description")) or f"Draft PR summary for {title}."
    return {
        "title": title,
        "item_id": item_id,
        "project_id": project_id,
        "summary": summary,
        "changed_files": changed_files,
        "tests": tests,
        "smoke_checks": smoke_checks,
        "risks": risks,
        "rollback_notes": rollback_notes,
        "linked_issue_references": _linked_issue_references(linked_issue, item),
        "artifact_paths": artifacts,
        "remaining_blockers": remaining_blockers,
        "ready_for_operator_review": not bool(remaining_blockers),
        "pr_creation_allowed": False,
    }


def _render_markdown(draft: dict[str, Any]) -> str:
    lines = [
        f"# {draft['title']}",
        "",
        "## Summary",
        draft["summary"] or "No summary recorded.",
        "",
        "## Changed Files",
        *_bullets(draft.get("changed_files")),
        "",
        "## Tests",
        *_bullets(draft.get("tests")),
        "",
        "## Smoke Checks",
        *_bullets(draft.get("smoke_checks")),
        "",
        "## Risks",
        *_bullets(draft.get("risks")),
        "",
        "## Rollback Notes",
        *_bullets(draft.get("rollback_notes")),
        "",
        "## Linked Issues",
        *_bullets(draft.get("linked_issue_references")),
        "",
        "## Artifacts",
        *_bullets(draft.get("artifact_paths")),
        "",
        "## Remaining Blockers",
        *_bullets(draft.get("remaining_blockers")),
        "",
        "PR creation is not allowed by this artifact. Use a future explicit machine-gated PR creation command if one is implemented.",
    ]
    return "\n".join(lines)


def _remaining_blockers(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    validation: dict[str, Any],
    artifacts: list[str],
    gates: list[dict[str, Any]],
    plan_payload: dict[str, Any],
    item_plan: dict[str, Any],
    evidence: dict[str, Any],
) -> list[str]:
    blockers = [*queue_result.get("blocked_reasons", [])]
    if not queue_result.get("ok"):
        blockers.append("Local queue must be readable before a PR draft summary can be generated.")
    if not item:
        blockers.append("Queue item must exist before a PR draft summary can be generated.")
    if item and _list(item.get("blocked_by")):
        blockers.append("Queue item has blocked_by entries.")
    if not validation.get("present"):
        blockers.append("Validation evidence is required for a complete PR draft summary.")
    if not artifacts:
        blockers.append("At least one artifact path or evidence bundle reference is required for a complete PR draft summary.")
    for gate in gates:
        if gate.get("passed") is not True:
            blockers.extend(_list(gate.get("blocked_reasons")) or [f"Machine gate did not pass: {gate.get('gate_profile')}"])
    if bool(plan_payload.get("blocked")):
        blockers.extend(_list(plan_payload.get("blocked_reasons")))
    if bool(item_plan.get("blocked")):
        blockers.extend(_list(item_plan.get("blocked_reasons")))
    if evidence and evidence.get("blocked") is True:
        blockers.append("Codex evidence bundle reports blocked status.")
        blockers.extend(_list(evidence.get("blocked_reasons")))
    return _dedupe(blockers)


def _warnings(
    *,
    queue_result: dict[str, Any],
    item: dict[str, Any],
    evidence: dict[str, Any],
    plan_payload: dict[str, Any],
    item_plan: dict[str, Any],
    autonomy_payload: dict[str, Any],
    changed_files: list[str],
) -> list[str]:
    warnings = [
        *queue_result.get("warnings", []),
        *_list(evidence.get("warnings")),
        *_list(plan_payload.get("warnings")),
        *_list(item_plan.get("warnings")),
        *_list(autonomy_payload.get("warnings")),
        "Draft PR summary generation does not create, update, or merge pull requests.",
    ]
    if item and _text(item.get("status")) != "done":
        warnings.append("Queue item is not done; generated PR draft summary may be preliminary.")
    if not changed_files:
        warnings.append("No changed files were discovered from queue evidence, Codex evidence, or tracked git diff.")
    if not evidence:
        warnings.append("No Codex evidence bundle was found; summary uses queue and workspace evidence only.")
    return _dedupe(warnings)


def _validation_evidence(*, item: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_validation = evidence.get("validation_evidence") if isinstance(evidence.get("validation_evidence"), dict) else {}
    tests = _dedupe([*_list(item.get("tests_run")), *_list(evidence_validation.get("validation_commands"))])
    summary = _text(item.get("validation_summary")) or _text(evidence_validation.get("validation_summary"))
    present = bool(summary and tests) or bool(evidence_validation.get("validation_passed"))
    return {
        "present": present,
        "validation_summary": summary,
        "tests_run": tests,
        "evidence_note": _text(item.get("evidence_note")),
        "validation_passed": bool(evidence_validation.get("validation_passed")) if evidence_validation else bool(summary and tests),
        "validation_command_execution_performed": bool(evidence.get("validation_command_execution_performed")),
    }


def _tests(validation: dict[str, Any]) -> list[str]:
    return _list(validation.get("tests_run")) or ["No tests recorded."]


def _smoke_checks(item: dict[str, Any]) -> list[str]:
    tests = _list(item.get("tests_run"))
    smokes = [entry for entry in tests if "aresforge" in entry and "pytest" not in entry]
    completion = item.get("completion_evidence") if isinstance(item.get("completion_evidence"), dict) else {}
    command = _text(completion.get("command"))
    if command:
        smokes.append(command)
    return _dedupe(smokes) or ["No smoke checks recorded."]


def _risks(
    *,
    item: dict[str, Any],
    evidence: dict[str, Any],
    plan_payload: dict[str, Any],
    gates: list[dict[str, Any]],
) -> list[str]:
    risks = [
        *_list(item.get("risk_notes")),
        *_list(evidence.get("blocked_reasons")),
        *_list(plan_payload.get("blocked_reasons")),
    ]
    for gate in gates:
        risks.extend(_list(gate.get("blocked_reasons")))
    if not risks:
        risks.append("No additional risks recorded beyond standard operator review and future PR creation gating.")
    return _dedupe(risks)


def _rollback_notes(*, item: dict[str, Any], changed_files: list[str]) -> list[str]:
    notes = _list(item.get("rollback_notes"))
    if not notes:
        notes.append("Revert the future PR branch or commit that applies these changes; this command created only local draft summary artifacts.")
    if changed_files:
        notes.append(f"Review rollback impact for {len(changed_files)} changed file(s).")
    return _dedupe(notes)


def _artifact_paths(*, item: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    artifacts = [*_list(item.get("artifact_paths")), *_list(evidence.get("artifacts_created"))]
    source = _text(evidence.get("_source_path"))
    if source:
        artifacts.append(source)
    completion = item.get("completion_evidence") if isinstance(item.get("completion_evidence"), dict) else {}
    artifacts.extend(_list(completion.get("artifacts_created")))
    return _dedupe(artifacts)


def _changed_files(*, config: AppConfig, item: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    evidence_changed = evidence.get("changed_files") if isinstance(evidence.get("changed_files"), dict) else {}
    candidates = [
        *_list(item.get("changed_files")),
        *_list(evidence_changed.get("bundled_changed_files")),
        *_list(evidence_changed.get("workspace_changed_files")),
        *_git_diff_files(config.repo_root),
    ]
    return _dedupe(path.replace("\\", "/") for path in candidates)


def _queue_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": _text(item.get("status")),
        "priority": _text(item.get("priority")),
        "item_type": _text(item.get("item_type")),
        "dependencies": _list(item.get("dependencies")) + _list(item.get("depends_on")),
        "blocked_by": _list(item.get("blocked_by")),
        "completion_commit": _text(item.get("completion_commit")),
    }


def _linked_issue_references(linked_issue: dict[str, Any], item: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    issue_number = _text(linked_issue.get("issue_number"))
    issue_url = _text(linked_issue.get("issue_url"))
    if issue_number:
        refs.append(f"#{issue_number}")
    if issue_url:
        refs.append(issue_url)
    github_issue = item.get("github_issue")
    if isinstance(github_issue, dict):
        number = _text(github_issue.get("number"))
        url = _text(github_issue.get("url"))
        if number:
            refs.append(f"#{number}")
        if url:
            refs.append(url)
    return _dedupe(refs) or ["No linked issue metadata recorded."]


def _source_plan_summary(plan_payload: dict[str, Any], item_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(plan_payload.get("record_type")),
        "status": _text(plan_payload.get("status")),
        "machine_gates_passed": bool(plan_payload.get("machine_gates_passed")),
        "item_recommendations": item_plan.get("recommendations", []),
        "linked_issue": item_plan.get("linked_issue", {}),
    }


def _autonomy_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": _text(payload.get("record_type")),
        "status": _text(payload.get("status")),
        "blocked": bool(payload.get("blocked")),
        "blocked_reasons": _list(payload.get("blocked_reasons")),
        "machine_gates_passed": bool(payload.get("machine_gates_passed")),
        "autonomy_profile": _text(payload.get("autonomy_profile")),
    }


def _evidence_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "found": bool(evidence),
        "source_path": _text(evidence.get("_source_path")),
        "record_type": _text(evidence.get("record_type")),
        "status": _text(evidence.get("status")),
        "blocked": bool(evidence.get("blocked")),
        "run_id": _text(evidence.get("run_id")),
        "artifacts_created": _list(evidence.get("artifacts_created")),
    }


def _next_safe_action(*, blocked: bool) -> str:
    if blocked:
        return "Resolve PR draft summary blockers and regenerate the local artifact before any separate PR action."
    return "Review the local draft PR summary artifact; PR creation remains a separate future machine-gated command."


def _gate_payload(config: AppConfig, *, item_id: str, gate_profile: str, queue_path: str | Path | None) -> dict[str, Any]:
    return _payload(
        evaluate_machine_safety_gates(
            config,
            item_id=item_id,
            gate_profile=gate_profile,
            queue_path=queue_path,
            output_format="json",
        )
    )


def _gate_summary(gate_payload: dict[str, Any]) -> dict[str, Any]:
    checks = gate_payload.get("checks", [])
    failed = [
        _text(check.get("check_id"))
        for check in checks
        if isinstance(check, dict) and not bool(check.get("passed")) and not bool(check.get("warning_only"))
    ]
    return {
        "gate_profile": _text(gate_payload.get("gate_profile")) or "read_only_agent",
        "passed": bool(gate_payload.get("passed")) and not bool(gate_payload.get("blocked")),
        "blocked": bool(gate_payload.get("blocked")),
        "blocked_reasons": _list(gate_payload.get("blocked_reasons")),
        "checks_failed": failed,
    }


def _load_evidence_bundle(config: AppConfig, *, item_id: str, explicit_path: str | Path | None) -> dict[str, Any]:
    path = _resolve(config.repo_root, explicit_path) if explicit_path else _latest_evidence_bundle(config, item_id)
    if not path or not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"_source_path": str(path), "blocked": True, "blocked_reasons": [f"Codex evidence bundle could not be read: {path}"]}
    if not isinstance(raw, dict):
        return {"_source_path": str(path), "blocked": True, "blocked_reasons": [f"Codex evidence bundle JSON must decode to an object: {path}"]}
    raw["_source_path"] = str(path)
    return raw


def _latest_evidence_bundle(config: AppConfig, item_id: str) -> Path | None:
    root = config.repo_root / ".aresforge" / "codex_loop_validation_evidence" / _path_id(item_id)
    if not root.exists():
        return None
    candidates = sorted(root.glob("*/codex-loop-validation-evidence-bundle.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue not found: {path}"]}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": [f"Project queue could not be read as JSON: {exc}"]}
    if not isinstance(raw, dict):
        return {"ok": False, "queue": {}, "warnings": [], "blocked_reasons": ["Project queue JSON must decode to an object."]}
    return {"ok": True, "queue": raw, "warnings": [], "blocked_reasons": []}


def _find_item(queue: dict[str, Any], item_id: str) -> dict[str, Any]:
    items = queue.get("work_items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and _text(item.get("item_id")) == item_id:
            return item
    return {}


def _item_plan(plan_payload: dict[str, Any], item_id: str) -> dict[str, Any]:
    for entry in plan_payload.get("issue_sync_items", []):
        if isinstance(entry, dict) and _text(entry.get("item_id")) == item_id:
            return entry
    return {}


def _git_diff_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    return _dedupe(line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip())


def _payload(result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload", {}) if isinstance(result, dict) else {}
    return payload if isinstance(payload, dict) else {}


def _emit(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output_path: Path,
    markdown_path: Path,
    ok: bool,
) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": bool(ok),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "markdown_output": str(markdown_path),
        "wrote_output_file": output_path.exists() and not bool(payload.get("blocked")),
        "stdout": json.dumps(payload, indent=2),
        "payload": payload,
    }


def _default_output_path(config: AppConfig, item_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return (config.repo_root / ".aresforge" / "pr_draft_summaries" / f"{stamp}-{_safe_id(item_id)}.json").resolve()


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _bullets(values: Any) -> list[str]:
    entries = _list(values)
    return [f"- {entry}" for entry in entries] if entries else ["- None recorded."]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(entry) for entry in value if _text(entry)]
    if isinstance(value, tuple):
        return [_text(entry) for entry in value if _text(entry)]
    if value in (None, ""):
        return []
    return [_text(value)]


def _dedupe(values: Any) -> list[str]:
    deduped: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in _text(value).lower())
    return cleaned.strip("-") or "pr-draft-summary"


def _path_id(value: str) -> str:
    safe = _safe_id(value)
    if len(safe) <= 24:
        return safe
    return f"{safe[:10]}-{safe[-10:]}"


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
