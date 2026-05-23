from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig


def append_github_mutation_audit_log(config: AppConfig, *, record: dict[str, Any]) -> dict[str, Any]:
    log_path = _default_log_path(config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "logged_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "record": record,
        "local_only": True,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return {"ok": True, "log_path": str(log_path)}


def inspect_github_mutation_audit_log(config: AppConfig, *, limit: int = 20) -> dict[str, Any]:
    log_path = _default_log_path(config)
    if not log_path.exists():
        return {
            "command": "inspect-github-mutation-audit-log",
            "ok": True,
            "log_path": str(log_path),
            "entry_count": 0,
            "entries": [],
            "warnings": ["No local mutation audit log entries found yet."],
            "boundary_confirmations": [
                "Read-only local audit log inspection only.",
                "No GitHub mutation was performed.",
                "Audit artifacts remain local-only unless explicitly exported by an operator.",
            ],
        }

    lines = log_path.read_text(encoding="utf-8").splitlines()
    parsed: list[dict[str, Any]] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            entry = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            parsed.append(entry)

    tail = parsed[-limit:] if limit > 0 else parsed
    return {
        "command": "inspect-github-mutation-audit-log",
        "ok": True,
        "log_path": str(log_path),
        "entry_count": len(parsed),
        "entries": tail,
        "warnings": [],
        "boundary_confirmations": [
            "Read-only local audit log inspection only.",
            "No GitHub mutation was performed.",
            "Audit artifacts remain local-only unless explicitly exported by an operator.",
        ],
    }


def _default_log_path(config: AppConfig) -> Path:
    return (config.artifact_root / "mutation_audit" / "github-mutation-audit-log.jsonl").resolve()
