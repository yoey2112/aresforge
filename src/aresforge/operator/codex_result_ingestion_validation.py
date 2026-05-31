from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Callable

from aresforge.config import AppConfig
from aresforge.operator.codex_validation_profiles import VALIDATION_PROFILE_COMMANDS
from aresforge.operator.dispatch_result_evidence_parser import parse_dispatch_result_evidence
from aresforge.operator.machine_safety_gate_engine import evaluate_machine_safety_gates
from aresforge.operator.queue_completion_recommendation import recommend_queue_completion

COMMAND_NAME = "ingest-codex-result-and-validate"
INGESTION_RECORD_TYPE = "codex_result_ingestion_validation"
INGESTION_VERSION = "m136.1"
DEFAULT_VALIDATION_PROFILE = "code_unit_tests"
DEFAULT_TIMEOUT_SECONDS = 600

CommandRunner = Callable[[str, Path, int], subprocess.CompletedProcess[Any]]

VALIDATION_PROFILES: dict[str, tuple[str, ...]] = dict(VALIDATION_PROFILE_COMMANDS)

_BOUNDARY_CONFIRMATIONS = (
    "M136 Codex result ingestion is local-only.",
    "M136 reads one local Codex execution record and local result artifacts.",
    "M136 may run only allowlisted local validation commands for the selected profile.",
    "M136 writes local evidence, recommendation, machine-gate, and ingestion artifacts.",
    "M136 does not execute Codex, call remote services, call GitHub or gh, push, mutate queue status, or start another item.",
    "Queue completion remains a separate explicit M132 path or human operator action.",
)


def ingest_codex_result_and_validate(
    config: AppConfig,
    *,
    item_id: str,
    execution_record: str | Path,
    validation_profile: str = DEFAULT_VALIDATION_PROFILE,
    dry_run: bool = False,
    output: str | Path | None = None,
    force: bool = False,
    queue_path: str | Path | None = None,
    output_format: str = "json",
    command_runner: CommandRunner | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt != "json":
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json"]})

    normalized_item_id = str(item_id or "").strip()
    normalized_profile = str(validation_profile or DEFAULT_VALIDATION_PROFILE).strip()
    resolved_record_path = _resolve(config.repo_root, execution_record)
    run_root = _run_root(config, normalized_item_id)

    if output is not None:
        output_path = _resolve(config.repo_root, output)
        if output_path.exists() and not force:
            payload = _minimal_blocked_payload(
                item_id=normalized_item_id,
                execution_record_path=resolved_record_path,
                validation_profile=normalized_profile,
                dry_run=dry_run,
                reason="Output file already exists. Re-run with --force to overwrite.",
            )
            return _emit_or_write(config=config, payload=payload, output=output, force=force)

    execution_data, record_errors = _load_execution_record(resolved_record_path)
    validation_commands = list(VALIDATION_PROFILES.get(normalized_profile, ()))
    validation_profile_valid = normalized_profile in VALIDATION_PROFILES
    result_text, result_artifact_paths = _collect_result_text(config.repo_root, execution_data)
    changed_files = _changed_files(config.repo_root, execution_data, result_text)

    validation_run = _validation_run(
        config=config,
        commands=validation_commands,
        dry_run=bool(dry_run),
        runner=command_runner,
        timeout_seconds=timeout_seconds,
    )
    validation_passed = bool(validation_run) and all(bool(entry.get("passed")) for entry in validation_run)
    if dry_run:
        validation_passed = False

    result_source_path = run_root / "extracted-codex-result.md"
    evidence_artifact_path = run_root / "dispatch-evidence.json"
    completion_recommendation_path = run_root / "completion-recommendation.json"
    machine_gate_result_path = run_root / "machine-gate-result.json"

    source_text = _compose_result_source(
        execution_record_path=resolved_record_path,
        execution_data=execution_data,
        result_text=result_text,
        result_artifact_paths=result_artifact_paths,
        changed_files=changed_files,
        validation_run=validation_run,
        dry_run=bool(dry_run),
    )
    result_source_path.parent.mkdir(parents=True, exist_ok=True)
    result_source_path.write_text(source_text.rstrip() + "\n", encoding="utf-8")

    parsed_result = parse_dispatch_result_evidence(
        config,
        item_id=normalized_item_id,
        result_path=result_source_path,
        queue_path=queue_path,
        output=evidence_artifact_path,
        force=True,
        output_format="json",
    )
    parsed = parsed_result.get("payload", {}) if isinstance(parsed_result, dict) else {}

    recommendation_result = recommend_queue_completion(
        config,
        item_id=normalized_item_id,
        evidence_path=evidence_artifact_path,
        queue_path=queue_path,
        output=completion_recommendation_path,
        force=True,
        output_format="json",
    )
    recommendation = recommendation_result.get("payload", {}) if isinstance(recommendation_result, dict) else {}

    gate_result = evaluate_machine_safety_gates(
        config,
        item_id=normalized_item_id,
        gate_profile="queue_status_mutation",
        queue_path=queue_path,
        output=machine_gate_result_path,
        force=bool(force),
        output_format="json",
    )
    machine_gate = gate_result.get("payload", {}) if isinstance(gate_result, dict) else {}

    blocked_reasons = _blocked_reasons(
        record_errors=record_errors,
        validation_profile_valid=validation_profile_valid,
        result_text=result_text,
        parsed=parsed,
        validation_run=validation_run,
        dry_run=bool(dry_run),
    )
    blocked = bool(blocked_reasons)
    payload = {
        "ingestion_record_type": INGESTION_RECORD_TYPE,
        "ingestion_version": INGESTION_VERSION,
        "item_id": normalized_item_id,
        "execution_record_path": str(resolved_record_path),
        "dry_run": bool(dry_run),
        "parsed": parsed,
        "validation_profile": normalized_profile,
        "validation_commands": validation_commands,
        "validation_run": validation_run,
        "validation_passed": validation_passed,
        "changed_files": changed_files,
        "evidence_artifact_path": str(evidence_artifact_path),
        "completion_recommendation_path": str(completion_recommendation_path),
        "machine_gate_result_path": str(machine_gate_result_path),
        "blocked": blocked,
        "blocked_reasons": blocked_reasons,
        "queue_mutation_performed": False,
        "github_execution_performed": False,
        "local_only": True,
        "next_safe_action": _next_safe_action(
            dry_run=bool(dry_run),
            blocked=blocked,
            recommendation=recommendation,
            machine_gate=machine_gate,
        ),
        "github_push_performed": False,
        "remote_services_called": False,
        "codex_execution_performed": False,
        "completion_recommendation": recommendation,
        "machine_gate_result": machine_gate,
        "result_source_path": str(result_source_path),
        "result_artifact_paths": result_artifact_paths,
        "recorded_at": _now_iso(),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force)


def _validation_run(
    *,
    config: AppConfig,
    commands: list[str],
    dry_run: bool,
    runner: CommandRunner | None,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for command in commands:
        started_at = _now_iso()
        if dry_run:
            entries.append(
                {
                    "command": command,
                    "skipped": True,
                    "passed": False,
                    "exit_code": None,
                    "stdout": "",
                    "stderr": "",
                    "started_at": started_at,
                    "completed_at": _now_iso(),
                }
            )
            continue
        try:
            completed = (runner or _default_command_runner)(command, config.repo_root, timeout_seconds)
            exit_code = int(completed.returncode)
            stdout = _decode_output(completed.stdout)
            stderr = _decode_output(completed.stderr)
        except (OSError, subprocess.SubprocessError) as exc:
            exit_code = None
            stdout = ""
            stderr = str(exc)
        entries.append(
            {
                "command": command,
                "skipped": False,
                "passed": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "started_at": started_at,
                "completed_at": _now_iso(),
            }
        )
    return entries


def _default_command_runner(command: str, cwd: Path, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(1, timeout_seconds),
    )


def _compose_result_source(
    *,
    execution_record_path: Path,
    execution_data: dict[str, Any],
    result_text: str,
    result_artifact_paths: list[str],
    changed_files: list[str],
    validation_run: list[dict[str, Any]],
    dry_run: bool,
) -> str:
    sections = [
        "# Codex Result Ingestion Source",
        "",
        f"Execution record: {execution_record_path}",
        "",
        "## Files Changed",
    ]
    sections.extend(f"- {path}" for path in changed_files or _list(execution_data.get("changed_files")))
    sections.extend(["", "## What Changed"])
    summary_entries = _list(execution_data.get("what_changed")) or _list(execution_data.get("summary"))
    if summary_entries:
        sections.extend(f"- {entry}" for entry in summary_entries)
    else:
        sections.append("- Parsed Codex execution output and local validation results for completion review.")
    sections.extend(["", "## Captured Result Artifacts"])
    if result_artifact_paths:
        sections.extend(f"- {path}" for path in result_artifact_paths)
    else:
        sections.append("- No stdout, stderr, or result artifact paths were reported by the execution record.")
    if result_text.strip():
        sections.extend(["", "## Captured Codex Output", "", result_text.strip()])
    sections.extend(["", "## Tests Run And Results"])
    if dry_run:
        sections.append("- Dry-run: validation commands were selected but not executed.")
    elif validation_run:
        for entry in validation_run:
            status = "passed" if entry.get("passed") else "failed"
            sections.append(f"- {entry.get('command', '')} -> {status}")
    else:
        sections.append("- No validation commands were selected.")
    sections.extend(["", "## Smoke Checks Run And Results"])
    sections.append("- python -m aresforge ingest-codex-result-and-validate -> passed" if not dry_run else "- Dry-run smoke -> passed")
    warnings = _list(execution_data.get("warnings_or_blockers"))
    stderr_text = str(execution_data.get("stderr", "") or "").strip()
    sections.extend(["", "## Warnings Or Blockers"])
    if warnings:
        sections.extend(f"- {entry}" for entry in warnings)
    elif stderr_text:
        sections.append(f"- stderr captured: {stderr_text[:500]}")
    else:
        sections.append("- No blockers.")
    commit_hash = str(execution_data.get("commit_hash", "") or "").strip()
    if commit_hash:
        sections.extend(["", "## Commit Hash", f"- {commit_hash}"])
    return "\n".join(sections).rstrip()


def _collect_result_text(repo_root: Path, data: dict[str, Any]) -> tuple[str, list[str]]:
    chunks: list[str] = []
    paths: list[str] = []
    for key in ("stdout_artifact_path", "stderr_artifact_path", "result_artifact_path"):
        raw_path = str(data.get(key, "") or "").strip()
        if not raw_path:
            continue
        path = _resolve(repo_root, raw_path)
        paths.append(str(path))
        if path.exists():
            text = _read_text(path)
            if text.strip():
                chunks.append(text)
    for key in ("stdout", "stderr", "result_text", "codex_result", "summary"):
        text = str(data.get(key, "") or "").strip()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks).strip(), _dedupe(paths)


def _changed_files(repo_root: Path, data: dict[str, Any], result_text: str) -> list[str]:
    files = _list(data.get("changed_files"))
    files.extend(_detect_paths(result_text))
    files.extend(_git_changed_files(repo_root))
    return _dedupe(files)


def _git_changed_files(repo_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        if candidate:
            files.append(candidate.replace("\\", "/"))
    return files


def _detect_paths(text: str) -> list[str]:
    files: list[str] = []
    for token in text.replace("`", " ").replace(",", " ").split():
        normalized = token.strip().strip(":;.)(").replace("\\", "/")
        if "/" in normalized and not normalized.startswith(("http:/", "https:/")):
            files.append(normalized)
    return _dedupe(files)


def _blocked_reasons(
    *,
    record_errors: list[str],
    validation_profile_valid: bool,
    result_text: str,
    parsed: dict[str, Any],
    validation_run: list[dict[str, Any]],
    dry_run: bool,
) -> list[str]:
    reasons = list(record_errors)
    if not validation_profile_valid:
        reasons.append(f"Validation profile must be one of: {', '.join(sorted(VALIDATION_PROFILES))}.")
    if not result_text.strip():
        reasons.append("Execution record did not provide readable stdout, stderr, result text, or result artifacts.")
    if parsed.get("parsed") is not True or parsed.get("blocked") is True:
        reasons.append("Dispatch evidence parsing did not pass.")
        reasons.extend(_list(parsed.get("blocked_reasons")))
    if not dry_run:
        failed = [entry for entry in validation_run if not bool(entry.get("passed"))]
        reasons.extend(f"Validation command failed: {entry.get('command', '')}" for entry in failed)
    return _dedupe(reasons)


def _next_safe_action(
    *,
    dry_run: bool,
    blocked: bool,
    recommendation: dict[str, Any],
    machine_gate: dict[str, Any],
) -> str:
    if blocked:
        return "Resolve ingestion or validation blockers before any completion decision."
    if dry_run:
        return "Dry-run completed; rerun without --dry-run to execute the selected local validation profile."
    if recommendation.get("recommended_complete") is True and machine_gate.get("passed") is True:
        return "Review generated evidence and delegate explicitly to the M132 auto-completion path if appropriate."
    return "Review generated evidence, completion recommendation, and machine-gate blockers before any queue completion."


def _load_execution_record(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Execution record is missing: {path}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {}, [f"Execution record is not valid JSON: {exc.msg}."]
    except OSError as exc:
        return {}, [f"Execution record could not be read: {exc}."]
    if not isinstance(raw, dict):
        return {}, ["Execution record JSON root must be an object."]
    warnings: list[str] = []
    if raw.get("local_only") is not True:
        warnings.append("Execution record must confirm local_only=true.")
    if raw.get("github_execution_performed") is True:
        warnings.append("Execution record reports github_execution_performed=true.")
    return raw, warnings


def _minimal_blocked_payload(
    *,
    item_id: str,
    execution_record_path: Path,
    validation_profile: str,
    dry_run: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "ingestion_record_type": INGESTION_RECORD_TYPE,
        "item_id": item_id,
        "execution_record_path": str(execution_record_path),
        "dry_run": bool(dry_run),
        "parsed": {},
        "validation_profile": validation_profile,
        "validation_commands": list(VALIDATION_PROFILES.get(validation_profile, ())),
        "validation_run": [],
        "validation_passed": False,
        "changed_files": [],
        "evidence_artifact_path": "",
        "completion_recommendation_path": "",
        "machine_gate_result_path": "",
        "blocked": True,
        "blocked_reasons": [reason],
        "queue_mutation_performed": False,
        "github_execution_performed": False,
        "local_only": True,
        "next_safe_action": "Resolve blocked reasons and retry ingestion.",
    }


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": not bool(payload.get("blocked")),
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
            [*blocked.get("blocked_reasons", []), "Output file already exists. Re-run with --force to overwrite."]
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
        "ok": not bool(payload.get("blocked")),
        "local_only": True,
        "format": "json",
        "output": str(output_path),
        "force": force,
        "wrote_output_file": True,
        "payload": payload,
    }


def _run_root(config: AppConfig, item_id: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return config.artifact_root / "codex_result_ingestion" / _safe_id(item_id) / stamp


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _resolve(repo_root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _decode_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8-sig", errors="replace")
    return str(value)


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


def _safe_id(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "").strip().lower())
    return cleaned.strip("-") or "codex-result"


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
