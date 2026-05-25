from __future__ import annotations

from aresforge.cli import build_parser
from aresforge.db.repository import (
    ROADMAP_ALLOWED_STATUSES,
    ROADMAP_SEED_AREAS,
    ROADMAP_SEED_MILESTONES,
    inspect_roadmap_db,
    render_roadmap_events_markdown,
    render_roadmap_markdown,
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

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, _params: object = None) -> None:
        if "FROM roadmap_areas" in sql:
            self._rows = [{"id": "a1", "project_id": "project-aresforge", "name": "Area", "description": "", "status": "planned", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            return
        if "FROM roadmap_milestones" in sql:
            self._rows = [{"id": "m1", "project_id": "project-aresforge", "area_id": "a1", "name": "Milestone", "description": "", "status": "planned", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            return
        if "FROM roadmap_tasks" in sql:
            self._rows = [{"id": "t1", "project_id": "project-aresforge", "milestone_id": "m1", "title": "Task", "description": "", "status": "planned", "priority": "normal", "sort_order": 1, "metadata": {}, "created_at": "", "updated_at": ""}]
            return
        if "FROM roadmap_task_dependencies" in sql:
            self._rows = [{"task_id": "t1", "depends_on_task_id": "t0", "dependency_type": "blocks", "metadata": {}, "created_at": ""}]
            return
        if "FROM roadmap_events" in sql:
            self._rows = [{"id": "e1", "project_id": "project-aresforge", "area_id": None, "milestone_id": None, "task_id": None, "event_type": "roadmap_seed", "actor": "aresforge-cli", "summary": "Seed", "details": {}, "created_at": ""}]
            return
        self._rows = []

    def fetchall(self) -> list[dict[str, object]]:
        return self._rows


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
