from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

LOG_TYPE = "queue_mutation_transaction_log"
LOG_SCHEMA_VERSION = "m122.1"
LOG_PATH_RELATIVE = Path(".aresforge") / "queue" / "transaction_log.json"
COMMAND_NAME = "inspect-queue-transaction-log"

_BOUNDARY_CONFIRMATIONS = (
    "M122 queue mutation transaction log is local-only.",
    "M122 records metadata for file-backed queue mutations only.",
    "M122 does not execute Codex, Ollama, local LLMs, agents, GitHub, gh, network services, validation commands, or patches.",
    "M122 does not start, block, or complete work from the inspection command.",
    "execution_allowed=false is preserved for inspection payloads.",
)


def append_queue_transaction(
    config: AppConfig,
    *,
    project_id: str | None,
    item_id: str | None,
    previous_status: str | None,
    new_status: str | None,
    mutation_type: str,
    actor: str | None = None,
    source: str | None = None,
    evidence_summary: str | None = None,
    reason: str | None = None,
    title: str | None = None,
    queue_path: str | Path | None = None,
    log_path: str | Path | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_log_path = resolve_queue_transaction_log_path(config.repo_root, log_path)
    try:
        loaded = _load_log_file(resolved_log_path)
        transactions = loaded["transactions"]
        now = _now_iso()
        transaction = {
            "transaction_id": _transaction_id(item_id=item_id, mutation_type=mutation_type, timestamp=now, sequence=len(transactions) + 1),
            "timestamp": now,
            "item_id": str(item_id or "").strip(),
            "title": str(title or "").strip(),
            "project_id": str(project_id or "").strip(),
            "previous_status": str(previous_status or "").strip(),
            "new_status": str(new_status or "").strip(),
            "mutation_type": str(mutation_type or "queue_mutation").strip() or "queue_mutation",
            "actor": str(actor or "local_operator").strip() or "local_operator",
            "source": str(source or "").strip(),
            "evidence_summary": str(evidence_summary or "").strip(),
            "reason": str(reason or "").strip(),
            "queue_path": str(Path(queue_path).resolve()) if queue_path is not None else "",
            "metadata": metadata if isinstance(metadata, dict) else {},
            "local_only": True,
            "execution_allowed": False,
        }
        transactions.append(transaction)
        _write_log_file(resolved_log_path, transactions, now)
        return {
            "ok": True,
            "transaction": transaction,
            "log_path": str(resolved_log_path),
            "warnings": [],
        }
    except Exception as exc:  # pragma: no cover - deliberately best-effort around queue mutations.
        return {
            "ok": False,
            "transaction": {},
            "log_path": str(resolved_log_path),
            "warnings": [f"Queue transaction log append failed: {exc}"],
        }


def inspect_queue_transaction_log(
    config: AppConfig,
    *,
    project_id: str,
    item_id: str | None = None,
    output: str | Path | None = None,
    force: bool = False,
    output_format: str = "json",
    log_path: str | Path | None = None,
) -> dict[str, Any]:
    fmt = str(output_format or "json").strip().lower()
    if fmt not in {"json", "markdown"}:
        return _error("invalid_format", {"format": output_format, "supported_formats": ["json", "markdown"]})
    normalized_project_id = str(project_id or "").strip()
    if not normalized_project_id:
        return _error("invalid_project_id", {"message": "project_id is required."})

    normalized_item_id = str(item_id or "").strip()
    resolved_log_path = resolve_queue_transaction_log_path(config.repo_root, log_path)
    loaded = _load_log_file(resolved_log_path)
    transactions = [
        transaction
        for transaction in loaded["transactions"]
        if _matches_filters(transaction, project_id=normalized_project_id, item_id=normalized_item_id)
    ]
    latest_by_item = _latest_transaction_by_item(transactions)
    mutation_warnings = list(loaded["warnings"])
    if not resolved_log_path.exists():
        mutation_warnings.append("Queue transaction log file does not exist yet.")

    payload: dict[str, Any] = {
        "ok": True,
        "log_type": LOG_TYPE,
        "log_schema_version": LOG_SCHEMA_VERSION,
        "generated": True,
        "generated_at": _now_iso(),
        "project_id": normalized_project_id,
        "item_id": normalized_item_id,
        "log_path": str(resolved_log_path),
        "transaction_count": len(transactions),
        "transactions": transactions,
        "latest_transaction_by_item": latest_by_item,
        "mutation_warnings": sorted(set(warning for warning in mutation_warnings if str(warning).strip())),
        "local_only": True,
        "execution_allowed": False,
        "next_safe_action": _next_safe_action(transactions=transactions, warnings=mutation_warnings),
        "boundary_confirmations": list(_BOUNDARY_CONFIRMATIONS),
    }
    return _emit_or_write(config=config, payload=payload, output=output, force=force, output_format=fmt)


def resolve_queue_transaction_log_path(repo_root: Path, path: str | Path | None = None) -> Path:
    if path is None:
        return (repo_root / LOG_PATH_RELATIVE).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def queue_transaction_warning(result: dict[str, Any]) -> list[str]:
    return [
        str(warning).strip()
        for warning in result.get("warnings", [])
        if str(warning).strip()
    ]


def _load_log_file(path: Path) -> dict[str, Any]:
    warnings: list[str] = []
    if not path.exists():
        return {"transactions": [], "warnings": warnings}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f"Queue transaction log could not be read: {exc}")
        return {"transactions": [], "warnings": warnings}
    if not isinstance(raw, dict):
        warnings.append("Queue transaction log JSON must decode to an object.")
        return {"transactions": [], "warnings": warnings}
    transactions = raw.get("transactions", [])
    if not isinstance(transactions, list):
        warnings.append("Queue transaction log transactions field is not a list.")
        transactions = []
    return {
        "transactions": [
            transaction
            for transaction in transactions
            if isinstance(transaction, dict)
        ],
        "warnings": warnings,
    }


def _write_log_file(path: Path, transactions: list[dict[str, Any]], updated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": LOG_SCHEMA_VERSION,
        "log_type": LOG_TYPE,
        "updated_at": updated_at,
        "transactions": transactions,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _emit_or_write(
    *,
    config: AppConfig,
    payload: dict[str, Any],
    output: str | Path | None,
    force: bool,
    output_format: str,
) -> dict[str, Any]:
    rendered = json.dumps(payload, indent=2) if output_format == "json" else _render_markdown(payload)
    if output is None:
        return {
            "command": COMMAND_NAME,
            "ok": True,
            "local_only": True,
            "format": output_format,
            "wrote_output_file": False,
            "stdout": rendered,
            "payload": payload,
        }
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = config.repo_root / output_path
    output_path = output_path.resolve()
    if output_path.exists() and not force:
        return _error(
            "output_exists",
            {
                "output_path": str(output_path),
                "message": "Output file already exists. Re-run with --force to overwrite.",
            },
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered + "\n", encoding="utf-8")
    return {
        "command": COMMAND_NAME,
        "ok": True,
        "local_only": True,
        "format": output_format,
        "wrote_output_file": True,
        "output_path": str(output_path),
        "payload": payload,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Queue Mutation Transaction Log",
        "",
        f"- log_type: {payload.get('log_type')}",
        f"- project_id: {payload.get('project_id')}",
        f"- item_id: {payload.get('item_id') or ''}",
        f"- transaction_count: {payload.get('transaction_count')}",
        f"- execution_allowed: {str(payload.get('execution_allowed')).lower()}",
        "",
        "## Transactions",
    ]
    transactions = payload.get("transactions", [])
    if not isinstance(transactions, list) or not transactions:
        lines.append("- None")
    else:
        for transaction in transactions:
            if not isinstance(transaction, dict):
                continue
            lines.append(
                "- "
                f"{transaction.get('timestamp')} | "
                f"{transaction.get('item_id')} | "
                f"{transaction.get('mutation_type')} | "
                f"{transaction.get('previous_status')} -> {transaction.get('new_status')} | "
                f"actor={transaction.get('actor')}"
            )
    warnings = payload.get("mutation_warnings", [])
    lines.extend(["", "## Mutation Warnings"])
    if isinstance(warnings, list) and warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")
    lines.extend(["", f"- next_safe_action: {payload.get('next_safe_action')}"])
    return "\n".join(lines)


def _matches_filters(transaction: dict[str, Any], *, project_id: str, item_id: str) -> bool:
    if str(transaction.get("project_id", "")).strip() != project_id:
        return False
    if item_id and str(transaction.get("item_id", "")).strip() != item_id:
        return False
    return True


def _latest_transaction_by_item(transactions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for transaction in sorted(transactions, key=lambda entry: str(entry.get("timestamp", ""))):
        item_id = str(transaction.get("item_id", "")).strip()
        if item_id:
            latest[item_id] = transaction
    return latest


def _next_safe_action(*, transactions: list[dict[str, Any]], warnings: list[str]) -> str:
    if warnings:
        return "Review transaction log warnings and inspect the local queue before further mutations."
    if not transactions:
        return "Perform an explicit local queue mutation, then inspect the transaction log again."
    return "Review the latest transaction entries alongside the local queue before any next operator-gated mutation."


def _transaction_id(*, item_id: str | None, mutation_type: str, timestamp: str, sequence: int) -> str:
    seed = f"{timestamp}|{item_id or ''}|{mutation_type}|{sequence}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    normalized_type = _slug(mutation_type)
    return f"queue-tx-{timestamp.replace(':', '').replace('-', '').replace('+00:00', 'Z')}-{normalized_type}-{digest}"


def _slug(value: str) -> str:
    return "-".join(part for part in "".join(char.lower() if char.isalnum() else " " for char in str(value)).split() if part) or "mutation"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _error(error: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "command": COMMAND_NAME,
        "ok": False,
        "local_only": True,
        "error": error,
        "details": details,
    }
