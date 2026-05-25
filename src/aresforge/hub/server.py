from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

from aresforge.config import AppConfig
from aresforge.hub.api import (
    get_bootstrap_plan,
    get_bootstrap_status,
    get_active_project,
    get_agent,
    get_agents,
    get_docs_status,
    get_escalation_plan,
    get_health,
    get_handoff_preview,
    get_handoff_target,
    get_handoff_targets,
    get_orchestration_plan,
    get_project,
    get_project_factory_dossier,
    get_project_factory_architecture_contract,
    get_project_factory_agent_dispatch_plan,
    get_project_factory_documentation_closeout_plan,
    get_project_factory_execution_phase_approval,
    get_project_factory_execution_readiness,
    get_project_factory_validation_execution_plan,
    get_project_factory_github_apply_plan,
    get_project_factory_milestone_issue_plan,
    get_project_factory_scope_package,
    get_project_repo_github_link,
    get_project_repos,
    get_reports_action_center,
    get_reports_dashboard,
    get_reports_export,
    get_reports_operator_workflows,
    get_reports_readiness,
    get_projects,
    get_queue,
    get_queue_item,
    get_settings,
    get_summary,
    patch_queue_item,
    post_active_project,
    post_agent,
    post_bootstrap_apply,
    post_escalation_plan,
    post_handoff_target,
    post_orchestration_plan,
    post_project,
    post_project_factory_new_project,
    post_project_factory_scope_package_approve,
    post_project_factory_architecture_contract_approve,
    post_project_factory_architecture_contract,
    post_project_factory_scope_package,
    patch_project_factory_architecture_contract,
    patch_project_factory_github_apply_plan,
    patch_project_factory_agent_dispatch_plan,
    patch_project_factory_documentation_closeout_plan,
    patch_project_factory_execution_phase_approval,
    patch_project_factory_validation_execution_plan,
    patch_project_factory_milestone_issue_plan,
    patch_project_factory_scope_package,
    post_project_factory_milestone_issue_plan,
    post_project_factory_milestone_issue_plan_approve,
    post_project_factory_github_apply_plan,
    post_project_factory_github_apply_plan_approve,
    post_project_factory_agent_dispatch_plan,
    post_project_factory_agent_dispatch_plan_approve,
    post_project_factory_documentation_closeout_plan,
    post_project_factory_documentation_closeout_plan_approve,
    post_project_factory_execution_phase_approval,
    post_project_factory_execution_phase_approval_approve,
    post_project_factory_validation_execution_plan,
    post_project_factory_validation_execution_plan_approve,
    post_project_repo,
    post_queue_item,
)

_DEFAULT_MIME_TYPE = "application/octet-stream"


def _is_loopback_host(host: str) -> bool:
    value = host.strip().lower()
    return value in {"127.0.0.1", "localhost", "::1"}


def _render_json(handler: BaseHTTPRequestHandler, status_code: int, payload: dict[str, Any]) -> None:
    safe_payload = {key: value for key, value in payload.items() if key != "_status"}
    body = json.dumps(safe_payload, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _status_from_payload(payload: dict[str, Any], fallback: HTTPStatus = HTTPStatus.OK) -> HTTPStatus:
    raw = payload.get("_status")
    if isinstance(raw, int) and 100 <= raw <= 599:
        return HTTPStatus(raw)
    return fallback


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    return _DEFAULT_MIME_TYPE


def _build_handler(config: AppConfig, static_root: Path) -> type[BaseHTTPRequestHandler]:
    class HubRequestHandler(BaseHTTPRequestHandler):
        def _read_json_body(self) -> dict[str, Any] | None:
            content_length = self.headers.get("Content-Length", "0").strip()
            try:
                length = int(content_length)
            except ValueError:
                return None

            if length <= 0:
                return {}

            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            if not isinstance(parsed, dict):
                return None
            return parsed

        def _handle_api_route(
            self,
            *,
            method: str,
            path: str,
            query_values: dict[str, list[str]],
            body: dict[str, Any] | None,
        ) -> bool:
            segments = [unquote(segment) for segment in path.split("/") if segment]
            if len(segments) < 2 or segments[0] != "api":
                return False

            if method == "GET" and path == "/api/health":
                _render_json(self, HTTPStatus.OK, get_health())
                return True
            if method == "GET" and path == "/api/summary":
                _render_json(self, HTTPStatus.OK, get_summary(config))
                return True
            if method == "GET" and path == "/api/bootstrap/status":
                _render_json(self, HTTPStatus.OK, get_bootstrap_status(config))
                return True
            if method == "GET" and path == "/api/bootstrap/plan":
                payload = get_bootstrap_plan(
                    config,
                    {
                        "seed_sample_work": query_values.get("seed_sample_work", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/bootstrap/apply":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_bootstrap_apply(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/docs/status":
                _render_json(self, HTTPStatus.OK, get_docs_status(config))
                return True
            if method == "GET" and path == "/api/settings":
                _render_json(self, HTTPStatus.OK, get_settings(config))
                return True

            if method == "GET" and path == "/api/reports/dashboard":
                _render_json(self, HTTPStatus.OK, get_reports_dashboard(config))
                return True
            if method == "GET" and path == "/api/reports/action-center":
                _render_json(self, HTTPStatus.OK, get_reports_action_center(config))
                return True
            if method == "GET" and path == "/api/reports/readiness":
                _render_json(self, HTTPStatus.OK, get_reports_readiness(config))
                return True
            if method == "GET" and path == "/api/reports/operator-workflows":
                _render_json(self, HTTPStatus.OK, get_reports_operator_workflows(config))
                return True
            if method == "GET" and path == "/api/reports/export":
                payload = get_reports_export(
                    config,
                    {
                        "format": query_values.get("format", [None])[0],
                        "output": query_values.get("output", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/agents":
                _render_json(self, HTTPStatus.OK, get_agents(config))
                return True
            if method == "POST" and path == "/api/agents":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_agent(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if len(segments) == 3 and segments[1] == "agents" and method == "GET":
                payload = get_agent(config, segments[2])
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/handoff-targets":
                _render_json(self, HTTPStatus.OK, get_handoff_targets(config))
                return True
            if method == "POST" and path == "/api/handoff-targets":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_handoff_target(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if len(segments) == 3 and segments[1] == "handoff-targets" and method == "GET":
                payload = get_handoff_target(config, segments[2])
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/handoff/preview":
                payload = get_handoff_preview(config)
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/orchestration/plan":
                payload = get_orchestration_plan(config)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/orchestration/plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_orchestration_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/escalation/plan":
                payload = get_escalation_plan(config)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/escalation/plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_escalation_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if method == "GET" and path == "/api/projects/active":
                payload = get_active_project(config)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/projects/active":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_active_project(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/projects":
                _render_json(self, HTTPStatus.OK, get_projects(config))
                return True
            if method == "POST" and path == "/api/projects":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/new-project":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_new_project(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/dossier":
                payload = get_project_factory_dossier(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/scope-package":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_scope_package(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/scope-package":
                payload = get_project_factory_scope_package(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/scope-package":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_project_factory_scope_package(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/scope-package/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_scope_package_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/architecture-contract":
                payload = get_project_factory_architecture_contract(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/architecture-contract":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_architecture_contract(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/architecture-contract":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_project_factory_architecture_contract(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/architecture-contract/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_architecture_contract_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/milestone-issue-plan":
                payload = get_project_factory_milestone_issue_plan(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/milestone-issue-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_milestone_issue_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/milestone-issue-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_project_factory_milestone_issue_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/milestone-issue-plan/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_milestone_issue_plan_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/github-apply-plan":
                payload = get_project_factory_github_apply_plan(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/github-apply-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_github_apply_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/github-apply-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_project_factory_github_apply_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/github-apply-plan/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_github_apply_plan_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/agent-dispatch-plan":
                payload = get_project_factory_agent_dispatch_plan(
                    config,
                    {"project_id": query_values.get("project_id", [""])[0] if query_values.get("project_id") else ""},
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/agent-dispatch-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_agent_dispatch_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/agent-dispatch-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_project_factory_agent_dispatch_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/agent-dispatch-plan/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_project_factory_agent_dispatch_plan_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/validation-execution-plan":
                payload = get_project_factory_validation_execution_plan(
                    config,
                    {
                        "project_id": query_values.get("project_id", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/validation-execution-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_validation_execution_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/validation-execution-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = patch_project_factory_validation_execution_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/validation-execution-plan/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_validation_execution_plan_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/documentation-closeout-plan":
                payload = get_project_factory_documentation_closeout_plan(
                    config,
                    {
                        "project_id": query_values.get("project_id", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/documentation-closeout-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_documentation_closeout_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/documentation-closeout-plan":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = patch_project_factory_documentation_closeout_plan(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/documentation-closeout-plan/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_documentation_closeout_plan_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/execution-phase-approval":
                payload = get_project_factory_execution_phase_approval(
                    config,
                    {
                        "project_id": query_values.get("project_id", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "GET" and path == "/api/project-factory/execution-readiness":
                payload = get_project_factory_execution_readiness(
                    config,
                    {
                        "project_id": query_values.get("project_id", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/execution-phase-approval":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_execution_phase_approval(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "PATCH" and path == "/api/project-factory/execution-phase-approval":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = patch_project_factory_execution_phase_approval(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/project-factory/execution-phase-approval/approve":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "local_only": True, "error": "invalid_json_body", "message": "Request body must be a JSON object."},
                    )
                    return True
                payload = post_project_factory_execution_phase_approval_approve(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True

            if len(segments) >= 3 and segments[1] == "projects":
                project_id = segments[2]
                if len(segments) == 3 and method == "GET":
                    payload = get_project(config, project_id)
                    _render_json(self, _status_from_payload(payload), payload)
                    return True
                if len(segments) == 4 and segments[3] == "repos" and method == "GET":
                    payload = get_project_repos(config, project_id)
                    _render_json(self, _status_from_payload(payload), payload)
                    return True
                if len(segments) == 4 and segments[3] == "repos" and method == "POST":
                    if body is None:
                        _render_json(
                            self,
                            HTTPStatus.BAD_REQUEST,
                            {
                                "ok": False,
                                "local_only": True,
                                "error": "invalid_json_body",
                                "message": "Request body must be a JSON object.",
                            },
                        )
                        return True
                    payload = post_project_repo(config, project_id, body)
                    _render_json(self, _status_from_payload(payload), payload)
                    return True
                if len(segments) == 6 and segments[3] == "repos" and segments[5] == "github-link" and method == "GET":
                    inspect_value = str(query_values.get("inspect_local_git", ["false"])[0]).strip().lower()
                    inspect_local_git = inspect_value in {"1", "true", "yes", "on"}
                    payload = get_project_repo_github_link(
                        config,
                        project_id,
                        segments[4],
                        inspect_local_git=inspect_local_git,
                    )
                    _render_json(self, _status_from_payload(payload), payload)
                    return True

            if method == "GET" and path == "/api/queue":
                payload = get_queue(
                    config,
                    {
                        "project_id": query_values.get("project_id", [None])[0],
                        "repo_id": query_values.get("repo_id", [None])[0],
                        "status": query_values.get("status", [None])[0],
                        "type": query_values.get("type", [None])[0],
                        "assigned_agent": query_values.get("assigned_agent", [None])[0],
                    },
                )
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if method == "POST" and path == "/api/queue":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = post_queue_item(config, body)
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if len(segments) == 3 and segments[1] == "queue" and method == "GET":
                payload = get_queue_item(config, segments[2])
                _render_json(self, _status_from_payload(payload), payload)
                return True
            if len(segments) == 3 and segments[1] == "queue" and method == "PATCH":
                if body is None:
                    _render_json(
                        self,
                        HTTPStatus.BAD_REQUEST,
                        {
                            "ok": False,
                            "local_only": True,
                            "error": "invalid_json_body",
                            "message": "Request body must be a JSON object.",
                        },
                    )
                    return True
                payload = patch_queue_item(config, segments[2], body)
                _render_json(self, _status_from_payload(payload), payload)
                return True

            return False

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query_values = parse_qs(parsed.query, keep_blank_values=False)

            if self._handle_api_route(method="GET", path=path, query_values=query_values, body=None):
                return

            if path.startswith("/api/"):
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "local_only": True,
                        "error": "unknown_api_endpoint",
                        "path": path,
                        "method": "GET",
                    },
                )
                return

            requested = "index.html" if path in {"", "/", "/index.html"} else unquote(path.lstrip("/"))
            candidate = (static_root / requested).resolve()
            if not str(candidate).startswith(str(static_root.resolve())) or not candidate.exists() or not candidate.is_file():
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "error": "static_asset_not_found",
                        "path": path,
                    },
                )
                return

            data = candidate.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", _guess_content_type(candidate))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query_values = parse_qs(parsed.query, keep_blank_values=False)
            body = self._read_json_body()
            if self._handle_api_route(method="POST", path=path, query_values=query_values, body=body):
                return
            if path.startswith("/api/"):
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "local_only": True,
                        "error": "unknown_api_endpoint",
                        "path": path,
                        "method": "POST",
                    },
                )
                return
            _render_json(
                self,
                HTTPStatus.METHOD_NOT_ALLOWED,
                {
                    "ok": False,
                    "local_only": True,
                    "error": "method_not_allowed",
                    "path": path,
                    "method": "POST",
                },
            )

        def do_PATCH(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query_values = parse_qs(parsed.query, keep_blank_values=False)
            body = self._read_json_body()
            if self._handle_api_route(method="PATCH", path=path, query_values=query_values, body=body):
                return
            if path.startswith("/api/"):
                _render_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {
                        "ok": False,
                        "local_only": True,
                        "error": "unknown_api_endpoint",
                        "path": path,
                        "method": "PATCH",
                    },
                )
                return
            _render_json(
                self,
                HTTPStatus.METHOD_NOT_ALLOWED,
                {
                    "ok": False,
                    "local_only": True,
                    "error": "method_not_allowed",
                    "path": path,
                    "method": "PATCH",
                },
            )

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return HubRequestHandler


def serve_hub(
    config: AppConfig,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
) -> dict[str, Any]:
    static_root = (Path(__file__).resolve().parent / "static").resolve()
    handler = _build_handler(config, static_root)
    server = ThreadingHTTPServer((host, port), handler)

    url_host = "127.0.0.1" if host == "0.0.0.0" else host
    hub_url = f"http://{url_host}:{port}/"

    browser_opened = False
    browser_warning: str | None = None
    if open_browser:
        if _is_loopback_host(url_host):
            browser_opened = bool(webbrowser.open(hub_url))
        else:
            browser_warning = "--open-browser ignored because host is not loopback/localhost."

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    payload = {
        "command": "serve-hub",
        "ok": True,
        "local_only": True,
        "host": host,
        "port": port,
        "url": hub_url,
        "open_browser": open_browser,
        "browser_opened": browser_opened,
        "boundary_confirmations": [
            "Local-only server for hub UI.",
            "No GitHub calls.",
            "No gh calls.",
            "No network service calls.",
            "No local LLM calls.",
            "No cloud LLM calls.",
            "No Codex calls.",
            "No ChatGPT calls.",
            "No Ollama calls.",
            "No external API calls.",
            "Default bind host is 127.0.0.1.",
        ],
    }
    if browser_warning:
        payload["warning"] = browser_warning
    return payload
