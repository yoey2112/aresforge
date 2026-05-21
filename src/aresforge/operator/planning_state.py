from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig

PLANNING_STATE_SCHEMA_VERSION = "1.0"
DEFAULT_PLANNING_STATE_RELATIVE_PATH = ".aresforge/planning-state.json"


@dataclass(frozen=True)
class PlanningStateLoadResult:
    path: Path
    exists: bool
    valid: bool
    data: dict[str, Any] | None
    errors: list[str]


def resolve_planning_state_path(
    *,
    config: AppConfig | None = None,
    path_override: str | None = None,
    repo_root: Path | None = None,
) -> Path:
    if path_override:
        raw = Path(path_override)
        if raw.is_absolute():
            return raw
        if config is not None:
            return (config.repo_root / raw).resolve()
        if repo_root is not None:
            return (repo_root / raw).resolve()
        return raw.resolve()

    root = repo_root
    if root is None and config is not None:
        root = config.repo_root
    if root is None:
        root = Path.cwd()
    return (root / DEFAULT_PLANNING_STATE_RELATIVE_PATH).resolve()


def load_planning_state(path: Path) -> PlanningStateLoadResult:
    if not path.exists():
        return PlanningStateLoadResult(path=path, exists=False, valid=False, data=None, errors=[])

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return PlanningStateLoadResult(
            path=path,
            exists=True,
            valid=False,
            data=None,
            errors=[f"invalid_json: {exc}"],
        )

    errors = validate_planning_state(payload)
    return PlanningStateLoadResult(
        path=path,
        exists=True,
        valid=not errors,
        data=payload if isinstance(payload, dict) else None,
        errors=errors,
    )


def validate_planning_state(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["root_must_be_object"]

    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str):
        errors.append("schema_version_missing_or_invalid")
    elif schema_version != PLANNING_STATE_SCHEMA_VERSION:
        errors.append("unsupported_schema_version")

    if not isinstance(payload.get("sprint_plans"), list):
        errors.append("sprint_plans_missing_or_invalid")
    if not isinstance(payload.get("closeout_snapshots"), list):
        errors.append("closeout_snapshots_missing_or_invalid")

    return errors


def empty_planning_state() -> dict[str, Any]:
    return {
        "schema_version": PLANNING_STATE_SCHEMA_VERSION,
        "planned_state": {
            "sprint_plans": [],
            "parent_child_relationships": [],
        },
        "observed_state": {
            "closeout_snapshots": [],
        },
        "historical_snapshots": {
            "closeout_planning": [],
        },
        "command_runs": [],
        "sprint_plans": [],
        "closeout_snapshots": [],
    }


def _ensure_collections(data: dict[str, Any]) -> None:
    if not isinstance(data.get("sprint_plans"), list):
        data["sprint_plans"] = []
    if not isinstance(data.get("closeout_snapshots"), list):
        data["closeout_snapshots"] = []
    if not isinstance(data.get("command_runs"), list):
        data["command_runs"] = []
    if not isinstance(data.get("planned_state"), dict):
        data["planned_state"] = {"sprint_plans": [], "parent_child_relationships": []}
    if not isinstance(data.get("observed_state"), dict):
        data["observed_state"] = {"closeout_snapshots": []}
    if not isinstance(data.get("historical_snapshots"), dict):
        data["historical_snapshots"] = {"closeout_planning": []}


def _write_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def persist_sprint_plan(
    *,
    path: Path,
    sprint_plan: dict[str, Any],
    command_name: str,
) -> dict[str, Any]:
    loaded = load_planning_state(path)
    if loaded.exists and loaded.valid and loaded.data is not None:
        data = loaded.data
    elif loaded.exists:
        data = empty_planning_state()
    else:
        data = empty_planning_state()

    _ensure_collections(data)
    sprint_plans: list[dict[str, Any]] = data["sprint_plans"]

    sprint_id = sprint_plan.get("sprint_id")
    if isinstance(sprint_id, str):
        sprint_plans = [item for item in sprint_plans if item.get("sprint_id") != sprint_id]
    sprint_plans.append(sprint_plan)
    sprint_plans.sort(key=lambda item: str(item.get("sprint_id", "")))
    data["sprint_plans"] = sprint_plans

    relationships = _derive_relationships(sprint_plans)
    data["planned_state"] = {
        "sprint_plans": sprint_plans,
        "parent_child_relationships": relationships,
    }

    command_runs = [
        item
        for item in data["command_runs"]
        if not (
            item.get("command") == command_name and item.get("context") == str(sprint_id)
        )
    ]
    command_runs.append(
        {
            "command": command_name,
            "context": str(sprint_id),
            "mutation": "local_state_write",
        }
    )
    command_runs.sort(key=lambda item: (str(item.get("command", "")), str(item.get("context", ""))))
    data["command_runs"] = command_runs

    _write_state(path, data)
    return {
        "path": str(path),
        "schema_version": data["schema_version"],
        "sprint_plan_count": len(data["sprint_plans"]),
        "closeout_snapshot_count": len(data["closeout_snapshots"]),
    }


def persist_closeout_snapshot(
    *,
    path: Path,
    snapshot: dict[str, Any],
    command_name: str,
) -> dict[str, Any]:
    loaded = load_planning_state(path)
    if loaded.exists and loaded.valid and loaded.data is not None:
        data = loaded.data
    elif loaded.exists:
        data = empty_planning_state()
    else:
        data = empty_planning_state()

    _ensure_collections(data)
    snapshots: list[dict[str, Any]] = data["closeout_snapshots"]

    snapshot_id = snapshot.get("snapshot_id")
    if isinstance(snapshot_id, str):
        snapshots = [item for item in snapshots if item.get("snapshot_id") != snapshot_id]
    snapshots.append(snapshot)
    snapshots.sort(key=lambda item: str(item.get("snapshot_id", "")))
    data["closeout_snapshots"] = snapshots
    data["observed_state"] = {"closeout_snapshots": snapshots}
    data["historical_snapshots"] = {"closeout_planning": snapshots}

    parent_issue = snapshot.get("parent_issue")
    command_runs = [
        item
        for item in data["command_runs"]
        if not (
            item.get("command") == command_name and item.get("context") == str(parent_issue)
        )
    ]
    command_runs.append(
        {
            "command": command_name,
            "context": str(parent_issue),
            "mutation": "local_state_write",
        }
    )
    command_runs.sort(key=lambda item: (str(item.get("command", "")), str(item.get("context", ""))))
    data["command_runs"] = command_runs

    _write_state(path, data)
    return {
        "path": str(path),
        "schema_version": data["schema_version"],
        "sprint_plan_count": len(data["sprint_plans"]),
        "closeout_snapshot_count": len(data["closeout_snapshots"]),
    }


def inspect_planning_state(*, path: Path) -> dict[str, Any]:
    loaded = load_planning_state(path)
    if not loaded.exists:
        return {
            "command": "inspect-planning-state",
            "ok": True,
            "state_exists": False,
            "planning_state_path": str(path),
            "summary": {
                "schema_version": None,
                "sprint_plan_count": 0,
                "closeout_snapshot_count": 0,
                "relationship_count": 0,
                "validation_status": "missing_state",
            },
            "warnings": ["No local planning state file exists."],
        }

    if not loaded.valid or loaded.data is None:
        return {
            "command": "inspect-planning-state",
            "ok": False,
            "state_exists": True,
            "planning_state_path": str(path),
            "summary": {
                "schema_version": loaded.data.get("schema_version") if isinstance(loaded.data, dict) else None,
                "sprint_plan_count": 0,
                "closeout_snapshot_count": 0,
                "relationship_count": 0,
                "validation_status": "invalid",
            },
            "validation_errors": loaded.errors,
        }

    data = loaded.data
    sprint_plans = data.get("sprint_plans") if isinstance(data.get("sprint_plans"), list) else []
    snapshots = data.get("closeout_snapshots") if isinstance(data.get("closeout_snapshots"), list) else []
    relationships = _derive_relationships([item for item in sprint_plans if isinstance(item, dict)])

    latest_sprint = sprint_plans[-1].get("sprint_id") if sprint_plans else None
    latest_snapshot = snapshots[-1].get("snapshot_id") if snapshots else None

    return {
        "command": "inspect-planning-state",
        "ok": True,
        "state_exists": True,
        "planning_state_path": str(path),
        "summary": {
            "schema_version": data.get("schema_version"),
            "sprint_plan_count": len(sprint_plans),
            "closeout_snapshot_count": len(snapshots),
            "relationship_count": len(relationships),
            "validation_status": "valid",
            "latest_sprint_id": latest_sprint,
            "latest_snapshot_id": latest_snapshot,
        },
    }


def compare_planning_state(*, path: Path) -> dict[str, Any]:
    loaded = load_planning_state(path)
    if not loaded.exists:
        return {
            "command": "compare-planning-state",
            "ok": True,
            "state_exists": False,
            "planning_state_path": str(path),
            "drift_findings": ["no_planning_state"],
        }

    if not loaded.valid or loaded.data is None:
        return {
            "command": "compare-planning-state",
            "ok": False,
            "state_exists": True,
            "planning_state_path": str(path),
            "drift_findings": ["invalid_or_unsupported_state"],
            "validation_errors": loaded.errors,
        }

    data = loaded.data
    sprint_plans = [item for item in data.get("sprint_plans", []) if isinstance(item, dict)]
    snapshots = [item for item in data.get("closeout_snapshots", []) if isinstance(item, dict)]

    findings: list[dict[str, Any]] = []
    parent_numbers = {
        item.get("parent_issue", {}).get("number")
        for item in sprint_plans
        if isinstance(item.get("parent_issue"), dict) and isinstance(item.get("parent_issue", {}).get("number"), int)
    }

    for sprint in sprint_plans:
        sprint_id = sprint.get("sprint_id")
        children = [c for c in sprint.get("children", []) if isinstance(c, dict)]
        child_numbers = [c.get("number") for c in children if isinstance(c.get("number"), int)]
        child_titles = [c.get("title") for c in children if isinstance(c.get("title"), str)]

        dup_numbers = sorted({n for n in child_numbers if child_numbers.count(n) > 1})
        dup_titles = sorted({t for t in child_titles if child_titles.count(t) > 1})
        if dup_numbers:
            findings.append({"type": "duplicate_child_issue_numbers", "sprint_id": sprint_id, "values": dup_numbers})
        if dup_titles:
            findings.append({"type": "duplicate_child_issue_titles", "sprint_id": sprint_id, "values": dup_titles})

        relationships = sprint.get("relationships")
        if not isinstance(relationships, list) or not relationships:
            findings.append({"type": "missing_relationship_metadata", "sprint_id": sprint_id})

    snapshot_parents = []
    for snap in snapshots:
        parent_issue = snap.get("parent_issue")
        if isinstance(parent_issue, int):
            snapshot_parents.append(parent_issue)
        if isinstance(parent_issue, int) and parent_issue not in parent_numbers:
            findings.append({"type": "snapshot_parent_without_known_sprint_parent", "parent_issue": parent_issue})

    for parent in sorted(parent_numbers):
        if parent not in snapshot_parents:
            findings.append({"type": "stale_or_absent_snapshot_for_known_parent", "parent_issue": parent})

    return {
        "command": "compare-planning-state",
        "ok": True,
        "state_exists": True,
        "planning_state_path": str(path),
        "drift_findings": findings,
        "drift_detected": bool(findings),
    }


def _derive_relationships(sprint_plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    relationships: list[dict[str, Any]] = []
    for sprint in sprint_plans:
        sprint_id = sprint.get("sprint_id")
        parent = sprint.get("parent_issue") if isinstance(sprint.get("parent_issue"), dict) else {}
        parent_number = parent.get("number") if isinstance(parent.get("number"), int) else None
        children = sprint.get("children") if isinstance(sprint.get("children"), list) else []
        for child in children:
            if not isinstance(child, dict):
                continue
            relationships.append(
                {
                    "sprint_id": sprint_id,
                    "parent_issue_number": parent_number,
                    "child_issue_number": child.get("number") if isinstance(child.get("number"), int) else None,
                    "child_title": child.get("title"),
                }
            )
    relationships.sort(
        key=lambda item: (
            str(item.get("sprint_id", "")),
            int(item["parent_issue_number"]) if isinstance(item.get("parent_issue_number"), int) else -1,
            int(item["child_issue_number"]) if isinstance(item.get("child_issue_number"), int) else -1,
            str(item.get("child_title", "")),
        )
    )
    return relationships
