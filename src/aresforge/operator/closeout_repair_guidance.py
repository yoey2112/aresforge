from __future__ import annotations

from typing import Any

from aresforge.config import AppConfig
from aresforge.operator.child_evidence_marker_preflight import inspect_child_evidence_marker_preflight
from aresforge.operator.parent_child_linkage_preflight import inspect_parent_child_linkage_preflight
from aresforge.operator.pr_mapping_preflight import inspect_pr_mapping_preflight


COMMAND_NAME = "generate-closeout-preflight-repair-guidance"


def generate_closeout_preflight_repair_guidance(config: AppConfig, *, parent_issue: int) -> dict[str, Any]:
    linkage = inspect_parent_child_linkage_preflight(config, parent_issue=parent_issue)
    evidence = inspect_child_evidence_marker_preflight(config, parent_issue=parent_issue)
    pr_mapping = inspect_pr_mapping_preflight(config, parent_issue=parent_issue)

    failures = _collect_failures(linkage=linkage, evidence=evidence, pr_mapping=pr_mapping)
    if failures:
        return {
            "command": COMMAND_NAME,
            "ok": False,
            "read_only": True,
            "error": "repair_guidance_dependency_failed",
            "parent_issue": parent_issue,
            "failures": failures,
            "required_operator_actions": [
                "Resolve preflight dependency command failures before generating repair guidance."
            ],
        }

    parent_repair = _parent_repair_guidance(parent_issue=parent_issue, linkage=linkage)
    child_repair = _child_repair_guidance(evidence=evidence)
    pr_repair = _pr_repair_guidance(pr_mapping=pr_mapping)
    evidence_marker_repair = _evidence_marker_repair_guidance(evidence=evidence)
    canonical_marker_repair = _canonical_marker_repair_guidance(parent_issue=parent_issue)

    guidance_text = _render_plain_text_guidance(
        parent_issue=parent_issue,
        parent_repair=parent_repair,
        child_repair=child_repair,
        pr_repair=pr_repair,
        evidence_marker_repair=evidence_marker_repair,
        canonical_marker_repair=canonical_marker_repair,
    )

    return {
        "command": COMMAND_NAME,
        "ok": True,
        "read_only": True,
        "parent_issue": parent_issue,
        "guidance": {
            "parent_repair": parent_repair,
            "child_repair": child_repair,
            "pr_mapping_repair": pr_repair,
            "evidence_marker_repair": evidence_marker_repair,
            "canonical_marker_repair": canonical_marker_repair,
        },
        "guidance_text": guidance_text,
        "mutation_executed": False,
        "boundary_confirmations": [
            "Read-only guidance generation only.",
            "No GitHub mutation was executed.",
            "Output is copy/paste guidance and does not execute mutation.",
        ],
    }


def _collect_failures(
    *,
    linkage: dict[str, Any],
    evidence: dict[str, Any],
    pr_mapping: dict[str, Any],
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for command, payload in (
        ("inspect-parent-child-linkage-preflight", linkage),
        ("inspect-child-evidence-marker-preflight", evidence),
        ("inspect-pr-mapping-preflight", pr_mapping),
    ):
        if bool(payload.get("ok")):
            continue
        failures.append({"command": command, "error": payload.get("error", "unknown_error")})
    return failures


def _parent_repair_guidance(*, parent_issue: int, linkage: dict[str, Any]) -> list[str]:
    blocked = linkage.get("blocked_reasons") if isinstance(linkage.get("blocked_reasons"), list) else []
    if not blocked:
        return ["Parent-child lineage references are ready; no parent lineage repair required."]
    return [
        "Update the parent issue body so each child issue appears once in the numbered child checklist.",
        f"PowerShell example: gh issue edit {parent_issue} --body-file artifacts/issue-{parent_issue}-body.md",
        "Re-run: python -m aresforge inspect-parent-child-linkage-preflight --parent-issue " + str(parent_issue),
    ]


def _child_repair_guidance(*, evidence: dict[str, Any]) -> list[str]:
    warnings = evidence.get("warning_reasons") if isinstance(evidence.get("warning_reasons"), list) else []
    blocked = evidence.get("blocked_reasons") if isinstance(evidence.get("blocked_reasons"), list) else []
    if not warnings and not blocked:
        return ["Child evidence marker coverage is ready; no child repair required."]
    return [
        "Update each child issue evidence comment/body to include branch, commit, PR, validation, and safety notes.",
        "PowerShell example: gh issue comment <child_issue> --body-file artifacts/issue-<child_issue>-evidence.txt",
        "Re-run: python -m aresforge inspect-child-evidence-marker-preflight --parent-issue <parent_issue>",
    ]


def _pr_repair_guidance(*, pr_mapping: dict[str, Any]) -> list[str]:
    warnings = pr_mapping.get("warning_reasons") if isinstance(pr_mapping.get("warning_reasons"), list) else []
    blocked = pr_mapping.get("blocked_reasons") if isinstance(pr_mapping.get("blocked_reasons"), list) else []
    if not warnings and not blocked:
        return ["PR mapping and merge evidence are ready; no PR mapping repair required."]
    return [
        "Ensure each child issue maps to exactly one implementation PR and that PR is merged.",
        "PowerShell example: gh pr view <pr_number> --json state,mergeCommit,url",
        "Re-run: python -m aresforge inspect-pr-mapping-preflight --parent-issue <parent_issue>",
    ]


def _evidence_marker_repair_guidance(*, evidence: dict[str, Any]) -> list[str]:
    children = evidence.get("children") if isinstance(evidence.get("children"), list) else []
    missing_rows: list[str] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        missing = child.get("missing_fields") if isinstance(child.get("missing_fields"), list) else []
        if not missing:
            continue
        issue_number = child.get("issue_number")
        if isinstance(issue_number, int):
            missing_rows.append(f"Issue #{issue_number}: missing {', '.join(sorted(str(item) for item in missing))}")
    if not missing_rows:
        return ["No child evidence marker field gaps detected."]
    return sorted(set(missing_rows))


def _render_plain_text_guidance(
    *,
    parent_issue: int,
    parent_repair: list[str],
    child_repair: list[str],
    pr_repair: list[str],
    evidence_marker_repair: list[str],
    canonical_marker_repair: list[str],
) -> str:
    lines: list[str] = [
        f"M23 closeout preflight repair guidance for parent issue #{parent_issue}",
        "",
        "PowerShell examples:",
        f"- gh issue view {parent_issue} --json state,url",
        f"- python -m aresforge inspect-milestone-closeout-preflight --parent-issue {parent_issue}",
        "",
        "Parent repair:",
        *[f"- {item}" for item in parent_repair],
        "",
        "Child repair:",
        *[f"- {item}" for item in child_repair],
        "",
        "PR mapping repair:",
        *[f"- {item}" for item in pr_repair],
        "",
        "Evidence marker repair:",
        *[f"- {item}" for item in evidence_marker_repair],
        "",
        "Canonical marker repair:",
        *[f"- {item}" for item in canonical_marker_repair],
        "",
        "Safety boundary: guidance only, no mutation executed.",
    ]
    return "\n".join(lines).strip() + "\n"


def _canonical_marker_repair_guidance(*, parent_issue: int) -> list[str]:
    return [
        f"Generate canonical child marker templates: python -m aresforge generate-child-evidence-marker-template --parent-issue {parent_issue} --child-issue <child_issue>",
        "Generate canonical PR marker templates: python -m aresforge generate-pr-evidence-marker-template --issue <child_issue> --pr <pr_number>",
        f"Generate canonical parent marker template: python -m aresforge generate-parent-closeout-marker-template --parent-issue {parent_issue}",
    ]
