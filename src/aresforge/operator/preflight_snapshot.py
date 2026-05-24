from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_preflight import inspect_child_evidence_marker_preflight
from aresforge.operator.milestone_closeout_preflight import inspect_milestone_closeout_preflight
from aresforge.operator.milestone_state_inspector import inspect_milestone_state
from aresforge.operator.parent_closeout_readiness import inspect_parent_closeout_readiness
from aresforge.operator.pr_mapping_preflight import inspect_pr_mapping_preflight


GENERATE_COMMAND_NAME = "generate-preflight-baseline-snapshot"
DIFF_COMMAND_NAME = "diff-preflight-snapshots"
SNAPSHOT_SCHEMA_VERSION = "m24.v1"


def generate_preflight_baseline_snapshot(
    config: AppConfig,
    *,
    parent_issue: int,
    output_path: str | None = None,
) -> dict[str, Any]:
    snapshot_payload = build_preflight_snapshot(config, parent_issue=parent_issue)
    if not bool(snapshot_payload.get("ok")):
        return {
            "command": GENERATE_COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "error": "snapshot_dependency_failed",
            "details": snapshot_payload,
        }

    destination = _resolve_output_path(config=config, parent_issue=parent_issue, output_path=output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(snapshot_payload["snapshot"], indent=2) + "\n", encoding="utf-8")

    return {
        "command": GENERATE_COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "snapshot_path": str(destination),
        "snapshot": snapshot_payload["snapshot"],
        "safety_notes": [
            "Read-only snapshot generation only.",
            "No GitHub issue, PR, or closeout mutation was executed.",
            "Snapshot file is local artifact output for audit/reconciliation use.",
        ],
    }


def build_preflight_snapshot(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    milestone = inspect_milestone_state(config, parent_issue=parent_issue)
    child_evidence = inspect_child_evidence_marker_preflight(config, parent_issue=parent_issue)
    pr_mapping = inspect_pr_mapping_preflight(config, parent_issue=parent_issue)
    readiness = inspect_parent_closeout_readiness(config, parent_issue=parent_issue)
    closeout_preflight = inspect_milestone_closeout_preflight(config, parent_issue=parent_issue)

    failures = _collect_failures(
        milestone=milestone,
        child_evidence=child_evidence,
        pr_mapping=pr_mapping,
        readiness=readiness,
        closeout_preflight=closeout_preflight,
    )
    if failures:
        return {
            "command": GENERATE_COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "parent_issue": parent_issue,
            "failures": failures,
        }

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "parent_issue": parent_issue,
        "lineage_state": _as_text((milestone.get("summary") or {}).get("state_summary")),
        "child_evidence_state": _as_text((child_evidence.get("evidence_summary") or {}).get("aggregate_state")),
        "pr_mapping_state": _as_text((pr_mapping.get("pr_mapping_summary") or {}).get("aggregate_state")),
        "readiness_state": _readiness_state(readiness),
        "closeout_preflight_state": _as_text((closeout_preflight.get("closeout_preflight") or {}).get("aggregate_state")),
        "blocked_reasons": _sorted_strings(closeout_preflight.get("blocked_reasons")),
        "warning_reasons": _sorted_strings(closeout_preflight.get("warning_reasons")),
        "unknown_reasons": _sorted_strings(closeout_preflight.get("unknown_reasons")),
        "child_issue_count": int((milestone.get("summary") or {}).get("child_issue_count") or 0),
        "closeout_ready": bool((closeout_preflight.get("closeout_preflight") or {}).get("closeout_ready")),
    }

    return {
        "command": GENERATE_COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "snapshot": snapshot,
    }


def diff_preflight_snapshots(*, before_path: str, after_path: str) -> dict[str, Any]:
    before = _load_snapshot(before_path)
    after = _load_snapshot(after_path)

    field_changes: dict[str, dict[str, Any]] = {}
    verdicts: list[str] = []
    for field in (
        "lineage_state",
        "child_evidence_state",
        "pr_mapping_state",
        "readiness_state",
        "closeout_preflight_state",
    ):
        verdict = _state_change_verdict(before.get(field), after.get(field))
        verdicts.append(verdict)
        field_changes[field] = {
            "before": before.get(field),
            "after": after.get(field),
            "verdict": verdict,
        }

    for field in (
        "blocked_reasons",
        "warning_reasons",
        "unknown_reasons",
    ):
        verdict = _count_change_verdict(before.get(field), after.get(field))
        verdicts.append(verdict)
        field_changes[field] = {
            "before": before.get(field),
            "after": after.get(field),
            "verdict": verdict,
        }

    verdicts = [value for value in verdicts if value in {"no-change", "improved", "regressed"}]
    classification = _classify_diff(verdicts)

    return {
        "command": DIFF_COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "before_path": before_path,
        "after_path": after_path,
        "classification": classification,
        "field_changes": field_changes,
        "summary": {
            "improved_count": verdicts.count("improved"),
            "regressed_count": verdicts.count("regressed"),
            "no_change_count": verdicts.count("no-change"),
        },
        "safety_notes": [
            "Read-only snapshot diff only.",
            "No GitHub issue, PR, or closeout mutation was executed.",
        ],
    }


def _collect_failures(
    *,
    milestone: dict[str, Any],
    child_evidence: dict[str, Any],
    pr_mapping: dict[str, Any],
    readiness: dict[str, Any],
    closeout_preflight: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for command, payload in (
        ("inspect-milestone-state", milestone),
        ("inspect-child-evidence-marker-preflight", child_evidence),
        ("inspect-pr-mapping-preflight", pr_mapping),
        ("inspect-parent-closeout-readiness", readiness),
        ("inspect-milestone-closeout-preflight", closeout_preflight),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append(
            {
                "command": command,
                "error": payload.get("error", "unknown_error"),
            }
        )
    return failures


def _resolve_output_path(*, config: AppConfig, parent_issue: int, output_path: str | None) -> Path:
    if output_path:
        return Path(output_path)
    return config.evidence_dir / f"preflight-snapshot-parent-{parent_issue}.json"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _sorted_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    rows = [str(item).strip() for item in values if isinstance(item, str) and item.strip()]
    return sorted(set(rows))


def _readiness_state(readiness: dict[str, Any]) -> str:
    closeout = readiness.get("closeout_readiness") if isinstance(readiness.get("closeout_readiness"), dict) else {}
    return "ready" if closeout.get("parent_closeout_ready") is True else "blocked"


def _load_snapshot(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return payload


def _state_rank(value: Any) -> int:
    normalized = _as_text(value)
    ranks = {
        "blocked": 0,
        "unknown": 1,
        "warning": 2,
        "ready": 3,
    }
    return ranks.get(normalized, 1)


def _state_change_verdict(before_value: Any, after_value: Any) -> str:
    before_rank = _state_rank(before_value)
    after_rank = _state_rank(after_value)
    if after_rank > before_rank:
        return "improved"
    if after_rank < before_rank:
        return "regressed"
    return "no-change"


def _count_change_verdict(before_value: Any, after_value: Any) -> str:
    before_count = len(before_value) if isinstance(before_value, list) else 0
    after_count = len(after_value) if isinstance(after_value, list) else 0
    if after_count < before_count:
        return "improved"
    if after_count > before_count:
        return "regressed"
    return "no-change"


def _classify_diff(verdicts: list[str]) -> str:
    has_improved = "improved" in verdicts
    has_regressed = "regressed" in verdicts
    if not has_improved and not has_regressed:
        return "no-change"
    if has_improved and not has_regressed:
        return "improved"
    if has_regressed and not has_improved:
        return "regressed"
    return "mixed"
