from pathlib import Path

from aresforge.operator.registry_inspection import (
    AGENT_REGISTRY_SOURCE_DOCUMENT,
    DEFAULT_REGISTRY_INSPECTION_SPECS,
    PROJECT_REGISTRY_SOURCE_DOCUMENT,
    WORK_ITEM_LIFECYCLE_SOURCE_DOCUMENT,
    inspect_local_registries,
)
from aresforge.validation import ValidationFinding, ValidationReport


def _write_text(root: Path, relative_path: str, content: str) -> None:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _write_registry_fixture_documents(root: Path) -> None:
    content_by_path: dict[str, list[str]] = {}
    for spec in DEFAULT_REGISTRY_INSPECTION_SPECS:
        content_by_path.setdefault(spec.source_document, []).extend(spec.required_markers)
    for relative_path, markers in content_by_path.items():
        ordered_unique_markers = list(dict.fromkeys(markers))
        _write_text(root, relative_path, "\n".join(ordered_unique_markers) + "\n")


def test_inspect_local_registries_summarizes_documented_sources(tmp_path: Path) -> None:
    _write_registry_fixture_documents(tmp_path)

    payload = inspect_local_registries(
        tmp_path,
        seed_validation_report=ValidationReport(ok=True, findings=()),
    )

    assert payload["ok"] is True
    assert payload["inspection_mode"] == "local_repo_only"
    assert payload["summary"]["registry_count"] == len(DEFAULT_REGISTRY_INSPECTION_SPECS)
    assert payload["summary"]["ok"] == len(DEFAULT_REGISTRY_INSPECTION_SPECS)
    assert [item["registry"] for item in payload["registries"]] == [
        "project_registry",
        "agent_registry",
        "model_registry",
        "queue_registry",
        "work_item_lifecycle",
    ]
    assert all(item["status"] == "ok" for item in payload["registries"])


def test_inspect_local_registries_reports_missing_registry_files(tmp_path: Path) -> None:
    _write_text(
        tmp_path,
        PROJECT_REGISTRY_SOURCE_DOCUMENT,
        "# AresForge Project Registry Schema\n## Project Record Minimum Useful Schema\n`project_id`\n`autonomy_level`\n",
    )

    payload = inspect_local_registries(
        tmp_path,
        seed_validation_report=ValidationReport(ok=True, findings=()),
    )

    assert payload["ok"] is False
    assert payload["summary"]["missing"] == len(DEFAULT_REGISTRY_INSPECTION_SPECS) - 1
    assert payload["registries"][0]["status"] == "ok"
    assert any(item["status"] == "missing" for item in payload["registries"][1:])


def test_inspect_local_registries_reports_malformed_documents_and_seed_validation_findings(
    tmp_path: Path,
) -> None:
    for relative_path in {
        spec.source_document for spec in DEFAULT_REGISTRY_INSPECTION_SPECS
    }:
        _write_text(tmp_path, relative_path, "# placeholder\n")

    payload = inspect_local_registries(
        tmp_path,
        seed_validation_report=ValidationReport(
            ok=False,
            findings=(
                ValidationFinding(
                    severity="error",
                    code="agent.invalid_queue_participation",
                    message="Agent references unknown queue 'queue-not-real'.",
                    location="agents[agent-worker].metadata.queue_participation",
                ),
            ),
        ),
    )

    agent_registry = next(
        item for item in payload["registries"] if item["registry"] == "agent_registry"
    )
    project_registry = next(
        item for item in payload["registries"] if item["registry"] == "project_registry"
    )

    assert payload["ok"] is False
    assert project_registry["status"] == "malformed"
    assert project_registry["missing_markers"]
    assert agent_registry["status"] in {"malformed", "validation_problem"}
    assert payload["summary"]["problem_registry_count"] == len(DEFAULT_REGISTRY_INSPECTION_SPECS)


def test_inspect_local_registries_returns_deterministic_order_and_counts(tmp_path: Path) -> None:
    _write_registry_fixture_documents(tmp_path)

    payload = inspect_local_registries(
        tmp_path,
        seed_validation_report=ValidationReport(ok=True, findings=()),
    )

    assert [item["registry"] for item in payload["registries"]] == [
        spec.registry for spec in DEFAULT_REGISTRY_INSPECTION_SPECS
    ]
    assert payload["summary"] == {
        "registry_count": len(DEFAULT_REGISTRY_INSPECTION_SPECS),
        "ok": len(DEFAULT_REGISTRY_INSPECTION_SPECS),
        "missing": 0,
        "empty": 0,
        "malformed": 0,
        "read_error": 0,
        "validation_problem": 0,
        "problem_registry_count": 0,
    }


def test_inspect_local_registries_uses_queue_schema_for_work_item_lifecycle(tmp_path: Path) -> None:
    _write_registry_fixture_documents(tmp_path)

    payload = inspect_local_registries(
        tmp_path,
        seed_validation_report=ValidationReport(ok=True, findings=()),
    )

    work_item_registry = next(
        item for item in payload["registries"] if item["registry"] == "work_item_lifecycle"
    )

    assert work_item_registry["source_document"] == WORK_ITEM_LIFECYCLE_SOURCE_DOCUMENT
    assert work_item_registry["status"] == "ok"
    assert work_item_registry["exists"] is True


def test_inspect_local_registries_reports_empty_document(tmp_path: Path) -> None:
    _write_text(tmp_path, AGENT_REGISTRY_SOURCE_DOCUMENT, "")

    payload = inspect_local_registries(
        tmp_path,
        registry_specs=(
            next(
                spec
                for spec in DEFAULT_REGISTRY_INSPECTION_SPECS
                if spec.registry == "agent_registry"
            ),
        ),
        seed_validation_report=ValidationReport(ok=True, findings=()),
    )

    assert payload["ok"] is False
    assert payload["summary"]["empty"] == 1
    assert payload["registries"][0]["status"] == "empty"
