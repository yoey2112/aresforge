import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import (
    add_queue_item,
    capture_local_queue_completion_evidence,
    close_local_queue_item,
    init_project_queue,
    start_local_queue_item,
)
from aresforge.operator.queue_transaction_log import inspect_queue_transaction_log
from aresforge.operator.managed_project_registry_local import (
    init_managed_project_registry,
    register_managed_project,
    register_managed_repo,
)


def _config(tmp_path: Path) -> AppConfig:
    artifact_root = tmp_path / "artifacts"
    return AppConfig(
        repo_root=tmp_path,
        db_host="127.0.0.1",
        db_port=5433,
        db_name="aresforge",
        db_user="aresforge",
        db_password="aresforge",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen2.5:32b",
        artifact_root=artifact_root,
        prompts_dir=artifact_root / "prompts" / "generated",
        evidence_dir=artifact_root / "evidence" / "generated",
        codex_handoffs_dir=artifact_root / "codex_handoffs" / "generated",
        github_owner="local",
        github_repo="aresforge",
    )


def test_queue_transaction_log_is_created_when_item_is_added(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True

    payload = add_queue_item(
        config,
        item_id="m122-log-create",
        project_id="aresforge",
        repo_id="aresforge-primary",
        title="Create transaction log",
        status="ready",
    )
    log_path = tmp_path / ".aresforge" / "queue" / "transaction_log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))

    assert payload["ok"] is True
    assert payload["warnings"] == ["Managed project registry not found. Registry validation was skipped."]
    assert log["log_type"] == "queue_mutation_transaction_log"
    assert len(log["transactions"]) == 1
    transaction = log["transactions"][0]
    assert transaction["item_id"] == "m122-log-create"
    assert transaction["project_id"] == "aresforge"
    assert transaction["previous_status"] == ""
    assert transaction["new_status"] == "ready"
    assert transaction["mutation_type"] == "propose"
    assert transaction["local_only"] is True
    assert transaction["execution_allowed"] is False


def test_queue_transaction_log_appends_start_evidence_and_closeout(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True
    assert init_managed_project_registry(config)["ok"] is True
    assert register_managed_project(
        config,
        project_id="aresforge",
        name="AresForge",
        root_path=str(tmp_path),
        primary_repo_id="aresforge-primary",
    )["ok"] is True
    assert register_managed_repo(
        config,
        project_id="aresforge",
        repo_id="aresforge-primary",
        name="AresForge",
        path=str(tmp_path),
        role="primary",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id="m122-log-append",
        project_id="aresforge",
        repo_id="aresforge-primary",
        title="Append transactions",
        description="Exercise local transaction append behavior.",
        status="proposed",
    )["ok"] is True
    assert start_local_queue_item(config, item_id="m122-log-append", started_via="tester")["ok"] is True
    assert capture_local_queue_completion_evidence(
        config,
        item_id="m122-log-append",
        evidence_summary="Validation passed locally.",
        validation_results=["pytest -> passed"],
        diff_check_result="git diff --check -> pass",
        review_evidence=["Operator reviewed transaction evidence."],
    )["ok"] is True
    assert close_local_queue_item(
        config,
        item_id="m122-log-append",
        closeout_summary="Evidence reviewed.",
        closed_by="tester",
    )["ok"] is True

    payload = inspect_queue_transaction_log(config, project_id="aresforge", output_format="json")
    parsed = json.loads(payload["stdout"])
    mutation_types = [entry["mutation_type"] for entry in parsed["transactions"]]

    assert parsed["log_type"] == "queue_mutation_transaction_log"
    assert parsed["transaction_count"] == 4
    assert mutation_types == ["propose", "start", "record_validation_evidence", "closeout"]
    assert parsed["latest_transaction_by_item"]["m122-log-append"]["mutation_type"] == "closeout"
    assert parsed["local_only"] is True
    assert parsed["execution_allowed"] is False


def test_queue_transaction_log_inspection_filters_by_item_and_project(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert init_project_queue(config)["ok"] is True
    for item_id, project_id in (("m122-project-a", "aresforge"), ("m122-project-b", "other-project")):
        assert add_queue_item(
            config,
            item_id=item_id,
            project_id=project_id,
            repo_id="repo-main",
            title=f"{item_id} title",
            status="ready",
        )["ok"] is True

    by_project = json.loads(inspect_queue_transaction_log(config, project_id="aresforge")["stdout"])
    by_item = json.loads(
        inspect_queue_transaction_log(config, project_id="aresforge", item_id="m122-project-a")["stdout"]
    )

    assert by_project["transaction_count"] == 1
    assert by_project["transactions"][0]["item_id"] == "m122-project-a"
    assert by_item["transaction_count"] == 1
    assert by_item["item_id"] == "m122-project-a"
    assert "m122-project-a" in by_item["latest_transaction_by_item"]


def test_queue_transaction_log_handles_missing_log_for_backward_compatibility(tmp_path: Path) -> None:
    config = _config(tmp_path)

    payload = inspect_queue_transaction_log(config, project_id="aresforge")
    parsed = json.loads(payload["stdout"])

    assert payload["ok"] is True
    assert parsed["transaction_count"] == 0
    assert parsed["transactions"] == []
    assert parsed["latest_transaction_by_item"] == {}
    assert "Queue transaction log file does not exist yet." in parsed["mutation_warnings"]
    assert parsed["next_safe_action"].startswith("Review transaction log warnings")


def test_queue_transaction_log_output_path_requires_force(tmp_path: Path) -> None:
    config = _config(tmp_path)
    output_path = tmp_path / "artifacts" / "transaction-log.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text("existing\n", encoding="utf-8")

    blocked = inspect_queue_transaction_log(
        config,
        project_id="aresforge",
        output=output_path,
        output_format="json",
    )
    written = inspect_queue_transaction_log(
        config,
        project_id="aresforge",
        output=output_path,
        force=True,
        output_format="json",
    )

    assert blocked["ok"] is False
    assert blocked["error"] == "output_exists"
    assert written["ok"] is True
    assert written["wrote_output_file"] is True
    assert json.loads(output_path.read_text(encoding="utf-8"))["log_type"] == "queue_mutation_transaction_log"
