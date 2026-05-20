from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aresforge.config import AppConfig
from aresforge.db.connection import connect
from aresforge.db.migrations import apply_migrations, discover_migrations, plan_migrations
from aresforge.db.repository import (
    DEFAULT_AGENT_ID,
    DEFAULT_MODEL_ID,
    DEFAULT_PROJECT_ID,
    bootstrap_reference_data,
    inspect_model,
    create_work_item,
    inspect_project,
    inspect_queue,
    inspect_state,
    inspect_work_item,
    list_agents,
    list_models,
    list_projects,
    list_queues,
    list_work_items,
    store_evidence_record,
    store_prompt_record,
    WorkItemCreate,
)
from aresforge.integrations.ollama import test_generate
from aresforge.operator.artifact_discovery import discover_local_artifacts
from aresforge.operator.inspection_reports import (
    render_queue_inspection_report,
    render_work_item_inspection_report,
)
from aresforge.operator.registry_inspection import inspect_local_registries
from aresforge.operator.service import (
    render_codex_handoff,
    render_evidence_package,
    render_prompt_package,
)
from aresforge.routing.routes import build_route_plan
from aresforge.validation import validate_registry_seed_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aresforge", description="AresForge local operator CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-config", help="Validate local configuration and artifact paths.")
    subparsers.add_parser(
        "validate-registries",
        help="Validate seeded queue and agent registry data without mutating local state.",
    )

    migrate_parser = subparsers.add_parser("migrate", help="Apply PostgreSQL migrations.")
    migrate_parser.add_argument(
        "--plan",
        action="store_true",
        help="List pending migration files without applying them.",
    )

    subparsers.add_parser("inspect-project-state", help="Show local database state summary.")
    inspect_project_parser = subparsers.add_parser(
        "inspect-project", help="Inspect one local project record with expanded metadata."
    )
    inspect_project_parser.add_argument("--project-id", required=True)
    subparsers.add_parser(
        "inspect-registries",
        help="Summarize documented local registry and lifecycle sources in the repo.",
    )
    subparsers.add_parser(
        "list-artifacts",
        help="Summarize generated local artifacts under the configured artifact root.",
    )
    subparsers.add_parser("list-projects", help="List registered projects.")
    subparsers.add_parser("list-agents", help="List registered agent roles.")
    subparsers.add_parser("list-models", help="List registered local model records.")
    inspect_model_parser = subparsers.add_parser(
        "inspect-model", help="Inspect one local model record with expanded metadata."
    )
    inspect_model_parser.add_argument("--model-id", required=True)
    subparsers.add_parser("list-queues", help="List known queues.")
    inspect_queue_parser = subparsers.add_parser(
        "inspect-queue", help="Inspect one queue with registry-aware metadata interpretation."
    )
    inspect_queue_parser.add_argument("--queue-id", required=True)
    inspect_queue_parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write a local Markdown and JSON inspection report artifact while still emitting JSON.",
    )
    inspect_work_item_parser = subparsers.add_parser(
        "inspect-work-item", help="Inspect one work item with registry-aware queue context."
    )
    inspect_work_item_parser.add_argument("--work-item-id", required=True)
    inspect_work_item_parser.add_argument(
        "--write-artifact",
        action="store_true",
        help="Write a local Markdown and JSON inspection report artifact while still emitting JSON.",
    )

    create_work = subparsers.add_parser("create-work-item", help="Create a local work item.")
    create_work.add_argument("--title", required=True)
    create_work.add_argument("--description", default="")
    create_work.add_argument("--project-id", default=DEFAULT_PROJECT_ID)
    create_work.add_argument("--queue-id", required=True)
    create_work.add_argument("--status", default="queued")
    create_work.add_argument("--priority", default="normal")
    create_work.add_argument("--route-status", default="queued")
    create_work.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    create_work.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    create_work.add_argument("--prompt-id")
    create_work.add_argument(
        "--metadata-json",
        default="{}",
        help="JSON object with additional work item metadata.",
    )
    create_work.add_argument(
        "--metadata",
        action="append",
        default=[],
        help="Additional metadata entries in key=value form. May be repeated.",
    )

    list_work = subparsers.add_parser("list-work-items", help="List work items.")
    list_work.add_argument("--status")

    prompt_parser = subparsers.add_parser(
        "generate-prompt-package",
        help="Generate a human-reviewable prompt package artifact.",
    )
    prompt_parser.add_argument("--title", required=True)
    prompt_parser.add_argument("--objective", required=True)
    prompt_parser.add_argument("--work-item-id")
    prompt_parser.add_argument("--queue-id", default="queue-planning")
    prompt_parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    prompt_parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    prompt_parser.add_argument("--route-status", default="ready")
    prompt_parser.add_argument("--notes", default="")
    prompt_parser.add_argument("--store-db", action="store_true")

    evidence_parser = subparsers.add_parser(
        "record-evidence-package",
        help="Record evidence package metadata and write a local artifact.",
    )
    evidence_parser.add_argument("--title", required=True)
    evidence_parser.add_argument("--work-item-id")
    evidence_parser.add_argument("--files-changed", nargs="*", default=[])
    evidence_parser.add_argument("--validations-run", nargs="*", default=[])
    evidence_parser.add_argument("--skipped-checks", nargs="*", default=[])
    evidence_parser.add_argument("--protected-issue-checks", nargs="*", default=[])
    evidence_parser.add_argument(
        "--automation-boundary-confirmation",
        default="No autonomous GitHub or repository state changes were performed.",
    )
    evidence_parser.add_argument("--store-db", action="store_true")

    ollama_parser = subparsers.add_parser("test-ollama", help="Send a small prompt to Ollama.")
    ollama_parser.add_argument(
        "--prompt",
        default="Return one short sentence confirming that the local AresForge skeleton check reached Ollama.",
    )

    handoff_parser = subparsers.add_parser(
        "prepare-codex-handoff",
        help="Generate a Codex handoff file without invoking Codex.",
    )
    handoff_parser.add_argument("--title", required=True)
    handoff_parser.add_argument("--summary", required=True)
    handoff_parser.add_argument("--requested-output", required=True)
    handoff_parser.add_argument("--work-item-id")
    handoff_parser.add_argument("--queue-id", default="queue-implementation")
    handoff_parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID)
    handoff_parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    handoff_parser.add_argument("--route-status", default="ready")

    return parser


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=str))


def parse_metadata(raw_json: str) -> dict[str, Any]:
    value = json.loads(raw_json)
    if not isinstance(value, dict):
        raise ValueError("metadata-json must decode to a JSON object.")
    return value


def parse_metadata_pairs(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"metadata entries must use key=value form: {item}")
        key, value = item.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def command_requires_directories(args: argparse.Namespace) -> bool:
    if args.command == "validate-config":
        return True
    if args.command in (
        "generate-prompt-package",
        "record-evidence-package",
        "prepare-codex-handoff",
    ):
        return True
    if args.command in ("inspect-queue", "inspect-work-item"):
        return bool(getattr(args, "write_artifact", False))
    return False


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig.from_env()
    if command_requires_directories(args):
        config.ensure_directories()

    if args.command == "validate-config":
        errors = config.validate()
        payload = {"ok": not errors, "errors": errors, "config": config.summary()}
        emit_json(payload)
        return 0 if not errors else 1

    if args.command == "validate-registries":
        report = validate_registry_seed_data()
        payload = {
            "ok": report.ok,
            "findings": [asdict(finding) for finding in report.findings],
        }
        emit_json(payload)
        has_error = any(finding.severity == "error" for finding in report.findings)
        return 1 if has_error else 0

    if args.command == "migrate":
        migrations_dir = config.repo_root / "migrations"
        if args.plan:
            with connect(config) as conn:
                pending = plan_migrations(conn, migrations_dir)
            emit_json({"pending_migrations": [item.path.name for item in pending]})
            return 0
        with connect(config) as conn:
            applied = apply_migrations(conn, migrations_dir)
            bootstrap_reference_data(conn, config)
        emit_json({"applied_migrations": applied, "bootstrap": "ok"})
        return 0

    if args.command == "inspect-project-state":
        with connect(config) as conn:
            emit_json(inspect_state(conn))
        return 0

    if args.command == "inspect-project":
        with connect(config) as conn:
            project_record = inspect_project(conn, args.project_id)
        if project_record is None:
            emit_json(
                {"ok": False, "error": "project_not_found", "project_id": args.project_id}
            )
            return 1
        emit_json({"ok": True, "project": project_record})
        return 0

    if args.command == "inspect-registries":
        payload = inspect_local_registries(config.repo_root)
        emit_json(payload)
        return 0 if payload["ok"] else 1

    if args.command == "list-artifacts":
        emit_json(discover_local_artifacts(config))
        return 0

    if args.command == "list-projects":
        with connect(config) as conn:
            emit_json({"projects": list_projects(conn)})
        return 0

    if args.command == "list-agents":
        with connect(config) as conn:
            emit_json({"agents": list_agents(conn)})
        return 0

    if args.command == "list-models":
        with connect(config) as conn:
            emit_json({"models": list_models(conn)})
        return 0

    if args.command == "inspect-model":
        with connect(config) as conn:
            model_record = inspect_model(conn, args.model_id)
        if model_record is None:
            emit_json({"ok": False, "error": "model_not_found", "model_id": args.model_id})
            return 1
        emit_json({"ok": True, "model": model_record})
        return 0

    if args.command == "list-queues":
        with connect(config) as conn:
            emit_json({"queues": list_queues(conn)})
        return 0

    if args.command == "inspect-queue":
        with connect(config) as conn:
            queue_record = inspect_queue(conn, args.queue_id)
        if queue_record is None:
            emit_json({"ok": False, "error": "queue_not_found", "queue_id": args.queue_id})
            return 1
        response: dict[str, Any] = {"ok": True, "queue": queue_record}
        if args.write_artifact:
            bundle = render_queue_inspection_report(
                config=config,
                inspection_payload=queue_record,
            )
            response["inspection_payload"] = queue_record
            response["markdown_path"] = str(bundle.markdown_path)
            response["json_path"] = str(bundle.json_path)
        emit_json(response)
        return 0

    if args.command == "create-work-item":
        metadata = parse_metadata(args.metadata_json)
        metadata.update(parse_metadata_pairs(args.metadata))
        payload = WorkItemCreate(
            project_id=args.project_id,
            queue_id=args.queue_id,
            title=args.title,
            description=args.description,
            status=args.status,
            priority=args.priority,
            route_status=args.route_status,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_id=args.prompt_id,
            metadata=metadata,
        )
        with connect(config) as conn:
            emit_json({"work_item": create_work_item(conn, payload)})
        return 0

    if args.command == "list-work-items":
        with connect(config) as conn:
            emit_json({"work_items": list_work_items(conn, status=args.status)})
        return 0

    if args.command == "inspect-work-item":
        with connect(config) as conn:
            work_item = inspect_work_item(conn, args.work_item_id)
        if work_item is None:
            emit_json({"ok": False, "error": "work_item_not_found", "work_item_id": args.work_item_id})
            return 1
        response: dict[str, Any] = {"ok": True, "work_item": work_item}
        if args.write_artifact:
            bundle = render_work_item_inspection_report(
                config=config,
                inspection_payload=work_item,
            )
            response["inspection_payload"] = work_item
            response["markdown_path"] = str(bundle.markdown_path)
            response["json_path"] = str(bundle.json_path)
        emit_json(response)
        return 0

    if args.command == "generate-prompt-package":
        route_plan = build_route_plan(
            work_item_id=args.work_item_id,
            queue_id=args.queue_id,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_package=None,
            route_status=args.route_status,
        )
        bundle = render_prompt_package(
            config=config,
            title=args.title,
            objective=args.objective,
            work_item_id=args.work_item_id,
            route_plan=route_plan,
            notes=args.notes,
        )
        response: dict[str, Any] = {
            "markdown_path": str(bundle.markdown_path),
            "json_path": str(bundle.json_path),
        }
        if args.store_db:
            with connect(config) as conn:
                response["db_record"] = store_prompt_record(
                    conn,
                    project_id=DEFAULT_PROJECT_ID,
                    work_item_id=args.work_item_id,
                    title=args.title,
                    artifact_path=bundle.markdown_path,
                    summary=args.objective,
                    metadata=bundle.payload,
                )
        emit_json(response)
        return 0

    if args.command == "record-evidence-package":
        bundle = render_evidence_package(
            config=config,
            title=args.title,
            work_item_id=args.work_item_id,
            files_changed=args.files_changed,
            validations_run=args.validations_run,
            skipped_checks=args.skipped_checks,
            protected_issue_checks=args.protected_issue_checks,
            automation_boundary_confirmation=args.automation_boundary_confirmation,
        )
        response = {
            "markdown_path": str(bundle.markdown_path),
            "json_path": str(bundle.json_path),
        }
        if args.store_db:
            with connect(config) as conn:
                response["db_record"] = store_evidence_record(
                    conn,
                    project_id=DEFAULT_PROJECT_ID,
                    work_item_id=args.work_item_id,
                    title=args.title,
                    artifact_path=bundle.markdown_path,
                    metadata=bundle.payload,
                )
        emit_json(response)
        return 0

    if args.command == "test-ollama":
        result = test_generate(config, args.prompt)
        emit_json(
            {
                "ok": result.ok,
                "message": result.message,
                "response_text": result.response_text,
            }
        )
        return 0 if result.ok else 1

    if args.command == "prepare-codex-handoff":
        route_plan = build_route_plan(
            work_item_id=args.work_item_id,
            queue_id=args.queue_id,
            agent_id=args.agent_id,
            model_id=args.model_id,
            prompt_package=None,
            route_status=args.route_status,
        )
        bundle = render_codex_handoff(
            config=config,
            title=args.title,
            summary=args.summary,
            work_item_id=args.work_item_id,
            route_plan=route_plan,
            requested_output=args.requested_output,
        )
        emit_json(
            {
                "markdown_path": str(bundle.markdown_path),
                "json_path": str(bundle.json_path),
            }
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
