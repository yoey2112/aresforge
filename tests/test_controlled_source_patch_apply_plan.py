import json
from pathlib import Path

from aresforge.config import AppConfig
from aresforge.operator.local_project_queue import add_queue_item, init_project_queue
from aresforge.operator.source_patch_apply_plan import (
    DEFAULT_ITEM_ID,
    plan_source_patch_apply,
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


def _seed_queue(config: AppConfig) -> None:
    assert init_project_queue(config)["ok"] is True
    assert add_queue_item(
        config,
        item_id="m148-safe-source-patch-detection-and-risk-classifier",
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M148 Safe Source Patch Detection and Risk Classifier",
        description="Completed predecessor.",
        status="done",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m148"],
        source="unit-test",
        notes="Predecessor evidence present.",
    )["ok"] is True
    assert add_queue_item(
        config,
        item_id=DEFAULT_ITEM_ID,
        project_id="aresforge",
        repo_id="aresforge-main",
        title="M149 Controlled Source Patch Apply Plan",
        description="Plan controlled source patch application without applying patches.",
        status="ready",
        priority="high",
        item_type="orchestration",
        tags=["milestone:m149", "machine-gated"],
        dependencies=["m148-safe-source-patch-detection-and-risk-classifier"],
        source="unit-test",
        notes="Plan-only source patch apply boundary.",
    )["ok"] is True


def _write_patch(tmp_path: Path, text: str) -> Path:
    patch_path = tmp_path / "artifacts" / "manual" / "sample.patch"
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text(text, encoding="utf-8")
    return patch_path


def test_plan_source_patch_apply_generates_plan_without_applying(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/operator/example.py b/src/aresforge/operator/example.py
--- a/src/aresforge/operator/example.py
+++ b/src/aresforge/operator/example.py
@@ -1 +1,2 @@
 VALUE = "old"
+CONTROLLED_PATCH_PLAN = True
diff --git a/tests/test_example.py b/tests/test_example.py
--- a/tests/test_example.py
+++ b/tests/test_example.py
@@ -1 +1,2 @@
 def test_old():
+    assert True
""",
    )

    payload = plan_source_patch_apply(config, patch_path=patch_path)["payload"]

    assert payload["record_type"] == "source_patch_apply_plan_v1"
    assert payload["artifact_type"] == "source_patch_apply_plan_v1"
    assert payload["status"] == "planned"
    assert payload["blocked"] is False
    assert payload["machine_gates_passed"] is True
    assert payload["controlled_apply_plan_available"] is True
    assert payload["future_controlled_apply_eligible"] is True
    assert payload["automatic_apply_allowed"] is False
    assert payload["patch_application_performed"] is False
    assert payload["validation_command_execution_performed"] is False
    assert payload["mutation_performed"] is False
    assert payload["external_execution_performed"] is False
    assert payload["model_execution_performed"] is False
    assert payload["codex_execution_performed"] is False
    assert payload["github_execution_performed"] is False
    assert payload["local_only"] is True
    assert payload["source_classification"]["record_type"] == "source_patch_risk_classification_v1"
    assert payload["touched_files"] == [
        "src/aresforge/operator/example.py",
        "tests/test_example.py",
    ]
    assert payload["apply_plan_steps"][4]["step_id"] == "05_controlled_patch_apply"
    assert payload["apply_plan_steps"][4]["executed"] is False
    assert payload["apply_plan_steps"][4]["allowed_by_m149"] is False


def test_plan_source_patch_apply_blocks_missing_patch(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)

    result = plan_source_patch_apply(config, patch_path=tmp_path / "missing.patch")
    payload = result["payload"]

    assert result["ok"] is False
    assert payload["status"] == "blocked"
    assert payload["blocked"] is True
    assert any("Patch file is missing" in reason for reason in payload["blocked_reasons"])
    assert payload["patch_application_performed"] is False


def test_plan_source_patch_apply_marks_workflow_patch_apply_blocked(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -1 +1,2 @@
 name: ci
+on: push
""",
    )

    payload = plan_source_patch_apply(config, patch_path=patch_path)["payload"]

    assert payload["status"] == "apply_blocked"
    assert payload["blocked"] is False
    assert payload["controlled_apply_plan_available"] is False
    assert payload["future_controlled_apply_eligible"] is False
    assert "workflow_mutation" in payload["hard_apply_blockers"]
    assert payload["patch_application_performed"] is False


def test_plan_source_patch_apply_output_path_writes_artifact(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _seed_queue(config)
    patch_path = _write_patch(
        tmp_path,
        """diff --git a/src/aresforge/example.py b/src/aresforge/example.py
--- a/src/aresforge/example.py
+++ b/src/aresforge/example.py
@@ -1 +1,2 @@
 value = 1
+value = 2
""",
    )
    output = tmp_path / ".aresforge" / "source_patch_apply_plans" / "plan.json"

    result = plan_source_patch_apply(config, patch_path=patch_path, output=output)
    written = json.loads(output.read_text(encoding="utf-8"))

    assert result["ok"] is True
    assert result["wrote_output_file"] is True
    assert written["artifact_type"] == "source_patch_apply_plan_v1"
    assert str(output) in written["artifacts_created"]
