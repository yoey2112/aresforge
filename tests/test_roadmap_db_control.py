from __future__ import annotations

from pathlib import Path

import pytest

from aresforge.cli import build_parser
from aresforge.db import repository as repository_module
from aresforge.db.repository import (
    ROADMAP_ALLOWED_STATUSES,
    ROADMAP_SEED_AREAS,
    ROADMAP_SEED_MILESTONES,
    WORK_ITEM_ALLOWED_STATUSES,
    create_work_item_from_roadmap_task,
    add_roadmap_task_dependency,
    remove_roadmap_task_dependency,
    inspect_roadmap_task_dependencies,
    inspect_roadmap_db,
    inspect_project_queue_dashboard,
    inspect_work_item_readiness,
    move_work_item_queue_if_allowed,
    plan_work_item_queue_transition,
    build_work_item_execution_dossier,
    export_work_item_operator_prompt,
    handoff_work_item_to_implementation,
    render_start_work_item_markdown,
    render_implementation_handoff_markdown,
    render_move_work_item_queue_markdown,
    render_queue_work_state_markdown,
    render_project_queue_dashboard_markdown,
    render_queue_readiness_markdown,
    render_roadmap_events_markdown,
    render_roadmap_task_dependencies_markdown,
    render_add_roadmap_task_dependency_markdown,
    render_remove_roadmap_task_dependency_markdown,
    render_work_item_queue_transition_plan_markdown,
    render_work_item_readiness_markdown,
    render_work_item_lifecycle_markdown,
    render_work_item_execution_dossier_markdown,
    render_export_work_item_operator_prompt_markdown,
    render_roadmap_markdown,
    render_roadmap_work_item_links_markdown,
    start_work_item_if_ready,
    update_work_item_status,
    update_roadmap_task_status,
)


def test_seed_constants_include_expected_area_and_milestone_counts() -> None:
    assert len(ROADMAP_SEED_AREAS) == 12
    assert len(ROADMAP_SEED_MILESTONES) == 10


def test_roadmap_allowed_statuses_match_m2_contract() -> None:
    assert ROADMAP_ALLOWED_STATUSES == (
        "planned",
        "active",
        "blocked",
        "complete",
        "cancelled",
    )


def test_work_item_allowed_statuses_match_m4_contract() -> None:
    assert WORK_ITEM_ALLOWED_STATUSES == (
        "queued",
        "active",
        "blocked",
        "complete",
        "cancelled",
    )


def test_render_roadmap_markdown_contains_stable_headings_and_entities() -> None:
    payload = {
        "project_id": "project-aresforge",
        "counts": {"areas": 1, "milestones": 1, "tasks": 1},
        "areas": [
            {
                "id": "ra-state-authority-lifecycle",
                "name": "State Authority and Lifecycle Model",
                "status": "planned",
                "sort_order": 1,
            }
        ],
        "milestones": [
            {
                "id": "rm-02-state-authority",
                "area_id": "ra-state-authority-lifecycle",
                "name": "State authority matrix and lifecycle contract",
                "status": "planned",
                "sort_order": 1,
            }
        ],
        "tasks": [
            {
                "id": "rt-02-starter",
                "milestone_id": "rm-02-state-authority",
                "title": "Define starter scope for State authority matrix and lifecycle contract",
                "status": "planned",
                "sort_order": 1,
            }
        ],
    }

    markdown = render_roadmap_markdown(payload)

    assert "# Roadmap DB Inspection" in markdown
    assert "## Area: State Authority and Lifecycle Model (ra-state-authority-lifecycle)" in markdown
    assert "### Milestone: State authority matrix and lifecycle contract (rm-02-state-authority)" in markdown
    assert "- Task: Define starter scope for State authority matrix and lifecycle contract (rt-02-starter) [planned]" in markdown


def test_render_roadmap_events_markdown_contains_stable_headings_and_event_rows() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "event_count": 1,
        "events": [
            {
                "id": "roadmap-event-123",
                "project_id": "project-aresforge",
                "area_id": "ra-state-authority-lifecycle",
                "milestone_id": None,
                "task_id": None,
                "event_type": "roadmap_area_status_changed",
                "actor": "aresforge-cli",
                "summary": "Area status changed",
                "details": {},
                "created_at": "2026-05-25T12:00:00Z",
            }
        ],
    }
    markdown = render_roadmap_events_markdown(payload)
    assert "# Roadmap Events" in markdown
    assert "- Project ID: `project-aresforge`" in markdown
    assert "- Event count: `1`" in markdown
    assert "roadmap_area_status_changed" in markdown


def test_render_roadmap_task_dependencies_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "task_id": "rt-04-starter",
        "dependency_count": 1,
        "dependencies": [
            {
                "task_id": "rt-04-starter",
                "task_status": "planned",
                "depends_on_task_id": "rt-03-starter",
                "depends_on_task_status": "active",
                "dependency_type": "blocks",
                "satisfied": False,
            }
        ],
    }
    markdown = render_roadmap_task_dependencies_markdown(payload)
    assert "# Roadmap Task Dependencies" in markdown
    assert "rt-04-starter" in markdown
    assert "depends_on=`rt-03-starter`" in markdown


def test_render_add_roadmap_task_dependency_markdown_is_deterministic() -> None:
    markdown = render_add_roadmap_task_dependency_markdown(
        {
            "ok": True,
            "changed": True,
            "reason": "dependency_added",
            "task_id": "rt-04-starter",
            "depends_on_task_id": "rt-03-starter",
            "dependency": {"dependency_type": "blocks"},
        }
    )
    assert "# Add Roadmap Task Dependency" in markdown
    assert "- Changed: `True`" in markdown


def test_render_remove_roadmap_task_dependency_markdown_is_deterministic() -> None:
    markdown = render_remove_roadmap_task_dependency_markdown(
        {
            "ok": True,
            "changed": False,
            "reason": "dependency_not_found",
            "task_id": "rt-04-starter",
            "depends_on_task_id": "rt-03-starter",
        }
    )
    assert "# Remove Roadmap Task Dependency" in markdown
    assert "dependency_not_found" in markdown


class _FakeCursor:
    def __init__(self) -> None:
        self._rows: list[dict[str, object]] = []
        self._row: dict[str, object] | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        if "to_regclass('public.roadmap_work_item_links')" in sql:
            self._row = {"table_name": "roadmap_work_item_links"}
            self._rows = []
            return
        if "FROM roadmap_areas" in sql:
            self._rows = [{"id": "a1", "project_id": "project-aresforge", "name": "Area", "description": "", "status": "planned", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            self._row = None
            return
        if "FROM roadmap_milestones" in sql:
            self._rows = [{"id": "m1", "project_id": "project-aresforge", "area_id": "a1", "name": "Milestone", "description": "", "status": "planned", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            self._row = None
            return
        if "FROM roadmap_tasks" in sql:
            self._rows = [{"id": "t1", "project_id": "project-aresforge", "milestone_id": "m1", "title": "Task", "description": "", "status": "planned", "priority": "normal", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            self._row = None
            return
        if "FROM roadmap_task_dependencies" in sql:
            self._rows = [{"task_id": "t1", "depends_on_task_id": "t0", "dependency_type": "blocks", "metadata": {}, "created_at": ""}]
            self._row = None
            return
        if "FROM roadmap_events" in sql:
            self._rows = [{"id": "e1", "project_id": "project-aresforge", "area_id": None, "milestone_id": None, "task_id": None, "event_type": "roadmap_seed", "actor": "aresforge-cli", "summary": "Seed", "details": {}, "created_at": ""}]
            self._row = None
            return
        if "FROM roadmap_work_item_links" in sql:
            self._rows = [{"id": "l1"}]
            self._row = None
            return
        self._rows = []
        self._row = None

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _FakeConnection:
    def cursor(self) -> _FakeCursor:
        return _FakeCursor()


def test_inspect_roadmap_db_payload_shape_is_deterministic() -> None:
    payload = inspect_roadmap_db(_FakeConnection())

    assert payload["ok"] is True
    assert payload["project_id"] == "project-aresforge"
    assert payload["counts"] == {
        "areas": 1,
        "milestones": 1,
        "tasks": 1,
        "task_dependencies": 1,
        "events": 1,
        "roadmap_work_item_links": 1,
    }
    assert list(payload.keys()) == [
        "ok",
        "project_id",
        "counts",
        "areas",
        "milestones",
        "tasks",
        "task_dependencies",
        "events",
    ]


def test_update_roadmap_task_status_invalid_status_response_shape() -> None:
    payload = update_roadmap_task_status(_FakeConnection(), task_id="t1", status="not-a-real-status")
    assert payload == {
        "ok": False,
        "error": "invalid_status",
        "status": "not-a-real-status",
        "allowed_statuses": list(ROADMAP_ALLOWED_STATUSES),
    }


def test_update_work_item_status_invalid_status_response_shape() -> None:
    payload = update_work_item_status(_FakeConnection(), work_item_id="work-1", status="not-valid")
    assert payload == {
        "ok": False,
        "error": "invalid_work_item_status",
        "status": "not-valid",
        "allowed_statuses": list(WORK_ITEM_ALLOWED_STATUSES),
    }


def test_cli_parser_recognizes_roadmap_commands_and_formats() -> None:
    parser = build_parser()

    init_args = parser.parse_args(["init-roadmap-schema"])
    assert init_args.command == "init-roadmap-schema"

    seed_args = parser.parse_args(["seed-aresforge-roadmap"])
    assert seed_args.command == "seed-aresforge-roadmap"

    inspect_json_args = parser.parse_args(["inspect-roadmap-db", "--format", "json"])
    assert inspect_json_args.command == "inspect-roadmap-db"
    assert inspect_json_args.format == "json"

    inspect_markdown_args = parser.parse_args(["inspect-roadmap-db", "--format", "markdown"])
    assert inspect_markdown_args.command == "inspect-roadmap-db"
    assert inspect_markdown_args.format == "markdown"

    update_task_args = parser.parse_args(
        ["update-roadmap-task-status", "--task-id", "rt-01-starter", "--status", "active"]
    )
    assert update_task_args.command == "update-roadmap-task-status"
    assert update_task_args.status == "active"
    assert update_task_args.details_file is None

    update_milestone_args = parser.parse_args(
        ["update-roadmap-milestone-status", "--milestone-id", "rm-01-audit-baseline", "--status", "blocked"]
    )
    assert update_milestone_args.command == "update-roadmap-milestone-status"
    assert update_milestone_args.status == "blocked"
    assert update_milestone_args.details_file is None

    update_area_args = parser.parse_args(
        ["update-roadmap-area-status", "--area-id", "ra-recovery-reconciliation", "--status", "complete"]
    )
    assert update_area_args.command == "update-roadmap-area-status"
    assert update_area_args.status == "complete"
    assert update_area_args.details_file is None

    add_event_args = parser.parse_args(
        ["add-roadmap-event", "--event-type", "operator_note", "--summary", "note"]
    )
    assert add_event_args.command == "add-roadmap-event"
    assert add_event_args.project_id == "project-aresforge"
    assert add_event_args.details_file is None

    inspect_events_json_args = parser.parse_args(["inspect-roadmap-events", "--format", "json"])
    assert inspect_events_json_args.command == "inspect-roadmap-events"
    assert inspect_events_json_args.format == "json"

    inspect_events_markdown_args = parser.parse_args(["inspect-roadmap-events", "--format", "markdown"])
    assert inspect_events_markdown_args.command == "inspect-roadmap-events"
    assert inspect_events_markdown_args.format == "markdown"
    add_dependency_args = parser.parse_args(
        [
            "add-roadmap-task-dependency",
            "--task-id",
            "rt-04-starter",
            "--depends-on-task-id",
            "rt-03-starter",
            "--format",
            "json",
        ]
    )
    assert add_dependency_args.command == "add-roadmap-task-dependency"
    assert add_dependency_args.format == "json"
    remove_dependency_args = parser.parse_args(
        [
            "remove-roadmap-task-dependency",
            "--task-id",
            "rt-04-starter",
            "--depends-on-task-id",
            "rt-03-starter",
            "--format",
            "markdown",
        ]
    )
    assert remove_dependency_args.command == "remove-roadmap-task-dependency"
    assert remove_dependency_args.format == "markdown"
    inspect_dependencies_args = parser.parse_args(
        ["inspect-roadmap-task-dependencies", "--task-id", "rt-04-starter", "--format", "markdown"]
    )
    assert inspect_dependencies_args.command == "inspect-roadmap-task-dependencies"
    assert inspect_dependencies_args.format == "markdown"

    create_work_item_from_task_args = parser.parse_args(
        [
            "create-work-item-from-roadmap-task",
            "--task-id",
            "rt-01-starter",
            "--details-file",
            "details.json",
        ]
    )
    assert create_work_item_from_task_args.command == "create-work-item-from-roadmap-task"
    assert create_work_item_from_task_args.details_file == "details.json"

    inspect_links_json_args = parser.parse_args(["inspect-roadmap-work-item-links", "--format", "json"])
    assert inspect_links_json_args.command == "inspect-roadmap-work-item-links"
    assert inspect_links_json_args.format == "json"

    inspect_links_markdown_args = parser.parse_args(["inspect-roadmap-work-item-links", "--format", "markdown"])
    assert inspect_links_markdown_args.command == "inspect-roadmap-work-item-links"
    assert inspect_links_markdown_args.format == "markdown"

    update_work_item_args = parser.parse_args(
        ["update-work-item-status", "--work-item-id", "work-1", "--status", "active", "--details-file", "details.json"]
    )
    assert update_work_item_args.command == "update-work-item-status"
    assert update_work_item_args.details_file == "details.json"

    inspect_work_item_lifecycle_json_args = parser.parse_args(
        ["inspect-work-item-lifecycle", "--work-item-id", "work-1", "--format", "json"]
    )
    assert inspect_work_item_lifecycle_json_args.command == "inspect-work-item-lifecycle"
    assert inspect_work_item_lifecycle_json_args.format == "json"

    inspect_work_item_lifecycle_markdown_args = parser.parse_args(
        ["inspect-work-item-lifecycle", "--work-item-id", "work-1", "--format", "markdown"]
    )
    assert inspect_work_item_lifecycle_markdown_args.command == "inspect-work-item-lifecycle"
    assert inspect_work_item_lifecycle_markdown_args.format == "markdown"

    inspect_queue_state_json_args = parser.parse_args(["inspect-queue-work-state", "--format", "json"])
    assert inspect_queue_state_json_args.command == "inspect-queue-work-state"
    assert inspect_queue_state_json_args.format == "json"

    inspect_queue_state_markdown_args = parser.parse_args(["inspect-queue-work-state", "--format", "markdown"])
    assert inspect_queue_state_markdown_args.command == "inspect-queue-work-state"
    assert inspect_queue_state_markdown_args.format == "markdown"

    inspect_work_item_readiness_json_args = parser.parse_args(
        ["inspect-work-item-readiness", "--work-item-id", "work-1", "--format", "json"]
    )
    assert inspect_work_item_readiness_json_args.command == "inspect-work-item-readiness"
    assert inspect_work_item_readiness_json_args.format == "json"

    inspect_work_item_readiness_markdown_args = parser.parse_args(
        ["inspect-work-item-readiness", "--work-item-id", "work-1", "--format", "markdown"]
    )
    assert inspect_work_item_readiness_markdown_args.command == "inspect-work-item-readiness"
    assert inspect_work_item_readiness_markdown_args.format == "markdown"

    inspect_queue_readiness_json_args = parser.parse_args(["inspect-queue-readiness", "--format", "json"])
    assert inspect_queue_readiness_json_args.command == "inspect-queue-readiness"
    assert inspect_queue_readiness_json_args.format == "json"

    inspect_queue_readiness_markdown_args = parser.parse_args(
        ["inspect-queue-readiness", "--format", "markdown"]
    )
    assert inspect_queue_readiness_markdown_args.command == "inspect-queue-readiness"
    assert inspect_queue_readiness_markdown_args.format == "markdown"

    start_work_item_json_args = parser.parse_args(
        ["start-work-item", "--work-item-id", "work-1", "--format", "json"]
    )
    assert start_work_item_json_args.command == "start-work-item"
    assert start_work_item_json_args.format == "json"

    start_work_item_markdown_args = parser.parse_args(
        ["start-work-item", "--work-item-id", "work-1", "--format", "markdown"]
    )
    assert start_work_item_markdown_args.command == "start-work-item"
    assert start_work_item_markdown_args.format == "markdown"

    start_work_item_details_args = parser.parse_args(
        [
            "start-work-item",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--details-file",
            "details.json",
            "--format",
            "json",
        ]
    )
    assert start_work_item_details_args.command == "start-work-item"
    assert start_work_item_details_args.actor == "local-test"
    assert start_work_item_details_args.details_file == "details.json"

    plan_queue_transition_json_args = parser.parse_args(
        [
            "plan-work-item-queue-transition",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-verification",
            "--format",
            "json",
        ]
    )
    assert plan_queue_transition_json_args.command == "plan-work-item-queue-transition"
    assert plan_queue_transition_json_args.format == "json"

    plan_queue_transition_markdown_args = parser.parse_args(
        [
            "plan-work-item-queue-transition",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-verification",
            "--format",
            "markdown",
        ]
    )
    assert plan_queue_transition_markdown_args.command == "plan-work-item-queue-transition"
    assert plan_queue_transition_markdown_args.format == "markdown"

    move_queue_json_args = parser.parse_args(
        [
            "move-work-item-queue",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-verification",
            "--format",
            "json",
        ]
    )
    assert move_queue_json_args.command == "move-work-item-queue"
    assert move_queue_json_args.format == "json"

    move_queue_markdown_args = parser.parse_args(
        [
            "move-work-item-queue",
            "--work-item-id",
            "work-1",
            "--target-queue-id",
            "queue-verification",
            "--actor",
            "local-test",
            "--details-file",
            "details.json",
            "--format",
            "markdown",
        ]
    )
    assert move_queue_markdown_args.command == "move-work-item-queue"
    assert move_queue_markdown_args.actor == "local-test"
    assert move_queue_markdown_args.details_file == "details.json"
    assert move_queue_markdown_args.format == "markdown"

    handoff_impl_json_args = parser.parse_args(
        ["handoff-work-item-to-implementation", "--work-item-id", "work-1", "--format", "json"]
    )
    assert handoff_impl_json_args.command == "handoff-work-item-to-implementation"
    assert handoff_impl_json_args.format == "json"

    handoff_impl_markdown_args = parser.parse_args(
        [
            "handoff-work-item-to-implementation",
            "--work-item-id",
            "work-1",
            "--actor",
            "local-test",
            "--details-file",
            "details.json",
            "--format",
            "markdown",
        ]
    )
    assert handoff_impl_markdown_args.command == "handoff-work-item-to-implementation"
    assert handoff_impl_markdown_args.actor == "local-test"
    assert handoff_impl_markdown_args.details_file == "details.json"
    assert handoff_impl_markdown_args.format == "markdown"

    dossier_json_args = parser.parse_args(
        ["build-work-item-execution-dossier", "--work-item-id", "work-1", "--format", "json"]
    )
    assert dossier_json_args.command == "build-work-item-execution-dossier"
    assert dossier_json_args.format == "json"

    dossier_markdown_args = parser.parse_args(
        ["build-work-item-execution-dossier", "--work-item-id", "work-1", "--format", "markdown"]
    )
    assert dossier_markdown_args.command == "build-work-item-execution-dossier"
    assert dossier_markdown_args.format == "markdown"


class _MissingRoadmapTaskCursor:
    def __enter__(self) -> _MissingRoadmapTaskCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, _sql: str, _params: object = None) -> None:
        return None

    def fetchone(self) -> None:
        return None


class _MissingRoadmapTaskConnection:
    def cursor(self) -> _MissingRoadmapTaskCursor:
        return _MissingRoadmapTaskCursor()


def test_create_work_item_from_roadmap_task_returns_task_not_found_when_missing() -> None:
    payload = create_work_item_from_roadmap_task(
        _MissingRoadmapTaskConnection(),
        roadmap_task_id="rt-missing",
    )
    assert payload == {
        "ok": False,
        "error": "roadmap_task_not_found",
        "roadmap_task_id": "rt-missing",
    }


def test_add_roadmap_task_dependency_self_dependency_rejected() -> None:
    payload = add_roadmap_task_dependency(_FakeConnection(), "rt-1", "rt-1")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "self_dependency_not_allowed"


def test_add_roadmap_task_dependency_missing_task_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    class _MissingTaskCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchone(self): return None
    class _MissingTaskConn:
        def cursor(self): return _MissingTaskCursor()
    payload = add_roadmap_task_dependency(_MissingTaskConn(), "rt-1", "rt-2")
    assert payload["ok"] is False
    assert payload["reason"] == "task_not_found"


def test_add_roadmap_task_dependency_duplicate_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            {"id": "rt-1", "project_id": "project-aresforge", "title": "T1", "status": "planned"},
            {"id": "rt-2", "project_id": "project-aresforge", "title": "T2", "status": "planned"},
            {"task_id": "rt-1", "depends_on_task_id": "rt-2", "dependency_type": "blocks", "metadata": {}, "created_at": ""},
        ]
    )
    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchone(self): return next(responses, None)
    class _Conn:
        def cursor(self): return _Cursor()
    payload = add_roadmap_task_dependency(_Conn(), "rt-1", "rt-2")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["reason"] == "dependency_already_exists"


def test_add_roadmap_task_dependency_creates_row(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            {"id": "rt-1", "project_id": "project-aresforge", "title": "T1", "status": "planned"},
            {"id": "rt-2", "project_id": "project-aresforge", "title": "T2", "status": "planned"},
            None,
            {"task_id": "rt-1", "depends_on_task_id": "rt-2", "dependency_type": "blocks", "metadata": {}, "created_at": ""},
        ]
    )
    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchone(self): return next(responses, None)
    class _Conn:
        def cursor(self): return _Cursor()
    monkeypatch.setattr(repository_module, "add_roadmap_event", lambda *_args, **_kwargs: {"ok": True, "event_id": "ev-1"})
    payload = add_roadmap_task_dependency(_Conn(), "rt-1", "rt-2")
    assert payload["ok"] is True
    assert payload["changed"] is True


def test_remove_roadmap_task_dependency_missing_is_idempotent() -> None:
    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchone(self): return None
    class _Conn:
        def cursor(self): return _Cursor()
    payload = remove_roadmap_task_dependency(_Conn(), "rt-1", "rt-2")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["reason"] == "dependency_not_found"


def test_remove_roadmap_task_dependency_removes_row(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            {"task_id": "rt-1", "depends_on_task_id": "rt-2", "dependency_type": "blocks", "metadata": {}, "created_at": ""},
            {"project_id": "project-aresforge"},
        ]
    )
    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchone(self): return next(responses, None)
    class _Conn:
        def cursor(self): return _Cursor()
    monkeypatch.setattr(repository_module, "add_roadmap_event", lambda *_args, **_kwargs: {"ok": True, "event_id": "ev-2"})
    payload = remove_roadmap_task_dependency(_Conn(), "rt-1", "rt-2")
    assert payload["ok"] is True
    assert payload["changed"] is True


def test_inspect_roadmap_task_dependencies_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        {
            "task_id": "rt-04-starter",
            "task_title": "Task 4",
            "task_status": "planned",
            "depends_on_task_id": "rt-03-starter",
            "depends_on_task_title": "Task 3",
            "depends_on_task_status": "active",
            "dependency_type": "blocks",
            "metadata": {},
            "created_at": "",
        }
    ]
    class _Cursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return None
        def execute(self, _sql: str, _params: object = None) -> None: return None
        def fetchall(self): return rows
    class _Conn:
        def cursor(self): return _Cursor()
    payload = inspect_roadmap_task_dependencies(_Conn(), task_id="rt-04-starter")
    assert payload["ok"] is True
    assert payload["dependency_count"] == 1
    assert payload["dependencies"][0]["satisfied"] is False


def test_render_roadmap_work_item_links_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "link_count": 1,
        "links": [
            {
                "id": "rwil-1",
                "roadmap_task_id": "rt-01-starter",
                "work_item_id": "work-1",
                "status": "active",
                "queue_id": "queue-planning",
                "roadmap_task_title": "Plan foundational state authority",
                "work_item_title": "Plan foundational state authority",
            }
        ],
    }
    markdown = render_roadmap_work_item_links_markdown(payload)
    assert "# Roadmap Work Item Links" in markdown
    assert "- Project ID: `project-aresforge`" in markdown
    assert "- Link count: `1`" in markdown
    assert "task=`rt-01-starter` -> work_item=`work-1`" in markdown


def test_render_work_item_lifecycle_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "work_item_id": "work-1",
        "work_item": {"id": "work-1", "status": "queued", "queue_id": "queue-planning", "route_status": "queued"},
        "roadmap_links": [{"id": "rwil-1", "roadmap_task_id": "rt-01-starter", "status": "active"}],
        "roadmap_events": [{"created_at": "2026-05-25T12:00:00Z", "event_type": "work_item_status_changed", "task_id": "rt-01-starter"}],
        "audit_events": [{"created_at": "2026-05-25T12:00:01Z", "event_type": "work_item_status_changed", "actor": "aresforge-cli"}],
    }
    markdown = render_work_item_lifecycle_markdown(payload)
    assert "# Work Item Lifecycle" in markdown
    assert "- Work Item ID: `work-1`" in markdown
    assert "## Roadmap Links" in markdown
    assert "## Audit Events" in markdown
    assert "## Roadmap Events" in markdown


def test_render_queue_work_state_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "queue_id": None,
        "counts_by_queue": [{"queue_id": "queue-planning", "count": 2}],
        "counts_by_status": [{"status": "active", "count": 1}, {"status": "queued", "count": 1}],
        "work_items": [{"id": "work-1", "queue_id": "queue-planning", "status": "queued", "title": "Work title"}],
    }
    markdown = render_queue_work_state_markdown(payload)
    assert "# Queue Work State" in markdown
    assert "- Project ID: `project-aresforge`" in markdown
    assert "## Counts by Queue" in markdown
    assert "## Counts by Status" in markdown
    assert "## Active Queued Blocked Work Items" in markdown


def test_inspect_work_item_readiness_returns_missing_shape_when_work_item_is_missing() -> None:
    payload = inspect_work_item_readiness(_MissingRoadmapTaskConnection(), "work-missing")
    assert payload["ok"] is False
    assert payload["error"] == "work_item_not_found"
    assert payload["readiness_status"] == "missing"
    assert payload["ready"] is False
    assert payload["work_item_id"] == "work-missing"


class _ReadinessActiveCursor:
    def __init__(self) -> None:
        self._rows: list[dict[str, object]] = []
        self._row: dict[str, object] | None = None

    def __enter__(self) -> _ReadinessActiveCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        if "FROM work_items wi" in sql and "WHERE wi.id = %s" in sql:
            self._row = {
                "id": "work-1",
                "title": "Active work",
                "description": "Test",
                "status": "active",
                "priority": "normal",
                "route_status": "queued",
                "queue_id": "queue-planning",
                "agent_id": None,
                "model_id": None,
                "prompt_id": None,
                "metadata": {
                    "roadmap_task_id": "rt-04-starter",
                    "roadmap_task_status": "planned",
                    "roadmap_milestone_id": "rm-04-hub-workbench",
                },
                "created_at": "",
                "updated_at": "",
                "queue_name": "planning",
                "queue_purpose": "Planning",
                "queue_metadata": {},
                "agent_name": None,
                "model_name": None,
                "model_provider": None,
            }
            self._rows = []
            return
        if "FROM roadmap_work_item_links rwil" in sql:
            self._rows = [
                {
                    "id": "rwil-1",
                    "project_id": "project-aresforge",
                    "roadmap_task_id": "rt-04-starter",
                    "work_item_id": "work-1",
                    "link_type": "implements",
                    "status": "active",
                    "metadata": {},
                    "created_at": "",
                    "updated_at": "",
                    "roadmap_task_title": "Task title",
                    "roadmap_task_status": "planned",
                }
            ]
            self._row = None
            return
        if "FROM audit_events" in sql and "COUNT(*) AS count" in sql:
            self._row = {"count": 2}
            self._rows = []
            return
        if "FROM roadmap_task_dependencies d" in sql:
            self._rows = [
                {
                    "task_id": "rt-04-starter",
                    "depends_on_task_id": "rt-03-starter",
                    "depends_on_task_status": "complete",
                }
            ]
            self._row = None
            return
        if "FROM roadmap_events" in sql and "COUNT(*) AS count" in sql:
            self._row = {"count": 3}
            self._rows = []
            return
        self._row = None
        self._rows = []

    def fetchone(self) -> dict[str, object] | None:
        return self._row

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class _ReadinessActiveConnection:
    def cursor(self) -> _ReadinessActiveCursor:
        return _ReadinessActiveCursor()


def test_inspect_work_item_readiness_active_still_includes_links_and_roadmap_event_counts() -> None:
    payload = inspect_work_item_readiness(_ReadinessActiveConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["readiness_status"] == "already_active"
    assert payload["ready"] is False
    assert payload["roadmap_links"] == [
        {
            "id": "rwil-1",
            "project_id": "project-aresforge",
            "roadmap_task_id": "rt-04-starter",
            "work_item_id": "work-1",
            "link_type": "implements",
            "status": "active",
            "metadata": {},
            "created_at": "",
            "updated_at": "",
            "roadmap_task_title": "Task title",
            "roadmap_task_status": "planned",
        }
    ]
    assert payload["related_events"]["audit_event_count"] == 2
    assert payload["related_events"]["roadmap_event_count"] == 3
    assert payload["dependency_summary"] == {
        "total_dependencies": 1,
        "unsatisfied_dependencies": [],
    }


class _ReadinessBlockedDependencyCursor:
    def __init__(self) -> None:
        self._rows: list[dict[str, object]] = []
        self._row: dict[str, object] | None = None

    def __enter__(self) -> "_ReadinessBlockedDependencyCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        if "FROM work_items wi" in sql and "WHERE wi.id = %s" in sql:
            self._row = {
                "id": "work-1",
                "title": "Queued work",
                "description": "Test",
                "status": "queued",
                "priority": "normal",
                "route_status": "queued",
                "queue_id": "queue-implementation",
                "agent_id": None,
                "model_id": None,
                "prompt_id": None,
                "metadata": {},
                "created_at": "",
                "updated_at": "",
                "queue_name": "implementation",
                "queue_purpose": "Implementation",
                "queue_metadata": {},
                "agent_name": None,
                "model_name": None,
                "model_provider": None,
            }
            self._rows = []
            return
        if "FROM roadmap_work_item_links rwil" in sql:
            self._rows = [
                {
                    "id": "rwil-1",
                    "project_id": "project-aresforge",
                    "roadmap_task_id": "rt-04-starter",
                    "work_item_id": "work-1",
                    "link_type": "implements",
                    "status": "active",
                    "metadata": {},
                    "created_at": "",
                    "updated_at": "",
                    "roadmap_task_title": "Task title",
                    "roadmap_task_status": "planned",
                }
            ]
            self._row = None
            return
        if "FROM audit_events" in sql and "COUNT(*) AS count" in sql:
            self._row = {"count": 1}
            self._rows = []
            return
        if "FROM roadmap_task_dependencies d" in sql:
            self._rows = [
                {
                    "task_id": "rt-04-starter",
                    "depends_on_task_id": "rt-03-starter",
                    "depends_on_task_status": "active",
                }
            ]
            self._row = None
            return
        if "FROM roadmap_events" in sql and "COUNT(*) AS count" in sql:
            self._row = {"count": 1}
            self._rows = []
            return
        self._row = None
        self._rows = []

    def fetchone(self) -> dict[str, object] | None:
        return self._row

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


class _ReadinessBlockedDependencyConnection:
    def cursor(self) -> _ReadinessBlockedDependencyCursor:
        return _ReadinessBlockedDependencyCursor()


def test_inspect_work_item_readiness_unsatisfied_dependency_blocks_item() -> None:
    payload = inspect_work_item_readiness(_ReadinessBlockedDependencyConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["readiness_status"] == "blocked"
    assert payload["ready"] is False
    assert payload["dependency_summary"]["unsatisfied_dependencies"] == [
        {
            "task_id": "rt-04-starter",
            "depends_on_task_id": "rt-03-starter",
            "status": "active",
        }
    ]


def test_render_work_item_readiness_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "work_item_id": "work-1",
        "ready": False,
        "readiness_status": "blocked",
        "next_safe_action": "Resolve blockers before starting.",
        "blockers": [{"code": "unsatisfied_roadmap_dependencies", "dependencies": [{"task_id": "rt-2", "depends_on_task_id": "rt-1", "status": "active"}]}],
        "warnings": [],
        "work_item": {"id": "work-1", "status": "queued"},
        "roadmap_links": [{"id": "rwil-1", "roadmap_task_id": "rt-2", "roadmap_task_status": "active", "status": "active"}],
        "dependency_summary": {"total_dependencies": 1, "unsatisfied_dependencies": [{"task_id": "rt-2", "depends_on_task_id": "rt-1", "status": "active"}]},
    }
    markdown = render_work_item_readiness_markdown(payload)
    assert "# Work Item Readiness" in markdown
    assert "- Work item ID: `work-1`" in markdown
    assert "## Blockers" in markdown
    assert "## Roadmap Links" in markdown
    assert "## Dependencies" in markdown
    assert "depends_on=`rt-1` status=`active`" in markdown


def test_render_queue_readiness_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "queue_id": "queue-planning",
        "total_items": 2,
        "counts": {
            "ready": 1,
            "not_ready": 0,
            "blocked": 1,
            "already_active": 0,
            "already_complete": 0,
            "cancelled": 0,
            "missing": 0,
        },
        "next_ready_work_items": [{"work_item_id": "work-1", "next_safe_action": "Start work item or assign to operator.", "work_item": {"queue_id": "queue-planning", "status": "queued"}}],
        "blocked_work_items": [{"work_item_id": "work-2", "blockers": [{"code": "unsatisfied_roadmap_dependencies"}]}],
    }
    markdown = render_queue_readiness_markdown(payload)
    assert "# Queue Readiness" in markdown
    assert "- `ready`: `1`" in markdown
    assert "## Next Ready Work Items" in markdown
    assert "## Blocked Work Items" in markdown


def test_render_start_work_item_markdown_is_deterministic() -> None:
    payload = {
        "ok": False,
        "changed": False,
        "work_item_id": "work-1",
        "readiness_status": "blocked",
        "reason": "work_item_not_ready",
        "next_safe_action": "Resolve blockers before starting.",
        "readiness": {"blockers": [{"code": "unsatisfied_roadmap_dependencies"}]},
        "roadmap_links": [{"id": "rwil-1", "roadmap_task_id": "rt-1", "status": "active"}],
    }
    markdown = render_start_work_item_markdown(payload)
    assert "# Start Work Item" in markdown
    assert "- Work item ID: `work-1`" in markdown
    assert "- Changed: `False`" in markdown
    assert "## Blockers" in markdown
    assert "unsatisfied_roadmap_dependencies" in markdown
    assert "## Roadmap Links" in markdown


def test_render_work_item_queue_transition_plan_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "work_item_id": "work-1",
        "can_transition": False,
        "transition_status": "blocked",
        "reason": "target_queue_not_allowed",
        "next_safe_action": "Choose one of the allowed next queues.",
        "blockers": [{"code": "target_queue_not_allowed", "current_queue_id": "queue-planning", "target_queue_id": "queue-testing"}],
        "current_queue": {"id": "queue-planning"},
        "target_queue": {"id": "queue-testing"},
        "allowed_next_queues": ["queue-triage", "queue-blocked"],
        "readiness": {"readiness_status": "ready", "ready": True, "next_safe_action": "Start work item or assign to operator."},
    }
    markdown = render_work_item_queue_transition_plan_markdown(payload)
    assert "# Queue Transition Plan" in markdown
    assert "- Work item ID: `work-1`" in markdown
    assert "## Allowed Next Queues" in markdown
    assert "## Readiness" in markdown
    assert "target_queue_not_allowed" in markdown


def test_render_move_work_item_queue_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "previous_queue_id": "queue-planning",
        "new_queue_id": "queue-triage",
        "transition_status": "moved",
        "reason": "transition_applied",
        "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
        "blockers": [],
    }
    markdown = render_move_work_item_queue_markdown(payload)
    assert "# Move Work Item Queue" in markdown
    assert "- Changed: `True`" in markdown
    assert "- Previous queue: `queue-planning`" in markdown
    assert "- New queue: `queue-triage`" in markdown


def test_render_work_item_execution_dossier_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "work_item_id": "work-1",
        "dossier_status": "active",
        "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
        "work_item": {"id": "work-1", "status": "active", "queue_id": "queue-triage"},
        "readiness": {"readiness_status": "already_active", "ready": False},
        "operator_summary": {
            "status_line": "Work item is active in queue-triage.",
            "queue_line": "Current queue: queue-triage.",
            "readiness_line": "Readiness is already_active.",
            "dependency_line": "No unsatisfied roadmap dependencies.",
            "event_line": "Related events: 1 audit, 1 roadmap.",
            "recommended_next_step": "Next safe action: Inspect queue readiness or continue work item lifecycle.",
        },
        "blockers": [],
        "warnings": [],
        "roadmap_links": [],
        "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
        "queue_transition_options": [
            {
                "target_queue_id": "queue-blocked",
                "can_transition": True,
                "transition_status": "ready",
                "reason": "transition_allowed",
                "next_safe_action": "Move work item to target queue.",
            }
        ],
        "related_events": {"audit_event_count": 1, "roadmap_event_count": 1},
        "suggested_operator_prompt": "Continue AresForge work item work-1.",
    }
    markdown = render_work_item_execution_dossier_markdown(payload)
    assert "# Work Item Execution Dossier" in markdown
    assert "- Dossier status: `active`" in markdown
    assert "## Queue Transition Options" in markdown
    assert "target=`queue-blocked`" in markdown
    assert "## Suggested Operator Prompt" in markdown


def test_render_implementation_handoff_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "previous_queue_id": "queue-triage",
        "new_queue_id": "queue-implementation",
        "transition_status": "moved",
        "reason": "transition_applied",
        "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
        "move_result": {"ok": True, "changed": True},
        "dossier": {
            "dossier_status": "active",
            "work_item": {"status": "active", "queue_id": "queue-implementation"},
            "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
            "suggested_operator_prompt": "Continue AresForge work item work-1.",
        },
    }
    markdown = render_implementation_handoff_markdown(payload)
    assert "# Implementation Handoff" in markdown
    assert "- Work item ID: `work-1`" in markdown
    assert "## Move Result" in markdown
    assert "## Execution Dossier Summary" in markdown
    assert "## Suggested Operator Prompt" in markdown


def test_render_project_queue_dashboard_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "project_id": "project-aresforge",
        "dashboard_status": "ready",
        "totals": {"total_work_items": 2, "active": 1, "blocked": 0, "ready": 1},
        "queue_summaries": [
            {
                "queue_id": "queue-implementation",
                "queue_name": "implementation",
                "status": "active",
                "total_items": 1,
                "next_ready_work_items": [],
                "blocked_work_items": [],
            }
        ],
        "active_work_items": [{"work_item_id": "work-1", "queue_id": "queue-implementation", "status": "active", "readiness_status": "already_active", "roadmap_task_id": "rt-1"}],
        "ready_work_items": [{"work_item_id": "work-2", "queue_id": "queue-triage", "status": "queued", "readiness_status": "ready", "roadmap_task_id": "rt-2"}],
        "blocked_work_items": [],
        "roadmap_summary": {"total_areas": 1, "total_milestones": 1, "total_tasks": 2, "tasks_by_status": {"planned": 1, "active": 1, "blocked": 0, "complete": 0, "cancelled": 0}},
        "recent_events_summary": {"audit_event_count": 2, "roadmap_event_count": 3, "recent_audit_events": [], "recent_roadmap_events": []},
        "next_safe_actions": ["Inspect queue readiness before mutating queue placement."],
    }
    markdown = render_project_queue_dashboard_markdown(payload)
    assert "# Project Queue Dashboard" in markdown
    assert "- Project ID: `project-aresforge`" in markdown
    assert "## Queue Summaries" in markdown
    assert "queue-implementation" in markdown
    assert "## Next Safe Actions" in markdown


def test_render_export_work_item_operator_prompt_markdown_is_deterministic() -> None:
    payload = {
        "ok": True,
        "changed": True,
        "work_item_id": "work-1",
        "output_path": "artifacts/work-1.txt",
        "dossier_status": "active",
        "reason": "output_file_written",
        "bytes_written": 42,
        "suggested_operator_prompt": "Continue AresForge work item work-1.",
    }
    markdown = render_export_work_item_operator_prompt_markdown(payload)
    assert "# Export Work Item Operator Prompt" in markdown
    assert "- Work item ID: `work-1`" in markdown
    assert "## Suggested Operator Prompt Preview" in markdown


def test_build_work_item_execution_dossier_missing_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda *_args, **_kwargs: {
            "ok": False,
            "work_item_id": "work-missing",
            "project_id": "project-aresforge",
            "readiness_status": "missing",
            "ready": False,
            "next_safe_action": "Create or inspect the local work item before starting.",
            "blockers": [{"code": "work_item_not_found"}],
            "warnings": [],
            "work_item": None,
            "roadmap_links": [],
            "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
        },
    )
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_lifecycle",
        lambda *_args, **_kwargs: {"ok": False, "error": "work_item_not_found"},
    )
    payload = build_work_item_execution_dossier(_FakeConnection(), "work-missing")
    assert payload["ok"] is False
    assert payload["dossier_status"] == "missing"
    assert payload["queue_transition_options"] == []


def test_build_work_item_execution_dossier_active_maps_status_and_queue_options_sorted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda *_args, **_kwargs: {
            "ok": True,
            "work_item_id": "work-1",
            "project_id": "project-aresforge",
            "readiness_status": "already_active",
            "ready": False,
            "next_safe_action": "Continue or inspect active work item.",
            "blockers": [],
            "warnings": [],
            "work_item": {
                "id": "work-1",
                "title": "Active work",
                "status": "active",
                "queue_id": "queue-triage",
                "queue_allowed_next_queues": ["queue-blocked", "queue-implementation"],
            },
            "roadmap_links": [
                {
                    "id": "rwil-1",
                    "roadmap_task_id": "rt-1",
                    "roadmap_task_title": "Task",
                    "roadmap_task_status": "planned",
                    "status": "active",
                }
            ],
            "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
        },
    )
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_lifecycle",
        lambda *_args, **_kwargs: {
            "ok": True,
            "roadmap_events": [{"id": "re-1"}],
            "audit_events": [{"id": "ae-1"}],
        },
    )
    monkeypatch.setattr(repository_module, "inspect_queue", lambda *_args, **_kwargs: {"id": "queue-triage"})

    def fake_plan(_conn: object, _work_item_id: str, target_queue_id: str) -> dict[str, object]:
        return {
            "can_transition": target_queue_id != "queue-blocked",
            "transition_status": "blocked" if target_queue_id == "queue-blocked" else "ready",
            "reason": "target_queue_not_allowed" if target_queue_id == "queue-blocked" else "transition_allowed",
            "next_safe_action": "Choose one of the allowed next queues."
            if target_queue_id == "queue-blocked"
            else "Move work item to target queue.",
        }

    monkeypatch.setattr(repository_module, "plan_work_item_queue_transition", fake_plan)

    payload = build_work_item_execution_dossier(_FakeConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["dossier_status"] == "active"
    assert [row["target_queue_id"] for row in payload["queue_transition_options"]] == [
        "queue-blocked",
        "queue-implementation",
    ]


def test_build_work_item_execution_dossier_ready_maps_to_ready_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda *_args, **_kwargs: {
            "ok": True,
            "work_item_id": "work-2",
            "project_id": "project-aresforge",
            "readiness_status": "ready",
            "ready": True,
            "next_safe_action": "Start work item or assign to operator.",
            "blockers": [],
            "warnings": [],
            "work_item": {
                "id": "work-2",
                "title": "Ready work",
                "status": "queued",
                "queue_id": "queue-planning",
                "queue_allowed_next_queues": [],
            },
            "roadmap_links": [],
            "dependency_summary": {"total_dependencies": 0, "unsatisfied_dependencies": []},
        },
    )
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_lifecycle",
        lambda *_args, **_kwargs: {"ok": True, "roadmap_events": [], "audit_events": []},
    )
    payload = build_work_item_execution_dossier(_FakeConnection(), "work-2")
    assert payload["dossier_status"] == "ready_to_start"
    assert "```" not in payload["suggested_operator_prompt"]
    assert "work locally only" in payload["suggested_operator_prompt"]
    assert "do not call GitHub" in payload["suggested_operator_prompt"]

def test_start_work_item_if_ready_missing_is_non_mutating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda _conn, _work_item_id: {
            "ok": False,
            "work_item_id": "work-missing",
            "readiness_status": "missing",
            "ready": False,
            "next_safe_action": "Create or inspect the local work item before starting.",
            "blockers": [{"code": "work_item_not_found"}],
            "roadmap_links": [],
        },
    )
    payload = start_work_item_if_ready(_FakeConnection(), "work-missing")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["readiness_status"] == "missing"
    assert payload["reason"] == "work_item_not_found"


def test_start_work_item_if_ready_already_active_is_non_mutating(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda _conn, _work_item_id: {
            "ok": True,
            "work_item_id": "work-1",
            "readiness_status": "already_active",
            "ready": False,
            "next_safe_action": "Continue or inspect active work item.",
            "blockers": [],
            "roadmap_links": [],
        },
    )
    payload = start_work_item_if_ready(_FakeConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["readiness_status"] == "already_active"
    assert payload["reason"] == "already_active"


def test_start_work_item_if_ready_not_ready_missing_link_does_not_mutate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda _conn, _work_item_id: {
            "ok": True,
            "work_item_id": "work-2",
            "readiness_status": "not_ready",
            "ready": False,
            "next_safe_action": "Create or restore a roadmap work item link before starting.",
            "blockers": [{"code": "missing_roadmap_link"}],
            "roadmap_links": [],
        },
    )
    payload = start_work_item_if_ready(_FakeConnection(), "work-2")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "work_item_not_ready"


def test_start_work_item_if_ready_ready_starts_and_logs_events(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item_readiness",
        lambda _conn, _work_item_id: {
            "ok": True,
            "work_item_id": "work-3",
            "project_id": "project-aresforge",
            "readiness_status": "ready",
            "ready": True,
            "next_safe_action": "Start work item or assign to operator.",
            "blockers": [],
            "roadmap_links": [{"id": "rwil-1", "roadmap_task_id": "rt-1", "status": "active"}],
        },
    )
    monkeypatch.setattr(
        repository_module,
        "update_work_item_status",
        lambda *_args, **_kwargs: {
            "ok": True,
            "changed": True,
            "previous_status": "queued",
            "status": "active",
            "work_item_id": "work-3",
            "event_ids": ["audit-1", "roadmap-status-1"],
            "work_item": {"id": "work-3", "status": "active"},
        },
    )
    monkeypatch.setattr(
        repository_module,
        "add_roadmap_event",
        lambda *_args, **_kwargs: {"ok": True, "event_id": "roadmap-started-1"},
    )
    payload = start_work_item_if_ready(
        _FakeConnection(),
        "work-3",
        actor="local-test",
        details={"source": "unit-test"},
    )
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["previous_status"] == "queued"
    assert payload["new_status"] == "active"
    assert payload["readiness_status"] == "ready"
    assert payload["events"]["started_event_ids"] == ["roadmap-started-1"]


def test_move_work_item_queue_if_allowed_missing_work_item_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": False,
            "work_item_id": "work-missing",
            "can_transition": False,
            "transition_status": "missing",
            "reason": "work_item_not_found",
            "next_safe_action": "Create or inspect the local work item before moving queues.",
            "blockers": [{"code": "work_item_not_found"}],
        },
    )
    payload = move_work_item_queue_if_allowed(_FakeConnection(), "work-missing", "queue-triage")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "work_item_not_found"


def test_move_work_item_queue_if_allowed_missing_target_queue_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": False,
            "work_item_id": "work-1",
            "can_transition": False,
            "transition_status": "missing_target_queue",
            "reason": "target_queue_not_found",
            "next_safe_action": "Inspect available queues before moving work items.",
            "blockers": [{"code": "target_queue_not_found"}],
        },
    )
    payload = move_work_item_queue_if_allowed(_FakeConnection(), "work-1", "queue-missing")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["transition_status"] == "missing_target_queue"


def test_move_work_item_queue_if_allowed_already_in_target_queue_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": True,
            "work_item_id": "work-1",
            "can_transition": False,
            "transition_status": "already_in_target_queue",
            "reason": "already_in_target_queue",
            "next_safe_action": "No queue move needed.",
            "blockers": [],
        },
    )
    payload = move_work_item_queue_if_allowed(_FakeConnection(), "work-1", "queue-planning")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["reason"] == "already_in_target_queue"


def test_move_work_item_queue_if_allowed_target_queue_not_allowed_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": True,
            "work_item_id": "work-1",
            "can_transition": False,
            "transition_status": "blocked",
            "reason": "target_queue_not_allowed",
            "next_safe_action": "Choose one of the allowed next queues.",
            "blockers": [{"code": "target_queue_not_allowed"}],
        },
    )
    payload = move_work_item_queue_if_allowed(_FakeConnection(), "work-1", "queue-testing")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["reason"] == "target_queue_not_allowed"


class _QueueMoveCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self._row: dict[str, object] | None = None

    def __enter__(self) -> "_QueueMoveCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: object = None) -> None:
        self.executed.append((sql, params))
        if "FROM roadmap_work_item_links" in sql:
            self._row = {"id": "rwil-1", "roadmap_task_id": "rt-1"}
        else:
            self._row = None

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _QueueMoveConnection:
    def __init__(self) -> None:
        self.last_cursor: _QueueMoveCursor | None = None

    def cursor(self) -> _QueueMoveCursor:
        self.last_cursor = _QueueMoveCursor()
        return self.last_cursor


def test_move_work_item_queue_if_allowed_allowed_target_updates_and_logs_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": True,
            "work_item_id": "work-1",
            "project_id": "project-aresforge",
            "can_transition": True,
            "work_item": {"queue_id": "queue-planning"},
        },
    )
    seen: dict[str, object] = {}

    def fake_add_roadmap_event(*_args, **kwargs):
        seen["event_type"] = kwargs.get("event_type")
        seen["task_id"] = kwargs.get("task_id")
        return {"ok": True, "event_id": "roadmap-queue-change-1"}

    monkeypatch.setattr(repository_module, "add_roadmap_event", fake_add_roadmap_event)

    conn = _QueueMoveConnection()
    payload = move_work_item_queue_if_allowed(conn, "work-1", "queue-triage", actor="local-test")

    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["previous_queue_id"] == "queue-planning"
    assert payload["new_queue_id"] == "queue-triage"
    assert payload["transition_status"] == "moved"
    assert seen["event_type"] == "work_item_queue_changed"
    assert seen["task_id"] == "rt-1"
    assert conn.last_cursor is not None
    executed_sql = "\n".join(sql for sql, _params in conn.last_cursor.executed)
    assert "UPDATE work_items" in executed_sql
    assert "INSERT INTO audit_events" in executed_sql


def test_handoff_work_item_to_implementation_missing_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repository_module, "inspect_work_item", lambda *_args, **_kwargs: None)
    payload = handoff_work_item_to_implementation(_FakeConnection(), "work-missing")
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "work_item_not_found"


def test_handoff_work_item_to_implementation_already_in_implementation_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item",
        lambda *_args, **_kwargs: {"id": "work-1", "queue_id": "queue-implementation"},
    )
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {"ok": True, "dossier_status": "active"},
    )
    payload = handoff_work_item_to_implementation(_FakeConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["reason"] == "already_in_implementation"
    assert payload["dossier"]["dossier_status"] == "active"


def test_handoff_work_item_to_implementation_blocked_transition_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item",
        lambda *_args, **_kwargs: {"id": "work-1", "queue_id": "queue-triage"},
    )
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {
            "ok": True,
            "can_transition": False,
            "transition_status": "blocked",
            "reason": "target_queue_not_allowed",
            "next_safe_action": "Choose one of the allowed next queues.",
            "blockers": [{"code": "target_queue_not_allowed"}],
        },
    )
    payload = handoff_work_item_to_implementation(_FakeConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["changed"] is False
    assert payload["transition_status"] == "blocked"
    assert payload["reason"] == "target_queue_not_allowed"


def test_handoff_work_item_to_implementation_allowed_moves_and_returns_dossier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_work_item",
        lambda *_args, **_kwargs: {"id": "work-1", "queue_id": "queue-triage"},
    )
    monkeypatch.setattr(
        repository_module,
        "plan_work_item_queue_transition",
        lambda *_args, **_kwargs: {"ok": True, "can_transition": True},
    )
    monkeypatch.setattr(
        repository_module,
        "move_work_item_queue_if_allowed",
        lambda *_args, **_kwargs: {
            "ok": True,
            "changed": True,
            "previous_queue_id": "queue-triage",
            "new_queue_id": "queue-implementation",
            "transition_status": "moved",
            "reason": "transition_applied",
            "next_safe_action": "Inspect queue readiness or continue work item lifecycle.",
        },
    )
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {
            "ok": True,
            "dossier_status": "active",
            "work_item": {"queue_id": "queue-implementation"},
        },
    )
    payload = handoff_work_item_to_implementation(_FakeConnection(), "work-1")
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["previous_queue_id"] == "queue-triage"
    assert payload["new_queue_id"] == "queue-implementation"
    assert payload["dossier"]["dossier_status"] == "active"


def test_cli_parser_recognizes_project_queue_dashboard_formats() -> None:
    parser = build_parser()
    dashboard_json_args = parser.parse_args(["inspect-project-queue-dashboard", "--format", "json"])
    assert dashboard_json_args.command == "inspect-project-queue-dashboard"
    assert dashboard_json_args.format == "json"
    dashboard_markdown_args = parser.parse_args(["inspect-project-queue-dashboard", "--format", "markdown"])
    assert dashboard_markdown_args.command == "inspect-project-queue-dashboard"
    assert dashboard_markdown_args.format == "markdown"


def test_cli_parser_recognizes_export_work_item_operator_prompt_formats() -> None:
    parser = build_parser()
    export_json_args = parser.parse_args(
        [
            "export-work-item-operator-prompt",
            "--work-item-id",
            "work-1",
            "--output",
            "artifacts/work-1.txt",
            "--format",
            "json",
        ]
    )
    assert export_json_args.command == "export-work-item-operator-prompt"
    assert export_json_args.format == "json"
    export_markdown_args = parser.parse_args(
        [
            "export-work-item-operator-prompt",
            "--work-item-id",
            "work-1",
            "--output",
            "artifacts/work-1.txt",
            "--force",
            "--format",
            "markdown",
        ]
    )
    assert export_markdown_args.command == "export-work-item-operator-prompt"
    assert export_markdown_args.force is True
    assert export_markdown_args.format == "markdown"


def test_export_work_item_operator_prompt_missing_does_not_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "operator-prompt.txt"
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {"ok": False, "dossier_status": "missing"},
    )
    payload = export_work_item_operator_prompt(_FakeConnection(), "work-missing", output_path)
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "work_item_not_found"
    assert not output_path.exists()


def test_export_work_item_operator_prompt_writes_file_and_content(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "operator-prompt.txt"
    prompt = "\n".join(
        [
            "Continue AresForge work item work-1.",
            "Current queue: queue-implementation",
            "Readiness status: already_active",
            "Dossier status: active",
            "Next safe action: Continue",
            "Constraints: work locally only; do not call GitHub;",
        ]
    )
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {
            "ok": True,
            "dossier_status": "active",
            "suggested_operator_prompt": prompt,
        },
    )
    payload = export_work_item_operator_prompt(_FakeConnection(), "work-1", output_path)
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["reason"] == "output_file_written"
    written = output_path.read_text(encoding="utf-8")
    assert "work locally only" in written
    assert "do not call GitHub" in written
    assert "```" not in written


def test_export_work_item_operator_prompt_existing_without_force_is_non_mutating(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "operator-prompt.txt"
    output_path.write_text("existing", encoding="utf-8")
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {
            "ok": True,
            "dossier_status": "active",
            "suggested_operator_prompt": "new prompt",
        },
    )
    payload = export_work_item_operator_prompt(_FakeConnection(), "work-1", output_path, force=False)
    assert payload["ok"] is False
    assert payload["changed"] is False
    assert payload["reason"] == "output_file_exists"
    assert output_path.read_text(encoding="utf-8") == "existing"


def test_export_work_item_operator_prompt_existing_with_force_overwrites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_path = tmp_path / "operator-prompt.txt"
    output_path.write_text("existing", encoding="utf-8")
    monkeypatch.setattr(
        repository_module,
        "build_work_item_execution_dossier",
        lambda *_args, **_kwargs: {
            "ok": True,
            "dossier_status": "active",
            "suggested_operator_prompt": "new prompt",
        },
    )
    payload = export_work_item_operator_prompt(_FakeConnection(), "work-1", output_path, force=True)
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["reason"] == "output_file_overwritten"
    assert output_path.read_text(encoding="utf-8") == "new prompt"


def test_inspect_project_queue_dashboard_empty_is_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repository_module, "inspect_queue_readiness", lambda *_args, **_kwargs: {"ok": True, "counts": {}, "work_items": []})
    monkeypatch.setattr(repository_module, "list_queues", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        repository_module,
        "_inspect_project_work_item_status_counts",
        lambda *_args, **_kwargs: (
            {},
            {"total_work_items": 0, "queued": 0, "active": 0, "blocked": 0, "complete": 0, "cancelled": 0},
        ),
    )
    monkeypatch.setattr(
        repository_module,
        "inspect_roadmap_db",
        lambda *_args, **_kwargs: {"counts": {"areas": 0, "milestones": 0, "tasks": 0}, "tasks": []},
    )
    monkeypatch.setattr(
        repository_module,
        "_inspect_recent_event_summary",
        lambda *_args, **_kwargs: {"audit_event_count": 0, "roadmap_event_count": 0, "recent_audit_events": [], "recent_roadmap_events": []},
    )
    payload = inspect_project_queue_dashboard(_FakeConnection())
    assert payload["ok"] is True
    assert payload["totals"]["total_work_items"] == 0
    assert payload["queue_summaries"] == []
    assert payload["active_work_items"] == []


def test_inspect_project_queue_dashboard_queue_summaries_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "inspect_queue_readiness",
        lambda _conn, queue_id=None, project_id="project-aresforge": {
            "ok": True,
            "counts": {"ready": 1, "already_active": 1} if queue_id is None else {"ready": 0, "already_active": 1},
            "work_items": [
                {
                    "work_item_id": "work-1",
                    "readiness_status": "already_active",
                    "ready": False,
                    "next_safe_action": "Continue.",
                    "work_item": {"id": "work-1", "title": "W1", "status": "active", "queue_id": "queue-implementation"},
                    "roadmap_links": [{"roadmap_task_id": "rt-1"}],
                }
            ]
            if queue_id == "queue-implementation"
            else [],
        },
    )
    monkeypatch.setattr(
        repository_module,
        "list_queues",
        lambda *_args, **_kwargs: [
            {"id": "queue-triage", "name": "triage", "status": "active", "purpose": "triage", "allowed_next_queues": ["queue-implementation"]},
            {"id": "queue-implementation", "name": "implementation", "status": "active", "purpose": "impl", "allowed_next_queues": ["queue-verification"]},
        ],
    )
    monkeypatch.setattr(
        repository_module,
        "_inspect_project_work_item_status_counts",
        lambda *_args, **_kwargs: (
            {
                "queue-implementation": {"queued": 0, "active": 1, "blocked": 0, "complete": 0, "cancelled": 0},
                "queue-triage": {"queued": 1, "active": 0, "blocked": 0, "complete": 0, "cancelled": 0},
            },
            {"total_work_items": 2, "queued": 1, "active": 1, "blocked": 0, "complete": 0, "cancelled": 0},
        ),
    )
    monkeypatch.setattr(
        repository_module,
        "inspect_roadmap_db",
        lambda *_args, **_kwargs: {"counts": {"areas": 1, "milestones": 1, "tasks": 1}, "tasks": [{"status": "planned"}]},
    )
    monkeypatch.setattr(
        repository_module,
        "_inspect_recent_event_summary",
        lambda *_args, **_kwargs: {"audit_event_count": 1, "roadmap_event_count": 1, "recent_audit_events": [], "recent_roadmap_events": []},
    )
    payload = inspect_project_queue_dashboard(_FakeConnection())
    assert [row["queue_id"] for row in payload["queue_summaries"]] == [
        "queue-implementation",
        "queue-triage",
    ]
    assert payload["totals"]["active"] == 1


def test_plan_work_item_queue_transition_missing_work_item_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repository_module, "inspect_work_item", lambda *_args, **_kwargs: None)
    payload = plan_work_item_queue_transition(_FakeConnection(), "work-missing", "queue-triage")
    assert payload["ok"] is False
    assert payload["can_transition"] is False
    assert payload["transition_status"] == "missing"
    assert payload["reason"] == "work_item_not_found"
