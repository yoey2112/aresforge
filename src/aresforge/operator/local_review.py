from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from aresforge.artifacts.store import ArtifactBundle, write_markdown_json_bundle
from aresforge.config import AppConfig
from aresforge.db.connection import connect
from aresforge.db.repository import (
    inspect_model,
    inspect_project,
    list_agents,
    list_models,
    list_projects,
    list_queues,
)
from aresforge.operator.artifact_discovery import (
    discover_local_artifacts,
    discover_local_evidence_packages,
    inspect_local_artifact,
    inspect_local_evidence_package,
)
from aresforge.operator.registry_inspection import inspect_local_registries
from aresforge.validation import validate_registry_seed_data


@dataclass(frozen=True, slots=True)
class LocalReviewOptions:
    project_id: str
    model_id: str
    include_artifacts: bool = False
    artifact_path: str | None = None
    include_evidence_packages: bool = False
    evidence_path: str | None = None
    write_review_package: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "model_id": self.model_id,
            "include_artifacts": self.include_artifacts,
            "artifact_path": self.artifact_path,
            "include_evidence_packages": self.include_evidence_packages,
            "evidence_path": self.evidence_path,
            "write_review_package": self.write_review_package,
        }


def _local_reviews_dir(config: AppConfig) -> Path:
    return config.artifact_root / "local_reviews" / "generated"


def _code_block(value: Any) -> list[str]:
    return ["```json", json.dumps(value, indent=2, sort_keys=True), "```"]


def _bullet_lines(items: list[str], empty_message: str) -> list[str]:
    return [f"- {item}" for item in items] or [f"- {empty_message}"]


def _render_local_review_package(
    *,
    config: AppConfig,
    payload: dict[str, Any],
) -> ArtifactBundle:
    checks_run = payload["checks_run"]
    checks_skipped = payload["checks_skipped"]
    status_lines = [
        f"- {check['name']}: `{check['status']}`"
        for check in checks_run
    ] or ["- No checks executed."]
    skipped_lines = [
        f"- {check['name']}: `{check['reason']}`"
        for check in checks_skipped
    ] or ["- No checks skipped."]
    markdown = "\n".join(
        [
            "# Local Review Package",
            "",
            "## Command",
            f"- Command: `{payload['command']}`",
            f"- Overall Status: `{payload['status']}`",
            "",
            "## Requested Options",
            *_code_block(payload["requested_options"]),
            "",
            "## Checks Run",
            *status_lines,
            "",
            "## Checks Skipped",
            *skipped_lines,
            "",
            "## Skip Reasons",
            *_code_block(payload["skip_reasons"]),
            "",
            "## Artifact Summary",
            *_code_block(payload.get("artifact_summary")),
            "",
            "## Evidence Package Summary",
            *_code_block(payload.get("evidence_package_summary")),
            "",
            "## Boundary Confirmation",
            *(
                _bullet_lines(
                    payload["boundary_confirmations"],
                    "No boundary confirmations recorded.",
                )
            ),
        ]
    )
    return write_markdown_json_bundle(
        _local_reviews_dir(config),
        title=(
            f"local-review-{payload['requested_options']['project_id']}-"
            f"{payload['requested_options']['model_id']}"
        ),
        markdown=markdown,
        payload=payload,
    )


def _execute_check(
    *,
    checks_run: list[dict[str, Any]],
    name: str,
    runner: Any,
) -> dict[str, Any] | None:
    try:
        payload = runner()
    except NotImplementedError as exc:
        return {"name": name, "reason": str(exc) or "capability_unavailable"}
    except Exception as exc:
        checks_run.append(
            {
                "name": name,
                "status": "failed",
                "ok": False,
                "error": str(exc),
                "result": None,
            }
        )
        return None

    ok = bool(payload.get("ok", True))
    checks_run.append(
        {
            "name": name,
            "status": "passed" if ok else "failed",
            "ok": ok,
            "error": payload.get("error"),
            "result": payload,
        }
    )
    return payload


def _database_check(config: AppConfig, action: Any) -> Any:
    def runner() -> dict[str, Any]:
        with connect(config) as conn:
            return action(conn)

    return runner


def run_local_review(
    config: AppConfig,
    *,
    options: LocalReviewOptions,
) -> dict[str, Any]:
    requested_options = options.as_dict()
    checks_run: list[dict[str, Any]] = []
    checks_skipped: list[dict[str, str]] = []
    artifact_summary: dict[str, Any] | None = None
    evidence_package_summary: dict[str, Any] | None = None

    def skip(name: str, reason: str) -> None:
        checks_skipped.append({"name": name, "reason": reason})

    validation_errors = config.validate()
    validate_config_payload = {
        "ok": not validation_errors,
        "errors": validation_errors,
        "config": config.summary(),
    }
    checks_run.append(
        {
            "name": "validate-config",
            "status": "passed" if validate_config_payload["ok"] else "failed",
            "ok": validate_config_payload["ok"],
            "error": None if validate_config_payload["ok"] else "config_validation_failed",
            "result": validate_config_payload,
        }
    )

    registry_report = validate_registry_seed_data()
    registry_findings = [asdict(finding) for finding in registry_report.findings]
    registry_has_error = any(finding.severity == "error" for finding in registry_report.findings)
    checks_run.append(
        {
            "name": "validate-registries",
            "status": "passed" if not registry_has_error else "failed",
            "ok": not registry_has_error,
            "error": None if not registry_has_error else "registry_validation_failed",
            "result": {"ok": registry_report.ok, "findings": registry_findings},
        }
    )

    check_specs: list[tuple[str, Any]] = [
        (
            "list-projects",
            _database_check(config, lambda conn: {"ok": True, "projects": list_projects(conn)}),
        ),
        (
            "list-agents",
            _database_check(config, lambda conn: {"ok": True, "agents": list_agents(conn)}),
        ),
        (
            "list-models",
            _database_check(config, lambda conn: {"ok": True, "models": list_models(conn)}),
        ),
        (
            "list-queues",
            _database_check(config, lambda conn: {"ok": True, "queues": list_queues(conn)}),
        ),
        (
            "inspect-project",
            _database_check(
                config,
                lambda conn: (
                    {"ok": True, "project": project}
                    if (project := inspect_project(conn, options.project_id)) is not None
                    else {
                        "ok": False,
                        "error": "project_not_found",
                        "project_id": options.project_id,
                    }
                ),
            ),
        ),
        (
            "inspect-model",
            _database_check(
                config,
                lambda conn: (
                    {"ok": True, "model": model}
                    if (model := inspect_model(conn, options.model_id)) is not None
                    else {
                        "ok": False,
                        "error": "model_not_found",
                        "model_id": options.model_id,
                    }
                ),
            ),
        ),
        (
            "inspect-registries",
            lambda: inspect_local_registries(config.repo_root),
        ),
    ]

    for name, runner in check_specs:
        skipped = _execute_check(
            checks_run=checks_run,
            name=name,
            runner=runner,
        )
        if isinstance(skipped, dict) and "reason" in skipped:
            skip(name, skipped["reason"])

    if options.include_artifacts:
        artifact_summary = {"list_artifacts": None, "inspect_artifact": None}
        artifact_payload = _execute_check(
            checks_run=checks_run,
            name="list-artifacts",
            runner=lambda: discover_local_artifacts(config),
        )
        if isinstance(artifact_payload, dict) and "reason" in artifact_payload:
            skip("list-artifacts", artifact_payload["reason"])
        elif artifact_payload is not None:
            artifact_summary["list_artifacts"] = artifact_payload
    else:
        skip("list-artifacts", "artifacts_not_requested")

    if options.artifact_path:
        if artifact_summary is None:
            artifact_summary = {"list_artifacts": None, "inspect_artifact": None}
        artifact_inspection_payload = _execute_check(
            checks_run=checks_run,
            name="inspect-artifact",
            runner=lambda: inspect_local_artifact(config, options.artifact_path or ""),
        )
        if isinstance(artifact_inspection_payload, dict) and "reason" in artifact_inspection_payload:
            skip("inspect-artifact", artifact_inspection_payload["reason"])
        elif artifact_inspection_payload is not None:
            artifact_summary["inspect_artifact"] = artifact_inspection_payload
    else:
        skip("inspect-artifact", "artifact_path_not_requested")

    if options.include_evidence_packages:
        evidence_package_summary = {
            "list_evidence_packages": None,
            "inspect_evidence_package": None,
        }
        evidence_list_payload = _execute_check(
            checks_run=checks_run,
            name="list-evidence-packages",
            runner=lambda: discover_local_evidence_packages(config),
        )
        if isinstance(evidence_list_payload, dict) and "reason" in evidence_list_payload:
            skip("list-evidence-packages", evidence_list_payload["reason"])
        elif evidence_list_payload is not None:
            evidence_package_summary["list_evidence_packages"] = evidence_list_payload
    else:
        skip("list-evidence-packages", "evidence_packages_not_requested")

    if options.evidence_path:
        if evidence_package_summary is None:
            evidence_package_summary = {
                "list_evidence_packages": None,
                "inspect_evidence_package": None,
            }
        evidence_inspection_payload = _execute_check(
            checks_run=checks_run,
            name="inspect-evidence-package",
            runner=lambda: inspect_local_evidence_package(config, options.evidence_path or ""),
        )
        if isinstance(evidence_inspection_payload, dict) and "reason" in evidence_inspection_payload:
            skip("inspect-evidence-package", evidence_inspection_payload["reason"])
        elif evidence_inspection_payload is not None:
            evidence_package_summary["inspect_evidence_package"] = evidence_inspection_payload
    else:
        skip("inspect-evidence-package", "evidence_path_not_requested")

    skip_reasons = {item["name"]: item["reason"] for item in checks_skipped}
    ok = all(check["ok"] for check in checks_run)
    payload: dict[str, Any] = {
        "ok": ok,
        "command": "run-local-review",
        "status": "passed" if ok else "failed",
        "requested_options": requested_options,
        "checks_run": checks_run,
        "checks_skipped": checks_skipped,
        "skip_reasons": skip_reasons,
        "artifact_summary": artifact_summary,
        "evidence_package_summary": evidence_package_summary,
        "boundary_confirmations": [
            "Human-triggered local orchestration only.",
            "No network calls were performed by this command surface.",
            "No GitHub mutation was performed by this command surface.",
            "No queue, registry, work-item, or artifact mutation was performed unless --write-review-package was explicitly requested.",
            "Protected historical references were not modified.",
        ],
        "output_package_path": None,
        "output_package_markdown_path": None,
    }

    if options.write_review_package:
        bundle = _render_local_review_package(config=config, payload=payload)
        payload["output_package_path"] = str(bundle.json_path)
        payload["output_package_markdown_path"] = str(bundle.markdown_path)

    return payload
