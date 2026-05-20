from __future__ import annotations

import argparse
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
    create_work_item,
    inspect_state,
    list_agents,
    list_projects,
    list_queues,
    list_work_items,
    store_evidence_record,
    store_prompt_record,
    WorkItemCreate,
)
from aresforge.integrations.ollama import test_generate
from aresforge.operator.service import (
    render_codex_handoff,
    render_evidence_package,
    render_prompt_package,
)
from aresforge.routing.routes import build_route_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aresforge", description="AresForge local operator CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-config", help="Validate local configuration and artifact paths.")

    migrate_parser = subparsers.add_parser("migrate", help="Apply PostgreSQL migrations.")
    migrate_parser.add_argument(
        "--plan",
        action="store_true",
        help="List pending migration files without applying them.",
    )

    subparsers.add_parser("inspect-project-state", help="Show local database state summary.")
    subparsers.add_parser("list-projects", help="List registered projects.")
    subparsers.add_parser("list-agents", help="List registered agent roles.")
    subparsers.add_parser("list-queues", help="List known queues.")

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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AppConfig.from_env()
    config.ensure_directories()

    if args.command == "validate-config":
        errors = config.validate()
        payload = {"ok": not errors, "errors": errors, "config": config.summary()}
        emit_json(payload)
        return 0 if not errors else 1

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

    if args.command == "list-projects":
        with connect(config) as conn:
            emit_json({"projects": list_projects(conn)})
        return 0

    if args.command == "list-agents":
        with connect(config) as conn:
            emit_json({"agents": list_agents(conn)})
        return 0

    if args.command == "list-queues":
        with connect(config) as conn:
            emit_json({"queues": list_queues(conn)})
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
