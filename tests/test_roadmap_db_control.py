from __future__ import annotations

from aresforge.cli import build_parser
from aresforge.db.repository import (
    ROADMAP_ALLOWED_STATUSES,
    ROADMAP_SEED_AREAS,
    ROADMAP_SEED_MILESTONES,
    WORK_ITEM_ALLOWED_STATUSES,
    create_work_item_from_roadmap_task,
    inspect_roadmap_db,
    inspect_work_item_readiness,
    render_queue_work_state_markdown,
    render_queue_readiness_markdown,
    render_roadmap_events_markdown,
    render_work_item_readiness_markdown,
    render_work_item_lifecycle_markdown,
    render_roadmap_markdown,
    render_roadmap_work_item_links_markdown,
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
